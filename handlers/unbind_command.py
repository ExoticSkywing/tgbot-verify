"""解绑站点命令处理器 —— 小芽精灵

/unbind 双模式：
  - 普通用户：发起解绑申请 → 管理员审批
  - 管理员：/unbind <tg_uid> 直接解绑
"""
import logging
import hashlib

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_BASE_URL, ADMIN_USER_ID
from database_mysql import Database
from utils.checks import reject_group_command

logger = logging.getLogger(__name__)


# ─── WP 侧清理 ────────────────────────────────────────

async def _clear_wp_tg_meta(tg_uid: int):
    """通过 WP REST API 清除 WP 侧的 TG 绑定 meta"""
    try:
        tg_uid_str = str(tg_uid)
        sign = hashlib.md5(
            (OAUTH_CLIENT_ID + tg_uid_str + OAUTH_CLIENT_SECRET).encode()
        ).hexdigest()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{OAUTH_BASE_URL}/user/unbindtg",
                data={
                    "appid": OAUTH_CLIENT_ID,
                    "tg_uid": tg_uid_str,
                    "sign": sign,
                },
            )
        if resp.status_code == 200:
            logger.info(f"[unbind] WP 侧 TG meta 清除成功: tg_uid={tg_uid}")
            return True
        else:
            logger.warning(f"[unbind] WP 侧清除失败: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.error(f"[unbind] WP API 调用失败: {e}")
        return False


async def _do_unbind(tg_uid: int, db: Database) -> bool:
    """执行双向解绑（WP + 精灵 DB）"""
    await _clear_wp_tg_meta(tg_uid)
    return db.unbind_wp_account(tg_uid)


# ─── /unbind 命令入口 ──────────────────────────────────

async def unbind_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """
    /unbind — 双模式命令
      管理员 + 带参数: /unbind <tg_uid>  → 直接解绑
      普通用户（或管理员无参数）: → 发起解绑申请
    """
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    is_admin = (user_id == ADMIN_USER_ID)

    # ── 管理员模式：/unbind <tg_uid> ──
    if is_admin and context.args:
        try:
            target_uid = int(context.args[0])
        except ValueError:
            await update.message.reply_text("参数格式错误，请输入有效的用户ID。")
            return

        if not db.user_exists(target_uid):
            await update.message.reply_text("用户不存在。")
            return

        openid = db.get_wp_openid(target_uid)
        if not openid:
            await update.message.reply_text(f"用户 {target_uid} 未绑定站点账号，无需解绑。")
            return

        success = await _do_unbind(target_uid, db)
        if success:
            target_user = db.get_user(target_uid)
            uname = target_user.get("username", "") if target_user else ""
            await update.message.reply_text(
                f"✅ 已解绑用户 {target_uid}"
                + (f" (@{uname})" if uname else "")
                + f"\n原绑定 openid: {openid}"
            )
            # 通知被解绑用户
            try:
                await context.bot.send_message(
                    chat_id=target_uid,
                    text=(
                        "🔓 你的星小芽站点绑定已由管理员解除。\n\n"
                        "如需重新绑定，请发送 /bind"
                    ),
                )
            except Exception:
                pass
            logger.info(f"[unbind] 管理员解绑用户 {target_uid}")
        else:
            await update.message.reply_text("操作失败，请稍后重试。")
        return

    # ── 用户模式：申请解绑 ──
    if not db.user_exists(user_id):
        await update.message.reply_text("请先使用 /start 注册")
        return

    openid = db.get_wp_openid(user_id)
    if not openid:
        await update.message.reply_text("❌ 你还没有绑定站点账号，无需解绑")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📮 申请解绑", callback_data=f"unbind_apply_{user_id}")]
    ])

    await update.message.reply_text(
        "⚠️ 解绑操作需要管理员审批\n\n"
        "解绑后：\n"
        "• 无法使用 /exchange 兑换站点积分\n"
        "• 需要重新 /bind 才能恢复关联\n"
        "• 绑定奖励不会重复发放\n\n"
        "👇 点击下方按钮提交解绑申请",
        reply_markup=keyboard,
    )


# ─── 回调处理 ──────────────────────────────────────────

async def unbind_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理所有 unbind_ 开头的回调"""
    query = update.callback_query
    await query.answer()

    data = query.data

    # ── 用户点击「申请解绑」 ──
    if data.startswith("unbind_apply_"):
        target_uid = int(data.replace("unbind_apply_", ""))
        caller_uid = query.from_user.id

        if target_uid != caller_uid:
            await query.edit_message_text("❌ 无法代他人提交申请")
            return

        user = db.get_user(target_uid)
        uname = user.get("username", "—") if user else "—"
        fname = user.get("full_name", "—") if user else "—"

        await query.edit_message_text("📮 解绑申请已提交，请等待管理员审批")

        # 通知管理员
        admin_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ 批准解绑", callback_data=f"unbind_approve_{target_uid}"),
                InlineKeyboardButton("❌ 拒绝", callback_data=f"unbind_reject_{target_uid}"),
            ]
        ])
        try:
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=(
                    f"📋 解绑申请\n\n"
                    f"用户 ID：{target_uid}\n"
                    f"用户名：@{uname}\n"
                    f"显示名：{fname}\n\n"
                    f"👇 请审批"
                ),
                reply_markup=admin_kb,
            )
        except Exception as e:
            logger.error(f"[unbind] 通知管理员失败: {e}")

        logger.info(f"[unbind] 用户 {target_uid} (@{uname}) 提交解绑申请")
        return

    # ── 管理员批准 ──
    if data.startswith("unbind_approve_"):
        if query.from_user.id != ADMIN_USER_ID:
            return

        target_uid = int(data.replace("unbind_approve_", ""))
        success = await _do_unbind(target_uid, db)

        if success:
            await query.edit_message_text(
                query.message.text + "\n\n✅ 已批准，解绑完成"
            )
            # 通知用户
            try:
                await context.bot.send_message(
                    chat_id=target_uid,
                    text=(
                        "✅ 你的解绑申请已通过！\n\n"
                        "TG 账号已与星小芽站点解除关联。\n"
                        "如需重新绑定，请发送 /bind"
                    ),
                )
            except Exception:
                pass
            logger.info(f"[unbind] 管理员批准解绑用户 {target_uid}")
        else:
            await query.edit_message_text(
                query.message.text + "\n\n❌ 解绑失败（用户可能已解绑）"
            )
        return

    # ── 管理员拒绝 ──
    if data.startswith("unbind_reject_"):
        if query.from_user.id != ADMIN_USER_ID:
            return

        target_uid = int(data.replace("unbind_reject_", ""))
        await query.edit_message_text(
            query.message.text + "\n\n❌ 已拒绝"
        )
        # 通知用户
        try:
            await context.bot.send_message(
                chat_id=target_uid,
                text="❌ 你的解绑申请已被管理员拒绝。\n如有疑问请联系管理员。",
            )
        except Exception:
            pass
        logger.info(f"[unbind] 管理员拒绝解绑用户 {target_uid}")
        return
