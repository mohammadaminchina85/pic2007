import logging
import asyncio
from openai import OpenAI
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, ChatWriteForbiddenError

# ═══════════════════════════════════════════
#  تنظیمات
# ═══════════════════════════════════════════
API_ID          = 39755599
API_HASH        = "f00ae152a735bc659c4569513bf8edd1"       # از my.telegram.org
GAPGPT_API_KEY  = "sk-5q28kGmss0TpGQBW3IVAe4p9eSX3DPBPQ2aHWnreIoEF26So" # از gapgpt.app

SOURCE_CHANNEL      = "naya_foriraq"   # آیدی عددی کانال مبدأ
DESTINATION_CHANNEL = "naya_far"       # username کانال مقصد

# ═══════════════════════════════════════════
#  لاگ
# ═══════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# ═══════════════════════════════════════════
#  GapGPT
# ═══════════════════════════════════════════
ai_client = OpenAI(
    base_url='https://api.gapgpt.app/v1',
    api_key=GAPGPT_API_KEY
)

# ═══════════════════════════════════════════
#  کلاینت تلگرام
# ═══════════════════════════════════════════
client = TelegramClient('naya_session', API_ID, API_HASH)


# ═══════════════════════════════════════════
#  ترجمه با GapGPT
# ═══════════════════════════════════════════
async def translate_content(text: str) -> str:
    if not text or len(text.strip()) < 3:
        return text

    for attempt in range(3):
        try:
            response = ai_client.chat.completions.create(
                model="gpt-5.4",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional Arabic to Persian translator. "
                            "Translate the given text to Persian (Farsi) accurately. "
                            "Keep all emojis, links, hashtags, and formatting exactly as they are. "
                            "Return ONLY the translated text, nothing else."
                        )
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.3,
                max_tokens=4096,
            )
            translated = response.choices[0].message.content.strip()
            log.info(f"✅ Translation OK (attempt {attempt+1})")
            return translated

        except Exception as e:
            log.warning(f"Translation attempt {attempt+1} failed: {e}")
            await asyncio.sleep(2 ** attempt)

    log.error("All translation attempts failed, sending original.")
    return text


# ═══════════════════════════════════════════
#  هندلر پیام جدید
# ═══════════════════════════════════════════
@client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def handler(event):
    log.info(f"📨 New message | chat_id={event.chat_id} | msg_id={event.message.id}")

    try:
        original_text = event.message.message or ""
        translated_text = ""

        if original_text.strip():
            log.info(f"Translating: {original_text[:80]}...")
            translated_text = await translate_content(original_text)
        else:
            log.info("No text in message, skipping translation.")

        if event.message.media:
            await client.send_file(
                DESTINATION_CHANNEL,
                file=event.message.media,
                caption=translated_text or None,
            )
            log.info("✅ Media + caption forwarded.")
        else:
            if translated_text:
                await client.send_message(DESTINATION_CHANNEL, translated_text)
                log.info("✅ Text message forwarded.")
            else:
                log.warning("⚠️ Empty message, nothing sent.")

    except FloodWaitError as e:
        log.warning(f"FloodWait: sleeping {e.seconds}s")
        await asyncio.sleep(e.seconds)
    except ChatWriteForbiddenError:
        log.error("❌ No permission to write in DESTINATION_CHANNEL!")
    except Exception as e:
        log.error(f"❌ Unexpected error: {e}", exc_info=True)


# ═══════════════════════════════════════════
#  استارت
# ═══════════════════════════════════════════
async def main():
    log.info("🚀 Bot starting...")
    await client.start()

    me = await client.get_me()
    log.info(f"✅ Logged in as: {me.first_name} (@{me.username})")

    try:
        src = await client.get_entity(SOURCE_CHANNEL)
        log.info(f"✅ Source: {src.title} | id={src.id}")
    except Exception as e:
        log.error(f"❌ SOURCE_CHANNEL error: {e}")
        return

    try:
        dst = await client.get_entity(DESTINATION_CHANNEL)
        log.info(f"✅ Destination: {dst.title} | id={dst.id}")
    except Exception as e:
        log.error(f"❌ DESTINATION_CHANNEL error: {e}")
        return

    log.info("👂 Waiting for new messages...")
    await client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())