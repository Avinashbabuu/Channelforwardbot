import os, json
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("forward_ai_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DATA_FOLDER = "user_data"
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

TEMP_SELECTION = {}

def get_user_file(user_id):
    return os.path.join(DATA_FOLDER, f"{user_id}.json")

def get_user_data(user_id):
    path = get_user_file(user_id)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

def save_user_data(user_id, data):
    path = get_user_file(user_id)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def is_logged_in(user_id):
    return os.path.exists(get_user_file(user_id))

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("**Welcome to Forward Ai Bot!**\nUse /login to begin. Use /help for full command list.")

@app.on_message(filters.command("help"))
async def help_command(client, message):
    await message.reply("""**Commands:**
/login - Register yourself
/setsource - Select joined channel/group as source
/setdestination - Select destination channel
/addfilter old new - Replace words
/delfilter word - Remove word filter
/addfilefilter old.ext new.ext - Rename files
/delfilefilter old.ext - Remove file rename rule
/startforward - Start auto-forward
/stopforward - Stop auto-forward
/status - Show setup""")

@app.on_message(filters.command("login"))
async def login(client, message):
    user_id = message.from_user.id
    if is_logged_in(user_id):
        return await message.reply("Already logged in.")
    data = {
        "source": None,
        "destination": None,
        "filters": {},
        "filefilters": {},
        "forward": False
    }
    save_user_data(user_id, data)
    await message.reply("Login successful! Now use /setsource and /setdestination")

async def list_user_chats(client, user_id):
    dialogs = []
    async for dialog in client.iter_dialogs():
        if dialog.chat.type in ["channel", "supergroup", "group"]:
            dialogs.append((dialog.chat.id, dialog.chat.title))
    TEMP_SELECTION[user_id] = dialogs
    return dialogs

@app.on_message(filters.command("setsource"))
async def set_source(client, message):
    user_id = message.from_user.id
    if not is_logged_in(user_id):
        return await message.reply("Use /login first.")
    
    dialogs = await list_user_chats(client, user_id)
    if not dialogs:
        return await message.reply("No joined channels or groups found.")
    
    msg = "**Select a source channel/group:**\n"
    for i, (_, title) in enumerate(dialogs, 1):
        msg += f"{i}. {title}\n"
    msg += "\nReply with the number."
    
    await message.reply(msg)
    TEMP_SELECTION[f"{user_id}_mode"] = "source"

@app.on_message(filters.command("setdestination"))
async def set_destination(client, message):
    user_id = message.from_user.id
    if not is_logged_in(user_id):
        return await message.reply("Use /login first.")

    dialogs = await list_user_chats(client, user_id)
    if not dialogs:
        return await message.reply("No joined channels or groups found.")
    
    msg = "**Select a destination channel/group:**\n"
    for i, (_, title) in enumerate(dialogs, 1):
        msg += f"{i}. {title}\n"
    msg += "\nReply with the number."

    await message.reply(msg)
    TEMP_SELECTION[f"{user_id}_mode"] = "destination"

@app.on_message(filters.text & filters.private)
async def handle_selection(client, message):
    user_id = message.from_user.id
    if f"{user_id}_mode" not in TEMP_SELECTION:
        return
    
    if not message.text.isdigit():
        return await message.reply("Please send a number from the list.")
    
    index = int(message.text) - 1
    mode = TEMP_SELECTION.pop(f"{user_id}_mode")
    chats = TEMP_SELECTION.pop(user_id, [])
    
    if index < 0 or index >= len(chats):
        return await message.reply("Invalid number.")
    
    chat_id, chat_title = chats[index]
    data = get_user_data(user_id)
    
    if mode == "source":
        data["source"] = chat_id
        await message.reply(f"Source set: {chat_title}")
    else:
        data["destination"] = chat_id
        await message.reply(f"Destination set: {chat_title}")
    
    save_user_data(user_id, data)

@app.on_message(filters.command("addfilter"))
async def add_filter(client, message):
    user_id = message.from_user.id
    if not is_logged_in(user_id): return
    try:
        old, new = message.text.split(" ", 2)[1:]
        data = get_user_data(user_id)
        data["filters"][old] = new
        save_user_data(user_id, data)
        await message.reply(f"Filter added: {old} → {new}")
    except:
        await message.reply("Usage: /addfilter old new")

@app.on_message(filters.command("delfilter"))
async def del_filter(client, message):
    user_id = message.from_user.id
    word = message.text.split(" ", 1)[1]
    data = get_user_data(user_id)
    if word in data["filters"]:
        del data["filters"][word]
        save_user_data(user_id, data)
        await message.reply("Filter removed.")
    else:
        await message.reply("Not found.")

@app.on_message(filters.command("addfilefilter"))
async def add_file_filter(client, message):
    user_id = message.from_user.id
    try:
        old, new = message.text.split(" ", 2)[1:]
        data = get_user_data(user_id)
        data["filefilters"][old] = new
        save_user_data(user_id, data)
        await message.reply(f"File rule: {old} → {new}")
    except:
        await message.reply("Usage: /addfilefilter old.ext new.ext")

@app.on_message(filters.command("delfilefilter"))
async def del_file_filter(client, message):
    user_id = message.from_user.id
    word = message.text.split(" ", 1)[1]
    data = get_user_data(user_id)
    if word in data["filefilters"]:
        del data["filefilters"][word]
        save_user_data(user_id, data)
        await message.reply("File rule removed.")
    else:
        await message.reply("Not found.")

@app.on_message(filters.command("startforward"))
async def start_forward(client, message):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    data["forward"] = True
    save_user_data(user_id, data)
    await message.reply("Forwarding started.")

@app.on_message(filters.command("stopforward"))
async def stop_forward(client, message):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    data["forward"] = False
    save_user_data(user_id, data)
    await message.reply("Forwarding stopped.")

@app.on_message(filters.command("status"))
async def status(client, message):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    await message.reply(f"""**Your Setup:**
Source: `{data['source']}`
Destination: `{data['destination']}`
Forwarding: {"✅ On" if data['forward'] else "❌ Off"}
Word Filters: {data['filters']}
File Filters: {data['filefilters']}
""")

@app.on_message(filters.all)
async def forward_messages(client, message: Message):
    for user_file in os.listdir(DATA_FOLDER):
        user_id = int(user_file.split(".")[0])
        data = get_user_data(user_id)
        if not data["forward"] or message.chat.id != data["source"]:
            continue

        text = message.text or message.caption or ""
        for old, new in data["filters"].items():
            text = text.replace(old, new)

        if message.text:
            await client.send_message(data["destination"], text)
        elif message.document:
            fname = message.document.file_name
            newname = data["filefilters"].get(fname, fname)
            await client.send_document(
                data["destination"],
                document=message.document.file_id,
                caption=text,
                file_name=newname
            )

app.run()
        
