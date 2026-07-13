from pathlib import Path

import pytest
from pydantic import ValidationError

from nonebot_plugin_douyin import config as config_mod
from nonebot_plugin_douyin.config import Config, is_configured, get_napcat_cache_file_path


def test_config_parses_fields():
    cfg = Config.model_validate(
        {
            'douyin_ttwid': '  abc  ',
            'douyin_group_blacklist': [123, 456],
            'douyin_napcat_cache_dir': '/tmp/cache',
            'douyin_max_video_size_mib': 80,
            'douyin_group_cd_seconds': 30,
            'douyin_cache_retention_hours': 12,
        }
    )
    assert cfg.douyin_ttwid == 'abc'
    assert cfg.douyin_group_blacklist == {123, 456}
    assert cfg.douyin_napcat_cache_dir == Path('/tmp/cache')
    assert cfg.douyin_max_video_size_mib == 80
    assert cfg.douyin_group_cd_seconds == 30
    assert cfg.douyin_cache_retention_hours == 12


def test_config_empty_path_becomes_none():
    cfg = Config.model_validate(
        {
            'douyin_ttwid': '',
            'douyin_group_blacklist': [],
            'douyin_napcat_cache_dir': '   ',
        }
    )
    assert cfg.douyin_ttwid == ''
    assert cfg.douyin_group_blacklist == set()
    assert cfg.douyin_napcat_cache_dir is None


def test_config_defaults():
    cfg = Config.model_validate({})
    assert cfg.douyin_ttwid == ''
    assert cfg.douyin_group_blacklist == set()
    assert cfg.douyin_napcat_cache_dir is None
    assert cfg.douyin_max_video_size_mib == 50
    assert cfg.douyin_group_cd_seconds == 60
    assert cfg.douyin_cache_retention_hours == 24


def test_config_rejects_invalid_limits():
    with pytest.raises(ValidationError):
        Config.model_validate({'douyin_max_video_size_mib': 0})
    with pytest.raises(ValidationError):
        Config.model_validate({'douyin_group_cd_seconds': -1})
    with pytest.raises(ValidationError):
        Config.model_validate({'douyin_cache_retention_hours': 0})


def test_is_configured():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config_mod, 'DOUYIN_TTWID', '')
        assert is_configured() is False
        mp.setattr(config_mod, 'DOUYIN_TTWID', 'x')
        assert is_configured() is True


def test_get_napcat_cache_file_path():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config_mod, 'DOUYIN_NAPCAT_CACHE_DIR', None)
        assert get_napcat_cache_file_path(Path('/a/b.mp4')) is None

        mp.setattr(config_mod, 'DOUYIN_NAPCAT_CACHE_DIR', Path('/napcat'))
        assert get_napcat_cache_file_path(Path('/a/b.mp4')) == Path('/napcat/b.mp4')
