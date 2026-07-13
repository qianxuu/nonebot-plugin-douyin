import asyncio
from unittest import IsolatedAsyncioTestCase, mock

from nonebot_plugin_douyin import utils as utils_mod
from nonebot_plugin_douyin.utils import KeyedLock, bytes_to_mib, is_key_in_cd, bytes_to_mibps, extract_aweme_id


def test_extract_aweme_id():
    assert extract_aweme_id('https://www.douyin.com/video/123') == '123'
    assert extract_aweme_id('https://www.douyin.com/note/456/?x=1') == '456'
    assert extract_aweme_id('https://www.douyin.com/slides/789') == '789'
    assert extract_aweme_id('https://v.douyin.com/abc') is None


def test_bytes_helpers():
    assert bytes_to_mib(1024 * 1024) == 1.0
    assert bytes_to_mibps(1024 * 1024, 2) == 0.5
    assert bytes_to_mibps(1024 * 1024, 0) == 0.0


def test_is_key_in_cd_and_expiry():
    utils_mod._douyin_cd_list.clear()
    with mock.patch('nonebot_plugin_douyin.utils.time.time', return_value=1000):
        assert is_key_in_cd('a', 1, seconds=10) is False
        assert is_key_in_cd('a', 1, seconds=10) is True
        assert is_key_in_cd('a', 2, seconds=10) is False

    with mock.patch('nonebot_plugin_douyin.utils.time.time', return_value=1020):
        # 过期后应允许再次发送，并写入新冷却
        assert is_key_in_cd('a', 1, seconds=10) is False
        assert is_key_in_cd('a', 1, seconds=10) is True


def test_is_key_in_cd_zero_seconds_expires_immediately():
    utils_mod._douyin_cd_list.clear()
    with mock.patch('nonebot_plugin_douyin.utils.time.time', return_value=1000):
        assert is_key_in_cd('b', 1, seconds=0) is False
        # expire_time == now，下次清理会移除，因此不会进入冷却命中
        assert is_key_in_cd('b', 1, seconds=0) is False


class KeyedLockTests(IsolatedAsyncioTestCase):
    async def test_same_key_is_serialized(self):
        lock = KeyedLock()
        order: list[str] = []

        async def worker(name: str):
            async with lock('k'):
                order.append(f'{name}-enter')
                await asyncio.sleep(0.01)
                order.append(f'{name}-exit')

        await asyncio.gather(worker('a'), worker('b'))
        # 不应交叉进入
        self.assertIn(order, (['a-enter', 'a-exit', 'b-enter', 'b-exit'], ['b-enter', 'b-exit', 'a-enter', 'a-exit']))
