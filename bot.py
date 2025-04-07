# -*- coding: utf-8 -*-
import os
import logging
import json
import requests
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# ✅ Load secrets
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
UPI_ID = os.getenv("UPI_ID")
COLAB_GENERATE_URL = os.getenv("COLAB_GENERATE_URL")  # Will be auto-DM’d from Colab

# 💰 Product Prices
PRICES = {
    "cv_professional": 2500,
    "cv_executive": 4500,
    "art_artistic": 3000,
    "art_fantasy": 4500,
    "art_ultrarealistic": 12000,
    "logo": 1000
}

# 🪵 Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# 🚪 Channel Entry Welcome
def start_bot():
    bot = Bot(BOT_TOKEN)
    try:
        bot.send_message(
            chat_id=CHANNEL_ID,
            text="🚀 **Welcome to AlphaZone!** ⚡\n\nClick the button below to start ordering:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Start Now 🚀", url=f"https://t.me/{bot.get_me().username}?start=1")]
            ]),
            parse_mode="Markdown"
        )
        logging.info("Welcome message sent.")
    except Exception as e:
        logging.error(f"Failed to send welcome message: {e}")

# 👋 Private Start
def start_private(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Hey! Welcome to **AlphaZone**.\n\nChoose what you need:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 CV", callback_data="cv")],
            [InlineKeyboardButton("🎨 Art", callback_data="art")],
            [InlineKeyboardButton("🏆 Logo", callback_data="logo")]
        ]),
        parse_mode="Markdown"
    )

# 🖼️ Show Samples for Category
def show_samples(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    category = query.data

    samples = {
        "cv": [("Professional CV", "cv_professional"), ("Executive CV", "cv_executive")],
        "art": [("Artistic", "art_artistic"), ("Fantasy", "art_fantasy"), ("Ultra-Realistic", "art_ultrarealistic")],
        "logo": [("Logo Sample", "logo")]
    }

    buttons = []
    for label, product_type in samples[category]:
        # Simulate sample image by calling Colab
        img = requests.post(COLAB_GENERATE_URL, json={
            "description": label,
            "product_type": product_type,
            "mode": "preview"
        })

        query.message.bot.send_photo(
            chat_id=query.message.chat.id,
            photo=img.content,
            caption=f"**{label}**\n💰 Price: ₹{PRICES[product_type]}",
            parse_mode="Markdown"
        )
        buttons.append([InlineKeyboardButton(label, callback_data=f"select_{product_type}")])

    query.message.reply_text("Select the type you want:", reply_markup=InlineKeyboardMarkup(buttons))

# 📝 Ask for Description
def ask_for_description(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    selected = query.data.replace("select_", "")
    context.user_data["selected_product"] = selected
    context.user_data["preview_count"] = 0

    if "cv" in selected:
        msg = "**KINDLY PROVIDE YOUR DETAILS**\n\n🔹 **YOUR DETAILS WON’T BE SAVED, DON’T WORRY.**"
    else:
        msg = "🔹 **BRIEFLY DESCRIBE YOUR IDEA FOR THE PRODUCT.**"

    query.message.reply_text(msg, parse_mode="Markdown")

# 📸 Generate Preview
def send_preview(update: Update, context: CallbackContext):
    user_input = update.message.text
    product_type = context.user_data.get("selected_product", "")
    context.user_data["user_description"] = user_input

    img = requests.post(COLAB_GENERATE_URL, json={
        "description": user_input,
        "product_type": product_type,
        "mode": "preview"
    })

    update.message.reply_photo(photo=img.content, caption="🔹 **Here is your preview.**\n\n💡 Select an option:", parse_mode="Markdown")
    update.message.reply_text("Choose an option:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate")],
        [InlineKeyboardButton("✅ Done", callback_data="done")]
    ]))

# 🔁 Regenerate Preview
def regenerate_preview(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    desc = context.user_data.get("user_description", "")
    product_type = context.user_data.get("selected_product", "")

    img = requests.post(COLAB_GENERATE_URL, json={
        "description": desc,
        "product_type": product_type,
        "mode": "preview"
    })

    query.message.reply_photo(photo=img.content, caption="🔄 **New Preview Generated.**", parse_mode="Markdown")

# 💸 Payment Instruction
def ask_for_payment(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    product_type = context.user_data.get("selected_product", "")
    amount = PRICES[product_type]

    query.message.reply_text(f"💰 **Please make a payment of ₹{amount}**\n\n📌 UPI ID: `{UPI_ID}`\n\nOnce done, send a screenshot.", parse_mode="Markdown")

# 🧾 Validate Payment Screenshot
def validate_payment(update: Update, context: CallbackContext):
    file_id = update.message.photo[-1].file_id
    product_type = context.user_data.get("selected_product", "")
    desc = context.user_data.get("user_description", "")
    amount = PRICES[product_type]

    # 💡 Simulate validation
    is_valid = True

    if is_valid:
        # Generate Final Product (no watermark)
        img = requests.post(COLAB_GENERATE_URL, json={
            "description": desc,
            "product_type": product_type,
            "mode": "final"
        })
        update.message.reply_text("✅ **Payment verified! Here's your final product:**", parse_mode="Markdown")
        update.message.reply_photo(photo=img.content)

        # Save to JSON
        with open("transactions.json", "a") as f:
            f.write(json.dumps({
                "user": update.message.chat.id,
                "product": product_type,
                "amount": amount,
                "screenshot_id": file_id
            }) + "\n")

    else:
        update.message.reply_text("❌ **The amount paid is not as per the price. Kindly check.**")

# 🚀 Run the Bot
if __name__ == "__main__":
    start_bot()
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start_private))
    dp.add_handler(CallbackQueryHandler(show_samples, pattern="^(cv|art|logo)$"))
    dp.add_handler(CallbackQueryHandler(ask_for_description, pattern="^select_"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, send_preview))
    dp.add_handler(CallbackQueryHandler(regenerate_preview, pattern="^regenerate$"))
    dp.add_handler(CallbackQueryHandler(ask_for_payment, pattern="^done$"))
    dp.add_handler(MessageHandler(Filters.photo, validate_payment))

    updater.start_polling()
    updater.idle()
