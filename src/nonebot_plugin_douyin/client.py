"""HTTP 客户端"""

import asyncio
from urllib.parse import urlencode

import aiohttp
from nonebot import logger

from .config import DOUYIN_TTWID

_TAG = '[抖音客户端]'

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    ),
    'Referer': 'https://www.douyin.com/',
}

_client_lock = asyncio.Lock()
_client: aiohttp.ClientSession | None = None
_missing_ttwid_warned = False


async def _get_client() -> aiohttp.ClientSession:
    """获取共享 HTTP 客户端，避免重复创建连接"""

    global _client
    async with _client_lock:
        if _client is None or _client.closed:
            cookies = {'ttwid': DOUYIN_TTWID} if DOUYIN_TTWID else None
            _client = aiohttp.ClientSession(headers=HEADERS, cookies=cookies)
        return _client


async def close_client() -> None:
    """关闭共享 HTTP 客户端。"""

    global _client
    async with _client_lock:
        if _client is not None and not _client.closed:
            await _client.close()
        _client = None


async def resolve_url(url: str) -> str | None:
    """解析短链接，返回重定向地址"""

    session = await _get_client()
    async with session.get(
        url,
        timeout=aiohttp.ClientTimeout(total=10),
        allow_redirects=False,
    ) as resp:
        resp.raise_for_status()
        return resp.headers.get('Location')


async def get_aweme_detail(aweme_id: str) -> dict | None:
    """通过抖音 Web 接口获取作品详情。

    依赖非公开接口与 ttwid，失败时返回 None（调用方应静默处理）。
    """

    global _missing_ttwid_warned
    if not DOUYIN_TTWID:
        if not _missing_ttwid_warned:
            logger.warning(f'{_TAG} 未配置 DOUYIN_TTWID，无法解析作品详情')
            _missing_ttwid_warned = True
        return None

    last_status: int | None = None
    for attempt in range(1, 6):
        data, last_status = await _request_aweme_detail(aweme_id)
        detail = data.get('aweme_detail') if data else None
        if isinstance(detail, dict):
            return detail
        if attempt < 5:
            logger.debug(f'{_TAG} 作品详情重试 {attempt}/5: aweme_id={aweme_id} status={last_status}')
    logger.warning(f'{_TAG} 作品详情获取失败: aweme_id={aweme_id} last_status={last_status}')
    return None


async def _request_aweme_detail(aweme_id: str) -> tuple[dict | None, int | None]:
    """请求单次详情接口。返回 (json 或 None, HTTP status 或 None)。"""

    # a_bogus 为占位签名参数，接口策略变更时可能直接失效
    query = urlencode({'aweme_id': aweme_id, 'aid': '6383', 'a_bogus': '1'})

    session = await _get_client()
    async with session.get(
        f'https://www.douyin.com/aweme/v1/web/aweme/detail/?{query}',
        timeout=aiohttp.ClientTimeout(total=10),
    ) as resp:
        status = resp.status
        if status != 200:
            return None, status
        body = await resp.read()
        if not body:
            return None, status
        data = await resp.json(content_type=None)
        return (data if isinstance(data, dict) else None), status
