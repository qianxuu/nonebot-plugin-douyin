from unittest import IsolatedAsyncioTestCase, mock

from tests.fixtures import LIVE_DETAIL, IMAGE_DETAIL, VIDEO_DETAIL
from nonebot_plugin_douyin.api import (
    MediaItem,
    DouyinApiError,
    get_aweme_info,
    video_cache_name,
    _resolve_aweme_id,
    _extract_image_url,
    _extract_video_url,
    _probe_video_stream,
    _extract_media_items,
)


class ResolveAwemeIdTests(IsolatedAsyncioTestCase):
    async def test_short_url_resolves_aweme_id_variants(self):
        cases = [
            ('https://www.iesdouyin.com/share/video/1234567890', '1234567890'),
            ('https://www.iesdouyin.com/share/note/7660507831200583025/?region=CN', '7660507831200583025'),
            ('https://www.iesdouyin.com/share/slides/7659385016279323889/?is_slides=1', '7659385016279323889'),
        ]
        for location, expected in cases:
            with self.subTest(location=location):

                async def fake_resolve_url(url: str, *, _location: str = location):
                    self.assertIn('v.douyin.com', url)
                    return _location

                with mock.patch('nonebot_plugin_douyin.api.resolve_url', fake_resolve_url):
                    aweme_id = await _resolve_aweme_id('https://v.douyin.com/abc123/')
                self.assertEqual(aweme_id, expected)

    async def test_short_url_parse_failure_raises(self):
        async def fake_resolve_url(_url: str):
            return None

        with mock.patch('nonebot_plugin_douyin.api.resolve_url', fake_resolve_url), self.assertRaises(DouyinApiError):
            await _resolve_aweme_id('https://v.douyin.com/abc123/')

    async def test_long_url_without_aweme_id_raises(self):
        with self.assertRaises(DouyinApiError):
            await _resolve_aweme_id('https://www.douyin.com/nothing-here')


class ExtractMediaTests(IsolatedAsyncioTestCase):
    def test_extract_video_url_prefers_largest_h265(self):
        self.assertEqual(_extract_video_url(VIDEO_DETAIL['video']), 'https://example.com/h265-1080.mp4')

    def test_extract_video_url_uses_largest_when_no_h265(self):
        video = {
            'bit_rate': [
                {'is_h265': 0, 'play_addr': {'data_size': 100, 'url_list': ['https://example.com/a.mp4']}},
                {'is_h265': 0, 'play_addr': {'data_size': 300, 'url_list': ['https://example.com/b.mp4']}},
                {'is_h265': 0, 'play_addr': {'data_size': 200, 'url_list': ['https://example.com/c.mp4']}},
            ]
        }
        self.assertEqual(_extract_video_url(video), 'https://example.com/b.mp4')

    def test_extract_video_url_returns_none_without_bit_rate(self):
        self.assertIsNone(_extract_video_url({'play_addr': {'url_list': ['https://example.com/fallback.mp4']}}))

    def test_extract_image_url_prefers_jpeg(self):
        self.assertEqual(
            _extract_image_url({'url_list': ['https://example.com/a.webp', 'https://example.com/a.jpeg']}),
            'https://example.com/a.jpeg',
        )

    def test_extract_media_items_from_images(self):
        items = _extract_media_items(IMAGE_DETAIL)
        self.assertEqual([item.type for item in items], ['image', 'image'])
        self.assertEqual(items[0].url, 'https://example.com/a.jpeg')
        self.assertEqual(items[1].url, 'https://example.com/b.webp')

    def test_extract_media_items_from_live_photos(self):
        items = _extract_media_items(LIVE_DETAIL)
        self.assertEqual([item.type for item in items], ['video', 'video'])
        self.assertEqual(items[0].url, 'https://example.com/live0-large.mp4')
        self.assertEqual(items[1].url, 'https://example.com/live1-h265.mp4')
        self.assertEqual([item.index for item in items], [0, 1])

    def test_extract_media_items_from_video(self):
        items = _extract_media_items(VIDEO_DETAIL)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].type, 'video')
        self.assertEqual(items[0].url, 'https://example.com/h265-1080.mp4')

    def test_extract_media_items_returns_empty_without_media(self):
        self.assertEqual(_extract_media_items({'aweme_id': 'x'}), [])


class VideoCacheNameTests(IsolatedAsyncioTestCase):
    def test_pure_video_uses_aweme_id(self):
        item = MediaItem(type='video', url='https://example.com/a.mp4', index=0)
        self.assertEqual(video_cache_name('123', item, pure_video=True), '123')

    def test_gallery_video_uses_index_suffix(self):
        item = MediaItem(type='video', url='https://example.com/a.mp4', index=2)
        self.assertEqual(video_cache_name('123', item, pure_video=False), '123_2')


