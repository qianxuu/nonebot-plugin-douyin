"""抖音链接识别与作品发送插件。"""

from importlib.metadata import PackageNotFoundError, version

from nonebot import get_driver
from nonebot.plugin import PluginMetadata

from .config import Config, is_configured

try:
    __version__ = version('nonebot-plugin-douyin')
except PackageNotFoundError:  # pragma: no cover - 源码未安装时的回退
    __version__ = '0.1.0'

__plugin_meta__ = PluginMetadata(
    name='抖音',
    description='自动识别聊天中的抖音链接，下载后发送视频 / 图文 / Live Photo',
    usage=(
        '在群聊或私聊中发送抖音链接，机器人自动解析：'
        '视频发视频，静态图发图片，Live Photo 发视频。\n'
        '需配置 DOUYIN_TTWID；可选 DOUYIN_GROUP_BLACKLIST / DOUYIN_NAPCAT_CACHE_DIR 等。\n'
        '依赖非公开接口，可能随时失效；请遵守平台条款与当地法律，勿未授权传播他人内容。'
    ),
    type='application',
    homepage='https://github.com/qianxuu/nonebot-plugin-douyin',
    config=Config,
    supported_adapters={'~onebot.v11'},
    extra={
        'author': 'qianxu',
        'version': __version__,
        'license': 'MIT',
    },
)

from . import handler as _handler  # noqa: E402, F401


@get_driver().on_startup
async def _on_startup() -> None:
    from nonebot import logger

    if not is_configured():
        logger.warning('[抖音] 未配置 DOUYIN_TTWID，作品解析不可用；请在 .env 中设置后重启')


@get_driver().on_shutdown
async def _on_shutdown() -> None:
    from .client import close_client

    await close_client()
