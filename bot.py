"""Telegram 机器人主程序 —— 小芽精灵"""
import asyncio
import logging
from functools import partial

from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from config import BOT_TOKEN
from database_mysql import Database
from handlers.user_commands import (
    start_command,
    about_command,
    help_command,
    balance_command,
    checkin_command,
    invite_command,
    use_command,
)
from handlers.verify_commands import (
    verify_command,
    verify2_command,
    verify3_command,
    verify4_command,
    getV4Code_command,
)
from handlers.bind_command import bind_command
from handlers.exchange_command import exchange_command, exchange_all_callback
from handlers.me_command import me_command
from handlers.admin_commands import (
    addbalance_command,
    block_command,
    white_command,
    blacklist_command,
    genkey_command,
    listkeys_command,
    broadcast_command,
)

# 配置日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context) -> None:
    """全局错误处理"""
    logger.exception("处理更新时发生异常: %s", context.error, exc_info=context.error)


async def post_init(application):
    """应用初始化后启动 OAuth 回调服务 + 注册命令菜单"""
    from oauth_server import start_oauth_server
    from telegram import BotCommand

    db = application.bot_data["db"]
    bot = application.bot
    runner = await start_oauth_server(db, bot)
    application.bot_data["oauth_runner"] = runner

    # 注册 TG 命令菜单（用户输入 / 时可见）
    commands = [
        BotCommand("me", "个人信息"),
        BotCommand("balance", "查看积分余额"),
        BotCommand("qd", "每日签到"),
        BotCommand("invite", "邀请好友"),
        BotCommand("bind", "绑定站点账号"),
        BotCommand("exchange", "TG积分兑换站点积分"),
        BotCommand("use", "使用卡密"),
        BotCommand("help", "帮助"),
    ]
    await bot.set_my_commands(commands)


def main():
    """主函数"""
    # 初始化数据库
    db = Database()

    # 创建应用 - 启用并发处理
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .post_init(post_init)
        .build()
    )

    # 将 db 存入 bot_data 以便 post_init 使用
    application.bot_data["db"] = db

    # 注册用户命令
    application.add_handler(CommandHandler("start", partial(start_command, db=db)))
    application.add_handler(CommandHandler("about", partial(about_command, db=db)))
    application.add_handler(CommandHandler("help", partial(help_command, db=db)))
    application.add_handler(CommandHandler("balance", partial(balance_command, db=db)))
    application.add_handler(CommandHandler("qd", partial(checkin_command, db=db)))
    application.add_handler(CommandHandler("invite", partial(invite_command, db=db)))
    application.add_handler(CommandHandler("use", partial(use_command, db=db)))
    application.add_handler(CommandHandler("bind", partial(bind_command, db=db)))
    application.add_handler(CommandHandler("exchange", partial(exchange_command, db=db)))
    application.add_handler(CommandHandler("me", partial(me_command, db=db)))

    # 注册回调处理器（InlineKeyboard 按钮）
    application.add_handler(CallbackQueryHandler(partial(exchange_all_callback, db=db), pattern="^exchange_all$"))

    # 注册验证命令（占位）
    application.add_handler(CommandHandler("verify", partial(verify_command, db=db)))
    application.add_handler(CommandHandler("verify2", partial(verify2_command, db=db)))
    application.add_handler(CommandHandler("verify3", partial(verify3_command, db=db)))
    application.add_handler(CommandHandler("verify4", partial(verify4_command, db=db)))
    application.add_handler(CommandHandler("getV4Code", partial(getV4Code_command, db=db)))

    # 注册管理员命令
    application.add_handler(CommandHandler("addbalance", partial(addbalance_command, db=db)))
    application.add_handler(CommandHandler("block", partial(block_command, db=db)))
    application.add_handler(CommandHandler("white", partial(white_command, db=db)))
    application.add_handler(CommandHandler("blacklist", partial(blacklist_command, db=db)))
    application.add_handler(CommandHandler("genkey", partial(genkey_command, db=db)))
    application.add_handler(CommandHandler("listkeys", partial(listkeys_command, db=db)))
    application.add_handler(CommandHandler("broadcast", partial(broadcast_command, db=db)))

    # 注册错误处理器
    application.add_error_handler(error_handler)

    logger.info("机器人启动中...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
