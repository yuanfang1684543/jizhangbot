import re
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.database.db import async_session
from bot.database.models import GroupSetting
from bot.services.utils import is_operator, get_group_setting


async def enable_proxy_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开启代付模式"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return
        setting = await get_group_setting(session, group_id)
        setting.proxy_enabled = True
        await session.commit()
    await update.message.reply_text("✅ 已开启代付模式，出款账单将单独显示")


async def disable_proxy_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """关闭代付模式"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return
        setting = await get_group_setting(session, group_id)
        setting.proxy_enabled = False
        await session.commit()
    await update.message.reply_text("✅ 已关闭代付模式，出款将混合显示")


async def set_proxy_fee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置代付手续费"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        matches = re.findall(r'(-?[\d.]+)', text)
        if not matches:
            await update.message.reply_text("ℹ️ 请指定手续费数值")
            return

        fee = float(matches[-1])
        setting = await get_group_setting(session, group_id)
        setting.proxy_fee = fee
        await session.commit()
    await update.message.reply_text(f"✅ 代付手续费已设置为：{fee}")


async def set_proxy_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置代付费率"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        matches = re.findall(r'(-?[\d.]+)', text)
        if not matches:
            await update.message.reply_text("ℹ️ 请指定费率数值")
            return

        rate = float(matches[-1])
        setting = await get_group_setting(session, group_id)
        setting.proxy_rate = rate
        await session.commit()
    await update.message.reply_text(f"✅ 代付汇率已设置为：{rate}")


async def set_proxy_exchange_rate_fee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置代付费率"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        matches = re.findall(r'(-?[\d.]+)', text)
        if not matches:
            await update.message.reply_text("ℹ️ 请指定费率数值")
            return

        rate = float(matches[-1])
        setting = await get_group_setting(session, group_id)
        if "费率" in text:
            setting.proxy_fee = rate
            await update.message.reply_text(f"✅ 代付费率已设置为：{rate}")
        else:
            setting.proxy_rate = rate
            await update.message.reply_text(f"✅ 代付汇率已设置为：{rate}")
        await session.commit()


def register_proxy_handlers(app):
    """Register proxy mode handlers."""
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^开启代付模式$'),
        enable_proxy_mode
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^关闭代付模式$'),
        disable_proxy_mode
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^设置代付手续费[-]?[\d.]+'),
        set_proxy_fee
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^设置代付费率[-]?[\d.]+'),
        set_proxy_exchange_rate_fee
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^设置代付汇率[\d.]+'),
        set_proxy_rate
    ))
