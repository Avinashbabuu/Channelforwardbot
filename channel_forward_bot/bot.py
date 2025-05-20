import os
import json
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_NAME = "Forward Ai Bot"

app = Client("forward_ai_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Utility Functions
def load_json(file):
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

config = load_json("config.json")
filters_data = load_json("filters.json")

# Startup Message
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(f"""**Welcome to {BOT_NAME}!**

This bot auto-forwards messages from a source channel to a destination channel.

Use /help to see all commands.
""")

# Help Command
@app.on_message(filters.command("help"))
async def help_command(client, message):
    await message.reply("""**Bot Commands:**

/login - Activate bot (only for authorized user)
/setsource <invite_link> - Join and set source channel
/setdestination - Set current channel as destination
/addfilter old new - Replace word before forwarding
/delfilter word - Delete word filter
/addfilefilter old.ext new.ext - Rename file before forward
/delfilefilter old.ext - Delete file rename rule
/status - View current setup & filters
""")

# Login Command
@app.on_message(filters.command("login"))
async def login(client, message):
    if message.from_user.id in config["authorized_users"]:
        await message.reply("Login successful. You are authorized.")
    else:
        await message.reply("Unauthorized access.")

# Set Source Channel
@app.on_message(filters.command("setsource"))
async def set_source(client, message):
    if message.from_user.id not in config["authorized_users"]:
        return await message.reply("Unauthorized.")
    try:
        link = message.text.split(" ", 1)[1]
        chat = await app.join_chat(link)
        config["source_channel"] = chat.id
        save_json("config.json", config)
        await message.reply(f"Source channel set to: {chat.title}")
    except Exception as e:
        await message.reply(f"Error: {e}")

# Set Destination Channel
@app.on_message(filters.command("setdestination"))
async def set_destination(client, message):
    if message.from_user.id not in config["authorized_users"]:
        return await message.reply("Unauthorized.")
    config["destination_channel"] = message.chat.id
    save_json("config.json", config)
    await message.reply(f"Destination channel set to: {message.chat.title}")

# Status
@app.on_message(filters.command("status"))
async def status(client, message):
    if message.from_user.id not in config["authorized_users"]:
        return await message.reply("Unauthorized.")
    src = config["source_channel"]
    dst = config["destination_channel"]
    word_filters = filters_data["words"]
    file_filters = filters_data["files"]
    await message.reply(f"""**Current Bot Status:**

Source Channel ID: `{src}`
Destination Channel ID: `{dst}`
Word Filters: {word_filters}
File Filters: {file_filters}
""")

# Add Word Filter
@app.on_message(filters.command("addfilter"))
async def add_filter(client, message):
    if message.from_user.id not in config["authorized_users"]:
        return
    try:
        old, new = message.text.split(" ", 2)[1:]
        filters_data["words"][old] = new
        save_json("filters.json", filters_data)
        await message.reply(f"Added filter: {old} → {new}")
    except:
        await message.reply("Usage: /addfilter old new")

# Delete Word Filter
@app.on_message(filters.command("delfilter"))
async def del_filter(client, message):
    if message.from_user.id not in config["authorized_users"]:
        return
    word = message.text.split(" ", 1)[1]
    if word in filters_data["words"]:
        del filters_data["words"][word]
        save_json("filters.json", filters_data)
        await message.reply(f"Deleted word filter: {word}")
    else:
        await message.reply("Filter not found.")

# Add File Rename Filter
@app.on_message(filters.command("addfilefilter"))
async def add_file_filter(client, message):
    if message.from_user.id not in config["authorized_users"]:
        return
    try:
        old, new = message.text.split(" ", 2)[1:]
        filters_data["files"][old] = new
        save_json("filters.json", filters_data)
        await message.reply(f"File rename rule added: {old} → {new}")
    except:
        await message.reply("Usage: /addfilefilter old.ext new.ext")

# Delete File Rename Filter
@app.on_message(filters.command("delfilefilter"))
async def del_file_filter(client, message):
    if message.from_user.id not in config["authorized_users"]:
        return
    name = message.text.split(" ", 1)[1]
    if name in filters_data["files"]:
        del filters_data["files"][name]
        save_json("filters.json", filters_data)
        await message.reply(f"Deleted file rename rule: {name}")
    else:
        await message.reply("File rule not found.")

# Auto Forward with Filters
@app.on_message(filters.chat(lambda _, __, msg: msg.chat.id == config.get("source_channel")))
async def forward(client, message: Message):
    dst = config.get("destination_channel")
    if not dst:
        return
    text = message.text or message.caption or ""
    for old, new in filters_data["words"].items():
        text = text.replace(old, new)

    if message.text:
        await client.send_message(dst, text)
    elif message.document:
        name = message.document.file_name
        new_name = filters_data["files"].get(name, name)
        await client.send_document(dst, message.document.file_id, caption=text, file_name=new_name)

app.run()
