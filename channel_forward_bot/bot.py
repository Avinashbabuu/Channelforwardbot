import os
import asyncio
import json
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_data_dir = "user_data"
os.makedirs(user_data_dir, exist_ok=True)

sessions = {}

def get_user_config(user_id):
    path = os.path.join(user_data_dir, f"{user_id}.json")
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({
                "source_id": None,
                "destination_id": None,
                "filters": [],
                "file_filters": [],
                "forwarding": False
            }, f)
    with open(path, "r") as f:
        return json.load(f)

def save_user_config(user_id, config):
    path = os.path.join(user_data_dir, f"{user_id}.json")
    with open(path, "w") as f:
        json.dump(config, f, indent=2)

@app.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply_text(
        "**Welcome to Forward Ai Bot**\n\n"
        "Commands:\n"
        "/login - Start login with your Telegram account\n"
        "/setsource - Set source channel or group\n"
        "/setdestination - Set destination channel\n"
        "/addfilter old|new - Replace words\n"
        "/removefilter old - Remove filter\n"
        "/startforward - Start auto forwarding\n"
        "/stopforward - Stop auto forwarding"
    )

@app.on_message(filters.command("login"))
async def login_handler(client, message):
    user_id = message.from_user.id
    if user_id in sessions:
        await message.reply("Already logged in.")
        return

    await message.reply("Please enter your phone number with country code (e.g. +91XXXXXXXXXX):")

    def phone_filter(_, m: Message):
        return m.from_user.id == user_id

    phone_msg = await app.listen(message.chat.id, phone_filter)
    phone = phone_msg.text

    user_client = Client(
        name=f"user_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True
    )

    await user_client.connect()
    sent = await user_client.send_code(phone)
    await message.reply("Enter the OTP code you received:")

    otp_msg = await app.listen(message.chat.id, phone_filter)
    otp = otp_msg.text.strip()

    try:
        await user_client.sign_in(phone, sent.phone_code_hash, otp)
        sessions[user_id] = user_client
        await message.reply("Login successful.")
    except Exception as e:
        await message.reply(f"Login failed: {e}")

@app.on_message(filters.command("setsource"))
async def set_source(client, message):
    user_id = message.from_user.id
    if user_id not in sessions:
        await message.reply("Please /login first.")
        return

    user_client = sessions[user_id]
    dialogs = [d async for d in user_client.get_dialogs() if d.chat.type in ["channel", "supergroup", "group"]]

    text = "**Select Source Channel/Group:**\n"
    for i, d in enumerate(dialogs, 1):
        text += f"{i}. {d.chat.title} ({d.chat.id})\n"

    await message.reply(text)

    def selection_filter(_, m: Message):
        return m.from_user.id == user_id

    reply = await app.listen(message.chat.id, selection_filter)
    index = int(reply.text.strip()) - 1

    config = get_user_config(user_id)
    config["source_id"] = dialogs[index].chat.id
    save_user_config(user_id, config)

    await message.reply(f"Source set to: {dialogs[index].chat.title}")

@app.on_message(filters.command("setdestination"))
async def set_dest(client, message):
    user_id = message.from_user.id
    if user_id not in sessions:
        await message.reply("Please /login first.")
        return

    user_client = sessions[user_id]
    dialogs = [d async for d in user_client.get_dialogs() if d.chat.type in ["channel", "supergroup", "group"]]

    text = "**Select Destination Channel/Group:**\n"
    for i, d in enumerate(dialogs, 1):
        text += f"{i}. {d.chat.title} ({d.chat.id})\n"

    await message.reply(text)

    def selection_filter(_, m: Message):
        return m.from_user.id == user_id

    reply = await app.listen(message.chat.id, selection_filter)
    index = int(reply.text.strip()) - 1

    config = get_user_config(user_id)
    config["destination_id"] = dialogs[index].chat.id
    save_user_config(user_id, config)

    await message.reply(f"Destination set to: {dialogs[index].chat.title}")

@app.on_message(filters.command("addfilter"))
async def add_filter(client, message):
    user_id = message.from_user.id
    if "|" not in message.text:
        await message.reply("Usage: /addfilter old|new")
        return
    old, new = message.text.split(" ", 1)[1].split("|")
    config = get_user_config(user_id)
    config["filters"].append((old.strip(), new.strip()))
    save_user_config(user_id, config)
    await message.reply(f"Filter added: `{old.strip()}` → `{new.strip()}`")

@app.on_message(filters.command("removefilter"))
async def remove_filter(client, message):
    user_id = message.from_user.id
    word = message.text.split(" ", 1)[1].strip()
    config = get_user_config(user_id)
    config["filters"] = [f for f in config["filters"] if f[0] != word]
    save_user_config(user_id, config)
    await message.reply(f"Filter removed for: `{word}`")

@app.on_message(filters.command("startforward"))
async def start_forward(client, message):
    user_id = message.from_user.id
    if user_id not in sessions:
        await message.reply("Please /login first.")
        return

    config = get_user_config(user_id)
    config["forwarding"] = True
    save_user_config(user_id, config)
    await message.reply("Forwarding started.")

@app.on_message(filters.command("stopforward"))
async def stop_forward(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    config["forwarding"] = False
    save_user_config(user_id, config)
    await message.reply("Forwarding stopped.")

async def auto_forward_loop():
    while True:
        for user_id, user_client in sessions.items():
            config = get_user_config(user_id)
            if config["forwarding"] and config["source_id"] and config["destination_id"]:
                async for msg in user_client.get_chat_history(config["source_id"], limit=3):
                    if hasattr(msg, "text") and msg.text:
                        text = msg.text
                        for old, new in config["filters"]:
                            text = text.replace(old, new)
                        try:
                            await user_client.send_message(config["destination_id"], text)
                        except:
                            pass
        await asyncio.sleep(10)

@app.on_message(filters.command("help"))
async def help_cmd(client, message):
    await start_handler(client, message)

@app.on_message()
async def ignore_all(client, message):
    pass

async def main():
    await app.start()
    asyncio.create_task(auto_forward_loop())
    print("Bot started.")
    await idle()

from pyrogram.idle import idle
app.run(main())
