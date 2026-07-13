"""测试用假 HTTP 会话与事件构造。"""

from __future__ import annotations

from typing import Any, cast
from collections.abc import AsyncIterator

import aiohttp
from yarl import URL
from multidict import CIMultiDict, CIMultiDictProxy
from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent


class FakeStreamContent:
    def __init__(self, data: bytes):
        self._data = data

    async def iter_chunked(self, _size: int) -> AsyncIterator[bytes]:
        if self._data:
            yield self._data


class FakeResponse:
    def __init__(
        self,
        status: int = 200,
        *,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        body: bytes | None = None,
    ):
        self.status = status
        self._headers = headers or {}
        self._payload = payload
        if body is not None:
            self._body = body
        elif payload is not None:
            self._body = b'{}'
        else:
            self._body = b''
        self.content = FakeStreamContent(self._body)

    @property
    def headers(self) -> dict[str, str]:
        return self._headers

    def raise_for_status(self) -> None:
        if self.status >= 400:
            request_info = aiohttp.RequestInfo(
                URL(),
                'GET',
                cast(CIMultiDictProxy[str], CIMultiDict()),
            )
            raise aiohttp.ClientResponseError(
                request_info=request_info,
                history=(),
                status=self.status,
                message='boom',
            )

    async def read(self) -> bytes:
        return self._body

    async def json(self, content_type: str | None = None) -> Any:
        return self._payload


class FakeGet:
    def __init__(self, response: FakeResponse):
        self._response = response

    async def __aenter__(self) -> FakeResponse:
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeSession:
    """顺序消费预设响应的假 ClientSession。"""

    def __init__(self, *responses: FakeResponse):
        self._responses = list(responses)
        self.closed = False
        self.get_calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeGet:
        self.get_calls.append({'url': url, **kwargs})
        if not self._responses:
            raise AssertionError(f'unexpected request: {url}')
        return FakeGet(self._responses.pop(0))

    async def close(self) -> None:
        self.closed = True


class FakeClientSessionFactory:
    """兼容 `async with aiohttp.ClientSession(...) as session`。"""

    def __init__(self, session: FakeSession):
        self._session = session
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> FakeClientSessionFactory:
        self.calls.append({'args': args, 'kwargs': kwargs})
        return self

    async def __aenter__(self) -> FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def group_event(group_id: int = 123456, text: str = '') -> GroupMessageEvent:
    event = GroupMessageEvent.model_construct(
        time=0,
        self_id=10001,
        post_type='message',
        message_type='group',
        sub_type='normal',
        message_id=1,
        user_id=10000000,
        group_id=group_id,
        raw_message=text,
        font=0,
        sender={},
    )

    def _get_plaintext() -> str:
        return text

    object.__setattr__(event, 'get_plaintext', _get_plaintext)
    return event


def private_event(user_id: int = 10000000, text: str = '') -> PrivateMessageEvent:
    event = PrivateMessageEvent.model_construct(
        time=0,
        self_id=10001,
        post_type='message',
        message_type='private',
        sub_type='friend',
        message_id=1,
        user_id=user_id,
        raw_message=text,
        font=0,
        sender={},
    )

    def _get_plaintext() -> str:
        return text

    object.__setattr__(event, 'get_plaintext', _get_plaintext)
    return event
