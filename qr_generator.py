import asyncio
import base64
import qrcode
from io import BytesIO

from pyrogram import Client
from pyrogram.raw.functions.auth import ExportLoginToken, ImportLoginToken
from pyrogram.raw.types.auth import LoginTokenSuccess, LoginTokenMigrateTo
from pyrogram.errors import SessionPasswordNeeded

from config import API_ID, API_HASH


async def generate_pyrogram_session(bot, user_id):
    app = Client(
        name="qr_temp",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True
    )

    await app.connect()

    token_data = await app.invoke(
        ExportLoginToken(api_id=API_ID, api_hash=API_HASH, except_ids=[])
    )

    login_token = token_data.token
    login_token_b64 = base64.urlsafe_b64encode(login_token).decode()
    qr_url = f"tg://login?token={login_token_b64}"

    qr = qrcode.make(qr_url)
    bio = BytesIO()
    bio.name = "qr.png"
    qr.save(bio, "PNG")
    bio.seek(0)

    qr_msg = await bot.send_photo(
        user_id,
        bio,
        caption="📲 Scan QR → Settings → Devices → Link Desktop Device\n⏳ 30s Expiry"
    )

    success = False

    for _ in range(20):
        await asyncio.sleep(3)
        try:
            result = await app.invoke(
                ImportLoginToken(token=login_token)
            )

            if isinstance(result, LoginTokenSuccess):
                success = True
                break

            elif isinstance(result, LoginTokenMigrateTo):
                await app.disconnect()
                app = Client(
                    name="qr_temp",
                    api_id=API_ID,
                    api_hash=API_HASH,
                    in_memory=True,
                    dc_id=result.dc_id
                )
                await app.connect()

        except Exception:
            continue

    if not success:
        await qr_msg.delete()
        await app.disconnect()
        return "EXPIRED"

    # 🔐 HANDLE 2FA PROPERLY
    try:
        me = await app.get_me()
    except SessionPasswordNeeded:
        return "PASSWORD_REQUIRED", app, qr_msg

    # Now session is FULLY AUTHORIZED
    session_string = await app.export_session_string()

    # Save session to Saved Messages
    await app.send_message(
        "me",
        f"🔐 **Your Pyrogram String Session**\n\n`{session_string}`"
    )

    await qr_msg.delete()
    await app.disconnect()

    return "SUCCESS", me
