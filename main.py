from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.account import UpdateStatusRequest
from telethon.errors import SessionPasswordNeededError
import os
import asyncio
import json

# --- CONFIG ---
API_ID = 30439688
API_HASH = '3976b77adb57ae21e80f66dd6520a244'
BOT_TOKEN = '8664323033:AAE-YMmlqWI1GxzETTl7VVxQjZdc-epC7rw-O_U80'
OWNER_ID = 8697358366 

# Admin Management
ADMIN_FILE = "admins.json"

def load_admins():
    if os.path.exists(ADMIN_FILE):
        with open(ADMIN_FILE, "r") as f:
            return set(json.load(f))
    return {OWNER_ID}

def save_admins(admins_set):
    with open(ADMIN_FILE, "w") as f:
        json.dump(list(admins_set), f)

ADMINS = load_admins()
bot = TelegramClient('manager_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
online_clients = {}

# --- UTILS ---
def get_sessions():
    return [f.split('.')[0] for f in os.listdir() if f.endswith('.session') and not f.startswith('manager_bot')]

async def keep_ids_active():
    """IDs ko hamesha 'Online' status mein rakhne ke liye loop"""
    while True:
        for s, client in list(online_clients.items()):
            try:
                await client(UpdateStatusRequest(offline=False))
                await client.get_me()
            except:
                try: 
                    await client.connect()
                except: 
                    del online_clients[s]
        await asyncio.sleep(45)

async def start_all_sessions():
    """Bot boot hote hi IDs ko connect karega"""
    sessions = get_sessions()
    for s in sessions:
        if s not in online_clients:
            try:
                client = TelegramClient(s, API_ID, API_HASH)
                await client.connect()
                if await client.is_user_authorized():
                    online_clients[s] = client
                    print(f"🟢 {s} is now Online.")
                else:
                    await client.disconnect()
            except Exception as e:
                print(f"🔴 Error starting {s}: {e}")

# --- ADMIN COMMANDS ---

@bot.on(events.NewMessage(pattern='/addadmin'))
async def add_admin(event):
    if event.sender_id != OWNER_ID: return
    try:
        new_admin_id = int(event.text.split()[1])
        ADMINS.add(new_admin_id)
        save_admins(ADMINS)
        await event.respond(f"✅ User `{new_admin_id}` ab admin hai.")
    except:
        await event.respond("❌ Format: `/addadmin ID`")

@bot.on(events.NewMessage(pattern='/removeadmin'))
async def remove_admin(event):
    if event.sender_id != OWNER_ID: return
    try:
        admin_id = int(event.text.split()[1])
        if admin_id == OWNER_ID: return
        ADMINS.discard(admin_id)
        save_admins(ADMINS)
        await event.respond(f"✅ User `{admin_id}` admin se hat gaya.")
    except:
        await event.respond("❌ Format: `/removeadmin ID`")

# --- MAIN HANDLERS ---

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    if event.sender_id not in ADMINS: return
    
    asyncio.create_task(start_all_sessions())
    sessions = get_sessions()
    text = (
        "🛡 **Manager Bot Pro (Always Online)**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👑 **Role:** {'Owner' if event.sender_id == OWNER_ID else 'Admin'}\n"
        f"👥 **Total Sessions:** {len(sessions)}\n"
        f"🌐 **IDs Online:** {len(online_clients)}\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    buttons = [
        [Button.inline("➕ Add New Account", data="add_acc")],
        [Button.inline("🚀 Joiner Mode", data="join_mode"), Button.inline("🔥 Leaver Mode", data="leave_mode")],
        [Button.inline("📋 List Accounts", data="list_acc")]
    ]
    await event.respond(text, buttons=buttons)

@bot.on(events.CallbackQuery(data="join_mode"))
async def joiner_logic(event):
    if event.sender_id not in ADMINS: return
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("🔗 **Channel/Group Link bhejein:**")
        link = (await conv.get_response()).text.strip()
        await conv.send_message("⏱️ **Delay (sec):**")
        try:
            delay = int((await conv.get_response()).text)
        except:
            delay = 5
        
        await conv.send_message(f"🚀 {len(online_clients)} active accounts se joining shuru...")
        
        for s, client in online_clients.items():
            try:
                if 't.me/+' in link or 't.me/joinchat/' in link:
                    hash_code = link.split('+')[-1] if '+' in link else link.split('/')[-1]
                    await client(ImportChatInviteRequest(hash_code))
                else:
                    target = link.split('/')[-1]
                    await client(JoinChannelRequest(target))
                await bot.send_message(event.sender_id, f"✅ Joined: {s}")
            except Exception as e:
                await bot.send_message(event.sender_id, f"❌ {s}: {e}")
            await asyncio.sleep(delay)

@bot.on(events.CallbackQuery(data="add_acc"))
async def add_account_logic(event):
    if event.sender_id not in ADMINS: return
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📱 **Phone (+):**")
        phone = (await conv.get_response()).text.strip().replace(" ", "")
        client = TelegramClient(phone, API_ID, API_HASH)
        await client.connect()
        try:
            await client.send_code_request(phone)
            await conv.send_message("📩 **OTP:**")
            otp = (await conv.get_response()).text
            await client.sign_in(phone, code=otp)
            online_clients[phone] = client
            await conv.send_message(f"✅ {phone} saved & Online!")
        except SessionPasswordNeededError:
            await conv.send_message("🔐 **2FA Password:**")
            pwd = (await conv.get_response()).text
            await client.sign_in(password=pwd)
            online_clients[phone] = client
            await conv.send_message(f"✅ {phone} saved & Online!")
        except Exception as e:
            await conv.send_message(f"❌ Error: {e}")

@bot.on(events.CallbackQuery(data="list_acc"))
async def list_accounts(event):
    if event.sender_id not in ADMINS: return
    msg = "📋 **Account Status:**\n\n"
    for s in get_sessions():
        st = "🟢 ONLINE" if s in online_clients else "🔴 OFFLINE"
        msg += f"• {s}: {st}\n"
    await event.respond(msg)

# --- BOOTUP ---
loop = asyncio.get_event_loop()
loop.create_task(start_all_sessions())
loop.create_task(keep_ids_active())

print("Bot is LIVE with Permanent Admin System...")
bot.run_until_disconnected()
