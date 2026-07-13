import base64
import hashlib
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, mock

from nonebot_plugin_douyin.upload import UploadOptions, upload_file_stream


class UploadFileStreamTests(IsolatedAsyncioTestCase):
    async def test_upload_streams_chunks_and_returns_path(self):
        bot = mock.AsyncMock()
        # 21 字节 / 8 = 3 个数据分片 + 1 次 complete
        bot.call_api = mock.AsyncMock(side_effect=[{}, {}, {}, {'file_path': '/napcat/uploaded.mp4'}])

        # 使用 NamedTemporaryFile 风格的临时路径
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            content = b'hello-world-upload-data'
            tmp.write(content)
            path = Path(tmp.name)

        try:
            options = UploadOptions(chunk_size=8, file_retention_ms=1234)
            result = await upload_file_stream(bot, path, options=options)
        finally:
            path.unlink(missing_ok=True)

        self.assertEqual(result, '/napcat/uploaded.mp4')
        # 21 字节 / 8 = 3 个数据分片 + 1 次 complete
        self.assertEqual(bot.call_api.await_count, 4)

        first = bot.call_api.await_args_list[0]
        self.assertEqual(first.args[0], 'upload_file_stream')
        self.assertEqual(first.kwargs['chunk_index'], 0)
        self.assertEqual(first.kwargs['total_chunks'], 3)
        self.assertEqual(first.kwargs['file_size'], len(content))
        self.assertEqual(first.kwargs['file_retention'], 1234)
        self.assertEqual(first.kwargs['chunk_data'], base64.b64encode(content[:8]).decode('ascii'))
        self.assertEqual(first.kwargs['expected_sha256'], hashlib.sha256(content).hexdigest())

        complete = bot.call_api.await_args_list[-1]
        self.assertTrue(complete.kwargs.get('is_complete'))

    async def test_upload_raises_when_complete_missing_path(self):
        bot = mock.AsyncMock()
        bot.call_api = mock.AsyncMock(side_effect=[{}, {'ok': True}])

        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b'abc')
            path = Path(tmp.name)

        try:
            with self.assertRaises(RuntimeError):
                await upload_file_stream(bot, path, options=UploadOptions(chunk_size=64))
        finally:
            path.unlink(missing_ok=True)
