"""
GDELT collector for geopolitics and news sentiment factors.
"""

import logging
import time
from datetime import datetime, timedelta
from json import JSONDecodeError

from collector.base import FactorCollector
from collector.http_utils import get_shared_session
from collector.registry import get_factors_by_collector

logger = logging.getLogger("oilrisk.collector.gdelt")

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"

# GDELT 免费 API 限频较严，请求间至少间隔此秒数
_REQUEST_INTERVAL = 2.0
_last_request_time = 0.0

GEO_QUERIES = {
    "GEOPOLITICS_SCORE": {
        "query": "(oil OR crude OR petroleum OR energy) AND (conflict OR war OR sanction OR crisis)",
        "description": "Composite geopolitics score",
    },
    "GEO_RUSSIA_UKRAINE": {
        "query": "(Russia OR Ukraine OR Russian OR Ukrainian) AND (oil OR gas OR energy OR pipeline)",
        "description": "Russia-Ukraine conflict",
    },
    "GEO_MIDDLE_EAST": {
        "query": "(Iran OR Saudi OR Yemen OR Iraq OR Syria) AND (oil OR energy OR conflict)",
        "description": "Middle East risk",
    },
    "GEO_RED_SEA": {
        "query": "(Red Sea OR Houthi OR Suez) AND (shipping OR oil OR tanker)",
        "description": "Red Sea shipping risk",
    },
    "GPR_INDEX": {
        "query": "geopolitical risk AND (oil OR energy OR commodity)",
        "description": "GPR proxy",
    },
}


