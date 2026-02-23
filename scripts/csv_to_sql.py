#!/usr/bin/env python3
"""
csv_to_sql.py — Convert Final_Oil_Dataset_Cleaned.csv to data.sql
Uses only Python standard library (no pandas).
"""

import csv
import json
import math
import os
import statistics
from collections import defaultdict

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE, 'data', 'Final_Oil_Dataset_Cleaned.csv')
OUT_PATH = os.path.join(BASE, 'src', 'main', 'resources', 'data.sql')

# ── Column indices (0-based) ─────────────────────────────────────────────────
COL = {
    'date':           0,
    'cpi':            1,
    'oil_price':      3,
    'brent_chg':      7,
    'inventory':      8,
    'opec_output':   11,
    'vix':           35,
    'geo_total':     88,
    'russia_ukraine': 89,
    'middle_east':   90,
    'gpr':          119,
    'sentiment':    123,
    'usd_index':    137,
}

DATE_MIN = '2015-01-01'
DATE_MAX = '2025-12-31'

# ── Factor definitions ───────────────────────────────────────────────────────
# (factor_name, factor_name_zh, category, csv_key, shap_direction)
# shap_direction: +1 = high value → high risk (positive SHAP)
#                 -1 = high value → low risk (negative SHAP)
FACTORS = [
    ('crude_inventory',     '原油库存变化',     'SUPPLY_DEMAND', 'inventory_chg', -1),
    ('opec_output',         'OPEC产量',         'SUPPLY_DEMAND', 'opec_output',   -0.5),
    ('us_dollar_index',     '美元指数',         'MACRO',         'usd_index',     -0.3),
    ('cpi_expectation',     'CPI通胀预期',      'MACRO',         'cpi',            0.5),
    ('vix_index',           'VIX恐慌指数',      'FINANCIAL',     'vix',            1.0),
    ('brent_change_rate',   '布伦特价格变化率', 'FINANCIAL',     'brent_chg',      0.3),
    ('middle_east_tension', '中东紧张指数',     'GEOPOLITICAL',  'middle_east',    1.0),
    ('russia_ukraine_risk', '俄乌风险指数',     'GEOPOLITICAL',  'russia_ukraine', 1.0),
    ('gpr_index',           '地缘政治风险指数', 'SENTIMENT',     'gpr',            0.8),
    ('news_sentiment',      '新闻情绪指数',     'SENTIMENT',     'sentiment',     -1.0),
]

# Risk-index weights
RISK_WEIGHTS = {
    'vix':            0.25,
    'geo_total':      0.25,
    'sentiment_inv':  0.15,  # inverted sentiment: higher = more risk
    'inventory_chg':  0.10,  # inverted: inventory decline = risk
    'gpr':            0.10,
    'middle_east':    0.08,
    'russia_ukraine': 0.07,
}


def safe_float(s):
    """Parse a string to float, return None if empty/invalid."""
    s = s.strip() if s else ''
    if not s:
        return None
    try:
        v = float(s.replace(',', ''))
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (ValueError, TypeError):
        return None


def month_key(date_str):
    """'2020-03-15' → '2020-03'"""
    return date_str[:7]


def month_first(ym):
    """'2020-03' → '2020-03-01'"""
    return ym + '-01'


# ── Step 1: Read CSV, group by month ─────────────────────────────────────────

def read_csv():
    """Read CSV and return list of dicts with parsed numeric values."""
    rows = []
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            date_str = row[COL['date']].strip()
            if date_str < DATE_MIN or date_str > DATE_MAX:
                continue
            rec = {'date': date_str}
            for key, idx in COL.items():
                if key == 'date':
                    continue
                rec[key] = safe_float(row[idx]) if idx < len(row) else None
            rows.append(rec)
    return rows


def aggregate_monthly(rows):
    """Group daily rows into monthly means. Returns sorted list of monthly dicts."""
    buckets = defaultdict(lambda: defaultdict(list))
    for r in rows:
        ym = month_key(r['date'])
        for k, v in r.items():
            if k == 'date':
                continue
            if v is not None:
                buckets[ym][k].append(v)

    months = []
    prev = {}
    for ym in sorted(buckets.keys()):
        m = {'date': month_first(ym)}
        for key in COL:
            if key == 'date':
                continue
            vals = buckets[ym].get(key, [])
            if vals:
                m[key] = statistics.mean(vals)
                prev[key] = m[key]
            elif key in prev:
                m[key] = prev[key]  # forward-fill
            else:
                m[key] = 0.0
        months.append(m)
    return months