class GetAwemeInfoTests(IsolatedAsyncioTestCase):
    async def test_returns_video(self):
        async def fake_get_aweme_detail(aweme_id: str):
            self.assertEqual(aweme_id, '1234567890')
            return VIDEO_DETAIL

        async def fake_get_content_length(url: str):
            self.assertEqual(url, 'https://example.com/h265-1080.mp4')
            return 1024

        with (
            mock.patch('nonebot_plugin_douyin.api.get_aweme_detail', fake_get_aweme_detail),
            mock.patch('nonebot_plugin_douyin.api.get_content_length', fake_get_content_length),
            mock.patch('nonebot_plugin_douyin.api.get_cache_file_path') as get_cache_file_path,
        ):
            get_cache_file_path.return_value.exists.return_value = False
            info = await get_aweme_info('https://www.douyin.com/video/1234567890')

        self.assertIsNotNone(info)
        assert info is not None
        self.assertEqual(info.aweme_id, '1234567890')
        self.assertEqual(info.items[0].type, 'video')
        self.assertEqual(info.items[0].url, 'https://example.com/h265-1080.mp4')
        self.assertFalse(info.items[0].skip_download)
        self.assertEqual(info.items[0].size, 1024)

    async def test_returns_images(self):
        async def fake_get_aweme_detail(_aweme_id: str):
            return IMAGE_DETAIL

        with mock.patch('nonebot_plugin_douyin.api.get_aweme_detail', fake_get_aweme_detail):
            info = await get_aweme_info('https://www.douyin.com/note/111')

        self.assertIsNotNone(info)
        assert info is not None
        self.assertEqual([item.type for item in info.items], ['image', 'image'])

    async def test_returns_none_when_detail_missing(self):
        with (
            mock.patch('nonebot_plugin_douyin.api.get_aweme_detail', mock.AsyncMock(return_value=None)),
            mock.patch('nonebot_plugin_douyin.api.logger') as log,
        ):
            info = await get_aweme_info('https://www.douyin.com/video/1234567890')

        self.assertIsNone(info)
        log.warning.assert_called()

    async def test_returns_none_when_no_media(self):
        with (
            mock.patch('nonebot_plugin_douyin.api.get_aweme_detail', mock.AsyncMock(return_value={'aweme_id': '1'})),
            mock.patch('nonebot_plugin_douyin.api.logger') as log,
        ):
            info = await get_aweme_info('https://www.douyin.com/video/1')

        self.assertIsNone(info)
        log.warning.assert_called()

    async def test_returns_none_on_unexpected_error(self):
        with (
            mock.patch('nonebot_plugin_douyin.api._resolve_aweme_id', mock.AsyncMock(side_effect=RuntimeError('boom'))),
            mock.patch('nonebot_plugin_douyin.api.logger') as log,
        ):
            info = await get_aweme_info('https://www.douyin.com/video/1')

        self.assertIsNone(info)
        log.error.assert_called()

    async def test_uses_cache_to_skip_stream_probe(self):
        with (
            mock.patch('nonebot_plugin_douyin.api.get_aweme_detail', mock.AsyncMock(return_value=VIDEO_DETAIL)),
            mock.patch('nonebot_plugin_douyin.api.get_cache_file_path') as get_cache_file_path,
            mock.patch('nonebot_plugin_douyin.api.logger') as log,
        ):
            get_cache_file_path.return_value.exists.return_value = True
            info = await get_aweme_info('https://www.douyin.com/video/1234567890')

        self.assertIsNotNone(info)
        assert info is not None
        self.assertTrue(info.items[0].skip_download)
        self.assertEqual(info.items[0].skip_reason, '视频已缓存')
        log.info.assert_called()


class ProbeVideoStreamTests(IsolatedAsyncioTestCase):
    async def test_probe_skips_large_video(self):
        item = MediaItem(type='video', url='https://example.com/video.mp4')
        with (
            mock.patch('nonebot_plugin_douyin.api.get_content_length', mock.AsyncMock(return_value=60 * 1024 * 1024)),
            mock.patch('nonebot_plugin_douyin.api.DOUYIN_MAX_VIDEO_SIZE', 50 * 1024 * 1024),
        ):
            await _probe_video_stream('123', item)

        self.assertTrue(item.skip_download)
        self.assertEqual(item.skip_reason, '视频大小超过限制')
        self.assertEqual(item.size, 60 * 1024 * 1024)

    async def test_probe_marks_downloadable_stream(self):
        item = MediaItem(type='video', url='https://example.com/video.mp4')
        with mock.patch(
            'nonebot_plugin_douyin.api.get_content_length',
            mock.AsyncMock(return_value=10 * 1024 * 1024),
        ):
            await _probe_video_stream('123', item)

        self.assertFalse(item.skip_download)
        self.assertIsNone(item.skip_reason)
        self.assertEqual(item.size, 10 * 1024 * 1024)

    async def test_probe_marks_failure(self):
        item = MediaItem(type='video', url='https://example.com/video.mp4')
        with mock.patch(
            'nonebot_plugin_douyin.api.get_content_length',
            mock.AsyncMock(side_effect=RuntimeError('network')),
        ):
            await _probe_video_stream('123', item)

        self.assertTrue(item.skip_download)
        self.assertEqual(item.skip_reason, '视频流信息获取失败')
