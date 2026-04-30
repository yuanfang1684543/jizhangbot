import re
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.database.db import async_session
from bot.database.models import GroupSetting
from bot.services.utils import is_operator, get_group_setting
from sqlalchemy import select


async def set_distribute_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置下发地址"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        match = re.search(r'T[a-zA-Z0-9]{33}', text)
        if not match:
            await update.message.reply_text("ℹ️ 请提供有效的Tron地址")
            return

        addr = match.group(0)
        setting = await get_group_setting(session, group_id)
        setting.distribute_address = addr
        await session.commit()
    await update.message.reply_text(f"✅ 下发地址已设置为：\n`{addr}`")


async def delete_distribute_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """删除下发地址"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        setting = await get_group_setting(session, group_id)
        old_addr = setting.distribute_address
        setting.distribute_address = ""
        await session.commit()

    if old_addr:
        await update.message.reply_text(f"✅ 已删除下发地址：\n`{old_addr}`")
    else:
        await update.message.reply_text("ℹ️ 当前没有设置下发地址")


async def show_distribute_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看下发地址"""
    if not update.effective_chat:
        return
    group_id = update.effective_chat.id

    async with async_session() as session:
        setting = await get_group_setting(session, group_id)

    if setting.distribute_address:
        await update.message.reply_text(f"📤 下发地址\n`{setting.distribute_address}`")
    else:
        await update.message.reply_text("ℹ️ 当前没有设置下发地址")


def register_distribute_handlers(app):
    """Register distribute address handlers."""
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^设置下发地址\s*T'),
        set_distribute_address
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^删除下发地址'),
        delete_distribute_address
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^(下发地址|查看地址)$'),
        show_distribute_address
    ))