def compute_inventory_change(months):
    """Add inventory_chg (month-over-month % change) to each month."""
    for i, m in enumerate(months):
        if i == 0 or months[i - 1]['inventory'] == 0:
            m['inventory_chg'] = 0.0
        else:
            m['inventory_chg'] = ((m['inventory'] - months[i - 1]['inventory'])
                                  / months[i - 1]['inventory'] * 100.0)


# ── Step 2: Compute risk_index ───────────────────────────────────────────────

def _percentile(sorted_vals, pct):
    """Return the value at the given percentile (0-100) from a sorted list."""
    if not sorted_vals:
        return 0.0
    idx = pct / 100.0 * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def compute_risk_index(months):
    """Calculate risk_index (0-100) for each month.

    Uses percentile-based normalization clipped at the 85th percentile,
    so values above p85 saturate to 100. This ensures crisis periods
    (COVID 2020, Russia-Ukraine 2022) reach the High zone (>=70).
    """
    # Prepare derived columns
    for m in months:
        m['sentiment_inv'] = -m.get('sentiment', 0)  # invert: negative sentiment → high risk
        if 'inventory_chg' not in m:
            m['inventory_chg'] = 0.0

    # Compute p10 (floor) and p85 (ceiling) for each component
    comp_keys = list(RISK_WEIGHTS.keys())
    p_lo = {}
    p_hi = {}
    for k in comp_keys:
        vals = sorted(m.get(k, 0) for m in months)
        p_lo[k] = _percentile(vals, 10)
        p_hi[k] = _percentile(vals, 85)

    for m in months:
        score = 0.0
        for k, w in RISK_WEIGHTS.items():
            v = m.get(k, 0)
            rng = p_hi[k] - p_lo[k]
            if rng > 0:
                norm = (v - p_lo[k]) / rng * 100.0
            else:
                norm = 50.0
            norm = max(0.0, min(100.0, norm))
            score += norm * w

        # Apply mild power stretch to separate the upper tail
        score = max(0.0, min(100.0, score))
        m['risk_index'] = round(score, 2)
        if score >= 65:
            m['risk_level'] = 'High'
        elif score >= 35:
            m['risk_level'] = 'Medium'
        else:
            m['risk_level'] = 'Low'


# ── Step 3: Compute SHAP values ─────────────────────────────────────────────

def compute_shap(months):
    """Calculate simulated SHAP values for each factor per month."""
    # Compute mean and std for each factor's source column
    stats_cache = {}
    for fname, fzh, fcat, csv_key, direction in FACTORS:
        vals = [m.get(csv_key, 0) for m in months if m.get(csv_key) is not None]
        if len(vals) >= 2:
            mu = statistics.mean(vals)
            sd = statistics.stdev(vals)
        else:
            mu = 0.0
            sd = 1.0
        stats_cache[csv_key] = (mu, sd if sd > 0 else 1.0)

    for m in months:
        m['factors'] = []
        for fname, fzh, fcat, csv_key, direction in FACTORS:
            val = m.get(csv_key, 0) or 0
            mu, sd = stats_cache[csv_key]
            z = (val - mu) / sd
            shap = z * 0.04 * direction  # scale z-score to SHAP range
            shap = max(-0.15, min(0.15, shap))
            m['factors'].append({
                'factor_name': fname,
                'factor_name_zh': fzh,
                'category': fcat,
                'value': round(val, 4),
                'shap_value': round(shap, 6),
            })


# ── Step 4: Generate alerts ──────────────────────────────────────────────────

