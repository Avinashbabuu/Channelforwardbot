
import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# === Load Configuration ===
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# === File Paths ===
FILTER_FILE = "filters.json"
CHANNELS_FILE = "channels.json"

# === Load Filters ===
def load_filters():
    try:
        with open(FILTER_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_filters(filters_dict):
    with open(FILTER_FILE, "w") as f:
        json.dump(filters_dict, f)

filters_dict = load_filters()
awaiting_filter_input = {}
awaiting_delete_input = {}

# === Load Channels ===
def load_channels():
    try:
        with open(CHANNELS_FILE, "r") as f:
            data = json.load(f)
            return data.get("source", []), data.get("destination", []), data.get("names", {})
    except FileNotFoundError:
        return [], [], {}

def save_channels(source_ids, dest_ids, names_dict):
    with open(CHANNELS_FILE, "w") as f:
        json.dump({"source": source_ids, "destination": dest_ids, "names": names_dict}, f)

source_channels, dest_channels, channel_names = load_channels()
awaiting_delete_source = {}
awaiting_delete_dest = {}

# === Bot Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
        message = (
        "Welcome!\n\n"
        "Commands:\n"
        "/start - Show this help\n"
        "/filter - Add a filter (e.g., Hi==Hello)\n"
        "/delfilter - Delete a filter\n"
        "/addsource <channel_id> - Add source channel\n"
        "/adddest <channel_id> - Add destination channel\n"
        "/delsource - Delete source channel\n"
        "/deldest - Delete destination channel"
        )
    await update.message.reply_text(message)

async def filter_example(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    awaiting_filter_input[update.effective_user.id] = True
    await update.message.reply_text("Send filter like this: Hi==Hello")

async def handle_filter_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if awaiting_filter_input.get(user_id):
        text = update.message.text
        if '==' in text:
            word, replacement = text.split('==', 1)
            filters_dict[word.strip()] = replacement.strip()
            save_filters(filters_dict)
            awaiting_filter_input[user_id] = False
            await update.message.reply_text(f"Filter set: {word.strip()} → {replacement.strip()}")
        else:
            await update.message.reply_text("Invalid format. Use: Hi==Hello")

async def del_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    if not filters_dict:
        await update.message.reply_text("No filters set.")
        return

        keys = list(filters_dict.keys())
    awaiting_delete_input[user_id] = keys
    msg = "Filters:\n" + "\n".join([f"{i+1}. {k} → {filters_dict[k]}" for i, k in enumerate(keys)])
    msg += "\nSend the number of the filter to delete."
    await update.message.reply_text(msg)

async def handle_delete_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in awaiting_delete_input:
        try:
            index = int(update.message.text) - 1
            keys = awaiting_delete_input[user_id]
            if 0 <= index < len(keys):
                removed = keys[index]
                del filters_dict[removed]
                save_filters(filters_dict)
                del awaiting_delete_input[user_id]
                await update.message.reply_text(f"Filter deleted: {removed}")
            else:
                await update.message.reply_text("Invalid number.")
        except:
            await update.message.reply_text("Please send a valid number.")
        return

    if user_id in awaiting_delete_source:
        try:
            index = int(update.message.text) - 1
            ids = awaiting_delete_source[user_id]
            if 0 <= index < len(ids):
                cid = ids[index]
                source_channels.remove(cid)
                channel_names.pop(str(cid), None)
                save_channels(source_channels, dest_channels, channel_names)
                del awaiting_delete_source[user_id]
                await update.message.reply_text(f"Deleted source channel: {cid}")
            else:
                await update.message.reply_text("Invalid number.")
        except:
            await update.message.reply_text("Please send a valid number.")
        return

    if user_id in awaiting_delete_dest:
        try:
            index = int(update.message.text) - 1
            ids = awaiting_delete_dest[user_id]
            if 0 <= index < len(ids):
                cid = ids[index]
                dest_channels.remove(cid)
                channel_names.pop(str(cid), None)
                save_channels(source_channels, dest_channels, channel_names)
                del awaiting_delete_dest[user_id]
                await update.message.reply_text(f"Deleted destination channel: {cid}")
            else:
                await update.message.reply_text("Invalid number.")
        except:
            await update.message.reply_text("Please send a valid number.")

async def add_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.args:
        try:
            cid = int(context.args[0])
            chat = await context.bot.get_chat(cid)
            if cid not in source_channels:
                source_channels.append(cid)
                channel_names[str(cid)] = chat.title or str(cid)
                save_channels(source_channels, dest_channels, channel_names)
                await update.message.reply_text(f"Added source channel: {chat.title}")
            else:
                await update.message.reply_text("Already exists.")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

async def add_dest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.args:
        try:
            cid = int(context.args[0])
            chat = await context.bot.get_chat(cid)
            if cid not in dest_channels:
                dest_channels.append(cid)
                channel_names[str(cid)] = chat.title or str(cid)
                save_channels(source_channels, dest_channels, channel_names)
                await update.message.reply_text(f"Added destination channel: {chat.title}")
            else:
                await update.message.reply_text("Already exists.")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

async def del_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID or not source_channels:
        await update.message.reply_text("No source channels to delete.")
        return
    awaiting_delete_source[user_id] = source_channels[:]
    msg = "Source Channels:
" + "
".join([f"{i+1}. {channel_names.get(str(cid), str(cid))}" for i, cid in enumerate(source_channels)])
    msg += "
Send the number to delete."
    await update.message.reply_text(msg)

async def del_dest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID or not dest_channels:
        await update.message.reply_text("No destination channels to delete.")
        return
    awaiting_delete_dest[user_id] = dest_channels[:]
    msg = "Destination Channels:
" + "
".join([f"{i+1}. {channel_names.get(str(cid), str(cid))}" for i, cid in enumerate(dest_channels)])
    msg += "
Send the number to delete."
    await update.message.reply_text(msg)

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post:
        msg = update.channel_post
        if msg.chat.id not in source_channels:
            return

        text = msg.text or msg.caption or ""
        for word, replacement in filters_dict.items():
            text = text.replace(word, replacement)

        for dest_id in dest_channels:
            try:
                if msg.text:
                    await context.bot.send_message(chat_id=dest_id, text=text)
                elif msg.photo:
                    await context.bot.send_photo(chat_id=dest_id, photo=msg.photo[-1].file_id, caption=text)
                elif msg.document:
                    await context.bot.send_document(chat_id=dest_id, document=msg.document.file_id, caption=text)
                else:
                    await context.bot.copy_message(chat_id=dest_id, from_chat_id=msg.chat.id, message_id=msg.message_id)
            except Exception as e:
                print(f"Error forwarding to {dest_id}: {e}")

# === Run Bot ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("filter", filter_example))
    app.add_handler(CommandHandler("delfilter", del_filter))
    app.add_handler(CommandHandler("addsource", add_source))
    app.add_handler(CommandHandler("adddest", add_dest))
    app.add_handler(CommandHandler("delsource", del_source))
    app.add_handler(CommandHandler("deldest", del_dest))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), handle_filter_input))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), handle_delete_input))
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("Bot running...")
    app.run_polling()
