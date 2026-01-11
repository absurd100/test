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
config = {"expiry": 3600} 

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
        res = await message.reply(f"✅ **Database** disetel untuk mengingat pesan selama {menit} menit.")
    else:
        res = await message.reply("❌ Contoh: `/setwaktu 60` (untuk 1 jam)")
    asyncio.create_task(auto_delete([message, res]))

@app.on_message(filters.command(["setlocal", "setglobal"]) & filters.group)
async def toggle_antispam(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id): return await message.delete()
    if len(message.command) < 2: return
    
    cmd = message.command[0].lower()
    arg = message.command[1].lower()
    
    if arg in ["on", "off"]:
        if message.chat.id not in group_configs:
            group_configs[message.chat.id] = {"local": False, "global": False}
        
        feature = "local" if "local" in cmd else "global"
        group_configs[message.chat.id][feature] = (arg == "on")
        res = await message.reply(f"✅ Fitur **{feature.upper()}** di grup ini: **{arg.upper()}**")
        asyncio.create_task(auto_delete([message, res]))

@app.on_message(filters.command("settings") & filters.group)
async def show_settings(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id): return await message.delete()
    cfg = group_configs.get(message.chat.id, {"local": False, "global": False})
    text = (
        "📊 **Status Bot 2026**\n\n"
        f"🔹 Lokal (Hapus Duplikat): {'✅ ON' if cfg['local'] else '❌ OFF'}\n"
        f"🔹 Global (Hapus Lintas Grup): {'✅ ON' if cfg['global'] else '❌ OFF'}\n"
        f"⏱ Durasi Memori: {config['expiry'] // 60} menit"
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

    cfg_now = group_configs.get(chat_id, {"local": False, "global": False})

    if content_key in seen_messages:
        data = seen_messages[content_key]
        
        if now - data["time"] < config["expiry"]:
            # --- 1. PROSES PEMBERSIHAN MUNDUR (RETROACTIVE) ---
            # Cari semua pesan lama (di grup yang sama maupun grup lain)
            for old_chat_id, old_msg_id in data["locations"]:
                cfg_old = group_configs.get(old_chat_id, {"local": False, "global": False})
                
                # Hapus pesan lama jika di grup itu fiturnya ON
                is_same_group = (old_chat_id == chat_id)
                if (is_same_group and cfg_old["local"]) or (not is_same_group and cfg_old["global"]):
                    try: await client.delete_messages(chat_id=old_chat_id, message_ids=old_msg_id)
                    except: pass

            # --- 2. PROSES PESAN YANG BARU MASUK ---
            is_already_here = any(loc_id == chat_id for loc_id, m_id in data["locations"])
            
            deleted_now = False
            # Hapus pesan baru jika fitur yang sesuai sedang ON
            if (is_already_here and cfg_now["local"]) or (not is_already_here and cfg_now["global"]):
                try: 
                    await message.delete()
                    deleted_now = True
                except: pass

            # Tetap catat lokasi pesan baru jika tidak dihapus (sebagai pemicu selanjutnya)
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
    print("Bot Antispam 2026 Aktif - Retroactive Local & Global Terpasang.")
    app.run()