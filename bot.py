#!/usr/bin/env python3
"""
Channel Tracker - Multi-Style Button System
Category stamps, mood labels, action buttons, separators, quotes, resources
Deployable on Render with health check
"""
import os
import sys
import asyncio
import re
import logging
from datetime import datetime
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError
from db import Database

# =============================================
# HEALTH CHECK - Handles GET + HEAD requests
# =============================================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, format, *args):
        pass

def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    print(f"Health check running on port {port}")

start_health_server()

# =============================================
# CONFIG
# =============================================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OWNER_ID = int(os.getenv("OWNER_ID"))

if not all([BOT_TOKEN, CHANNEL_ID, OWNER_ID]):
    print("ERROR: Missing configuration! Check your .env file")
    sys.exit(1)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

db = Database()

owner_prefs = {}

# =============================================
# BUTTON PRESETS
# =============================================
SEPARATORS = {
    "stars": "✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦",
    "hearts": "💗 • • • • • • • 💗",
    "dots": "· · · · · · · · · · ·",
    "diamonds": "◆ ◆ ◆ ◆ ◆ ◆ ◆ ◆ ◆",
    "sparkles": "✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨",
    "fire": "🔥 • • • • • • • 🔥",
    "moon": "🌙 • • • • • • • 🌙",
    "line": "───────────────",
    "double": "═══════════════",
    "wave": "≈ ≈ ≈ ≈ ≈ ≈ ≈ ≈ ≈",
    "flower": "❁ ❁ ❁ ❁ ❁ ❁ ❁ ❁ ❁",
}

RESOURCES = {
    "download": "💾 DOWNLOAD",
    "getfile": "📁 GET FILE",
    "view": "🌐 VIEW LINK",
    "open": "🚀 OPEN",
    "read": "📝 READ MORE",
    "save": "📥 SAVE",
    "browse": "📂 BROWSE",
    "access": "🔗 ACCESS",
    "listen": "🎧 LISTEN",
    "watch": "▶️ WATCH",
    "source": "📄 SOURCE",
    "discuss": "💬 DISCUSS",
}

CATEGORIES = {
    "rs": "🛰️ REMOTE SENSING",
    "ai": "🧠 AI & VISION",
    "code": "💻 CODE HUB",
    "poetry": "📚 POETRY/LIT",
    "startup": "🚀 STARTUP DIARY",
    "design": "🎨 DESIGN",
    "research": "🔬 RESEARCH",
    "geo": "🌍 GEO SPATIAL",
    "data": "📊 DATA SCIENCE",
}

MOODS = {
    "insight": "🎯 INSIGHT",
    "toolkit": "🛠️ TOOLKIT",
    "reflection": "☕ REFLECTION",
    "status": "📢 STATUS",
    "update": "🔄 UPDATE",
    "idea": "💡 IDEA",
    "question": "❓ QUESTION",
    "guide": "📖 GUIDE",
}

ACTIONS = {
    "explore": "🔍 EXPLORE TOPIC",
    "archive": "📂 VIEW ARCHIVE",
    "discuss": "💬 JOIN DISCUSS",
    "source": "🔗 SOURCE",
    "more": "📝 READ MORE",
    "share": "🔄 SHARE",
    "save": "⭐ SAVE",
}

def get_display_name(user) -> str:
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    return user.first_name or f"@{user.username}" or f"User {user.id}"

def is_my_channel(chat_id: int) -> bool:
    clean_channel = str(CHANNEL_ID).replace("-100", "").replace("-", "")
    clean_chat = str(chat_id).replace("-100", "").replace("-", "")
    return clean_chat == clean_channel

async def notify_owner(context, text):
    try:
        await context.bot.send_message(OWNER_ID, text, parse_mode="Markdown")
        return True
    except Exception as e:
        logger.error(f"Notify failed: {e}")
        return False

