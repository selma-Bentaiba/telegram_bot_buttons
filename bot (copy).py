#!/usr/bin/env python3
"""
Smart Channel Engagement Tracker
Monitors joins, leaves, and clicks in your channel
Sends instant DM notifications
"""
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ContextTypes,
)
from telegram.error import TelegramError
from db import Database

# Load config
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OWNER_ID = int(os.getenv("OWNER_ID"))

# Verify config
if not all([BOT_TOKEN, CHANNEL_ID, OWNER_ID]):
    print("❌ Missing configuration! Check your .env file")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize database
db = Database()

# =============================================
# HELPER FUNCTIONS
# =============================================

async def notify_owner(context: ContextTypes.DEFAULT_TYPE, text: str):
    """Send notification to channel owner"""
    try:
        await context.bot.send_message(OWNER_ID, text)
        logger.info(f"Notified owner: {text[:50]}...")
        return True
    except Exception as e:
        logger.error(f"Failed to notify owner: {e}")
        return False

def is_my_channel(chat_id: int) -> bool:
    """Check if chat ID matches our channel"""
    clean_channel = str(CHANNEL_ID).replace("-100", "").replace("-", "")
    clean_chat = str(chat_id).replace("-100", "").replace("-", "")
    return clean_chat == clean_channel

def get_display_name(user) -> str:
    """Get best available name for a user"""
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    elif user.first_name:
        return user.first_name
    elif user.username:
        return f"@{user.username}"
    else:
        return f"User {user.id}"

# =============================================
# COMMAND HANDLERS
# =============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    if update.effective_user.id != OWNER_ID:
        return
    
    await update.message.reply_text(
        "✅ **Channel Tracker Active!**\n\n"
        "I monitor your channel silently and DM you when:\n"
        "🆕 Someone joins\n"
        "👋 Someone leaves\n"
        "👆 Someone clicks a post\n\n"
        "Commands:\n"
        "/invite <name> - Create invite link\n"
        "/friends - List tracked members\n"
        "/stats <id> - Post click stats\n"
        "/check - Member count\n"
        "/broadcast <msg> - Send to channel"
    )

