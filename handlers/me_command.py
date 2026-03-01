"""个人信息命令处理器 —— 小芽精灵

/me 命令：展示 TG 信息 + 站点信息（已绑定用户）
"""
import hashlib
import logging

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from config import OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_BASE_URL
from database_mysql import Database
from utils.checks import reject_group_command

logger = logging.getLogger(__name__)


async def me_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /me 命令 — 查看个人信息"""
    if await reject_group_command(update):
        return

    tg_user = update.effective_user
    user_id = tg_user.id

    # 检查是否已注册
    if not db.user_exists(user_id):
        await update.message.reply_text("请先使用 /start 注册。")
        return

    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("请先使用 /start 注册。")
        return

    # ── TG 信息 ──
    username = user.get("username", "")
    full_name = user.get("full_name", "")
    created_at = user.get("created_at", "")
    last_checkin = user.get("last_checkin", "")
    invite_count = db.get_invite_count(user_id)

    # 格式化日期（保留到分钟 YYYY-MM-DD HH:MM）
    if created_at:
        created_at = str(created_at).replace("T", " ")[:16]
    if last_checkin:
        last_checkin = str(last_checkin).replace("T", " ")[:16]

    # 用户名展示
    name_display = full_name
    if username:
        name_display = f"{full_name} (@{username})"

    # 绑定状态
    openid = db.get_wp_openid(user_id)
    bind_status = "✅ 已绑定" if openid else "❌ 未绑定（/bind）"

    # 签到展示
    checkin_display = last_checkin if last_checkin else "暂未签到"

    tg_section = (
        f"── TG 信息 ──\n"
        f"🆔 {user_id}\n"
        f"🎭 {name_display}\n"
        f"📅 注册时间：{created_at}\n"
        f"🕐 上次签到：{checkin_display}\n"
        f"👥 邀请好友：{invite_count} 人\n"
        f"🔗 站点绑定：{bind_status}"
    )

    # ── 站点信息 ──（仅已绑定用户）
    site_section = ""
    if openid and OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET:
        try:
            sign_str = f"{OAUTH_CLIENT_ID}{openid}{OAUTH_CLIENT_SECRET}"
            sign = hashlib.md5(sign_str.encode()).hexdigest()

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{OAUTH_BASE_URL}/user/profile",
                    params={
                        "appid": OAUTH_CLIENT_ID,
                        "openid": openid,
                        "sign": sign,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    site_name = data.get("display_name", "?")
                    site_invites = data.get("invite_count", 0)
                    site_section = (
                        f"\n\n── 站点信息 ──\n"
                        f"🌱 站点昵称：{site_name}\n"
                        f"👥 推荐好友：{site_invites} 人"
                    )
        except Exception as e:
            logger.warning(f"查询站点个人信息失败: {e}")

    await update.message.reply_text(
        f"👤 个人信息\n\n{tg_section}{site_section}"
    )
