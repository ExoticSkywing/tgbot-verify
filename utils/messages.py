"""消息模板 —— 小芽精灵（星小芽 Telegram 助手）"""
from config import (
    CHANNEL_URL, VERIFY_COST, HELP_NOTION_URL,
    REGISTER_REWARD, CHECKIN_REWARD, INVITE_REWARD, BIND_REWARD
)


def get_welcome_message(full_name: str, invited_by: bool = False) -> str:
    """获取欢迎消息"""
    msg = (
        f"🌱 欢迎来到星小芽，{full_name}！\n"
        "我是「小芽精灵」，你的专属助手 ✨\n\n"
        f"🎁 注册成功，已赠送 {REGISTER_REWARD} 积分\n"
    )
    if invited_by:
        msg += f"💝 通过好友邀请加入，邀请人已获得 {INVITE_REWARD} 积分奖励\n"

    msg += (
        "\n🚀 快速开始：\n"
        "/about - 了解小芽精灵\n"
        "/balance - 查看积分余额\n"
        "/bind - 绑定站点账号\n"
        "/help - 完整命令列表\n\n"
        "💰 获取更多积分：\n"
        f"/bind - 绑定站点 +{BIND_REWARD}\n"
        f"/invite - 邀请好友 +{INVITE_REWARD}\n"
        f"/qd - 每日签到 +{CHECKIN_REWARD}\n"
        f"\n📢 加入频道获取最新动态：{CHANNEL_URL}"
    )
    return msg


def get_about_message() -> str:
    """获取关于消息"""
    return (
        "🌱 小芽精灵 —— 星小芽专属助手\n"
        "\n"
        "✨ 功能介绍：\n"
        "• 绑定站点，积分互通，免费换好物\n"
        "• 每日签到、邀请好友，积分多多\n"
        "• 更多积分消耗功能即将上线\n"
        "\n"
        "💰 积分获取：\n"
        f"• 绑定站点 +{BIND_REWARD} 积分\n"
        f"• 邀请好友 +{INVITE_REWARD} 积分/人\n"
        f"• 每日签到 +{CHECKIN_REWARD} 积分\n"
        f"• 注册赠送 {REGISTER_REWARD} 积分\n"
        "• 使用卡密（按卡密面值）\n"
        f"• 加入频道：{CHANNEL_URL}\n"
        "\n"
        "更多命令请发送 /help"
    )


def get_help_message(is_admin: bool = False) -> str:
    """获取帮助消息"""
    msg = (
        "🌱 小芽精灵 —— 命令帮助\n"
        "\n"
        "📌 基础命令：\n"
        "/start - 注册 / 开始使用\n"
        "/about - 了解小芽精灵\n"
        "/balance - 查看积分余额\n"
        f"/qd - 每日签到（+{CHECKIN_REWARD}积分）\n"
        f"/invite - 邀请好友（+{INVITE_REWARD}积分/人）\n"
        "/use <卡密> - 卡密兑换积分\n"
        "\n"
        "🔗 站点互通：\n"
        f"/bind - 绑定星小芽站点（+{BIND_REWARD}积分）\n"
        "/exchange <数量> - TG积分兑换站点积分\n"
        "\n"
        "🚧 更多功能即将上线，敬请期待 ✨\n"
    )

    if is_admin:
        msg += (
            "\n⚙️ 管理员命令：\n"
            "/addbalance <用户ID> <积分> - 增加用户积分\n"
            "/block <用户ID> - 拉黑用户\n"
            "/white <用户ID> - 取消拉黑\n"
            "/blacklist - 查看黑名单\n"
            "/genkey <卡密> <积分> [次数] [天数] - 生成卡密\n"
            "/listkeys - 查看卡密列表\n"
            "/broadcast <文本> - 群发通知\n"
        )

    return msg


def get_insufficient_balance_message(current_balance: int) -> str:
    """获取积分不足消息"""
    return (
        f"😢 积分不足！需要 {VERIFY_COST} 积分，当前仅 {current_balance} 积分\n\n"
        "💡 获取积分方式：\n"
        "• /bind 绑定站点\n"
        "• /invite 邀请好友\n"
        "• /qd 每日签到\n"
        "• /use <卡密> 兑换积分"
    )


def get_verify_usage_message(command: str, service_name: str) -> str:
    """获取验证命令使用说明"""
    return (
        f"使用方法: {command} <SheerID链接>\n\n"
        "示例:\n"
        f"{command} https://services.sheerid.com/verify/xxx/?verificationId=xxx\n\n"
        "获取验证链接:\n"
        f"1. 访问 {service_name} 认证页面\n"
        "2. 开始认证流程\n"
        "3. 复制浏览器地址栏中的完整 URL\n"
        f"4. 使用 {command} 命令提交"
    )
