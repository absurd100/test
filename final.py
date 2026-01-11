import time
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError

# --- KONFIGURASI API ---
API_ID = 31339570 
API_HASH = "1f14c1c891126b5bcd0800b94822c821"
BOT_TOKEN = "8337506694:AAEtaGjUC4e9TO9bAh51c2PuaVb4mhvW1MQ"

app = Client("antispam_final_2026", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# Database In-Memory
seen_messages = {}  
group_configs = {} 
config = {"expiry": 3600} # Ini hanya untuk LOKAL (bisa diubah via /setwaktu)
GLOBAL_EXPIRY = 300 # Permanen 5 menit untuk GLOBAL

async def is_admin(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

async def auto_delete(messages, delay=5):
    await asyncio.sleep(delay)
    for msg in messages:
        try: await msg.delete()
        except: pass

# --- PERINTAH ADMIN ---
@app.on_message(filters.command("setwaktu") & filters.group)
async def set_expiry(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id): return await message.delete()
    if len(message.command) >= 2 and message.command[1].isdigit():
        menit = int(message.command[1])
        config["expiry"] = menit * 60
        res = await message.reply(f"✅ **Database LOKAL** disetel ke {menit} menit.\n🌐 **Global** tetap permanen 5 menit.")
    else:
        res = await message.reply("❌ Contoh: `/setwaktu 60` (untuk duplikat lokal 1 jam)")
    asyncio.create_task(auto_delete([message, res]))

@app.on_message(filters.command(["setlocal", "setglobal"]) & filters.group)
async def toggle_antispam(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id): return await message.delete()
    if len(message.command) < 2: return
    
    cmd = message.command[0].lower()
    arg = message.command[1].lower()
    
    if arg in ["on", "off"]:
        if message.chat.id not in group_configs:
            group_configs[message.chat.id] = {"local": True, "global": True}
        
        feature = "local" if "local" in cmd else "global"
        group_configs[message.chat.id][feature] = (arg == "on")
        res = await message.reply(f"✅ Fitur **{feature.upper()}** di grup ini: **{arg.upper()}**")
        asyncio.create_task(auto_delete([message, res]))

@app.on_message(filters.command("settings") & filters.group)
async def show_settings(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id): return await message.delete()
    cfg = group_configs.get(message.chat.id, {"local": True, "global": True})
    text = (
        "📊 **Status Bot 2026**\n\n"
        f"🔹 Lokal (Hapus Duplikat): {'✅ ON' if cfg['local'] else '❌ OFF'}\n"
        f"🔹 Global (Hapus Lintas Grup): {'✅ ON' if cfg['global'] else '❌ OFF'}\n"
        f"⏱ Memori Lokal: {config['expiry'] // 60} menit\n"
        f"🌐 Memori Global: {GLOBAL_EXPIRY // 60} menit (Permanen)"
    )
    res = await message.reply(text)
    asyncio.create_task(auto_delete([message, res], 10))

# --- LOGIKA UTAMA ---
@app.on_message(filters.group & ~filters.service)
async def handle_antispam(client, message):
    if not message.text or not message.from_user: return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    content_key = f"{user_id}_{message.text.strip()}"
    now = time.time()

    if await is_admin(client, chat_id, user_id): return

    cfg_now = group_configs.get(chat_id, {"local": True, "global": True})

    if content_key in seen_messages:
        data = seen_messages[content_key]
        time_diff = now - data["time"]
        
        # Cek apakah masih dalam durasi (salah satu: lokal atau global)
        if time_diff < max(config["expiry"], GLOBAL_EXPIRY):
            
            # --- 1. PROSES PEMBERSIHAN MUNDUR ---
            for old_chat_id, old_msg_id in data["locations"]:
                cfg_old = group_configs.get(old_chat_id, {"local": True, "global": True})
                is_same_group = (old_chat_id == chat_id)
                
                # Cek filter waktu masing-masing
                if is_same_group and cfg_old["local"] and time_diff < config["expiry"]:
                    try: await client.delete_messages(chat_id=old_chat_id, message_ids=old_msg_id)
                    except: pass
                elif not is_same_group and cfg_old["global"] and time_diff < GLOBAL_EXPIRY:
                    try: await client.delete_messages(chat_id=old_chat_id, message_ids=old_msg_id)
                    except: pass

            # --- 2. PROSES PESAN YANG BARU MASUK ---
            is_already_here = any(loc_id == chat_id for loc_id, m_id in data["locations"])
            deleted_now = False
            
            if is_already_here and cfg_now["local"] and time_diff < config["expiry"]:
                try: 
                    await message.delete()
                    deleted_now = True
                except: pass
            elif not is_already_here and cfg_now["global"] and time_diff < GLOBAL_EXPIRY:
                try: 
                    await message.delete()
                    deleted_now = True
                except: pass

            if not deleted_now:
                data["locations"].append((chat_id, message.id))
            return
        else:
            del seen_messages[content_key]

    # Simpan sebagai pemicu awal
    seen_messages[content_key] = {
        "time": now,
        "locations": [(chat_id, message.id)]
    }

if __name__ == "__main__":
    print("Bot Antispam 2026 Aktif - Global 5 Menit Permanen & Default ON.")
    app.run()
