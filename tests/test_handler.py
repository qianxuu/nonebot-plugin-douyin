from unittest import IsolatedAsyncioTestCase, mock

from tests.fakes import group_event, private_event
from nonebot_plugin_douyin import handler as handler_mod
from nonebot_plugin_douyin.api import AwemeInfo, MediaItem
from nonebot_plugin_douyin.handler import _process_url, _extract_urls, _handle_content, _should_skip_event


class ExtractUrlsTests(IsolatedAsyncioTestCase):
    def test_extract_urls_deduplicates_supported_links(self):
        text = (
            '看看这个 https://v.douyin.com/abc123/ '
            '还有这个 https://www.douyin.com/video/1234567890 '
            '以及图文 https://www.douyin.com/note/7660507831200583025 '
            '以及图集 https://www.douyin.com/slides/7659385016279323889 '
            '重复一次 https://www.douyin.com/video/1234567890'
        )
        self.assertEqual(
            _extract_urls(text),
            [
                'https://v.douyin.com/abc123/',
                'https://www.douyin.com/video/1234567890',
                'https://www.douyin.com/note/7660507831200583025',
                'https://www.douyin.com/slides/7659385016279323889',
            ],
        )

    def test_extract_urls_keeps_underscore_in_short_link(self):
        text = (
            '9.92 复制打开抖音，看看【老母龟的作品】当bro出生在福建 '
            'https://v.douyin.com/c3B7DTa_3rw/ D@u.SY 05/11 VYZ:/ :8pm'
        )
        self.assertEqual(_extract_urls(text), ['https://v.douyin.com/c3B7DTa_3rw/'])


class HandlerPolicyTests(IsolatedAsyncioTestCase):
    def test_should_skip_blacklisted_group(self):
        ev = group_event(group_id=99)
        with mock.patch.object(handler_mod, 'DOUYIN_GROUP_BLACKLIST', {99}):
            self.assertTrue(_should_skip_event(ev))

    def test_should_not_skip_private_or_normal_group(self):
        with mock.patch.object(handler_mod, 'DOUYIN_GROUP_BLACKLIST', {99}):
            self.assertFalse(_should_skip_event(private_event()))
            self.assertFalse(_should_skip_event(group_event(group_id=1)))

    async def test_handle_content_skips_blacklist(self):
        bot = mock.AsyncMock()
        ev = group_event(group_id=99, text='https://www.douyin.com/video/1')
        with (
            mock.patch.object(handler_mod, 'DOUYIN_GROUP_BLACKLIST', {99}),
            mock.patch.object(handler_mod, '_process_url', mock.AsyncMock()) as process_url,
        ):
            await _handle_content(bot, ev)
        process_url.assert_not_called()

    async def test_process_url_respects_cooldown(self):
        bot = mock.AsyncMock()
        ev = group_event(group_id=1)
        data = AwemeInfo(aweme_id='1', items=[MediaItem(type='image', url='https://example.com/a.jpg')])
        with (
            mock.patch.object(handler_mod, 'get_aweme_info', mock.AsyncMock(return_value=data)),
            mock.patch.object(handler_mod, 'is_key_in_cd', return_value=True),
            mock.patch.object(handler_mod, 'send_aweme', mock.AsyncMock()) as send_aweme,
            mock.patch.object(handler_mod, 'DOUYIN_GROUP_CD_SECONDS', 60),
        ):
            await _process_url(bot, ev, 'https://www.douyin.com/video/1')
        send_aweme.assert_not_called()

    async def test_process_url_sends_when_not_in_cd(self):
        bot = mock.AsyncMock()
        ev = group_event(group_id=1)
        data = AwemeInfo(aweme_id='1', items=[MediaItem(type='image', url='https://example.com/a.jpg')])
        with (
            mock.patch.object(handler_mod, 'get_aweme_info', mock.AsyncMock(return_value=data)),
            mock.patch.object(handler_mod, 'is_key_in_cd', return_value=False),
            mock.patch.object(handler_mod, 'send_aweme', mock.AsyncMock()) as send_aweme,
            mock.patch.object(handler_mod, 'DOUYIN_GROUP_CD_SECONDS', 60),
        ):
            await _process_url(bot, ev, 'https://www.douyin.com/video/1')
        send_aweme.assert_awaited_once_with(bot, ev, data)

    async def test_process_url_skips_when_parse_fails(self):
        bot = mock.AsyncMock()
        ev = group_event()
        with (
            mock.patch.object(handler_mod, 'get_aweme_info', mock.AsyncMock(return_value=None)),
            mock.patch.object(handler_mod, 'send_aweme', mock.AsyncMock()) as send_aweme,
        ):
            await _process_url(bot, ev, 'https://www.douyin.com/video/1')
        send_aweme.assert_not_called()

    async def test_handle_content_processes_multiple_urls(self):
        bot = mock.AsyncMock()
        text = 'https://www.douyin.com/video/1 https://www.douyin.com/video/2'
        ev = group_event(text=text)
        with (
            mock.patch.object(handler_mod, 'DOUYIN_GROUP_BLACKLIST', set()),
            mock.patch.object(handler_mod, '_process_url', mock.AsyncMock()) as process_url,
        ):
            await _handle_content(bot, ev)
        self.assertEqual(process_url.await_count, 2)
