from typing import Literal
from dataclasses import dataclass

from nonebot import logger

from .utils import bytes_to_mib, extract_aweme_id
from .client import resolve_url, get_aweme_detail, get_content_length
from .config import DOUYIN_MAX_VIDEO_SIZE
from .download import get_cache_file_path

_TAG = '[抖音 API]'

MediaType = Literal['image', 'video']


class DouyinApiError(Exception):
    """抖音接口解析失败"""


@dataclass(slots=True)
class MediaItem:
    """单条媒体资源"""

    type: MediaType
    url: str
    index: int = 0
    size: int | None = None
    skip_download: bool = False
    skip_reason: str | None = None


@dataclass(slots=True)
class AwemeInfo:
    """作品信息"""

    aweme_id: str
    items: list[MediaItem]


async def get_aweme_info(url: str) -> AwemeInfo | None:
    """获取作品信息（视频 / 图文 / Live Photo）"""

    try:
        aweme_id = await _resolve_aweme_id(url)
        detail = await get_aweme_detail(aweme_id)
        if detail is None:
            logger.warning(f'{_TAG} 接口未返回作品详情: {url}')
            return None

        items = _extract_media_items(detail)
        if not items:
            logger.warning(f'{_TAG} 未提取到可发送媒体: {url}')
            return None

        await _fill_video_stream_meta(aweme_id, items)
        return AwemeInfo(aweme_id=aweme_id, items=items)
    except Exception as e:
        logger.error(f'{_TAG} 作品信息获取失败: {url} - {e}')
        return None


async def _fill_video_stream_meta(aweme_id: str, items: list[MediaItem]) -> None:
    video_items = [item for item in items if item.type == 'video']
    if not video_items:
        return

    pure_video = len(items) == 1 and video_items[0].index == 0
    for item in video_items:
        cache_name = video_cache_name(aweme_id, item, pure_video=pure_video)
        cache_file_path = get_cache_file_path(cache_name)
        if cache_file_path.exists():
            logger.info(f'{_TAG} 视频已缓存，跳过获取视频流信息: {cache_name}')
            item.skip_download = True
            item.skip_reason = '视频已缓存'
            continue

        await _probe_video_stream(aweme_id, item)


def video_cache_name(aweme_id: str, item: MediaItem, *, pure_video: bool) -> str:
    """生成本地视频缓存文件名（不含后缀）。"""

    if pure_video:
        return aweme_id
    return f'{aweme_id}_{item.index}'


async def _probe_video_stream(aweme_id: str, item: MediaItem) -> None:
    """探测视频大小，过大则标记跳过下载"""

    try:
        size = await get_content_length(item.url)
        item.size = size
        if size is not None and size > DOUYIN_MAX_VIDEO_SIZE:
            logger.info(f'{_TAG} 视频过大: {aweme_id} - {bytes_to_mib(size):.2f} MiB')
            item.skip_download = True
            item.skip_reason = '视频大小超过限制'
            return

        item.skip_download = False
        item.skip_reason = None
    except Exception as e:
        logger.error(f'{_TAG} 视频流信息获取失败: {aweme_id} - {e}')
        item.skip_download = True
        item.skip_reason = '视频流信息获取失败'


async def _resolve_aweme_id(url: str) -> str:
    aweme_id = extract_aweme_id(url)
    if aweme_id is not None:
        return aweme_id

    if 'v.douyin.com/' in url:
        real_url = await resolve_url(url)
        if real_url is not None:
            aweme_id = extract_aweme_id(real_url)
            if aweme_id is not None:
                return aweme_id

    raise DouyinApiError('未识别到作品 ID')


def _extract_media_items(detail: dict) -> list[MediaItem]:
    """从作品详情提取可发送媒体列表"""

    images = detail.get('images')
    if isinstance(images, list) and images:
        return _extract_from_images(images)

    video = detail.get('video')
    if not isinstance(video, dict):
        return []

    play_url = _extract_video_url(video)
    if play_url is None:
        return []
    return [MediaItem(type='video', url=play_url, index=0)]


def _extract_from_images(images: list) -> list[MediaItem]:
    items: list[MediaItem] = []
    for index, image in enumerate(images):
        if not isinstance(image, dict):
            continue

        video = image.get('video')
        if isinstance(video, dict):
            play_url = _extract_video_url(video)
            if play_url is not None:
                items.append(MediaItem(type='video', url=play_url, index=index))
                continue

        image_url = _extract_image_url(image)
        if image_url is not None:
            items.append(MediaItem(type='image', url=image_url, index=index))
    return items


def _extract_image_url(image: dict) -> str | None:
    urls = image.get('url_list') or []
    if not isinstance(urls, list):
        return None

    str_urls = [url for url in urls if isinstance(url, str) and url]
    if not str_urls:
        return None

    for url in str_urls:
        lower = url.lower()
        if '.jpeg' in lower or '.jpg' in lower:
            return url
    return str_urls[0]


def _extract_video_url(video: dict) -> str | None:
    """从 bit_rate 选流：优先 h265/bytevc1 中 data_size 最大，否则全体 data_size 最大。"""

    bit_rate_list = video.get('bit_rate')
    if not isinstance(bit_rate_list, list) or not bit_rate_list:
        return None

    h265_items = [item for item in bit_rate_list if isinstance(item, dict) and _is_h265_item(item)]
    candidates = h265_items or [item for item in bit_rate_list if isinstance(item, dict)]
    if not candidates:
        return None

    best = max(candidates, key=_bit_rate_data_size)
    return _play_addr_url(best)


def _is_h265_item(item: dict) -> bool:
    return bool(item.get('is_h265') or item.get('is_bytevc1'))


def _bit_rate_data_size(item: dict) -> int:
    play_addr = item.get('play_addr')
    if not isinstance(play_addr, dict):
        return -1
    size = play_addr.get('data_size')
    return size if isinstance(size, int) else -1


def _play_addr_url(item: dict) -> str | None:
    play_addr = item.get('play_addr')
    if not isinstance(play_addr, dict):
        return None
    urls = play_addr.get('url_list') or []
    if isinstance(urls, list) and urls and isinstance(urls[0], str):
        return urls[0]
    return None
