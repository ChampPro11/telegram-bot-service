# -*- coding: utf-8 -*-
import os
import logging
import json
import requests
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
UPI_ID = os.getenv("UPI_ID")
OWNER_ID = int(os.getenv("OWNER_ID"))

# Store ngrok_url persistently
NGROK_FILE = "ngrok_url.txt"

PRICES = {
    "cv_professional": 2500,
    "cv_executive": 4500,
    "art_artistic": 3000,
    "art_fantasy": 4500,
    "art_ultrarealistic": 12000,
    "logo": 2000
}

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Load latest ngrok URL from file
def get_ngrok_url():
    if os.path.exists(NGROK_FILE):
        with open(NGROK_FILE, "r") as f:
            return f.read().strip()
    return None

def save_ngrok_url(url):
    with open(NGROK_FILE, "w") as f:
        f.write(url)

def start_bot():
    bot = Bot(BOT_TOKEN)
    try:
        bot.send_message(
            chat_id=CHANNEL_ID,
            text="🚀 *Welcome to AlphaZone!* ⚡\n\nClick below to begin ordering:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Start Now 🚀", url=f"https://t.me/{bot.get_me().username}?start=1")]
            ]),
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Error sending welcome: {e}")

def start_private(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Hey! Welcome to *AlphaZone*.\n\nWhat would you like to create?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 CV", callback_data="cv")],
            [InlineKeyboardButton("🎨 Art", callback_data="art")],
            [InlineKeyboardButton("🏆 Logo", callback_data="logo")]
        ]),
        parse_mode="Markdown"
    )

def show_samples(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    category = query.data
    ngrok_url = get_ngrok_url()

    if not ngrok_url:
        query.message.reply_text("⚠️ Bot is not ready. Ngrok URL missing.")
        return

    samples = {
        "cv": [("Professional CV", "cv_professional"), ("Executive CV", "cv_executive")],
        "art": [("Artistic", "art_artistic"), ("Fantasy", "art_fantasy"), ("Ultra-Realistic", "art_ultrarealistic")],
        "logo": [("Logo Sample", "logo")]
    }

    buttons = []
    for label, product_type in samples[category]:
        img = requests.post(f"{ngrok_url}/generate", json={
            "description": label,
            "product_type": product_type,
            "mode": "preview"
        })
        query.message.bot.send_photo(
            chat_id=query.message.chat.id,
            photo=img.content,
            caption=f"*{label}*\n💰 Price: ₹{PRICES[product_type]}",
            parse_mode="Markdown"
        )
        buttons.append([InlineKeyboardButton(label, callback_data=f"select_{product_type}")])

    query.message.reply_text("Select one:", reply_markup=InlineKeyboardMarkup(buttons))

def ask_for_description(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    selected = query.data.replace("select_", "")
    context.user_data["selected_product"] = selected

    if "cv" in selected:
        msg = "*KINDLY PROVIDE YOUR DETAILS*\n\n🔹 *YOUR DETAILS WON’T BE SAVED.*"
    else:
        msg = "🔹 *Describe your idea for this product.*"

    query.message.reply_text(msg, parse_mode="Markdown")

def send_preview(update: Update, context: CallbackContext):
    desc = update.message.text
    product_type = context.user_data.get("selected_product", "")
    context.user_data["user_description"] = desc
    ngrok_url = get_ngrok_url()

    img = requests.post(f"{ngrok_url}/generate", json={
        "description": desc,
        "product_type": product_type,
        "mode": "preview"
    })

    update.message.reply_photo(photo=img.content, caption="🔹 *Here is your preview.*", parse_mode="Markdown")
    update.message.reply_text("Choose an option:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate")],
        [InlineKeyboardButton("✅ Done", callback_data="done")]
    ]))

def regenerate_preview(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    desc = context.user_data.get("user_description", "")
    product_type = context.user_data.get("selected_product", "")
    ngrok_url = get_ngrok_url()

    img = requests.post(f"{ngrok_url}/generate", json={
        "description": desc,
        "product_type": product_type,
        "mode": "preview"
    })

    query.message.reply_photo(photo=img.content, caption="🔄 *New Preview Generated.*", parse_mode="Markdown")

def ask_for_payment(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    product_type = context.user_data.get("selected_product", "")
    amount = PRICES[product_type]

    query.message.reply_text(
        f"💰 *Please pay ₹{amount}*\n\n📌 UPI ID: `{UPI_ID}`\n\nThen send a screenshot here.",
        parse_mode="Markdown"
    )

def validate_payment(update: Update, context: CallbackContext):
    file_id = update.message.photo[-1].file_id
    product_type = context.user_data.get("selected_product", "")
    desc = context.user_data.get("user_description", "")
    amount = PRICES[product_type]
    ngrok_url = get_ngrok_url()

    # Simulate successful payment
    img = requests.post(f"{ngrok_url}/generate", json={
        "description": desc,
        "product_type": product_type,
        "mode": "final"
    })

    update.message.reply_text("✅ *Payment verified! Here's your final product:*", parse_mode="Markdown")
    update.message.reply_photo(photo=img.content)

    # Save transaction
    record = {
        "user": update.message.chat.id,
        "product": product_type,
        "amount": amount,
        "screenshot_id": file_id
    }

    with open("transactions.json", "a") as f:
        f.write(json.dumps(record) + "\n")

    # Notify you (owner)
    context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"📦 New Paid Order!\n\nUser ID: `{record['user']}`\nProduct: {product_type}\nAmount: ₹{amount}",
        parse_mode="Markdown"
    )

def receive_ngrok(update: Update, context: CallbackContext):
    # This is ONLY allowed from you (owner)
    if update.message.chat.id != OWNER_ID:
        update.message.reply_text("❌ You're not authorized to send this.")
        return

    url = update.message.text.strip()
    if url.startswith("http") and "/generate" in url:
        save_ngrok_url(url)
        update.message.reply_text("✅ Ngrok URL saved.")
    else:
        update.message.reply_text("❌ Invalid ngrok URL.")

if __name__ == "__main__":
    start_bot()
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start_private))
    dp.add_handler(MessageHandler(Filters.regex("^http.*?/generate$"), receive_ngrok))
    dp.add_handler(CallbackQueryHandler(show_samples, pattern="^(cv|art|logo)$"))
    dp.add_handler(CallbackQueryHandler(ask_for_description, pattern="^select_"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, send_preview))
    dp.add_handler(CallbackQueryHandler(regenerate_preview, pattern="^regenerate$"))
    dp.add_handler(CallbackQueryHandler(ask_for_payment, pattern="^done$"))
    dp.add_handler(MessageHandler(Filters.photo, validate_payment))

    updater.start_polling()
    updater.idle()
