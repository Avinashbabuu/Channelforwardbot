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
        message = (
            "Welcome! Bot is running.\n\n"
            "Available Commands:\n"
            "/start - Welcome message\n"
            "/addfilter word:replacement - Set a word filter\n"
            "/delfilter word - Remove a word filter\n"
            "/listfilters - View all filters\n"
            "/filter - Get filter example"
        )
        await update.message.reply(message)
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
        try:
            filter_number = int(context.args[0]) - 1  # Indexing starts from 0
            filter_keys = list(filters_dict.keys())
            if 0 <= filter_number < len(filter_keys):
                word = filter_keys[filter_number]
                del filters_dict[word]
                save_filters(filters_dict)
                await update.message.reply(f"Filter removed: {word}")
            else:
                await update.message.reply("Invalid filter number.")
        except ValueError:
            await update.message.reply("Usage: /delfilter number")
    else:
        # Show available filters
        if filters_dict:
            filters_list = "\n".join([f"{i+1}. {word} → {replacement}" for i, (word, replacement) in enumerate(filters_dict.items())])
            await update.message.reply(f"Filters:\n{filters_list}")
        else:
            await update.message.reply("No filters set.")

# /filter command (show example)
async def filter_example(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply("You are not authorized.")
        return

    example_message = (
        "Example usage:\n\n"
        "/addfilter word:replacement\n"
        "For example: /addfilter Hi:Hello\n"
        "This will replace 'Hi' with 'Hello' in forwarded messages."
    )
    await update.message.reply(example_message)

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
    app.add_handler(CommandHandler("filter", filter_example))
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("laudaaa...")
    app.run_polling()
