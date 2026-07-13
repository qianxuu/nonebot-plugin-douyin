"""消息发送：图片 / 视频 / 合并转发。"""

import time
from pathlib import Path

from nonebot.log import logger
from nonebot.adapters.onebot.v11 import (
    Bot,
    Message,
    MessageEvent,
    MessageSegment,
    GroupMessageEvent,
    PrivateMessageEvent,
)

from .api import AwemeInfo, MediaItem, video_cache_name
from .utils import KeyedLock, bytes_to_mibps
from .config import get_napcat_cache_file_path
from .upload import UploadOptions, upload_file_stream
from .download import download, get_cache_file_path

_TAG = '[抖音]'
_SEND_LOCK = KeyedLock()
_FORWARD_NICKNAME = '抖音'


async def send_aweme(bot: Bot, ev: MessageEvent, data: AwemeInfo) -> None:
    pure_video = len(data.items) == 1 and data.items[0].type == 'video' and data.items[0].index == 0
    if pure_video:
        await _send_video_item(bot, ev, data.aweme_id, data.items[0], pure_video=True)
        return

    # 图文 / Live Photo：多条合并转发，避免刷屏
    if len(data.items) >= 2:
        await _send_gallery_forward(bot, ev, data)
        return

    item = data.items[0]
    if item.type == 'image':
        await _send_images(bot, ev, data.aweme_id, [item])
    else:
        await _send_video_item(bot, ev, data.aweme_id, item, pure_video=False)


async def _send_gallery_forward(bot: Bot, ev: MessageEvent, data: AwemeInfo) -> None:
    try:
        async with _SEND_LOCK(f'{data.aweme_id}:forward'):
            nodes: list[MessageSegment] = []
            for item in data.items:
                content = await _media_message_for_forward(bot, data.aweme_id, item, pure_video=False)
                if content is None:
                    continue
                nodes.append(
                    MessageSegment.node_custom(
                        user_id=int(bot.self_id),
                        nickname=_FORWARD_NICKNAME,
                        content=content,
                    )
                )

            if not nodes:
                logger.warning(f'{_TAG} {data.aweme_id} 合并转发无可用媒体')
                return

            await _send_forward_msg(bot, ev, nodes)
            logger.info(f'{_TAG} {data.aweme_id} 合并转发发送完成，共 {len(nodes)} 条')
    except Exception as e:
        logger.error(f'{_TAG} 合并转发发送失败: {data.aweme_id} - {e}')


async def _media_message_for_forward(
    bot: Bot,
    aweme_id: str,
    item: MediaItem,
    *,
    pure_video: bool,
) -> Message | None:
    if item.type == 'image':
        return Message(MessageSegment.image(item.url))

    file_path = await _prepare_video_file(aweme_id, item, pure_video=pure_video)
    if file_path is None:
        return None

    video_ref = await _resolve_video_ref(bot, file_path)
    return Message(MessageSegment.video(video_ref))


async def _send_forward_msg(bot: Bot, ev: MessageEvent, nodes: list[MessageSegment]) -> None:
    if isinstance(ev, GroupMessageEvent):
        await bot.call_api(
            'send_forward_msg',
            group_id=ev.group_id,
            messages=nodes,
        )
        return
    if isinstance(ev, PrivateMessageEvent):
        await bot.call_api(
            'send_forward_msg',
            user_id=ev.user_id,
            messages=nodes,
        )
        return
    raise TypeError(f'不支持的会话类型: {type(ev)!r}')


async def _send_images(bot: Bot, ev: MessageEvent, aweme_id: str, items: list[MediaItem]) -> None:
    try:
        async with _SEND_LOCK(f'{aweme_id}:images'):
            await bot.send(ev, Message([MessageSegment.image(item.url) for item in items]))
            logger.info(f'{_TAG} {aweme_id} 图片发送完成，共 {len(items)} 张')
    except Exception as e:
        logger.error(f'{_TAG} 图片发送失败: {aweme_id} - {e}')


async def _send_video_item(
    bot: Bot,
    ev: MessageEvent,
    aweme_id: str,
    item: MediaItem,
    *,
    pure_video: bool,
) -> None:
    file_path = await _prepare_video_file(aweme_id, item, pure_video=pure_video)
    if file_path is None:
        return

    cache_name = video_cache_name(aweme_id, item, pure_video=pure_video)
    try:
        async with _SEND_LOCK(cache_name):
            t0 = time.monotonic()
            await _send_video_segment(bot, ev, file_path)
            elapsed = time.monotonic() - t0
            speed = bytes_to_mibps(file_path.stat().st_size, elapsed)
            logger.info(f'{_TAG} {cache_name} 视频发送完成，耗时 {elapsed:.1f}s, 速度 {speed:.2f} MiB/s')
    except Exception as e:
        logger.error(f'{_TAG} 视频发送失败: {cache_name} - {e}')


async def _prepare_video_file(aweme_id: str, item: MediaItem, *, pure_video: bool) -> Path | None:
    cache_name = video_cache_name(aweme_id, item, pure_video=pure_video)
    cache_file_path = get_cache_file_path(cache_name)
    if cache_file_path.exists():
        return cache_file_path

    if item.skip_download:
        logger.info(f'{_TAG} 跳过下载: {cache_name} - {item.skip_reason or "未提供原因"}')
        return None

    if not item.url:
        logger.warning(f'{_TAG} 缺少视频流地址: {cache_name}')
        return None

    return await download(cache_name, item.url)


async def _resolve_video_ref(bot: Bot, file_path: Path) -> str:
    napcat_file_path = get_napcat_cache_file_path(file_path)
    if napcat_file_path is not None:
        return str(napcat_file_path)
    return await upload_file_stream(bot, file_path, options=UploadOptions(chunk_size=1024 * 1024))


async def _send_video_segment(bot: Bot, ev: MessageEvent, file_path: Path) -> None:
    napcat_file_path = get_napcat_cache_file_path(file_path)
    if napcat_file_path is not None:
        logger.debug(f'{_TAG} 使用缓存映射跳过 WS 流式上传')
        await bot.send(ev, MessageSegment.video(str(napcat_file_path)))
        return

    logger.debug(f'{_TAG} 未配置缓存映射，使用 WS 流式上传')
    uploaded_file_path = await upload_file_stream(bot, file_path, options=UploadOptions(chunk_size=1024 * 1024))
    await bot.send(ev, MessageSegment.video(uploaded_file_path))
