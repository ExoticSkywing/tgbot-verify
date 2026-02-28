"""积分兑换命令处理器 —— 小芽精灵

将 TG 积分兑换为站点积分（1:1 比例）
"""
import hashlib
import logging

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from config import (
    OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_BASE_URL, EXCHANGE_RATE
)
from database_mysql import Database
from utils.checks import reject_group_command

logger = logging.getLogger(__name__)


async def exchange_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /exchange 命令 — 将 TG 积分兑换为站点积分"""
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

    # 检查是否已绑定站点
    openid = db.get_wp_openid(user_id)
    if not openid:
        await update.message.reply_text(
            "⚠️ 请先使用 /bind 绑定星小芽站点账号\n"
            "绑定后才能兑换积分"
        )
        return

    # 解析兑换数量
    if not context.args or len(context.args) < 1:
        user = db.get_user(user_id)
        balance = user["balance"] if user else 0
        await update.message.reply_text(
            "🔄 积分兑换\n\n"
            f"💰 当前 TG 积分：{balance} 分\n"
            f"📐 兑换比例：{EXCHANGE_RATE} TG积分 = 1 站点积分\n\n"
            "用法：`/exchange <数量>`\n"
            "示例：`/exchange 300`\n\n"
            "兑换后 TG 积分将扣除，站点积分同步增加",
            parse_mode="Markdown"
        )
        return

    try:
        amount = int(context.args[0])
    except (ValueError, IndexError):
        await update.message.reply_text("❌ 请输入有效的数字\n\n用法：`/exchange 300`", parse_mode="Markdown")
        return

    if amount <= 0:
        await update.message.reply_text("❌ 兑换数量必须大于 0")
        return

    if amount > 10000:
        await update.message.reply_text("❌ 单次兑换不能超过 10000 积分")
        return

    # 检查 TG 积分是否充足
    user = db.get_user(user_id)
    if not user or user["balance"] < amount:
        current = user["balance"] if user else 0
        await update.message.reply_text(
            f"😢 TG 积分不足\n\n"
            f"需要：{amount} 积分\n"
            f"当前：{current} 积分\n\n"
            "💡 获取积分：/bind 绑定站点 · /invite 邀请好友 · /qd 签到"
        )
        return

    # 检查 OAuth 配置
    if not OAUTH_CLIENT_ID or not OAUTH_CLIENT_SECRET:
        await update.message.reply_text("⚠️ 兑换功能暂未开放")
        logger.warning("OAuth 配置不完整，无法兑换积分")
        return

    # 计算站点积分（按兑换比例）
    site_points = amount // EXCHANGE_RATE

    # 生成签名：md5(appid + openid + site_points + appkey)
    sign_str = f"{OAUTH_CLIENT_ID}{openid}{site_points}{OAUTH_CLIENT_SECRET}"
    sign = hashlib.md5(sign_str.encode()).hexdigest()

    # 调用站点 API 充值积分
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OAUTH_BASE_URL}/points/add",
                data={
                    "appid": OAUTH_CLIENT_ID,
                    "openid": openid,
                    "amount": site_points,
                    "desc": f"TG Bot 兑换 ({amount} TG积分)",
                    "sign": sign,
                },
            )

            if resp.status_code != 200:
                error_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = error_data.get("message", resp.text[:100])
                logger.error(f"积分兑换 API 失败: {resp.status_code} {error_msg}")
                await update.message.reply_text(f"❌ 兑换失败：{error_msg}\n\n请稍后重试")
                return

            result = resp.json()

    except Exception as e:
        logger.error(f"积分兑换请求异常: {e}")
        await update.message.reply_text("❌ 兑换请求失败，请稍后重试")
        return

    # API 调用成功，扣除 TG 积分
    if not db.deduct_balance(user_id, amount):
        logger.error(f"TG 积分扣除失败: user={user_id}, amount={amount}")
        await update.message.reply_text("⚠️ 站点积分已充值，但 TG 积分扣除异常，请联系管理员")
        return

    # 获取更新后的余额
    user = db.get_user(user_id)
    tg_balance = user["balance"] if user else "?"
    site_balance = result.get("points", "?")

    await update.message.reply_text(
        "🎉 兑换成功！\n\n"
        f"📤 消耗 TG 积分：-{amount}\n"
        f"📥 获得站点积分：+{site_points}\n\n"
        f"💰 TG 积分余额：{tg_balance} 分\n"
        f"🌱 站点积分余额：{site_balance} 分"
    )
