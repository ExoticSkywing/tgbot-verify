"""验证命令处理器 —— 占位模式

验证模块（SheerID 认证等）暂未上线，所有命令返回友好提示。
未来替换为实际项目时，在此文件中接入新逻辑即可。
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from database_mysql import Database
from utils.checks import reject_group_command

logger = logging.getLogger(__name__)

# 统一的占位提示
_COMING_SOON_MSG = (
    "🚧 该功能正在开发中，即将上线\n\n"
    "💡 目前可用的功能：\n"
    "• /qd 每日签到\n"
    "• /invite 邀请好友\n"
    "• /balance 查看积分\n\n"
    "敬请期待 ✨"
)


async def _coming_soon(update: Update, context, db: Database):
    """通用占位处理：检查基本状态后返回即将上线提示"""
    if await reject_group_command(update):
        return
    user_id = update.effective_user.id
    if db.is_user_blocked(user_id):
        await update.message.reply_text("❌ 你已被限制使用此功能")
        return
    if not db.user_exists(user_id):
        await update.message.reply_text("请先使用 /start 注册")
        return
    await update.message.reply_text(_COMING_SOON_MSG)


# ---- 以下命令全部指向占位处理 ----

async def verify_command(update: Update, context, db: Database):
    """Gemini One Pro 认证（占位）"""
    await _coming_soon(update, context, db)


async def verify2_command(update: Update, context, db: Database):
    """ChatGPT Teacher K12 认证（占位）"""
    await _coming_soon(update, context, db)


async def verify3_command(update: Update, context, db: Database):
    """Spotify Student 认证（占位）"""
    await _coming_soon(update, context, db)


async def verify4_command(update: Update, context, db: Database):
    """Bolt.new Teacher 认证（占位）"""
    await _coming_soon(update, context, db)


async def verify5_command(update: Update, context, db: Database):
    """YouTube Student Premium 认证（占位）"""
    await _coming_soon(update, context, db)


async def getV4Code_command(update: Update, context, db: Database):
    """获取 Bolt.new 认证码（占位）"""
    await _coming_soon(update, context, db)
