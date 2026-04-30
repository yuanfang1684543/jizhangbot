import datetime
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.database.db import async_session
from bot.database.models import GroupSetting
from bot.services.utils import is_operator, get_group_setting
from sqlalchemy import select


async def set_day_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置日切时间"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        import re
        match = re.search(r'(\d+)', text)
        if not match:
            await update.message.reply_text("ℹ️ 请指定日切时间（0-23之间的整数）")
            return

        hour = int(match.group(1))
        if hour < 0 or hour > 23:
            await update.message.reply_text("ℹ️ 日切时间应在0-23之间")
            return

        setting = await get_group_setting(session, group_id)
        setting.day_switch_hour = hour
        await session.commit()
    await update.message.reply_text(f"✅ 定时日切已设置为：{hour}:00")


async def disable_day_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """关闭日切"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return
        setting = await get_group_setting(session, group_id)
        setting.day_switch_hour = None
        await session.commit()
    await update.message.reply_text("✅ 定时日切已关闭")


async def set_exchange_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置入款汇率"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        import re
        match = re.search(r'([\d.]+)', text)
        if not match:
            await update.message.reply_text("ℹ️ 请指定汇率数值")
            return

        rate = float(match.group(1))
        setting = await get_group_setting(session, group_id)
        setting.exchange_rate = rate
        await session.commit()
    await update.message.reply_text(f"✅ 入款汇率已设置为：{rate}")


async def set_fee_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置入款费率"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        import re
        matches = re.findall(r'(-?[\d.]+)', text)
        if not matches:
            await update.message.reply_text("ℹ️ 请指定费率数值")
            return

        rate = float(matches[-1])
        setting = await get_group_setting(session, group_id)
        setting.fee_rate = rate
        await session.commit()
    await update.message.reply_text(f"✅ 入款费率已设置为：{rate}%")


async def set_transaction_fee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置单笔手续费"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        import re
        matches = re.findall(r'(-?[\d.]+)', text)
        if not matches:
            await update.message.reply_text("ℹ️ 请指定手续费数值")
            return

        fee = float(matches[-1])
        setting = await get_group_setting(session, group_id)
        setting.transaction_fee = fee
        await session.commit()
    await update.message.reply_text(f"✅ 单笔手续费已设置为：{fee}")


async def set_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置显示币种"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        import re
        match = re.search(r'币种\s*(\w+)', text)
        if not match:
            currency = text.replace("设置", "").replace("币种", "").strip() or "USDT"
        else:
            currency = match.group(1).upper()

        setting = await get_group_setting(session, group_id)
        setting.currency_name = currency
        await session.commit()
    await update.message.reply_text(f"✅ 显示币种已设置为：{currency}")


async def set_group_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置群组分组"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        import re
        match = re.search(r'分组\s*(.+)', text)
        if not match:
            await update.message.reply_text("ℹ️ 请指定分组名称，如：设置分组A组")
            return

        name = match.group(1).strip()
        setting = await get_group_setting(session, group_id)
        setting.group_name = name
        await session.commit()
    await update.message.reply_text(f"✅ 群组分组已设置为：{name}")


async def set_display_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置显示条数"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        import re
        match = re.search(r'(\d+)', text)
        if not match:
            await update.message.reply_text("ℹ️ 请指定显示条数")
            return

        count = int(match.group(1))
        if count < 1:
            count = 1
        if count > 50:
            count = 50

        setting = await get_group_setting(session, group_id)
        setting.display_count = count
        await session.commit()
    await update.message.reply_text(f"✅ 账单显示条数已设置为：{count}")


async def set_real_time_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置实时汇率"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return
        setting = await get_group_setting(session, group_id)
        setting.real_time_rate = not setting.real_time_rate
        status = "开启" if setting.real_time_rate else "关闭"
        await session.commit()
    await update.message.reply_text(f"✅ 实时汇率已{status}")


def register_settings_handlers(app):
    """Register settings handlers."""
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^设置日切时间'),
        set_day_switch
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^关闭日切$'),
        disable_day_switch
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^设置汇率[\d.]+'),
        set_exchange_rate
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^设置费率[-]?[\d.]+'),
        set_fee_rate
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^设置手续费[-]?[\d.]+'),
        set_transaction_fee
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^设置币种'),
        set_currency
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^设置分组'),
        set_group_name
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^设置显示条数'),
        set_display_count
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^设置实时汇率$'),
        set_real_time_rate
    ))