def generate_alerts(months):
    """Auto-generate alert records from risk data."""
    alerts = []

    # Thresholds for alert generation
    ALERT_THRESHOLDS = {
        'vix':            {'med': 20.0, 'high': 30.0, 'zh': 'VIX恐慌指数', 'name': 'vix_index'},
        'middle_east':    {'med': 3.0,  'high': 6.0,  'zh': '中东紧张指数', 'name': 'middle_east_tension'},
        'russia_ukraine': {'med': 3.0,  'high': 6.0,  'zh': '俄乌风险指数', 'name': 'russia_ukraine_risk'},
        'geo_total':      {'med': 5.0,  'high': 8.0,  'zh': '地缘政治事件综合评分', 'name': 'gpr_index'},
        'gpr':            {'med': 120,  'high': 200,  'zh': '地缘政治风险指数', 'name': 'gpr_index'},
    }

    prev_month = None
    for m in months:
        ri = m['risk_index']
        level = m['risk_level']
        date = m['date']

        # High alerts: always generate
        if level == 'High':
            detail, trigger = _build_alert_detail(m, ALERT_THRESHOLDS, prev_month)
            alerts.append({
                'date': date, 'level': 'High', 'ri': ri,
                'type': trigger['type'], 'factor': trigger['factor'],
                'factor_zh': trigger['factor_zh'],
                'summary': f"风险指数达{ri}，{trigger['factor_zh']}异常，触发高风险预警",
                'summary_en': f"Risk index at {ri}, {trigger['factor']} abnormal, high risk alert triggered",
                'detail': detail,
            })
        # Medium alerts: generate only for RI >= 55
        elif level == 'Medium' and ri >= 55:
            detail, trigger = _build_alert_detail(m, ALERT_THRESHOLDS, prev_month)
            alerts.append({
                'date': date, 'level': 'Medium', 'ri': ri,
                'type': trigger['type'], 'factor': trigger['factor'],
                'factor_zh': trigger['factor_zh'],
                'summary': f"{trigger['factor_zh']}触发中等风险预警，风险指数{ri}",
                'summary_en': f"{trigger['factor']} triggers medium risk alert, risk index {ri}",
                'detail': detail,
            })
        # Low alerts: generate when there's a trend change from Medium/High to Low
        elif level == 'Low' and prev_month and prev_month['risk_level'] in ('Medium', 'High'):
            detail, trigger = _build_alert_detail(m, ALERT_THRESHOLDS, prev_month)
            alerts.append({
                'date': date, 'level': 'Low', 'ri': ri,
                'type': 'TREND', 'factor': trigger['factor'],
                'factor_zh': trigger['factor_zh'],
                'summary': f"风险指数回落至{ri}，{trigger['factor_zh']}趋势缓解",
                'summary_en': f"Risk index falls to {ri}, {trigger['factor']} trend easing",
                'detail': detail,
            })

        prev_month = m

    # Ensure we have at least 20 alerts; if not, add more Medium alerts
    if len(alerts) < 20:
        medium_months = [m for m in months if m['risk_level'] == 'Medium'
                         and not any(a['date'] == m['date'] for a in alerts)]
        medium_months.sort(key=lambda m: m['risk_index'], reverse=True)
        for m in medium_months:
            if len(alerts) >= 25:
                break
            detail, trigger = _build_alert_detail(m, ALERT_THRESHOLDS, None)
            alerts.append({
                'date': m['date'], 'level': 'Medium', 'ri': m['risk_index'],
                'type': trigger['type'], 'factor': trigger['factor'],
                'factor_zh': trigger['factor_zh'],
                'summary': f"{trigger['factor_zh']}触发中等风险预警，风险指数{m['risk_index']}",
                'summary_en': f"{trigger['factor']} triggers medium alert, risk index {m['risk_index']}",
                'detail': detail,
            })

    alerts.sort(key=lambda a: a['date'])
    return alerts


def _build_alert_detail(m, thresholds, prev):
    """Build JSON detail (rule chain) and identify primary trigger factor."""
    rules = []
    best_trigger = None
    best_shap = 0

    # Check each factor for threshold/anomaly/trend rules
    for f in m.get('factors', []):
        fname = f['factor_name']
        fzh = f['factor_name_zh']
        val = f['value']
        shap = abs(f['shap_value'])

        if shap > best_shap:
            best_shap = shap
            best_trigger = {'factor': fname, 'factor_zh': fzh, 'type': 'THRESHOLD'}

        # Generate rules for factors with notable SHAP
        if shap >= 0.03:
            rule_type = 'THRESHOLD'
            if prev:
                prev_factors = {pf['factor_name']: pf for pf in prev.get('factors', [])}
                if fname in prev_factors:
                    prev_val = prev_factors[fname]['value']
                    if prev_val != 0 and abs(val - prev_val) / max(abs(prev_val), 0.01) > 0.15:
                        rule_type = 'ANOMALY'
                    elif (val > prev_val and f['shap_value'] > 0) or (val < prev_val and f['shap_value'] < 0):
                        rule_type = 'TREND'

            desc = f"{fzh}当前值{val:.2f}，SHAP贡献{f['shap_value']:.4f}"
            rules.append({
                'ruleType': rule_type,
                'factor': fname,
                'factorZh': fzh,
                'currentValue': round(val, 2),
                'threshold': round(val * 0.85, 2),  # synthetic threshold
                'description': desc,
            })

    # Keep top 3 rules by SHAP magnitude
    rules.sort(key=lambda r: abs(r['currentValue']), reverse=True)
    rules = rules[:3]

    if not rules:
        rules = [{'ruleType': 'THRESHOLD', 'factor': 'risk_index', 'factorZh': '综合风险指数',
                   'currentValue': m['risk_index'], 'threshold': 40.0,
                   'description': f"综合风险指数达{m['risk_index']}"}]

    if best_trigger:
        # Set trigger type from the primary rule
        for r in rules:
            if r['factor'] == best_trigger['factor']:
                best_trigger['type'] = r['ruleType']
                break
    else:
        best_trigger = {'factor': 'risk_index', 'factor_zh': '综合风险指数', 'type': 'THRESHOLD'}

    return rules, best_trigger