async def invite_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create unique invite link"""
    if update.effective_user.id != OWNER_ID:
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /invite <friend_name>")
        return
    
    name = " ".join(context.args)
    
    try:
        invite = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            name=f"Invited by {name}",
            member_limit=1
        )
        
        db.add_invite_link(name, invite.invite_link)
        
        await update.message.reply_text(
            f"🔗 **Invite for {name}**\n"
            f"`{invite.invite_link}`\n\n"
            f"_This link can only be used once_"
        )
        logger.info(f"Created invite for {name}")
        
    except TelegramError as e:
        await update.message.reply_text(f"❌ Failed: {e}")
        logger.error(f"Invite creation failed: {e}")

async def friends_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all tracked members"""
    if update.effective_user.id != OWNER_ID:
        return
    
    friends = db.get_all_friends()
    
    if not friends:
        await update.message.reply_text("📭 No members tracked yet.")
        return
    
    active = [f for f in friends if f[3] == "member"]
    left = [f for f in friends if f[3] != "member"]
    
    msg = f"👥 **Channel Members**\n\n"
    msg += f"🟢 Active: {len(active)}\n"
    msg += f"🔴 Left: {len(left)}\n\n"
    
    if active:
        msg += "**Currently in channel:**\n"
        for f in active[:10]:  # Show first 10
            msg += f"• {f[1]}"
            if f[2]:
                msg += f" (@{f[2]})"
            msg += "\n"
        if len(active) > 10:
            msg += f"_...and {len(active) - 10} more_\n"
    
    await update.message.reply_text(msg)

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show click stats for a post"""
    if update.effective_user.id != OWNER_ID:
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /stats <message_id>")
        return
    
    try:
        msg_id = int(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid message ID")
        return
    
    clicks = db.get_post_clicks(msg_id)
    
    if not clicks:
        await update.message.reply_text(f"📊 Post #{msg_id}: No clicks yet")
        return
    
    msg = f"📊 **Post #{msg_id} Stats**\n"
    msg += f"Total clicks: {len(clicks)}\n\n"
    msg += "**Clicked by:**\n"
    
    for i, click in enumerate(clicks[:20], 1):
        msg += f"{i}. {click[2] or click[1] or f'User {click[0]}'}"
        if click[3]:
            msg += f" - {click[3]}"
        msg += "\n"
    
    if len(clicks) > 20:
        msg += f"\n_...and {len(clicks) - 20} more_"
    
    await update.message.reply_text(msg)

async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check member count"""
    if update.effective_user.id != OWNER_ID:
        return
    
    try:
        count = await context.bot.get_chat_member_count(CHANNEL_ID)
        await update.message.reply_text(f"📈 Channel has **{count}** members")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast a message to the channel"""
    if update.effective_user.id != OWNER_ID:
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /broadcast <message>")
        return
    
    message = " ".join(context.args)
    
    try:
        sent = await context.bot.send_message(CHANNEL_ID, message)
        await update.message.reply_text(f"✅ Posted to channel (ID: {sent.message_id})")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Failed: {e}")

# =============================================
# EVENT HANDLERS
# =============================================

async def handle_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all member join/leave events"""
    try:
        member_update = update.chat_member
        
        # Log raw event
        logger.info(
            f"CHAT_MEMBER: chat={member_update.chat.id} "
            f"user={member_update.new_chat_member.user.id} "
            f"old={member_update.old_chat_member.status} "
            f"new={member_update.new_chat_member.status}"
        )
        
        # Check if this is our channel
        if not is_my_channel(member_update.chat.id):
            logger.debug(f"Skipping: not our channel")
            return
        
        user = member_update.new_chat_member.user
        old_status = str(member_update.old_chat_member.status)
        new_status = str(member_update.new_chat_member.status)
        
        # Ignore bot's own status changes
        if user.id == context.bot.id:
            logger.debug("Skipping: bot's own status")
            return
        
        display_name = get_display_name(user)
        
        # USER JOINED
        if (new_status in ["member", "administrator"] and 
            old_status not in ["member", "administrator"]):
            
            db.add_friend(user.id, display_name, user.username)
            
            notification = (
                f"🆕 **New Member!**\n\n"
                f"Name: {display_name}\n"
                f"Username: @{user.username or 'N/A'}\n"
                f"ID: `{user.id}`\n"
                f"Time: {datetime.now().strftime('%H:%M:%S')}"
            )
            await notify_owner(context, notification)
            logger.info(f"✅ User joined: {display_name}")
        
        # USER LEFT
        elif (new_status in ["left", "kicked"] and 
              old_status in ["member", "administrator"]):
            
            db.update_friend_status(user.id, "left")
            
            notification = (
                f"👋 **Member Left**\n\n"
                f"Name: {display_name}\n"
                f"Username: @{user.username or 'N/A'}\n"
                f"ID: `{user.id}`\n"
                f"Time: {datetime.now().strftime('%H:%M:%S')}"
            )
            await notify_owner(context, notification)
            logger.info(f"👋 User left: {display_name}")
        
        else:
            logger.info(f"Unhandled status: {old_status} → {new_status}")
    
    except Exception as e:
        logger.error(f"Member update error: {e}", exc_info=True)

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks"""
    query = update.callback_query
    
    try:
        user = query.from_user
        display_name = get_display_name(user)
        
        # Parse callback data
        data = query.data.split(":")
        
        if data[0] == "read":
            # Mark as read
            msg_id = int(data[1]) if len(data) > 1 else query.message.message_id
            
            db.log_click(user.id, user.username, display_name, msg_id)
            
            notification = (
                f"👆 **Post Clicked**\n\n"
                f"User: {display_name}\n"
                f"Username: @{user.username or 'N/A'}\n"
                f"Post: #{msg_id}\n"
                f"Time: {datetime.now().strftime('%H:%M:%S')}"
            )
            await notify_owner(context, notification)
            
            await query.answer("✅ Marked as read!")
            logger.info(f"Click: {display_name} on post #{msg_id}")
        
        else:
            await query.answer("Unknown action")
    
    except Exception as e:
        logger.error(f"Button error: {e}", exc_info=True)
        try:
            await query.answer("❌ Error processing click")
        except:
            pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors gracefully"""
    error_msg = str(context.error)
    logger.error(f"Update {update} caused error: {error_msg}")
    
    # Notify owner of critical errors
    if OWNER_ID and "unauthorized" not in error_msg.lower():
        try:
            await context.bot.send_message(
                OWNER_ID,
                f"⚠️ **Bot Error**\n```{error_msg[:200]}```"
            )
        except:
            pass

# =============================================
# MAIN
# =============================================

def main():
    """Start the bot"""
    logger.info("Starting bot...")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("invite", invite_cmd))
    app.add_handler(CommandHandler("friends", friends_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("check", check_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    
    # Member update handler - CHAT_MEMBER tracks all changes
    app.add_handler(
        ChatMemberHandler(handle_member_update, ChatMemberHandler.CHAT_MEMBER)
    )
    
    # Button click handler
    app.add_handler(CallbackQueryHandler(handle_button_click))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Start polling
    logger.info("✅ Bot is running! Monitoring channel...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
