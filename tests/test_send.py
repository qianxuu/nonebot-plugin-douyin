from pathlib import Path
from unittest import IsolatedAsyncioTestCase, mock

from tests.fakes import group_event, private_event
from nonebot_plugin_douyin import send as send_mod
from nonebot_plugin_douyin.api import AwemeInfo, MediaItem
from nonebot_plugin_douyin.send import send_aweme


class SendAwemeTests(IsolatedAsyncioTestCase):
    async def test_multi_images_use_group_forward(self):
        bot = mock.AsyncMock()
        bot.self_id = '10001'
        bot.call_api = mock.AsyncMock(return_value={'message_id': 1})
        ev = group_event()
        data = AwemeInfo(
            aweme_id='111',
            items=[
                MediaItem(type='image', url='https://example.com/a.jpg', index=0),
                MediaItem(type='image', url='https://example.com/b.jpg', index=1),
            ],
        )

        await send_aweme(bot, ev, data)

        call = bot.call_api.await_args
        self.assertIsNotNone(call)
        assert call is not None
        args, kwargs = call
        self.assertEqual(args[0], 'send_forward_msg')
        self.assertEqual(kwargs['group_id'], 123456)
        self.assertNotIn('user_id', kwargs)
        nodes = kwargs['messages']
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].data['nickname'], '抖音')
        self.assertEqual(nodes[0].data['content'][0].type, 'image')

    async def test_multi_images_use_private_forward(self):
        bot = mock.AsyncMock()
        bot.self_id = '10001'
        bot.call_api = mock.AsyncMock(return_value={'message_id': 1})
        ev = private_event()
        data = AwemeInfo(
            aweme_id='111',
            items=[
                MediaItem(type='image', url='https://example.com/a.jpg', index=0),
                MediaItem(type='image', url='https://example.com/b.jpg', index=1),
            ],
        )

        await send_aweme(bot, ev, data)

        call = bot.call_api.await_args
        self.assertIsNotNone(call)
        assert call is not None
        args, kwargs = call
        self.assertEqual(args[0], 'send_forward_msg')
        self.assertEqual(kwargs['user_id'], 10000000)
        self.assertNotIn('group_id', kwargs)

    async def test_multi_live_photos_use_forward_with_videos(self):
        bot = mock.AsyncMock()
        bot.self_id = '10001'
        bot.call_api = mock.AsyncMock(return_value={'message_id': 1})
        ev = group_event()
        data = AwemeInfo(
            aweme_id='222',
            items=[
                MediaItem(type='video', url='https://example.com/a.mp4', index=0),
                MediaItem(type='video', url='https://example.com/b.mp4', index=1),
            ],
        )

        with (
            mock.patch.object(
                send_mod,
                '_prepare_video_file',
                mock.AsyncMock(side_effect=[Path('/tmp/a.mp4'), Path('/tmp/b.mp4')]),
            ),
            mock.patch.object(
                send_mod,
                '_resolve_video_ref',
                mock.AsyncMock(side_effect=['/napcat/a.mp4', '/napcat/b.mp4']),
            ),
        ):
            await send_aweme(bot, ev, data)

        call = bot.call_api.await_args
        self.assertIsNotNone(call)
        assert call is not None
        args, kwargs = call
        self.assertEqual(args[0], 'send_forward_msg')
        nodes = kwargs['messages']
        self.assertEqual(nodes[0].data['content'][0].type, 'video')
        self.assertEqual(nodes[0].data['content'][0].data['file'], '/napcat/a.mp4')

    async def test_single_image_sends_directly(self):
        bot = mock.AsyncMock()
        bot.send = mock.AsyncMock()
        bot.call_api = mock.AsyncMock()
        ev = group_event()
        data = AwemeInfo(
            aweme_id='111',
            items=[MediaItem(type='image', url='https://example.com/a.jpg', index=0)],
        )

        await send_aweme(bot, ev, data)

        bot.send.assert_awaited()
        bot.call_api.assert_not_called()

    async def test_pure_video_uses_napcat_mapping(self):
        bot = mock.AsyncMock()
        bot.send = mock.AsyncMock()
        ev = group_event()
        data = AwemeInfo(
            aweme_id='v1',
            items=[MediaItem(type='video', url='https://example.com/a.mp4', index=0)],
        )
        file_path = Path('/tmp/v1.mp4')

        with (
            mock.patch.object(send_mod, '_prepare_video_file', mock.AsyncMock(return_value=file_path)),
            mock.patch.object(send_mod, 'get_napcat_cache_file_path', return_value=Path('/napcat/v1.mp4')),
            mock.patch.object(send_mod, 'bytes_to_mibps', return_value=1.0),
        ):
            await send_aweme(bot, ev, data)

        bot.send.assert_awaited()
        call = bot.send.await_args
        self.assertIsNotNone(call)
        assert call is not None
        sent = call.args[1]
        self.assertEqual(sent.type, 'video')
        self.assertEqual(sent.data['file'], '/napcat/v1.mp4')

    async def test_pure_video_falls_back_to_upload(self):
        bot = mock.AsyncMock()
        bot.send = mock.AsyncMock()
        ev = group_event()
        data = AwemeInfo(
            aweme_id='v2',
            items=[MediaItem(type='video', url='https://example.com/a.mp4', index=0)],
        )
        file_path = Path('/tmp/v2.mp4')
        upload = mock.AsyncMock(return_value='/uploaded/v2.mp4')

        with (
            mock.patch.object(send_mod, '_prepare_video_file', mock.AsyncMock(return_value=file_path)),
            mock.patch.object(send_mod, 'get_napcat_cache_file_path', return_value=None),
            mock.patch.object(send_mod, 'upload_file_stream', upload),
            mock.patch.object(send_mod, 'bytes_to_mibps', return_value=1.0),
        ):
            await send_aweme(bot, ev, data)

        upload.assert_awaited()
        call = bot.send.await_args
        self.assertIsNotNone(call)
        assert call is not None
        sent = call.args[1]
        self.assertEqual(sent.data['file'], '/uploaded/v2.mp4')

    async def test_skip_download_does_not_send(self):
        bot = mock.AsyncMock()
        bot.send = mock.AsyncMock()
        ev = group_event()
        data = AwemeInfo(
            aweme_id='v3',
            items=[
                MediaItem(
                    type='video',
                    url='https://example.com/a.mp4',
                    index=0,
                    skip_download=True,
                    skip_reason='视频大小超过限制',
                )
            ],
        )

        with (
            mock.patch.object(send_mod, 'get_cache_file_path') as get_cache,
            mock.patch.object(send_mod, 'download', mock.AsyncMock()) as download,
        ):
            get_cache.return_value.exists.return_value = False
            await send_aweme(bot, ev, data)

        download.assert_not_called()
        bot.send.assert_not_called()

    async def test_forward_with_no_media_does_not_call_api(self):
        bot = mock.AsyncMock()
        bot.self_id = '10001'
        bot.call_api = mock.AsyncMock()
        ev = group_event()
        data = AwemeInfo(
            aweme_id='empty',
            items=[
                MediaItem(type='video', url='', index=0, skip_download=True, skip_reason='x'),
                MediaItem(type='video', url='', index=1, skip_download=True, skip_reason='y'),
            ],
        )

        with mock.patch.object(send_mod, '_prepare_video_file', mock.AsyncMock(return_value=None)):
            await send_aweme(bot, ev, data)

        bot.call_api.assert_not_called()