# =============================================
# AUTO TRACKER
# =============================================
async def auto_track_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.channel_post or not is_my_channel(update.channel_post.chat.id):
        return
    message = update.channel_post
    msg_id = message.message_id
    text = message.text or message.caption or ""
    if not text or text.startswith("/"):
        return
    await asyncio.sleep(0.3)
    prefs = owner_prefs.get(OWNER_ID, {})

    # #2 left|right
    if "#2" in text:
        parts = text.split("#2", 1)
        clean = parts[0].strip()
        rest = parts[1].strip() if len(parts) > 1 else ""
        if "|" in rest:
            left_text, right_text = rest.split("|", 1)
            left_text, right_text = left_text.strip(), right_text.strip()
        else:
            left_text, right_text = rest if rest else "📂 VIEW", "💬 DISCUSS"
        if clean:
            try:
                if message.text: await message.edit_text(clean)
                elif message.caption: await message.edit_caption(caption=clean)
            except: pass
        keyboard = [[InlineKeyboardButton(left_text, callback_data=f"left:{msg_id}"),
                     InlineKeyboardButton(right_text, callback_data=f"right:{msg_id}")]]
        try: await message.edit_reply_markup(InlineKeyboardMarkup(keyboard))
        except: pass
        return

    # #c
    if "#c" in text:
        parts = text.split("#c", 1)
        clean = parts[0].strip()
        key = parts[1].strip() if len(parts) > 1 else ""
        btn_text = CATEGORIES.get(key, key if key else "📂 CATEGORY")
        if clean:
            try:
                if message.text: await message.edit_text(clean)
                elif message.caption: await message.edit_caption(caption=clean)
            except: pass
        keyboard = [[InlineKeyboardButton(btn_text, callback_data=f"cat:{msg_id}")]]
        try: await message.edit_reply_markup(InlineKeyboardMarkup(keyboard))
        except: pass
        return

    # #m
    if "#m" in text:
        parts = text.split("#m", 1)
        clean = parts[0].strip()
        key = parts[1].strip() if len(parts) > 1 else ""
        btn_text = MOODS.get(key, key if key else "🎯 MOOD")
        if clean:
            try:
                if message.text: await message.edit_text(clean)
                elif message.caption: await message.edit_caption(caption=clean)
            except: pass
        keyboard = [[InlineKeyboardButton(btn_text, callback_data=f"mood:{msg_id}")]]
        try: await message.edit_reply_markup(InlineKeyboardMarkup(keyboard))
        except: pass
        return

    # #a
    if "#a" in text:
        parts = text.split("#a", 1)
        clean = parts[0].strip()
        key = parts[1].strip() if len(parts) > 1 else ""
        btn_text = ACTIONS.get(key, key if key else "🔍 EXPLORE")
        if clean:
            try:
                if message.text: await message.edit_text(clean)
                elif message.caption: await message.edit_caption(caption=clean)
            except: pass
        keyboard = [[InlineKeyboardButton(btn_text, callback_data=f"action:{msg_id}")]]
        try: await message.edit_reply_markup(InlineKeyboardMarkup(keyboard))
        except: pass
        return

    # #s
    if text.strip().endswith("#s"):
        clean = text.strip()[:-2].strip()
        if clean:
            try:
                if message.text: await message.edit_text(clean)
                elif message.caption: await message.edit_caption(caption=clean)
            except: pass
        sep = prefs.get("separator", SEPARATORS["stars"])
        keyboard = [[InlineKeyboardButton(sep, callback_data=f"sep:{msg_id}")]]
        try: await message.edit_reply_markup(InlineKeyboardMarkup(keyboard))
        except: pass
        return

    # #q
    if "#q" in text:
        parts = text.split("#q", 1)
        clean = parts[0].strip()
        quote = parts[1].strip() if len(parts) > 1 else "❤️"
        if clean:
            try:
                if message.text: await message.edit_text(clean)
                elif message.caption: await message.edit_caption(caption=clean)
            except: pass
        keyboard = [[InlineKeyboardButton(quote, callback_data=f"quote:{msg_id}")]]
        try: await message.edit_reply_markup(InlineKeyboardMarkup(keyboard))
        except: pass
        return

    # #r
    if "#r" in text:
        parts = text.split("#r", 1)
        clean = parts[0].strip()
        custom = parts[1].strip() if len(parts) > 1 else ""
        btn_text = custom if custom else prefs.get("resource", RESOURCES["view"])
        if clean:
            try:
                if message.text: await message.edit_text(clean)
                elif message.caption: await message.edit_caption(caption=clean)
            except: pass
        keyboard = [[InlineKeyboardButton(btn_text, callback_data=f"res:{msg_id}")]]
        try: await message.edit_reply_markup(InlineKeyboardMarkup(keyboard))
        except: pass
        return

    logger.info(f"Post #{msg_id}: Clean")

