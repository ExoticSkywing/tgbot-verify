"""全局配置文件 —— 小芽精灵"""
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# Telegram Bot 配置
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "pk_oa")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/pk_oa")

# 管理员配置
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "123456789"))

# 积分配置
REGISTER_REWARD = 20    # 注册奖励积分
CHECKIN_REWARD = 75     # 签到奖励积分
INVITE_REWARD = 80      # 邀请奖励积分
BIND_REWARD = 120       # 绑定站点奖励积分
VERIFY_COST = 1         # 验证消耗积分（占位，未来使用）
EXCHANGE_RATE = 1       # 兑换比例：1 TG积分 = 1 站点积分

# OAuth 配置（zibll-oauth 应用）
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "")
OAUTH_BASE_URL = os.getenv("OAUTH_BASE_URL", "https://xingxy.manyuzo.com/wp-json/zibll-oauth/v1")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "")
OAUTH_CALLBACK_PORT = int(os.getenv("OAUTH_CALLBACK_PORT", "8443"))

# 帮助链接
HELP_NOTION_URL = "https://rhetorical-era-3f3.notion.site/dd78531dbac745af9bbac156b51da9cc"
