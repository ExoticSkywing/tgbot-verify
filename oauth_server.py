"""OAuth 回调 HTTP 服务 —— 小芽精灵

轻量 aiohttp 服务，接收 zibll-oauth 的 OAuth2 回调，
完成 TG 用户与 WP 用户的身份绑定。
"""
import logging
import httpx
from aiohttp import web

from config import (
    OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_BASE_URL,
    OAUTH_REDIRECT_URI, OAUTH_CALLBACK_PORT, BIND_REWARD
)

logger = logging.getLogger(__name__)

# 绑定成功后显示给浏览器的 HTML 页面
BIND_SUCCESS_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>绑定成功 - 小芽精灵</title>
<style>
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    display: flex; justify-content: center; align-items: center;
    min-height: 100vh; margin: 0;
    background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
}
.card {
    background: white; border-radius: 16px; padding: 40px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.1); text-align: center;
    max-width: 400px; width: 90%;
}
.icon { font-size: 64px; margin-bottom: 16px; }
h1 { color: #2e7d32; font-size: 24px; margin: 0 0 12px; }
p { color: #666; font-size: 16px; line-height: 1.6; }
.reward { color: #ff9800; font-weight: bold; font-size: 18px; }
</style>
</head>
<body>
<div class="card">
    <div class="icon">🌱</div>
    <h1>绑定成功！</h1>
    <p>你的 Telegram 账号已与星小芽站点关联</p>
    <p class="reward">🎁 已获得 """ + str(BIND_REWARD) + """ 积分奖励</p>
    <p>现在可以回到 Telegram 继续使用小芽精灵了</p>
</div>
</body>
</html>"""

BIND_FAIL_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>绑定失败 - 小芽精灵</title>
<style>
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    display: flex; justify-content: center; align-items: center;
    min-height: 100vh; margin: 0;
    background: linear-gradient(135deg, #fce4ec 0%, #f8bbd0 100%);
}
.card {
    background: white; border-radius: 16px; padding: 40px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.1); text-align: center;
    max-width: 400px; width: 90%;
}
.icon { font-size: 64px; margin-bottom: 16px; }
h1 { color: #c62828; font-size: 24px; margin: 0 0 12px; }
p { color: #666; font-size: 16px; line-height: 1.6; }
</style>
</head>
<body>
<div class="card">
    <div class="icon">😢</div>
    <h1>绑定失败</h1>
    <p>{message}</p>
    <p>请回到 Telegram 重新发送 /bind 重试</p>
</div>
</body>
</html>"""


async def oauth_callback(request):
    """处理 OAuth 回调：code + state → 绑定"""
    db = request.app["db"]
    bot = request.app["bot"]

    code = request.query.get("code")
    state = request.query.get("state")

    # 参数校验
    if not code or not state:
        return web.Response(
            text=BIND_FAIL_HTML.format(message="缺少必要参数，请重新发起绑定"),
            content_type="text/html"
        )

    # 消费 state，获取 tg_user_id
    user_id = db.consume_bind_state(state)
    if not user_id:
        return web.Response(
            text=BIND_FAIL_HTML.format(message="绑定链接已过期或无效，请重新发送 /bind"),
            content_type="text/html"
        )

    # 检查是否已绑定
    if db.get_wp_openid(user_id):
        return web.Response(
            text=BIND_FAIL_HTML.format(message="你已经绑定过站点账号了"),
            content_type="text/html"
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 第1步：用 code 换取 access_token
            token_resp = await client.post(
                f"{OAUTH_BASE_URL}/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": OAUTH_CLIENT_ID,
                    "client_secret": OAUTH_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": OAUTH_REDIRECT_URI,
                },
            )

            if token_resp.status_code != 200:
                logger.error(f"OAuth token 请求失败: {token_resp.status_code} {token_resp.text}")
                return web.Response(
                    text=BIND_FAIL_HTML.format(message="授权失败，请重新发送 /bind 重试"),
                    content_type="text/html"
                )

            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                logger.error(f"OAuth 响应中无 access_token: {token_data}")
                return web.Response(
                    text=BIND_FAIL_HTML.format(message="获取令牌失败，请重试"),
                    content_type="text/html"
                )

            # 第2步：用 access_token 获取用户信息（openid）
            userinfo_resp = await client.get(
                f"{OAUTH_BASE_URL}/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if userinfo_resp.status_code != 200:
                logger.error(f"获取用户信息失败: {userinfo_resp.status_code} {userinfo_resp.text}")
                return web.Response(
                    text=BIND_FAIL_HTML.format(message="获取用户信息失败，请重试"),
                    content_type="text/html"
                )

            userinfo = userinfo_resp.json().get("userinfo", {})
            openid = userinfo.get("openid")
            wp_name = userinfo.get("name", "")

            if not openid:
                logger.error(f"用户信息中无 openid: {userinfo}")
                return web.Response(
                    text=BIND_FAIL_HTML.format(message="获取站点账号信息失败，请重试"),
                    content_type="text/html"
                )

        # 第3步：写入绑定关系 + 奖励积分
        success = db.bind_wp_account(user_id, openid)
        if not success:
            return web.Response(
                text=BIND_FAIL_HTML.format(
                    message="绑定失败，该站点账号可能已被其他 TG 账号绑定"
                ),
                content_type="text/html"
            )

        # 第4步：通过 TG Bot API 通知用户
        try:
            user = db.get_user(user_id)
            balance = user["balance"] if user else "?"
            name_text = f"（{wp_name}）" if wp_name else ""
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 绑定成功！\n\n"
                    f"🌱 你的 TG 账号已与星小芽站点{name_text}关联\n"
                    f"🎁 获得绑定奖励：+{BIND_REWARD} 积分\n"
                    f"💰 当前积分：{balance} 分\n\n"
                    f"现在可以使用 /exchange 将积分兑换为站点积分啦！"
                ),
            )
        except Exception as e:
            logger.warning(f"通知用户绑定成功失败: {e}")

        logger.info(f"用户 {user_id} 绑定站点成功，openid={openid}")
        return web.Response(text=BIND_SUCCESS_HTML, content_type="text/html")

    except Exception as e:
        logger.error(f"OAuth 绑定过程异常: {e}")
        return web.Response(
            text=BIND_FAIL_HTML.format(message="服务器处理异常，请稍后重试"),
            content_type="text/html"
        )


def create_oauth_app(db, bot):
    """创建 OAuth 回调 HTTP 应用"""
    app = web.Application()
    app["db"] = db
    app["bot"] = bot
    app.router.add_get("/oauth/callback", oauth_callback)
    return app


async def start_oauth_server(db, bot):
    """启动 OAuth 回调服务（在 Bot 主循环中调用）"""
    app = create_oauth_app(db, bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", OAUTH_CALLBACK_PORT)
    await site.start()
    logger.info(f"OAuth 回调服务启动于 0.0.0.0:{OAUTH_CALLBACK_PORT}")
    return runner
