"""用户命令处理器 —— 小芽精灵"""
import logging
from typing import Optional
from urllib.parse import quote

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    ADMIN_USER_ID, CHECKIN_REWARD, INVITE_REWARD, REGISTER_REWARD,
    OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_BASE_URL,
)
from database_mysql import Database
from utils.checks import reject_group_command
from utils.messages import (
    get_welcome_message,
    get_about_message,
    get_help_message,
)

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /start 命令"""
    if await reject_group_command(update):
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    full_name = user.full_name or ""

    # deep link: /start bind → 自动注册 + 触发绑定流程
    if context.args and context.args[0] == "bind":
        if not db.user_exists(user_id):
            db.create_user(user_id, username, full_name, None)
        from handlers.bind_command import bind_command
        await bind_command(update, context, db=db)
        return

    # 已初始化直接返回
    if db.user_exists(user_id):
        await update.message.reply_text(
            f"🌱 欢迎回来，{full_name}！\n"
            "小芽精灵一直在等你 ✨\n"
            "发送 /help 查看可用命令"
        )
        return

    # 邀请参与
    invited_by: Optional[int] = None
    if context.args:
        try:
            invited_by = int(context.args[0])
            if not db.user_exists(invited_by):
                invited_by = None
        except Exception:
            invited_by = None

    # 创建用户
    if db.create_user(user_id, username, full_name, invited_by):
        welcome_msg = get_welcome_message(full_name, bool(invited_by))
        await update.message.reply_text(welcome_msg)
    else:
        await update.message.reply_text("注册失败，请稍后重试。")


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /about 命令"""
    if await reject_group_command(update):
        return

    await update.message.reply_text(get_about_message())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /help 命令"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_USER_ID
    await update.message.reply_text(get_help_message(is_admin))


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /balance 命令 — 查看 TG 积分 + 站点积分"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("您已被拉黑，无法使用此功能。")
        return

    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("请先使用 /start 注册。")
        return

    tg_balance = user['balance']

    # 查询站点积分（仅已绑定用户）
    openid = db.get_wp_openid(user_id)
    site_text = ""
    if openid and OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET:
        try:
            import hashlib
            sign_str = f"{OAUTH_CLIENT_ID}{openid}{OAUTH_CLIENT_SECRET}"
            sign = hashlib.md5(sign_str.encode()).hexdigest()

            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{OAUTH_BASE_URL}/points/balance",
                    params={
                        "appid": OAUTH_CLIENT_ID,
                        "openid": openid,
                        "sign": sign,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    site_points = data.get("points", "?")
                    site_text = f"🌱 站点积分：{site_points} 分\n"
        except Exception as e:
            logger.warning(f"查询站点积分失败: {e}")

    # 组装消息
    bind_hint = ""
    if not openid:
        bind_hint = "\n💡 使用 /bind 绑定站点，即可查看站点积分"

    await update.message.reply_text(
        f"🌱 小芽精灵 · 积分\n\n"
        f"💰 TG 积分：{tg_balance} 分\n"
        f"{site_text}"
        f"{bind_hint}\n"
        "获取更多积分：\n"
        "/bind 绑定站点 · /invite 邀请好友 · /qd 签到"
    )


async def checkin_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /qd 签到命令 - 临时禁用"""
    user_id = update.effective_user.id

    # 临时禁用签到功能（修复bug中）
    # await update.message.reply_text(
    #     "⚠️ 签到功能临时维护中\n\n"
    #     "由于发现bug，签到功能暂时关闭，正在修复。\n"
    #     "预计很快恢复，给您带来不便敬请谅解。\n\n"
    #     "💡 您可以通过以下方式获取积分：\n"
    #     "• 邀请好友 /invite（+2积分）\n"
    #     "• 使用卡密 /use <卡密>"
    # )
    # return
    
    # ===== 以下代码已禁用 =====
    if db.is_user_blocked(user_id):
        await update.message.reply_text("您已被拉黑，无法使用此功能。")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("请先使用 /start 注册。")
        return

    # 第1层检查：在命令处理器层面检查
    if not db.can_checkin(user_id):
        await update.message.reply_text("❌ 今天已经签到过了，明天再来吧。")
        return

    # 第2层检查：在数据库层面执行（SQL原子操作）
    if db.checkin(user_id):
        user = db.get_user(user_id)
        await update.message.reply_text(
            f"🌱 签到成功！\n\n🎁 获得积分：+{CHECKIN_REWARD}\n💰 当前积分：{user['balance']} 分\n\n明天记得再来哦 ✨"
        )
    else:
        # 如果数据库层面返回False，说明今天已签到（双重保险）
        await update.message.reply_text("❌ 今天已经签到过了，明天再来吧。")


async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /invite 邀请命令"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("您已被拉黑，无法使用此功能。")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("请先使用 /start 注册。")
        return

    bot_username = context.bot.username
    invite_link = f"https://t.me/{bot_username}?start={user_id}"

    # 转发分享 URL（点击后弹出 TG 转发选择器）
    share_text = quote("🌱 来星小芽探索吧！注册即送积分，免费换好物 ✨")
    share_url = f"https://t.me/share/url?url={quote(invite_link)}&text={share_text}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 转发给好友", url=share_url)]
    ])

    await update.message.reply_text(
        f"🌱 小芽精灵 · 邀请好友\n\n"
        f"🔗 你的专属邀请链接：\n`{invite_link}`\n\n"
        f"💝 每邀请 1 位好友注册，你将获得 {INVITE_REWARD} 积分\n"
        "分享给朋友，一起来星小芽探索吧！",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def use_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /use 命令 - 使用卡密"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("您已被拉黑，无法使用此功能。")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("请先使用 /start 注册。")
        return

    if not context.args:
        await update.message.reply_text(
            "使用方法: /use <卡密>\n\n示例: /use wandouyu"
        )
        return

    key_code = context.args[0].strip()
    result = db.use_card_key(key_code, user_id)

    if result is None:
        await update.message.reply_text("❌ 卡密不存在，请检查后重试")
    elif result == -1:
        await update.message.reply_text("❌ 该卡密已达到使用次数上限")
    elif result == -2:
        await update.message.reply_text("❌ 该卡密已过期")
    elif result == -3:
        await update.message.reply_text("❌ 你已经使用过该卡密")
    else:
        user = db.get_user(user_id)
        await update.message.reply_text(
            f"🎉 卡密兑换成功！\n\n🎁 获得积分：+{result}\n💰 当前积分：{user['balance']} 分"
        )