# =============================================
# COMMANDS
# =============================================
async def start(update, context):
    if update.effective_user.id != OWNER_ID: return
    await update.message.reply_text(
        "✨ **Tracker Ready**\n\n"
        "#s → Separator\n#q text → Quote\n#r text → Resource\n"
        "#c key → Category\n#m key → Mood\n#a key → Action\n"
        "#2 left|right → Two buttons\n\n/help - Full guide"
    )

async def help_cmd(update, context):
    if update.effective_user.id != OWNER_ID: return
    await update.message.reply_text(
        "📋 **Triggers**\n\n"
        "`#s` → Separator\n`#q text` → Quote button\n"
        "`#r text` → Resource button\n`#c key` → Category stamp\n"
        "`#m key` → Mood label\n`#a key` → Action button\n"
        "`#2 left|right` → Two buttons\n\n"
        "/lists → All presets\n/sep <s> → Set separator\n/res <s> → Set resource\n"
        "/invite <name> → Invite\n/friends → Members\n/stats <id> → Stats\n"
        "/summary → Today\n/check → Count\n/info <id> → Member info"
    )

async def lists_cmd(update, context):
    if update.effective_user.id != OWNER_ID: return
    msg = "📋 **Categories:**\n"
    for k, v in CATEGORIES.items(): msg += f"`#c {k}` → {v}\n"
    msg += "\n**Moods:**\n"
    for k, v in MOODS.items(): msg += f"`#m {k}` → {v}\n"
    msg += "\n**Actions:**\n"
    for k, v in ACTIONS.items(): msg += f"`#a {k}` → {v}\n"
    msg += "\n**Resources:**\n"
    for k, v in RESOURCES.items(): msg += f"`#r {k}` → {v}\n"
    msg += "\n**Separators:**\n"
    for k, v in SEPARATORS.items(): msg += f"`/sep {k}` → {v}\n"
    await update.message.reply_text(msg)

async def sep_cmd(update, context):
    if update.effective_user.id != OWNER_ID: return
    if not context.args: await update.message.reply_text("/sep <style>"); return
    s = context.args[0]
    if s in SEPARATORS:
        if OWNER_ID not in owner_prefs: owner_prefs[OWNER_ID] = {}
        owner_prefs[OWNER_ID]["separator"] = SEPARATORS[s]
        await update.message.reply_text(f"✅ {SEPARATORS[s]}")
    else: await update.message.reply_text("Unknown. /seps to list")

async def seps_cmd(update, context):
    if update.effective_user.id != OWNER_ID: return
    msg = "🎨 **Separators**\n\n"
    for k, v in SEPARATORS.items(): msg += f"`/sep {k}` → {v}\n"
    await update.message.reply_text(msg)

async def res_cmd(update, context):
    if update.effective_user.id != OWNER_ID: return
    if not context.args: await update.message.reply_text("/res <style>"); return
    s = context.args[0]
    if s in RESOURCES:
        if OWNER_ID not in owner_prefs: owner_prefs[OWNER_ID] = {}
        owner_prefs[OWNER_ID]["resource"] = RESOURCES[s]
        await update.message.reply_text(f"✅ {RESOURCES[s]}")
    else: await update.message.reply_text("Unknown. /lists to see")

async def invite_cmd(update, context):
    if update.effective_user.id != OWNER_ID: return
    if not context.args: await update.message.reply_text("/invite <name>"); return
    try:
        inv = await context.bot.create_chat_invite_link(chat_id=CHANNEL_ID, name=f"For {' '.join(context.args)}", member_limit=1)
        db.add_invite_link(" ".join(context.args), inv.invite_link)
        await update.message.reply_text(f"🔗 `{inv.invite_link}`")
    except TelegramError as e: await update.message.reply_text(f"Failed: {e}")

async def friends_cmd(update, context):
    if update.effective_user.id != OWNER_ID: return
    f = db.get_all_friends()
    if not f: await update.message.reply_text("No members."); return
    a = [x for x in f if x[3]=="member"]
    msg = f"👥 {len(a)}\n"
    for x in a[:20]: msg += f"• {x[1]}\n"
    await update.message.reply_text(msg)

async def stats_cmd(update, context):
    if update.effective_user.id != OWNER_ID: return
    if not context.args: await update.message.reply_text("/stats <id>"); return
    try: mid = int(context.args[0])
    except: await update.message.reply_text("Invalid"); return
    c = db.get_post_clicks(mid)
    if not c: await update.message.reply_text("No engagement"); return
    msg = f"📊 Post #{mid}: {len(set(x[0] for x in c))}\n"
    for x in c[:15]: msg += f"• {x[2] or x[1]}\n"
    await update.message.reply_text(msg)