class GdeltCollector(FactorCollector):
    """GDELT data collector (no API key required)."""

    def __init__(self):
        factors = get_factors_by_collector("gdelt")
        factor_keys = list(factors.keys())
        super().__init__(name="gdelt", source="gdelt", factor_keys=factor_keys)
        self._factors = factors

    @staticmethod
    def _window(date_str: str) -> tuple[str, str]:
        target = datetime.strptime(date_str, "%Y-%m-%d")
        start_date = (target - timedelta(days=1)).strftime("%Y%m%d%H%M%S")
        end_date = (target + timedelta(days=1)).strftime("%Y%m%d%H%M%S")
        return start_date, end_date

    @staticmethod
    def _throttle():
        """Enforce minimum interval between GDELT API requests to avoid 429."""
        global _last_request_time
        now = time.monotonic()
        elapsed = now - _last_request_time
        if elapsed < _REQUEST_INTERVAL:
            time.sleep(_REQUEST_INTERVAL - elapsed)
        _last_request_time = time.monotonic()

    @staticmethod
    def _extract_tone_timeline(tone_data: dict | list | None) -> list[dict]:
        """Normalize tonechart response to list[dict]."""
        if isinstance(tone_data, list):
            return [entry for entry in tone_data if isinstance(entry, dict)]
        if isinstance(tone_data, dict):
            for key in ("timeline", "tonechart"):
                timeline = tone_data.get(key)
                if isinstance(timeline, list):
                    return [entry for entry in timeline if isinstance(entry, dict)]
        return []

    def _query_gdelt_tone(self, query: str, date_str: str) -> dict | list | None:
        """Query GDELT DOC tonechart endpoint."""
        self._throttle()
        start_date, end_date = self._window(date_str)
        params = {
            "query": query,
            "mode": "tonechart",
            "startdatetime": start_date,
            "enddatetime": end_date,
            "format": "json",
        }

        session = get_shared_session()
        resp = None
        try:
            resp = session.get(GDELT_DOC_API, params=params, timeout=30)
            resp.raise_for_status()

            content_type = (resp.headers.get("Content-Type") or "").lower()
            if "json" not in content_type:
                body_preview = (resp.text or "").strip().replace("\n", " ")
                self.logger.warning(
                    "[gdelt] DOC API returned non-JSON: status=%s, content_type=%s, body=%r",
                    resp.status_code,
                    content_type,
                    body_preview[:200],
                )
                return None

            # 空响应提前判断，避免 JSONDecodeError
            body = (resp.text or "").strip()
            if not body:
                self.logger.warning("[gdelt] DOC API returned empty body (tonechart)")
                return None

            return resp.json()
        except JSONDecodeError:
            body_preview = (resp.text or "").strip().replace("\n", " ") if resp else ""
            self.logger.warning(
                "[gdelt] DOC API JSON decode failed: status=%s, body=%r",
                resp.status_code if resp else "unknown",
                body_preview[:200],
            )
            return None
        except Exception as e:
            self.logger.warning("[gdelt] DOC API request failed: %s", e)
            return None

    def _query_gdelt_volume(self, query: str, date_str: str) -> int:
        """Query GDELT article list and use record count as event intensity proxy."""
        self._throttle()
        start_date, end_date = self._window(date_str)
        params = {
            "query": query,
            "mode": "artlist",
            "startdatetime": start_date,
            "enddatetime": end_date,
            "maxrecords": 50,
            "format": "json",
        }

        session = get_shared_session()
        try:
            resp = session.get(GDELT_DOC_API, params=params, timeout=30)
            resp.raise_for_status()
            body = (resp.text or "").strip()
            if not body:
                return 0
            data = resp.json()
            if isinstance(data, dict):
                return len(data.get("articles", []))
            return 0
        except Exception:
            return 0

    def _compute_geopolitics_score(self, tone_data: dict | list | None, volume: int) -> float:
        """Map GDELT tone + volume to a 0-10 risk score."""
        if tone_data is None:
            return 5.0

        try:
            timeline = self._extract_tone_timeline(tone_data)
            if timeline:
                total_tone = 0.0
                total_count = 0
                for entry in timeline:
                    tone = float(entry.get("bin", 0))
                    count = int(entry.get("count", 1))
                    total_tone += tone * count
                    total_count += count

                if total_count > 0:
                    avg_tone = total_tone / total_count
                    score = max(0.0, min(10.0, 5.0 - avg_tone * 0.5))
                    volume_factor = min(2.0, max(0.5, volume / 50.0))
                    return round(score * volume_factor / 2.0, 2)
        except (ValueError, TypeError, KeyError) as e:
            self.logger.debug("[gdelt] score calculation error: %s", e)

        return 5.0

    def _compute_news_sentiment(self, query: str, date_str: str) -> float:
        """Map average tone to [-1, 1]."""
        # Use quoted phrase to satisfy GDELT query grammar.
        tone_data = self._query_gdelt_tone(
            f'"{query}" AND (oil OR crude OR petroleum)',
            date_str,
        )

        if tone_data is None:
            return 0.0

        try:
            timeline = self._extract_tone_timeline(tone_data)
            if timeline:
                tones = [float(entry.get("bin", 0)) for entry in timeline]
                if tones:
                    avg = sum(tones) / len(tones)
                    return round(max(-1.0, min(1.0, avg / 10.0)), 4)
        except (ValueError, TypeError):
            pass

        return 0.0

    def collect(self, date_str: str) -> dict[str, float | None]:
        """Collect GDELT geopolitics and sentiment factors for target date."""
        result: dict[str, float | None] = {k: None for k in self.factor_keys}

        try:
            sentiment = self._compute_news_sentiment("energy market", date_str)
            result["NEWS_SENTIMENT"] = sentiment
        except Exception as e:
            self.logger.error("[gdelt] news sentiment collection failed: %s", e)

        for fk, geo_conf in GEO_QUERIES.items():
            if fk not in result:
                continue
            try:
                tone_data = self._query_gdelt_tone(geo_conf["query"], date_str)
                volume = self._query_gdelt_volume(geo_conf["query"], date_str)
                score = self._compute_geopolitics_score(tone_data, volume)
                result[fk] = score
            except Exception as e:
                self.logger.error("[gdelt] %s collection failed: %s", fk, e)

        return result
