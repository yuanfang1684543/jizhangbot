from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters, CommandHandler

from bot.database.db import async_session
from bot.database.models import (
    GroupSetting, DisplayMode, StatMode, CategoryType
)
from bot.services.utils import is_operator, get_group_setting
from sqlalchemy import select


async def set_display_replier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """账单显示 - 显示回复人"""
    if not update.effective_chat or not update.effective_user:
        return
    async with async_session() as session:
        setting = await get_group_setting(session, update.effective_chat.id)
        setting.display_mode = DisplayMode.SHOW_REPLIER.value
        await session.commit()
    await update.message.reply_text("✅ 账单显示模式已设置为：**显示回复人**（显示谁记录的账单）")


async def set_display_creator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """账单显示 - 显示入账人"""
    if not update.effective_chat or not update.effective_user:
        return
    async with async_session() as session:
        setting = await get_group_setting(session, update.effective_chat.id)
        setting.display_mode = DisplayMode.SHOW_CREATOR.value
        await session.commit()
    await update.message.reply_text("✅ 账单显示模式已设置为：**显示入账人**（显示收款方）")


async def set_display_pure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """账单显示 - 纯净模式"""
    if not update.effective_chat or not update.effective_user:
        return
    async with async_session() as session:
        setting = await get_group_setting(session, update.effective_chat.id)
        setting.display_mode = DisplayMode.PURE.value
        await session.commit()
    await update.message.reply_text("✅ 账单显示模式已设置为：**纯净模式**（不显示回复人和入账人）")


async def set_display_default(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """账单显示 - 默认模式"""
    if not update.effective_chat or not update.effective_user:
        return
    async with async_session() as session:
        setting = await get_group_setting(session, update.effective_chat.id)
        setting.display_mode = DisplayMode.DEFAULT.value
        await session.commit()
    await update.message.reply_text("✅ 账单显示模式已设置为：**默认模式**")


async def enable_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开启分类"""
    if not update.effective_chat:
        return
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        setting = await get_group_setting(session, update.effective_chat.id)
        setting.category_enabled = True

        if "回复人" in text:
            setting.category_type = CategoryType.BY_REPLIER.value
            msg = "✅ 已开启账单分类，按**回复人**分类"
        elif "入账人" in text or "操作人" in text:
            setting.category_type = CategoryType.BY_CREATOR.value
            msg = "✅ 已开启账单分类，按**入账人**分类"
        else:
            msg = "✅ 已开启账单分类"

        await session.commit()
    await update.message.reply_text(msg)


async def disable_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """关闭分类"""
    if not update.effective_chat:
        return
    async with async_session() as session:
        setting = await get_group_setting(session, update.effective_chat.id)
        setting.category_enabled = False
        await session.commit()
    await update.message.reply_text("✅ 已关闭账单分类")


async def enable_category_collapse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开启分类缩展"""
    if not update.effective_chat:
        return
    async with async_session() as session:
        setting = await get_group_setting(session, update.effective_chat.id)
        setting.category_collapse = True
        await session.commit()
    await update.message.reply_text("✅ 已开启分类缩展")


async def disable_category_collapse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """关闭分类缩展"""
    if not update.effective_chat:
        return
    async with async_session() as session:
        setting = await get_group_setting(session, update.effective_chat.id)
        setting.category_collapse = False
        await session.commit()
    await update.message.reply_text("✅ 已关闭分类缩展")


async def set_stat_default(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """默认统计"""
    if not update.effective_chat:
        return
    async with async_session() as session:
        setting = await get_group_setting(session, update.effective_chat.id)
        setting.stat_mode = StatMode.DEFAULT.value
        await session.commit()
    await update.message.reply_text("✅ 统计显示已设置为：**默认统计**（汇率一致显双币，否则单币）")


async def set_stat_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """单币统计"""
    if not update.effective_chat:
        return
    async with async_session() as session:
        setting = await get_group_setting(session, update.effective_chat.id)
        setting.stat_mode = StatMode.SINGLE.value
        await session.commit()
    await update.message.reply_text("✅ 统计显示已设置为：**单币统计**（仅显示币种）")


async def set_stat_dual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """双币统计"""
    if not update.effective_chat:
        return
    async with async_session() as session:
        setting = await get_group_setting(session, update.effective_chat.id)
        setting.stat_mode = StatMode.DUAL.value
        await session.commit()
    await update.message.reply_text("✅ 统计显示已设置为：**双币统计**（同时显示CNY和币种）")


def register_display_handlers(app):
    """Register display settings handlers."""
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^显示回复人$'),
        set_display_replier
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^显示入账人$'),
        set_display_creator
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^纯净模式$'),
        set_display_pure
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^默认模式$'),
        set_display_default
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^开启分类'),
        enable_category
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^关闭分类$'),
        disable_category
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^开启分类缩展$'),
        enable_category_collapse
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^关闭分类缩展$'),
        disable_category_collapse
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^默认统计$'),
        set_stat_default
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^单币统计$'),
        set_stat_single
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^双币统计$'),
        set_stat_dual
    ))
