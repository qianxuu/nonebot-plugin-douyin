# nonebot-plugin-douyin

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![NoneBot2](https://img.shields.io/badge/NoneBot-2-red.svg)](https://nonebot.dev/)
[![OneBot](https://img.shields.io/badge/OneBot-V11-black.svg)](https://onebot.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![CI](https://github.com/qianxuu/nonebot-plugin-douyin/actions/workflows/ci.yml/badge.svg)](https://github.com/qianxuu/nonebot-plugin-douyin/actions/workflows/ci.yml)
<!-- 发布到 PyPI 后可取消下一行注释
[![PyPI](https://img.shields.io/pypi/v/nonebot-plugin-douyin.svg)](https://pypi.org/project/nonebot-plugin-douyin/)
-->

NoneBot2 插件：自动识别聊天中的抖音链接，下载后发送视频，或直接发送图文 / Live Photo。

> **免责声明**：仅供学习与自用。请遵守抖音平台服务条款与当地法律法规，勿用于未授权传播他人内容。本插件与抖音 / 字节跳动无官方关联；依赖非公开 Web 接口与用户自行配置的 Cookie，**可能随时失效，不保证长期可用**。作者不对滥用、账号风控、版权纠纷或服务中断承担责任。使用本插件即表示你理解并自行承担相关风险。

## 功能

- 识别群聊 / 私聊纯文本中的抖音链接
- 普通视频：下载后发送视频
- 静态图文：单图直接发送；多图（≥2）合并转发
- Live Photo：单张发送视频；多张（≥2）合并转发
- 群冷却、群黑名单、本地缓存与过期清理
- 可选 NapCat 缓存目录映射，跳过 WS 流式上传

## 环境要求

- Python 3.12+
- [NoneBot2](https://nonebot.dev/)
- [OneBot V11 适配器](https://onebot.adapters.nonebot.dev/)
- 发送视频推荐 [NapCat](https://github.com/NapNeko/NapCatQQ)；未配置缓存映射时回退 `upload_file_stream`
- 多图 / 多 Live Photo 依赖实现提供的 `send_forward_msg`
- 机器人宿主需自行安装 driver（常见为 `nonebot2[fastapi]`）

## 安装

### 使用 nb-cli

```bash
nb plugin install nonebot-plugin-douyin
```

### 使用 pip / uv

```bash
pip install nonebot-plugin-douyin
# 或
uv add nonebot-plugin-douyin
```

### 从 Git 安装

```bash
uv add git+https://github.com/qianxuu/nonebot-plugin-douyin
# 或指定本地路径
uv add /path/to/nonebot-plugin-douyin
```

在 `pyproject.toml` 中加载：

```toml
[tool.nonebot]
plugins = ["nonebot_plugin_douyin"]
```

或在引导文件中：

```python
nonebot.load_plugin('nonebot_plugin_douyin')
```

### 本地开发

```bash
git clone https://github.com/qianxuu/nonebot-plugin-douyin.git
cd nonebot-plugin-douyin
uv sync --group dev
```

## 支持的链接

- `https://v.douyin.com/...`
- `https://www.douyin.com/video/<aweme_id>`
- `https://www.douyin.com/note/<aweme_id>`
- `https://www.douyin.com/slides/<aweme_id>`

仅匹配消息**纯文本**中的链接；分享卡片等非纯文本形态暂不支持。

## 行为说明

- 同一 `aweme_id` 在同一群内默认冷却 `60` 秒；配置为 `0` 表示不冷却
- 视频超过默认 `50 MiB` 时跳过下载和发送
- 静态图片优先使用远程地址直接发送，不落盘
- 图文 / Live Photo 数量 ≥ 2 时使用 `send_forward_msg` 合并转发
- Live Photo 与多段视频缓存名为 `{aweme_id}_{index}.mp4`，纯视频为 `{aweme_id}.mp4`
- 本地缓存目录：`cache/douyin`（相对机器人工作目录）
- 下载前清理超过保留时长的缓存（默认 24 小时）
- 解析失败等情况写日志并静默跳过，避免刷屏
- 未配置 `DOUYIN_TTWID` 时启动 warning，解析不可用

## 配置

复制 [`.env.example`](./.env.example) 到机器人项目的 `.env`，字段名对应 `DOUYIN_*`（大小写不敏感）。

| 配置项 | 必需 | 默认 | 说明 |
|---|---|---|---|
| `DOUYIN_TTWID` | 是 | 空 | 抖音 Web 接口 Cookie `ttwid` |
| `DOUYIN_GROUP_BLACKLIST` | 否 | `[]` | 群黑名单，JSON 数组 |
| `DOUYIN_NAPCAT_CACHE_DIR` | 否 | 空 | NapCat 容器内缓存目录 |
| `DOUYIN_MAX_VIDEO_SIZE_MIB` | 否 | `50` | 跳过下载的视频大小上限（MiB） |
| `DOUYIN_GROUP_CD_SECONDS` | 否 | `60` | 同群同作品冷却秒数，`0` 表示不冷却 |
| `DOUYIN_CACHE_RETENTION_HOURS` | 否 | `24` | 本地缓存保留小时数 |

### 完整示例

```env
DOUYIN_TTWID=your_ttwid_value
DOUYIN_GROUP_BLACKLIST=["123456789", "987654321"]
DOUYIN_NAPCAT_CACHE_DIR=/app/.config/QQ/NapCat/temp
DOUYIN_MAX_VIDEO_SIZE_MIB=50
DOUYIN_GROUP_CD_SECONDS=60
DOUYIN_CACHE_RETENTION_HOURS=24
```

`ttwid` 可在浏览器登录 `www.douyin.com` 后，从开发者工具 Cookie 中复制。**请勿把真实 Cookie 提交到公开仓库或写进聊天记录。**

配置 `DOUYIN_NAPCAT_CACHE_DIR` 时，请确保机器人进程的 `cache/douyin` 与 NapCat 该目录为同一挂载或可互相访问。

## 目录结构

```text
nonebot-plugin-douyin/
├── src/nonebot_plugin_douyin/
│   ├── __init__.py   # 元数据、启停钩子
│   ├── handler.py    # 链接匹配入口
│   ├── api.py        # 作品解析
│   ├── client.py     # HTTP 客户端
│   ├── config.py     # 配置模型
│   ├── download.py   # 分片下载与缓存
│   ├── send.py       # 发送逻辑
│   ├── upload.py     # NapCat 流式上传
│   └── utils.py
├── tests/
├── .env.example
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
└── README.md
```

## 故障排查

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 启动 warning：未配置 `DOUYIN_TTWID` | 环境变量缺失 | 配置 `.env` 后重启 |
| 接口未返回作品详情 | ttwid 失效 / 风控 / 接口变更 | 更新 ttwid，查看日志 |
| 视频不发送 | 超过大小限制 / 下载失败 | 调大上限或检查下载日志 |
| 发送慢或失败 | 未配置 NapCat 映射 | 配置目录映射与挂载 |
| 群内不响应 | 黑名单或冷却中 | 检查相关配置 |
| 合并转发失败 | 实现未提供 `send_forward_msg` | 更换支持的 OneBot 实现（如 NapCat） |

## 已知限制

- 依赖非公开 Web 接口，签名参数与 Cookie 策略可能随时变更，**不承诺长期可用**
- 不处理分享卡片等非纯文本消息
- 不发送作品标题 / 作者信息，仅发送媒体本体
- 合并转发与流式上传依赖具体 OneBot 实现（如 NapCat）
- 大视频受 `DOUYIN_MAX_VIDEO_SIZE_MIB` 与宿主上传能力共同限制

## 开发

```bash
uv sync --group dev
uv run pytest
uv run ty check src/nonebot_plugin_douyin tests
uv run ruff check .
uv run ruff format .
uv build
uv run twine check dist/*
```

## 安全提示

- 切勿在仓库、Issue、截图中泄露真实 `ttwid` 或其他 Cookie
- 生产环境建议限制群范围（黑名单 / 冷却），避免被刷链导致带宽与风控压力
- 缓存目录可能包含他人作品文件，请勿公开分享 `cache/`

## License

[MIT](./LICENSE)
