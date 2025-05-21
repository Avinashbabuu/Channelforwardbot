import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# === Load Configuration ===
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
SOURCE_CHANNEL = int(os.getenv('SOURCE_CHANNEL'))
DEST_CHANNEL = int(os.getenv('DEST_CHANNEL'))
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# === Load Filters ===
def load_filters():
    try:
        with open("filters.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_filters(filters_dict):
    with open("filters.json", "w") as f:
        json.dump(filters_dict, f)

filters_dict = load_filters()
awaiting_filter_input = {}

# === Helper Functions ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        message = (
            "Welcome! Bot is running.\n\n"
            "Available Commands:\n"
            "/start - Welcome message\n"
            "/filter - Add word filter (e.g., Hi==Hello)\n"
            "/delfilter - Remove a word filter by number"
        )
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("You're not authorized to use this bot.")

# /filter - initiate filter add
async def filter_example(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    awaiting_filter_input[user_id] = True
    await update.message.reply_text("Send the word replacement in this format: Hi==Hello")

# Catch word replacement after /filter
async def handle_filter_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in awaiting_filter_input and awaiting_filter_input[user_id]:
        text = update.message.text
        if '==' in text:
            word, replacement = text.split('==', 1)
            filters_dict[word.strip()] = replacement.strip()
            save_filters(filters_dict)
            awaiting_filter_input[user_id] = False
            await update.message.reply_text(f"Filter set: '{word.strip()}' will be replaced with '{replacement.strip()}'")
        else:
            await update.message.reply_text("Invalid format. Use: word==replacement")

# /delfilter command
async def del_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    if len(context.args) == 1:
        try:
            index = int(context.args[0]) - 1
            keys = list(filters_dict.keys())
            if 0 <= index < len(keys):
                removed = keys[index]
                del filters_dict[removed]
                save_filters(filters_dict)
                await update.message.reply_text(f"Filter removed: {removed}")
            else:
                await update.message.reply_text("Invalid number.")
        except ValueError:
            await update.message.reply_text("Send the filter number to delete.")
    else:
        if not filters_dict:
            await update.message.reply_text("No filters available.")
        else:
            message = "Filters:\n" + "\n".join(
                [f"{i+1}. {k} → {v}" for i, (k, v) in enumerate(filters_dict.items())]
            )
            await update.message.reply_text(message)

# Forward messages with filters
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.chat.id == SOURCE_CHANNEL:
        msg = update.channel_post
        text = msg.text or msg.caption or ""

        # Apply filters
        for word, replacement in filters_dict.items():
            text = text.replace(word, replacement)

        # Send the appropriate message type
        if msg.text:
            await context.bot.send_message(chat_id=DEST_CHANNEL, text=text)
        elif msg.caption and msg.photo:
            await context.bot.send_photo(chat_id=DEST_CHANNEL, photo=msg.photo[-1].file_id, caption=text)
        elif msg.caption and msg.document:
            await context.bot.send_document(chat_id=DEST_CHANNEL, document=msg.document.file_id, caption=text)
        else:
            await context.bot.copy_message(chat_id=DEST_CHANNEL, from_chat_id=SOURCE_CHANNEL, message_id=msg.message_id)

# === Run the Bot ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("filter", filter_example))
    app.add_handler(CommandHandler("delfilter", del_filter))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), handle_filter_input))
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("Bot is running...")
    app.run_polling()
    