async def summary_cmd(update, context):
    if update.effective_user.id != OWNER_ID: return
    f = db.get_all_friends()
    await update.message.reply_text(f"📊 Today\n👥 {len([x for x in f if x[3]=='member'])}\n🆕 {len(db.get_today_joins())}\n👁 {len(db.get_today_clicks())}")

async def check_cmd(update, context):
    if update.effective_user.id != OWNER_ID: return
    try: await update.message.reply_text(f"📈 **{await context.bot.get_chat_member_count(CHANNEL_ID)}**")
    except TelegramError as e: await update.message.reply_text(f"Error: {e}")

async def note_cmd(update, context):
    if update.effective_user.id != OWNER_ID: return
    if len(context.args)<2: await update.message.reply_text("/note <id> <text>"); return
    try: db.add_note(int(context.args[0])," ".join(context.args[1:])); await update.message.reply_text("✅")
    except: await update.message.reply_text("Error")

async def info_cmd(update, context):
    if update.effective_user.id != OWNER_ID: return
    if not context.args: await update.message.reply_text("/info <id>"); return
    try:
        f=db.get_friend(int(context.args[0]))
        if not f: await update.message.reply_text("Not found"); return
        msg=f"👤 {f[1]}\n@{f[2] or 'N/A'}\n{f[3]}"
        if f[5]: msg+=f"\n📝 {f[5]}"
        await update.message.reply_text(msg)
    except: await update.message.reply_text("Error")

# =============================================
# MEMBER TRACKING
# =============================================
async def handle_member_update(update, context):
    try:
        mu=update.chat_member
        if not is_my_channel(mu.chat.id): return
        user=mu.new_chat_member.user
        old,new=str(mu.old_chat_member.status),str(mu.new_chat_member.status)
        if user.id==context.bot.id: return
        name=get_display_name(user)
        t=datetime.now().strftime('%H:%M:%S')
        if new in ["member","administrator"] and old not in ["member","administrator"]:
            db.add_friend(user.id,name,user.username)
            await notify_owner(context,f"🆕 {name}\n@{user.username or 'N/A'}\n{t}")
        elif new in ["left","kicked"] and old in ["member","administrator"]:
            db.update_friend_status(user.id,"left")
            await notify_owner(context,f"👋 {name}\n@{user.username or 'N/A'}\n{t}")
    except Exception as e: logger.error(f"Member error: {e}")

# =============================================
# BUTTON CLICKS
# =============================================
async def handle_click(update, context):
    query=update.callback_query
    try:
        user=query.from_user
        name=get_display_name(user)
        t=datetime.now().strftime('%H:%M:%S')
        data=query.data.split(":")
        action,msg_id=data[0],int(data[1]) if len(data)>1 else query.message.message_id
        labels={"sep":"✨ Separator","quote":"💬 Quote","res":"📦 Resource",
                "cat":"🏷 Category","mood":"🎯 Mood","action":"🔍 Action",
                "left":"◀️ Left","right":"▶️ Right"}
        db.log_click(user.id,user.username,name,msg_id,action)
        await notify_owner(context,f"{labels.get(action,'👆')}\n{name}\n@{user.username or 'N/A'}\nPost #{msg_id}\n{t}")
        await query.answer("✨")
    except Exception as e:
        logger.error(f"Click error: {e}")
        try: await query.answer()
        except: pass

async def error_handler(update, context): logger.error(f"Error: {context.error}")

# =============================================
# MAIN
# =============================================
def main():
    logger.info("Starting tracker...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    for cmd, h in [("start",start),("help",help_cmd),("lists",lists_cmd),
                   ("sep",sep_cmd),("seps",seps_cmd),("res",res_cmd),
                   ("invite",invite_cmd),("friends",friends_cmd),
                   ("stats",stats_cmd),("summary",summary_cmd),
                   ("check",check_cmd),("note",note_cmd),("info",info_cmd)]:
        app.add_handler(CommandHandler(cmd, h))
    
    app.add_handler(MessageHandler(filters.Chat(int(CHANNEL_ID)) & ~filters.COMMAND, auto_track_posts))
    app.add_handler(ChatMemberHandler(handle_member_update, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(handle_click))
    app.add_error_handler(error_handler)
    
    logger.info("Bot running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
