# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

## [0.1.1] - 2026-07-31

### 修复 / 改进

- 分片下载与超限判断改用 API 返回的 `bit_rate.play_addr.data_size`，移除 `Content-Length` 探测

### 文档

- README 启用 PyPI 版本徽章
- 强化接口可用性与 Cookie 安全提示
- 补充故障排查与安全说明

### 构建 / CI

- 升级 `actions/checkout@v7` 与 `astral-sh/setup-uv@v7`
- sdist 纳入 `CHANGELOG.md`、`.env.example`、测试源码等
- 开发依赖增加 `twine`，便于发布前校验

## [0.1.0] - 2026-07-12

### 新增

- 识别抖音短链与 `video` / `note` / `slides` 链接
- 支持普通视频、静态图文、Live Photo 发送
- 群冷却、群黑名单、本地缓存与过期清理
- 可选 NapCat 缓存目录映射，跳过 WS 流式上传
- 可配置视频大小上限、冷却时间、缓存保留时长

### 说明

- 首个面向独立开源分发的版本
- 解析依赖 `DOUYIN_TTWID` 与抖音 Web 接口，接口可能变更，不保证长期可用

[Unreleased]: https://github.com/qianxuu/nonebot-plugin-douyin/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/qianxuu/nonebot-plugin-douyin/releases/tag/v0.1.1
[0.1.0]: https://github.com/qianxuu/nonebot-plugin-douyin/releases/tag/v0.1.0
