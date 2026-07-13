"""测试公共初始化。"""

import nonebot

# 插件配置依赖 NoneBot 全局 driver；测试使用空 driver，无需 FastAPI。
nonebot.init(driver='~none')
