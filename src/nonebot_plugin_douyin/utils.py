import re
import time
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass

from nonebot import logger

_MIB = 1024 * 1024
_AWEME_ID_RE = re.compile(r'/(?:video|note|slides)/(\d+)')


class KeyedLock:
    """按 key 分组的锁管理器，引用计数归零时自动清理"""

    def __init__(self):
        self._state: dict[str, tuple[asyncio.Lock, int]] = {}

    @asynccontextmanager
    async def __call__(self, key: str):
        lock, refs = self._state.get(key, (asyncio.Lock(), 0))
        self._state[key] = (lock, refs + 1)

        try:
            async with lock:
                yield
        finally:
            lock, refs = self._state[key]
            if refs == 1:
                del self._state[key]
            else:
                self._state[key] = (lock, refs - 1)


@dataclass
class DouyinCdItem:
    """抖音视频冷却项"""

    key: str = ''
    group_id: int = 0
    expire_time: int = 0


_douyin_cd_list: list[DouyinCdItem] = []


def bytes_to_mib(size: int) -> float:
    return size / _MIB


def bytes_to_mibps(size: int, seconds: float) -> float:
    if seconds <= 0:
        return 0.0
    return bytes_to_mib(size) / seconds


def extract_aweme_id(url: str) -> str | None:
    match = _AWEME_ID_RE.search(url)
    if match is None:
        return None
    return match.group(1)


def is_key_in_cd(key: str, group_id: int, seconds: int = 60) -> bool:
    """检查指定 key 是否在群冷却列表中。

    seconds <= 0 时视为关闭冷却，始终返回 False（允许发送）。
    首次调用对未命中项写入冷却并返回 False；命中未过期项返回 True。
    """

    global _douyin_cd_list

    if seconds <= 0:
        return False

    now = int(time.time())
    _douyin_cd_list = [item for item in _douyin_cd_list if item.expire_time > now]
    logger.debug(f'抖音冷却列表: {_douyin_cd_list}')

    for item in _douyin_cd_list:
        if item.key == key and item.group_id == group_id:
            return True

    _douyin_cd_list.append(DouyinCdItem(key=key, group_id=group_id, expire_time=now + seconds))
    return False
