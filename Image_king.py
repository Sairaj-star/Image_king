import random
import requests
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)

# ========================
# 🔑 Your Tokens (Set them here)
# ========================
TELEGRAM_TOKEN = "8069902581:AAHX4eCXdF5Ks7_jo72TeQXHS0zMHu-TYT0"
HF_API_KEY = "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"
HF_MODEL = "stabilityai/stable-diffusion-2-1"

# ========================
# 🔒 Conversation States
# ========================
ASK_NAME, ASK_PHONE, VERIFY_OTP, READY = range(4)

# Store user sessions
user_data_store = {}


# ---------------- Start ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Welcome to Artify Bot!** 🎨\n\n"
        "✨ I can turn your imagination into AI-powered images.\n\n"
        "But first, let’s get you registered 📝\n\n"
        "👉 What’s your *name*?",
        parse_mode="Markdown"
    )
    return ASK_NAME


# ---------------- Ask Name ----------------
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data_store[user_id] = {"name": update.message.text}

    print(f"[NEW USER] Name entered: {update.message.text}")

    await update.message.reply_text(
        f"Nice to meet you, *{update.message.text}*! 😃\n\n"
        "📱 Please enter your mobile number:",
        parse_mode="Markdown"
    )
    return ASK_PHONE


# ---------------- Ask Phone ----------------
async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data_store[user_id]["phone"] = update.message.text

    print(f"[USER PHONE] {user_data_store[user_id]['name']} → {update.message.text}")

    otp = str(random.randint(1000, 9999))
    user_data_store[user_id]["otp"] = otp

    await update.message.reply_text(
        f"🔒 To verify your number, here’s your OTP:\n\n"
        f"👉 *{otp}*\n\n"
        "Please enter this OTP below 👇",
        parse_mode="Markdown"
    )
    return VERIFY_OTP


# ---------------- Verify OTP ----------------
async def verify_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    entered_otp = update.message.text.strip()

    if entered_otp == user_data_store[user_id]["otp"]:
        user_data_store[user_id]["verified"] = True

        print("\n===== USER REGISTERED =====")
        print(f"👤 Name: {user_data_store[user_id]['name']}")
        print(f"📱 Phone: {user_data_store[user_id]['phone']}")
        print(f"✅ OTP Verified: {entered_otp}")
        print("===========================\n")

        await update.message.reply_text(
            "✅ Verification successful!\n\n"
            "🎉 You’re now registered.\n"
            "Send me any text prompt and I’ll generate an image for you ✨"
        )
        return READY
    else:
        await update.message.reply_text("❌ Wrong OTP! Try again:")
        return VERIFY_OTP


# ---------------- Generate Image ----------------
async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_data_store or not user_data_store[user_id].get("verified"):
        await update.message.reply_text("⚠️ Please register first using /start")
        return

    prompt = update.message.text
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": prompt}

    print(f"[IMAGE REQUEST] {user_data_store[user_id]['name']} → '{prompt}'")

    await update.message.reply_text("✨ Generating your artwork... please wait 🎨")

    response = requests.post(
        f"https://api-inference.huggingface.co/models/{HF_MODEL}",
        headers=headers,
        json=payload,
    )

    if response.status_code == 200:
        await update.message.reply_photo(photo=response.content, caption="🎉 Here’s your AI-generated image!")
    else:
        print("HF API ERROR:", response.text)
        await update.message.reply_text("❌ Failed to generate image. Please try again later.")


# ---------------- Cancel ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚪 Registration canceled. Type /start to try again.")
    return ConversationHandler.END


# ---------------- Main ----------------
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            VERIFY_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_otp)],
            READY: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    print("🚀 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
