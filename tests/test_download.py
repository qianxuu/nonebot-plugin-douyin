import os
from typing import cast
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, mock

import pytest
import aiohttp

from tests.fakes import FakeSession, FakeResponse, FakeClientSessionFactory
from nonebot_plugin_douyin import download as download_mod
from nonebot_plugin_douyin.download import (
    download,
    _prune_cache,
    _download_chunk,
    get_cache_file_path,
    _calculate_chunk_count,
)


@pytest.mark.parametrize(
    ('content_length', 'expected'),
    [
        (1, 1),
        (2 * 1024 * 1024, 1),
        (2 * 1024 * 1024 + 1, 2),
        (20 * 1024 * 1024, 8),
    ],
)
def test_calculate_chunk_count(content_length: int, expected: int):
    assert _calculate_chunk_count(content_length) == expected


@pytest.mark.parametrize('content_length', [0, -1])
def test_calculate_chunk_count_rejects_non_positive_length(content_length: int):
    with pytest.raises(ValueError):
        _calculate_chunk_count(content_length)


def test_get_cache_file_path():
    assert get_cache_file_path('abc') == Path('cache/douyin/abc.mp4')
    assert get_cache_file_path('abc.mp4') == Path('cache/douyin/abc.mp4')


def test_prune_cache_only_deletes_expired_files(tmp_path: Path):
    expired = tmp_path / 'expired.mp4'
    fresh = tmp_path / 'fresh.mp4'
    expired.write_bytes(b'old')
    fresh.write_bytes(b'new')

    now = 200000.0
    os.utime(expired, (now - 86401, now - 86401))
    os.utime(fresh, (now - 10, now - 10))

    with mock.patch.object(download_mod, 'DOUYIN_CACHE_RETENTION_SECONDS', 86400):
        _prune_cache(tmp_path, now=now)

    assert not expired.exists()
    assert fresh.exists()


class DownloadChunkTests(IsolatedAsyncioTestCase):
    async def test_download_chunk_returns_data(self):
        session = FakeSession(FakeResponse(200, body=b'abcd'))
        start, data = await _download_chunk(cast(aiohttp.ClientSession, session), 'https://example.com/a.mp4', 0, 3)
        self.assertEqual(start, 0)
        self.assertEqual(data, b'abcd')
        self.assertEqual(session.get_calls[0]['headers']['Range'], 'bytes=0-3')


class DownloadTests(IsolatedAsyncioTestCase):
    async def test_download_skips_when_content_length_missing(self):
        cache_dir = Path('cache/douyin-test-missing')
        with (
            mock.patch.object(download_mod, '_CACHE_DIR', cache_dir),
            mock.patch.object(download_mod, 'get_content_length', mock.AsyncMock(return_value=None)),
            mock.patch.object(download_mod, '_prune_cache'),
        ):
            if cache_dir.exists():
                for p in cache_dir.iterdir():
                    p.unlink()
                cache_dir.rmdir()
            result = await download('miss', 'https://example.com/a.mp4')
        self.assertIsNone(result)

    async def test_download_success_writes_file(self):
        cache_dir = Path('cache/douyin-test-success')
        cache_dir.mkdir(parents=True, exist_ok=True)
        for p in cache_dir.iterdir():
            p.unlink()

        body = b'0123456789'
        # 单分片：content_length 小，num_chunks=1
        session = FakeSession(FakeResponse(200, body=body))
        factory = FakeClientSessionFactory(session)

        with (
            mock.patch.object(download_mod, '_CACHE_DIR', cache_dir),
            mock.patch.object(download_mod, 'get_content_length', mock.AsyncMock(return_value=len(body))),
            mock.patch.object(download_mod, '_prune_cache'),
            mock.patch.object(download_mod.aiohttp, 'ClientSession', factory),
            mock.patch.object(download_mod.aiohttp, 'TCPConnector', mock.Mock(return_value=mock.Mock())),
            mock.patch.object(download_mod.aiohttp, 'ClientTimeout', mock.Mock(return_value=mock.Mock())),
        ):
            result = await download('ok', 'https://example.com/a.mp4')

        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.exists())
        self.assertEqual(result.read_bytes(), body)
        result.unlink(missing_ok=True)
        cache_dir.rmdir()

    async def test_download_returns_existing_file_without_network(self):
        cache_dir = Path('cache/douyin-test-cached')
        cache_dir.mkdir(parents=True, exist_ok=True)
        file_path = cache_dir / 'cached.mp4'
        file_path.write_bytes(b'cached')

        with (
            mock.patch.object(download_mod, '_CACHE_DIR', cache_dir),
            mock.patch.object(download_mod, 'get_content_length', mock.AsyncMock()) as get_len,
        ):
            result = await download('cached', 'https://example.com/a.mp4')

        self.assertEqual(result, file_path)
        get_len.assert_not_called()
        file_path.unlink()
        cache_dir.rmdir()

    async def test_download_cleans_temp_on_chunk_size_mismatch(self):
        cache_dir = Path('cache/douyin-test-mismatch')
        cache_dir.mkdir(parents=True, exist_ok=True)
        for p in cache_dir.iterdir():
            p.unlink()

        # 期望 10 字节，只返回 4 字节
        session = FakeSession(FakeResponse(200, body=b'abcd'))
        factory = FakeClientSessionFactory(session)

        with (
            mock.patch.object(download_mod, '_CACHE_DIR', cache_dir),
            mock.patch.object(download_mod, 'get_content_length', mock.AsyncMock(return_value=10)),
            mock.patch.object(download_mod, '_prune_cache'),
            mock.patch.object(download_mod.aiohttp, 'ClientSession', factory),
            mock.patch.object(download_mod.aiohttp, 'TCPConnector', mock.Mock(return_value=mock.Mock())),
            mock.patch.object(download_mod.aiohttp, 'ClientTimeout', mock.Mock(return_value=mock.Mock())),
        ):
            result = await download('bad', 'https://example.com/a.mp4')

        self.assertIsNone(result)
        self.assertFalse((cache_dir / 'bad.mp4').exists())
        self.assertFalse((cache_dir / 'bad.tmp').exists())
        cache_dir.rmdir()
