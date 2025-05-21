import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes
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

# === Helper Functions ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        await update.message.reply("Bot is running. Use /addfilter and /delfilter commands to manage filters.")
    else:
        await update.message.reply("You're not authorized to use this bot.")

# === Command Handlers ===

# /addfilter command
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply("You are not authorized.")
        return

    if len(context.args) == 1 and ":" in context.args[0]:
        word, replacement = context.args[0].split(":")
        filters_dict[word] = replacement
        save_filters(filters_dict)
        await update.message.reply(f"Filter added: {word} → {replacement}")
    else:
        await update.message.reply("Usage: /addfilter word:replacement")

# /delfilter command
async def del_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply("You are not authorized.")
        return

    if len(context.args) == 1:
        word = context.args[0]
        if word in filters_dict:
            del filters_dict[word]
            save_filters(filters_dict)
            await update.message.reply(f"Filter removed: {word}")
        else:
            await update.message.reply(f"No filter found for: {word}")
    else:
        await update.message.reply("Usage: /delfilter word")

# /listfilters command
async def list_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply("You are not authorized.")
        return

    if filters_dict:
        filters_list = "\n".join([f"{word} → {replacement}" for word, replacement in filters_dict.items()])
        await update.message.reply(f"Current filters:\n{filters_list}")
    else:
        await update.message.reply("No filters set.")

# === Message Forwarding with Replacements ===
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.chat.id == SOURCE_CHANNEL:
        msg = update.channel_post
        text = msg.text or ""

        # Apply filters and replacements
        for word, replacement in filters_dict.items():
            text = text.replace(word, replacement)

        # Send modified message to destination channel
        if text:
            await context.bot.send_message(
                chat_id=DEST_CHANNEL,
                text=text
            )

        elif msg.photo:
            await context.bot.send_photo(
                chat_id=DEST_CHANNEL,
                photo=msg.photo[-1].file_id,
                caption=text
            )

        elif msg.document:
            await context.bot.send_document(
                chat_id=DEST_CHANNEL,
                document=msg.document.file_id,
                caption=text
            )

        else:
            # Forward message as is
            await context.bot.copy_message(
                chat_id=DEST_CHANNEL,
                from_chat_id=SOURCE_CHANNEL,
                message_id=msg.message_id
            )

# === Main Setup ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addfilter", add_filter))
    app.add_handler(CommandHandler("delfilter", del_filter))
    app.add_handler(CommandHandler("listfilters", list_filters))
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("Bot is running...")
    app.run_polling()
      
