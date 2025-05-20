import json
from pyrogram import Client, filters
from pyrogram.types import Message
import os

API_ID = 22630232  # Replace with your API ID
API_HASH = "907cba0d91d193a54375b2abe0e018a6"  # Replace with your API HASH
BOT_TOKEN = "8059875822:AAFLhYNSzHGkz7V5rDvtbJxZy44o52nof8w"  # Replace with your bot token

app = Client("forward_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def save_config(data):
    with open("config.json", "w") as f:
        json.dump(data, f, indent=4)

def load_filters():
    with open("filters.json", "r") as f:
        return json.load(f)

def save_filters(data):
    with open("filters.json", "w") as f:
        json.dump(data, f, indent=4)

@app.on_message(filters.private & filters.command("login"))
async def login(client, message):
    config = load_config()
    if message.from_user.id in config["authorized_users"]:
        await message.reply("Login successful.")
    else:
        await message.reply("Unauthorized.")

@app.on_message(filters.private & filters.command("setsource"))
async def set_source(client, message):
    config = load_config()
    if message.from_user.id not in config["authorized_users"]:
        return await message.reply("Unauthorized.")
    try:
        link = message.text.split(" ", 1)[1]
        chat = await app.join_chat(link)
        config["source_channel"] = chat.id
        save_config(config)
        await message.reply(f"Source channel set: {chat.title}")
    except Exception as e:
        await message.reply(f"Error: {e}")

@app.on_message(filters.command("setdestination"))
async def set_destination(client, message):
    config = load_config()
    if message.from_user.id not in config["authorized_users"]:
        return await message.reply("Unauthorized.")
    config["destination_channel"] = message.chat.id
    save_config(config)
    await message.reply(f"Destination channel set to: {message.chat.title}")

@app.on_message(filters.private & filters.command("addfilter"))
async def add_filter(client, message):
    filters_data = load_filters()
    config = load_config()
    if message.from_user.id not in config["authorized_users"]:
        return await message.reply("Unauthorized.")
    try:
        old, new = message.text.split(" ", 2)[1:]
        filters_data["words"][old] = new
        save_filters(filters_data)
        await message.reply(f"Filter added: {old} -> {new}")
    except:
        await message.reply("Usage: /addfilter old new")

@app.on_message(filters.private & filters.command("delfilter"))
async def del_filter(client, message):
    filters_data = load_filters()
    config = load_config()
    if message.from_user.id not in config["authorized_users"]:
        return await message.reply("Unauthorized.")
    word = message.text.split(" ", 1)[1]
    if word in filters_data["words"]:
        del filters_data["words"][word]
        save_filters(filters_data)
        await message.reply(f"Filter deleted: {word}")
    else:
        await message.reply("Word not found.")

@app.on_message(filters.private & filters.command("addfilefilter"))
async def add_file_filter(client, message):
    filters_data = load_filters()
    config = load_config()
    if message.from_user.id not in config["authorized_users"]:
        return await message.reply("Unauthorized.")
    try:
        old, new = message.text.split(" ", 2)[1:]
        filters_data["files"][old] = new
        save_filters(filters_data)
        await message.reply(f"File filter added: {old} -> {new}")
    except:
        await message.reply("Usage: /addfilefilter oldname newname")

@app.on_message(filters.private & filters.command("delfilefilter"))
async def del_file_filter(client, message):
    filters_data = load_filters()
    config = load_config()
    if message.from_user.id not in config["authorized_users"]:
        return await message.reply("Unauthorized.")
    name = message.text.split(" ", 1)[1]
    if name in filters_data["files"]:
        del filters_data["files"][name]
        save_filters(filters_data)
        await message.reply(f"File filter deleted: {name}")
    else:
        await message.reply("Filter not found.")

@app.on_message(filters.chat(lambda _, __, m: m.chat.id == load_config().get("source_channel")))
async def forwarder(client, message: Message):
    config = load_config()
    filters_data = load_filters()
    dest = config.get("destination_channel")
    if not dest:
        return

    # Text Handling
    if message.text:
        text = message.text
        for old, new in filters_data["words"].items():
            text = text.replace(old, new)
        await client.send_message(dest, text)

    # Document/File Handling
    elif message.document:
        file_name = message.document.file_name
        new_name = filters_data["files"].get(file_name, file_name)
        caption = message.caption or ""
        for old, new in filters_data["words"].items():
            caption = caption.replace(old, new)
        await client.send_document(dest, message.document.file_id, file_name=new_name, caption=caption)

app.run()
