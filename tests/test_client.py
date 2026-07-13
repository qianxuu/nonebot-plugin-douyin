from unittest import IsolatedAsyncioTestCase, mock

from tests.fakes import FakeSession, FakeResponse, FakeClientSessionFactory
from nonebot_plugin_douyin import client as client_mod
from nonebot_plugin_douyin.client import resolve_url, close_client, get_aweme_detail, get_content_length


class ResolveUrlTests(IsolatedAsyncioTestCase):
    async def test_resolve_url_returns_location_without_following_redirect(self):
        session = FakeSession(
            FakeResponse(302, headers={'Location': 'https://www.iesdouyin.com/share/video/1234567890'})
        )

        with mock.patch.object(client_mod, '_get_client', mock.AsyncMock(return_value=session)):
            location = await resolve_url('https://v.douyin.com/abc123/')

        self.assertEqual(location, 'https://www.iesdouyin.com/share/video/1234567890')
        self.assertFalse(session.get_calls[0]['allow_redirects'])


class GetAwemeDetailTests(IsolatedAsyncioTestCase):
    async def test_returns_aweme_detail(self):
        payload = {'aweme_detail': {'aweme_id': '1234567890', 'video': {}}}
        session = FakeSession(FakeResponse(200, payload=payload))

        with (
            mock.patch.object(client_mod, 'DOUYIN_TTWID', 'ttwid-value'),
            mock.patch.object(client_mod, '_get_client', mock.AsyncMock(return_value=session)),
        ):
            detail = await get_aweme_detail('1234567890')

        self.assertEqual(detail, payload['aweme_detail'])
        self.assertIn('aweme_id=1234567890', session.get_calls[0]['url'])
        self.assertIn('a_bogus=1', session.get_calls[0]['url'])
        self.assertIn('aid=6383', session.get_calls[0]['url'])

    async def test_retries_empty_response(self):
        session = FakeSession(*[FakeResponse(200, payload={}) for _ in range(5)])

        with (
            mock.patch.object(client_mod, 'DOUYIN_TTWID', 'ttwid-value'),
            mock.patch.object(client_mod, '_get_client', mock.AsyncMock(return_value=session)),
        ):
            detail = await get_aweme_detail('1234567890')

        self.assertIsNone(detail)
        self.assertEqual(len(session.get_calls), 5)

    async def test_returns_none_without_ttwid_and_warns_once(self):
        with (
            mock.patch.object(client_mod, 'DOUYIN_TTWID', ''),
            mock.patch.object(client_mod, '_missing_ttwid_warned', False),
            mock.patch.object(client_mod, '_get_client', mock.AsyncMock()) as get_client,
            mock.patch.object(client_mod, 'logger') as log,
        ):
            detail = await get_aweme_detail('1234567890')
            detail_again = await get_aweme_detail('1234567890')

        self.assertIsNone(detail)
        self.assertIsNone(detail_again)
        get_client.assert_not_called()
        log.warning.assert_called_once()

    async def test_non_200_status_returns_none_then_retries(self):
        session = FakeSession(*[FakeResponse(403, payload=None, body=b'') for _ in range(5)])

        with (
            mock.patch.object(client_mod, 'DOUYIN_TTWID', 'ttwid-value'),
            mock.patch.object(client_mod, '_get_client', mock.AsyncMock(return_value=session)),
        ):
            detail = await get_aweme_detail('1234567890')

        self.assertIsNone(detail)
        self.assertEqual(len(session.get_calls), 5)


class GetContentLengthTests(IsolatedAsyncioTestCase):
    async def test_parses_content_range_on_206(self):
        session = FakeSession(FakeResponse(206, headers={'Content-Range': 'bytes 0-0/12345'}, body=b'x'))
        factory = FakeClientSessionFactory(session)

        with mock.patch.object(client_mod.aiohttp, 'ClientSession', factory):
            size = await get_content_length('https://example.com/a.mp4')

        self.assertEqual(size, 12345)
        self.assertEqual(session.get_calls[0]['headers']['Range'], 'bytes=0-0')

    async def test_parses_content_length_on_200(self):
        session = FakeSession(FakeResponse(200, headers={'Content-Length': '99'}, body=b'x'))
        factory = FakeClientSessionFactory(session)

        with mock.patch.object(client_mod.aiohttp, 'ClientSession', factory):
            size = await get_content_length('https://example.com/a.mp4')

        self.assertEqual(size, 99)

    async def test_returns_none_when_headers_missing(self):
        session = FakeSession(FakeResponse(200, headers={}, body=b'x'))
        factory = FakeClientSessionFactory(session)

        with mock.patch.object(client_mod.aiohttp, 'ClientSession', factory):
            size = await get_content_length('https://example.com/a.mp4')

        self.assertIsNone(size)


class CloseClientTests(IsolatedAsyncioTestCase):
    async def test_close_client_closes_and_resets(self):
        session = FakeSession()
        session.closed = False

        with mock.patch.object(client_mod, '_client', session):
            await close_client()
            self.assertTrue(session.closed)
            self.assertIsNone(client_mod._client)