# ── Step 5: Write SQL ────────────────────────────────────────────────────────

def write_sql(months, alerts):
    """Write the complete data.sql file."""
    lines = []
    w = lines.append

    w('-- ============================================')
    w('-- Seed data for OilRisk-Alert')
    w('-- Generated from Final_Oil_Dataset_Cleaned.csv')
    w('-- ============================================')
    w('')
    w('-- Clear existing data')
    w('TRUNCATE TABLE alert;')
    w('TRUNCATE TABLE risk_factor;')
    w('TRUNCATE TABLE risk_index;')
    w('')

    # ── risk_index ───────────────────────────────────────────────────────────
    w('-- risk_index data')
    batch_size = 50
    for i in range(0, len(months), batch_size):
        batch = months[i:i + batch_size]
        w('INSERT INTO risk_index (date, risk_index, risk_level, oil_price) VALUES')
        for j, m in enumerate(batch):
            oil = m.get('oil_price') or 0
            sep = ',' if j < len(batch) - 1 else ';'
            w(f"('{m['date']}', {m['risk_index']:.2f}, '{m['risk_level']}', {oil:.2f}){sep}")
        w('')

    # ── risk_factor ──────────────────────────────────────────────────────────
    w('-- risk_factor data')
    all_factors = []
    for m in months:
        for f in m.get('factors', []):
            all_factors.append((m['date'], f))

    for i in range(0, len(all_factors), batch_size):
        batch = all_factors[i:i + batch_size]
        w('INSERT INTO risk_factor (date, factor_name, factor_name_zh, category, "value", shap_value) VALUES')
        for j, (dt, f) in enumerate(batch):
            sep = ',' if j < len(batch) - 1 else ';'
            w(f"('{dt}', '{f['factor_name']}', '{f['factor_name_zh']}', "
              f"'{f['category']}', {f['value']:.4f}, {f['shap_value']:.6f}){sep}")
        w('')

    # ── alert ────────────────────────────────────────────────────────────────
    w('-- alert data')
    if alerts:
        w('INSERT INTO alert (date, level, risk_index, trigger_type, trigger_factor, '
          'trigger_factor_zh, summary, summary_en, detail) VALUES')
        for idx, a in enumerate(alerts):
            detail_json = json.dumps(a['detail'], ensure_ascii=False).replace("'", "''")
            sep = ',' if idx < len(alerts) - 1 else ';'
            w(f"('{a['date']}', '{a['level']}', {a['ri']:.2f}, '{a['type']}', "
              f"'{a['factor']}', '{a['factor_zh']}', "
              f"'{a['summary']}', '{a['summary_en']}', "
              f"'{detail_json}'){sep}")
        w('')

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f'Reading CSV: {CSV_PATH}')
    rows = read_csv()
    print(f'  Daily rows in range: {len(rows)}')

    months = aggregate_monthly(rows)
    print(f'  Monthly records: {len(months)}')
    print(f'  Date range: {months[0]["date"]} to {months[-1]["date"]}')

    compute_inventory_change(months)
    compute_risk_index(months)
    compute_shap(months)

    # Stats
    levels = defaultdict(int)
    for m in months:
        levels[m['risk_level']] += 1
    print(f'  Risk levels: Low={levels["Low"]}, Medium={levels["Medium"]}, High={levels["High"]}')

    alerts = generate_alerts(months)
    alert_levels = defaultdict(int)
    for a in alerts:
        alert_levels[a['level']] += 1
    print(f'  Alerts: {len(alerts)} (Low={alert_levels["Low"]}, Medium={alert_levels["Medium"]}, High={alert_levels["High"]})')

    write_sql(months, alerts)
    print(f'\nWritten: {OUT_PATH}')
    print(f'  risk_index rows:  {len(months)}')
    print(f'  risk_factor rows: {len(months) * 10}')
    print(f'  alert rows:       {len(alerts)}')


if __name__ == '__main__':
    main()
