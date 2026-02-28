"""绑定站点命令处理器 —— 小芽精灵"""
import logging
from urllib.parse import urlencode

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    OAUTH_CLIENT_ID, OAUTH_BASE_URL, OAUTH_REDIRECT_URI, BIND_REWARD
)
from database_mysql import Database
from utils.checks import reject_group_command

logger = logging.getLogger(__name__)


async def bind_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /bind 命令 — 绑定星小芽站点账号"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    # 检查是否已注册
    if not db.user_exists(user_id):
        await update.message.reply_text("请先使用 /start 注册")
        return

    # 检查是否已被拉黑
    if db.is_user_blocked(user_id):
        await update.message.reply_text("❌ 你已被限制使用此功能")
        return

    # 检查是否已绑定
    openid = db.get_wp_openid(user_id)
    if openid:
        await update.message.reply_text(
            "✅ 你已经绑定过星小芽站点账号啦\n\n"
            "如需解绑或更换账号，请联系管理员"
        )
        return

    # 检查 OAuth 配置是否就绪
    if not OAUTH_CLIENT_ID or not OAUTH_REDIRECT_URI:
        await update.message.reply_text("⚠️ 绑定功能暂未开放，请稍后再试")
        logger.warning("OAuth 配置不完整，无法生成绑定链接")
        return

    # 生成 state 并保存到数据库
    state = db.generate_bind_state(user_id)
    if not state:
        await update.message.reply_text("⚠️ 生成绑定链接失败，请稍后重试")
        return

    # 构造 OAuth 授权 URL
    params = {
        "response_type": "code",
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "state": state,
        "scope": "basic",
    }
    auth_url = f"{OAUTH_BASE_URL}/authorize?{urlencode(params)}"

    # 发送绑定消息（带按钮）
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 前往绑定", url=auth_url)]
    ])

    await update.message.reply_text(
        "🔗 绑定星小芽站点账号\n\n"
        "绑定后你可以：\n"
        "✅ 将 TG 积分兑换为站点积分，免费换好物\n"
        "✅ 邀请好友注册站点自动关联推荐关系\n"
        "✅ 在 TG 直接查看站点余额和积分\n\n"
        f"🎁 首次绑定还可获得 {BIND_REWARD} 积分奖励！\n\n"
        "👇 点击下方按钮前往绑定",
        reply_markup=keyboard
    )
