from pathlib import Path

from nonebot import get_plugin_config
from pydantic import Field, BaseModel, field_validator


class Config(BaseModel):
    """抖音插件配置（字段名对应 .env 中的 DOUYIN_*，大小写不敏感）"""

    douyin_ttwid: str = ''
    douyin_group_blacklist: set[int] = Field(default_factory=set)
    douyin_napcat_cache_dir: Path | None = None
    # 超过该大小的视频跳过下载（MiB）
    douyin_max_video_size_mib: float = 50
    # 同一 aweme 在同一群的冷却秒数
    douyin_group_cd_seconds: int = 60
    # 本地缓存保留时长（小时）
    douyin_cache_retention_hours: float = 24

    @field_validator('douyin_ttwid', mode='before')
    @classmethod
    def _strip_ttwid(cls, value: object) -> str:
        return str(value or '').strip()

    @field_validator('douyin_napcat_cache_dir', mode='before')
    @classmethod
    def _empty_path_to_none(cls, value: object) -> object:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    @field_validator('douyin_max_video_size_mib')
    @classmethod
    def _positive_max_video_size(cls, value: float) -> float:
        if value <= 0:
            raise ValueError('douyin_max_video_size_mib 必须大于 0')
        return value

    @field_validator('douyin_group_cd_seconds')
    @classmethod
    def _non_negative_cd(cls, value: int) -> int:
        if value < 0:
            raise ValueError('douyin_group_cd_seconds 不能为负数')
        return value

    @field_validator('douyin_cache_retention_hours')
    @classmethod
    def _positive_retention(cls, value: float) -> float:
        if value <= 0:
            raise ValueError('douyin_cache_retention_hours 必须大于 0')
        return value


_SETTINGS = get_plugin_config(Config)
DOUYIN_NAPCAT_CACHE_DIR = _SETTINGS.douyin_napcat_cache_dir
DOUYIN_GROUP_BLACKLIST = _SETTINGS.douyin_group_blacklist
DOUYIN_TTWID = _SETTINGS.douyin_ttwid
DOUYIN_MAX_VIDEO_SIZE = int(_SETTINGS.douyin_max_video_size_mib * 1024 * 1024)
DOUYIN_GROUP_CD_SECONDS = _SETTINGS.douyin_group_cd_seconds
DOUYIN_CACHE_RETENTION_SECONDS = int(_SETTINGS.douyin_cache_retention_hours * 3600)


def is_configured() -> bool:
    """是否已配置解析作品所需的 ttwid。"""

    return bool(DOUYIN_TTWID)


def get_napcat_cache_file_path(file_path: Path) -> Path | None:
    """将本地缓存文件路径映射为 NapCat 容器内路径，未配置则返回 None"""

    if DOUYIN_NAPCAT_CACHE_DIR is None:
        return None
    return DOUYIN_NAPCAT_CACHE_DIR / file_path.name
