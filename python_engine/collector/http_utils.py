"""
共享 HTTP 会话工厂 — 解决中国网络环境下的 SSL/代理问题。

所有采集器应通过此模块获取 requests.Session，自动配置：
- HTTP/HTTPS 代理（从环境变量读取）
- SSL 重试 + 指数退避
- 自定义超时
"""

import logging
import os
import ssl

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("oilrisk.collector.http")


def create_robust_session(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    timeout: int = 30,
) -> requests.Session:
    """
    创建一个具有重试、代理、SSL 容错能力的 HTTP Session。

    支持环境变量:
      - HTTP_PROXY / HTTPS_PROXY: 代理地址（如 http://127.0.0.1:7890）
      - SSL_VERIFY: 设为 "false" 跳过 SSL 验证（不推荐，仅调试用）
    """
    session = requests.Session()

    # 代理配置
    http_proxy = os.environ.get("HTTP_PROXY", os.environ.get("http_proxy", ""))
    https_proxy = os.environ.get("HTTPS_PROXY", os.environ.get("https_proxy", ""))
    if http_proxy or https_proxy:
        session.proxies = {
            "http": http_proxy,
            "https": https_proxy or http_proxy,
        }
        logger.info("HTTP session configured with proxy: %s", https_proxy or http_proxy)

    # SSL 验证
    ssl_verify = os.environ.get("SSL_VERIFY", "true").lower()
    if ssl_verify == "false":
        session.verify = False
        # 抑制 InsecureRequestWarning
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        logger.warning("SSL verification DISABLED (SSL_VERIFY=false)")

    # 重试策略：对 SSL 错误、连接错误、超时均重试
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # 默认超时
    session.timeout = timeout

    # User-Agent 伪装，避免被反爬
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    })

    return session


# 模块级单例，所有采集器共享
_shared_session: requests.Session | None = None


def get_shared_session() -> requests.Session:
    """获取共享 HTTP 会话（惰性创建）。"""
    global _shared_session
    if _shared_session is None:
        _shared_session = create_robust_session()
    return _shared_session
