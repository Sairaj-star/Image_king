import random
import time
import requests
from telegram import Update, InputMediaPhoto
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# ---------------- CONFIG ----------------
HF_API_KEY = "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"       # 👈 Put your Hugging Face API key
TELEGRAM_TOKEN = "8069902581:AAHX4eCXdF5Ks7_jo72TeQXHS0zMHu-TYT0"   # 👈 Put your Telegram Bot token

# Models (main + 2 fallbacks)
HF_MODELS = [
    "stabilityai/stable-diffusion-xl-base-1.0",   # Main high-quality
    "stabilityai/stable-diffusion-2-1",           # Fallback
    "CompVis/stable-diffusion-v1-4"              # Lightweight fallback
]

HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

# ---------------- STATES ----------------
ASK_NAME, ASK_PHONE, VERIFY_OTP, IMAGE_GEN = range(4)
user_data_store = {}  # Stores user info + history


# ---------------- HELPERS ----------------
def log(msg: str):
    """Print timestamped logs to terminal."""
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"[{ts}] {msg}")


def generate_image(prompt: str) -> bytes:
    """Try generating image with multiple models until success."""
    for model in HF_MODELS:
        url = f"https://api-inference.huggingface.co/models/{model}"
        payload = {"inputs": prompt}
        log(f"Trying model: {model}")
        response = requests.post(url, headers=HEADERS, json=payload)

        if response.status_code == 200:
            log(f"✅ Success with model {model}")
            return response.content
        else:
            log(f"⚠️ HF API ERROR {response.status_code} for {model}: {response.text}")

    return None  # If all models fail


# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌟 *Welcome to Artify Bot!* 🎨\n\n"
        "I turn your words into *stunning AI images* 🤖🖼️\n\n"
        "But first, let’s register you 💬\n\n"
        "👉 What’s your *name*?",
        parse_mode="Markdown"
    )
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.message.text.strip()
    user_data_store[user_id] = {"name": name, "history": []}

    log(f"User started: {name} (user_id={user_id})")

    await update.message.reply_text(
        f"✨ Awesome, *{name}*! Nice to meet you 🤝\n\n"
        "📱 Please share your *mobile number*:",
        parse_mode="Markdown"
    )
    return ASK_PHONE


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    phone = update.message.text.strip()
    otp = str(random.randint(1000, 9999))

    user_data_store[user_id]["phone"] = phone
    user_data_store[user_id]["otp"] = otp

    log(f"User {user_data_store[user_id]['name']} (id={user_id}) phone: {phone}")

    await update.message.reply_text(
        f"📲 Perfect! Let’s verify your number.\n\n"
        f"🔐 Your *OTP* is: `{otp}`\n\n"
        "👉 Please type this OTP below 👇",
        parse_mode="Markdown"
    )
    return VERIFY_OTP


async def verify_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    entered = update.message.text.strip()
    expected = user_data_store[user_id]["otp"]

    if entered == expected:
        user_data_store[user_id]["verified"] = True

        log("===== USER VERIFIED =====")
        log(f"👤 Name: {user_data_store[user_id]['name']}")
        log(f"📱 Phone: {user_data_store[user_id]['phone']}")
        log(f"✅ OTP: {entered}")
        log(f"🆔 Telegram ID: {user_id}")
        log("==========================")

        await update.message.reply_text(
            "✅ *Verification successful!* 🎉\n\n"
            "Now the fun begins 🚀\n"
            "Type any prompt like:\n"
            "- `A cyberpunk city at night`\n"
            "- `A panda astronaut on Mars`\n"
            "- `A fantasy castle in the sky`\n\n"
            "🎨 I’ll create an image just for you!\n\n"
            "💡 You can also type /gallery to see your artworks.",
            parse_mode="Markdown"
        )
        return IMAGE_GEN
    else:
        await update.message.reply_text("❌ Wrong OTP 😔 Please try again:")
        return VERIFY_OTP


async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_data_store.get(user_id, {}).get("verified", False):
        await update.message.reply_text("⚠️ Please register first using /start")
        return

    prompt = update.message.text.strip()
    log(f"Prompt from {user_data_store[user_id]['name']} (id={user_id}): {prompt}")

    await update.message.reply_text(
        f"🎨 *Got it!* Generating your masterpiece for:\n\n`{prompt}`\n\n⏳ Please wait...",
        parse_mode="Markdown"
    )

    image_bytes = generate_image(prompt)
    if image_bytes:
        await update.message.reply_photo(
            photo=image_bytes,
            caption=f"✨ Here’s your AI artwork for:\n`{prompt}` 🖼️\n\nEnjoy! 🎉",
            parse_mode="Markdown"
        )
        # Save to user history
        user_data_store[user_id]["history"].append((prompt, image_bytes))
        # Keep only last 5
        user_data_store[user_id]["history"] = user_data_store[user_id]["history"][-5:]
        log(f"✅ Image generated for: {prompt}")
    else:
        await update.message.reply_text(
            "❌ Sorry! I couldn’t generate the image right now 😔\n"
            "Please try again later 🙏"
        )


async def show_gallery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    history = user_data_store.get(user_id, {}).get("history", [])

    if not history:
        await update.message.reply_text("📂 Your gallery is empty! Generate some images first 🎨")
        return

    media_group = []
    for prompt, img_bytes in history:
        media_group.append(InputMediaPhoto(media=img_bytes, caption=f"🖼️ {prompt}"))

    await update.message.reply_media_group(media=media_group)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚪 Registration canceled.\nYou can restart anytime with /start 🌟"
    )
    return ConversationHandler.END


# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            VERIFY_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_otp)],
            IMAGE_GEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("gallery", show_gallery))

    log("🤖 Bot is live... waiting for users 🚀")
    app.run_polling()


if __name__ == "__main__":
    main()
