import os
import json
from telegram import Update, Chat
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# === Load Configuration ===
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# === File Paths ===
FILTER_FILE = "filters.json"
CHANNELS_FILE = "channels.json"

# === Global Data ===
filters_dict = {}
awaiting_filter_input = {}
awaiting_delete_input = {}
source_channels = []
dest_channels = []
channel_names = {}

# === Helper Functions ===
def load_filters():
    try:
        with open(FILTER_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_filters(filters_dict):
    with open(FILTER_FILE, "w") as f:
        json.dump(filters_dict, f)

def load_channels():
    try:
        with open(CHANNELS_FILE, "r") as f:
            data = json.load(f)
            return data.get("source", []), data.get("destination", []), data.get("names", {})
    except FileNotFoundError:
        return [], [], {}

def save_channels(source_ids, dest_ids, names):
    with open(CHANNELS_FILE, "w") as f:
        json.dump({"source": source_ids, "destination": dest_ids, "names": names}, f)

# === Bot Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    message = (
        "Welcome!\n\n"
        "Commands:\n"
        "/filter - Add a filter (e.g., Hi==Hello)\n"
        "/delfilter - Delete a filter\n"
        "/addsource - Add source channel (forward message from that channel)\n"
        "/delsource - Delete a source channel\n"
        "/adddest - Add destination channel (forward message from that channel)\n"
        "/deldest - Delete a destination channel"
    )
    await update.message.reply_text(message)

async def filter_example(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    awaiting_filter_input[update.effective_user.id] = True
    await update.message.reply_text("Send filter like this: Hi==Hello")

async def del_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    if not filters_dict:
        await update.message.reply_text("No filters set.")
        return

    keys = list(filters_dict.keys())
    awaiting_delete_input[user_id] = ("filter", keys)
    msg = "Filters:\n" + "\n".join([f"{i+1}. {k} → {filters_dict[k]}" for i, k in enumerate(keys)])
    msg += "\nSend the number of the filter to delete."
    await update.message.reply_text(msg)

async def add_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("Forward a message from the source channel here to add it.")

async def add_dest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("Forward a message from the destination channel here to add it.")

async def del_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not source_channels:
        await update.message.reply_text("No source channels set.")
        return

    awaiting_delete_input[update.effective_user.id] = ("source", list(source_channels))
    msg = "Source Channels:\n" + "\n".join([
        f"{i+1}. {channel_names.get(cid, cid)}" for i, cid in enumerate(source_channels)
    ])
    msg += "\nSend the number of the source channel to delete."
    await update.message.reply_text(msg)

async def del_dest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not dest_channels:
        await update.message.reply_text("No destination channels set.")
        return

    awaiting_delete_input[update.effective_user.id] = ("dest", list(dest_channels))
    msg = "Destination Channels:\n" + "\n".join([
        f"{i+1}. {channel_names.get(cid, cid)}" for i, cid in enumerate(dest_channels)
    ])
    msg += "\nSend the number of the destination channel to delete."
    await update.message.reply_text(msg)

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Handle filter input
    if awaiting_filter_input.get(user_id):
        if '==' in text:
            word, replacement = text.split('==', 1)
            filters_dict[word.strip()] = replacement.strip()
            save_filters(filters_dict)
            awaiting_filter_input[user_id] = False
            await update.message.reply_text(f"Filter set: {word.strip()} → {replacement.strip()}")
        else:
            await update.message.reply_text("Invalid format. Use: Hi==Hello")
        return

    # Handle delete inputs
    if user_id in awaiting_delete_input:
        try:
            index = int(text) - 1
            key, items = awaiting_delete_input[user_id]

            if 0 <= index < len(items):
                target_id = items[index]

                if key == "filter":
                    del filters_dict[target_id]
                    save_filters(filters_dict)
                    await update.message.reply_text(f"Filter deleted: {target_id}")
                elif key == "source":
                    source_channels.remove(target_id)
                    channel_names.pop(str(target_id), None)
                    save_channels(source_channels, dest_channels, channel_names)
                    await update.message.reply_text(f"Source channel removed: {target_id}")
                elif key == "dest":
                    dest_channels.remove(target_id)
                    channel_names.pop(str(target_id), None)
                    save_channels(source_channels, dest_channels, channel_names)
                    await update.message.reply_text(f"Destination channel removed: {target_id}")
                del awaiting_delete_input[user_id]
            else:
                await update.message.reply_text("Invalid number.")
        except:
            await update.message.reply_text("Please send a valid number.")
        return

# === Message Forward Handler ===
async def handle_forwarded_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.forward_from_chat:
        chat: Chat = update.message.forward_from_chat
        cid = chat.id
        title = chat.title or str(cid)

        if cid not in source_channels and cid not in dest_channels:
            await update.message.reply_text(
                "Reply with 'source' or 'dest' to add this channel as source or destination."
            )
            context.chat_data['pending_add'] = cid
            context.chat_data['pending_title'] = title

    elif update.message.text.lower() in ["source", "dest"]:
        cid = context.chat_data.get('pending_add')
        title = context.chat_data.get('pending_title')

        if not cid:
            await update.message.reply_text("No channel pending for addition.")
            return

        if update.message.text.lower() == "source":
            if cid not in source_channels:
                source_channels.append(cid)
                channel_names[str(cid)] = title
                save_channels(source_channels, dest_channels, channel_names)
                await update.message.reply_text(f"Added source channel: {title}")
        else:
            if cid not in dest_channels:
                dest_channels.append(cid)
                channel_names[str(cid)] = title
                save_channels(source_channels, dest_channels, channel_names)
                await update.message.reply_text(f"Added destination channel: {title}")

        context.chat_data.pop('pending_add', None)
        context.chat_data.pop('pending_title', None)

# === Forward Channel Messages ===
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
    filters_dict = load_filters()
    source_channels, dest_channels, channel_names = load_channels()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("filter", filter_example))
    app.add_handler(CommandHandler("delfilter", del_filter))
    app.add_handler(CommandHandler("addsource", add_source))
    app.add_handler(CommandHandler("adddest", add_dest))
    app.add_handler(CommandHandler("delsource", del_source))
    app.add_handler(CommandHandler("deldest", del_dest))

    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), handle_admin_input))
    app.add_handler(MessageHandler(filters.FORWARDED & filters.User(ADMIN_ID), handle_forwarded_channel))
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("Bot running...")
    app.run_polling()
