"""链接识别与作品发送入口。"""

import re
import asyncio

from nonebot import on_regex
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent

from .api import get_aweme_info
from .send import send_aweme
from .utils import is_key_in_cd
from .config import DOUYIN_GROUP_BLACKLIST, DOUYIN_GROUP_CD_SECONDS

_TAG = '[抖音]'
_DOUYIN_URL_RE = r'https://(?:v\.douyin\.com/[A-Za-z0-9_-]+/?|www\.douyin\.com/(?:video|note|slides)/\d+)'


@on_regex(_DOUYIN_URL_RE).handle()
async def _handle_content(bot: Bot, ev: MessageEvent):
    if _should_skip_event(ev):
        return

    urls = _extract_urls(ev.get_plaintext())
    if not urls:
        return

    await asyncio.gather(*(_process_url(bot, ev, url) for url in urls))


def _should_skip_event(ev: MessageEvent) -> bool:
    if isinstance(ev, GroupMessageEvent) and ev.group_id in DOUYIN_GROUP_BLACKLIST:
        logger.info(f'{_TAG} 群黑名单跳过: {ev.group_id}')
        return True
    return False


def _extract_urls(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(_DOUYIN_URL_RE, text)))


async def _process_url(bot: Bot, ev: MessageEvent, url: str) -> None:
    data = await get_aweme_info(url)
    if data is None:
        return

    if isinstance(ev, GroupMessageEvent) and is_key_in_cd(
        data.aweme_id,
        ev.group_id,
        seconds=DOUYIN_GROUP_CD_SECONDS,
    ):
        logger.warning(f'{_TAG} 群组冷却: {ev.group_id} - {data.aweme_id}')
        return

    await send_aweme(bot, ev, data)
