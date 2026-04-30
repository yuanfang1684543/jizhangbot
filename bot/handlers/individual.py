import re
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.database.db import async_session
from bot.database.models import IndividualConfig, Operator
from bot.services.utils import is_operator, find_user_by_alias
from sqlalchemy import select, delete


async def set_individual_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置单独汇率"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        rate_match = re.search(r'([\d.]+)', text)
        if not rate_match:
            await update.message.reply_text("ℹ️ 请指定汇率数值")
            return
        rate = float(rate_match.group(1))

        target_user_id = None
        target_name = ""

        if update.message.reply_to_message:
            t_user = update.message.reply_to_message.from_user
            if t_user:
                target_user_id = t_user.id
                target_name = t_user.full_name or t_user.username or str(t_user.id)
        else:
            name_match = re.match(r'^设置\s*(\S+?)\s*汇率', text)
            if name_match:
                target_name = name_match.group(1)
                matched = await find_user_by_alias(session, group_id, target_name)
                if matched:
                    target_user_id = matched[0]

        if not target_user_id:
            await update.message.reply_text("ℹ️ 请回复用户消息或指定用户名称")
            return

        config = await session.scalar(
            select(IndividualConfig).where(
                IndividualConfig.group_id == group_id,
                IndividualConfig.user_id == target_user_id
            )
        )
        if config:
            config.exchange_rate = rate
        else:
            config = IndividualConfig(group_id=group_id, user_id=target_user_id, exchange_rate=rate)
            session.add(config)
        await session.commit()

    await update.message.reply_text(f"✅ {target_name} 的单独汇率已设置为：{rate}")


async def set_individual_fee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置单独费率"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        fee_matches = re.findall(r'(-?[\d.]+)', text)
        if not fee_matches:
            await update.message.reply_text("ℹ️ 请指定费率数值")
            return
        fee = float(fee_matches[-1])

        target_user_id = None
        target_name = ""

        if update.message.reply_to_message:
            t_user = update.message.reply_to_message.from_user
            if t_user:
                target_user_id = t_user.id
                target_name = t_user.full_name or t_user.username or str(t_user.id)
        else:
            name_match = re.match(r'^设置\s*(\S+?)\s*费率', text)
            if name_match:
                target_name = name_match.group(1)
                matched = await find_user_by_alias(session, group_id, target_name)
                if matched:
                    target_user_id = matched[0]

        if not target_user_id:
            await update.message.reply_text("ℹ️ 请回复用户消息或指定用户名称")
            return

        config = await session.scalar(
            select(IndividualConfig).where(
                IndividualConfig.group_id == group_id,
                IndividualConfig.user_id == target_user_id
            )
        )
        if config:
            config.fee_rate = fee
        else:
            config = IndividualConfig(group_id=group_id, user_id=target_user_id, fee_rate=fee)
            session.add(config)
        await session.commit()

    await update.message.reply_text(f"✅ {target_name} 的单独费率已设置为：{fee}%")


async def delete_individual_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """删除单独配置"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        target_user_id = None
        target_name = ""

        if update.message.reply_to_message:
            t_user = update.message.reply_to_message.from_user
            if t_user:
                target_user_id = t_user.id
                target_name = t_user.full_name or t_user.username or str(t_user.id)
        else:
            name_match = re.match(r'^删除\s*(\S+?)\s*配置', text)
            if name_match:
                target_name = name_match.group(1)
                matched = await find_user_by_alias(session, group_id, target_name)
                if matched:
                    target_user_id = matched[0]

        if not target_user_id:
            await update.message.reply_text("ℹ️ 请回复用户消息或指定用户名称")
            return

        deleted = await session.execute(
            delete(IndividualConfig).where(
                IndividualConfig.group_id == group_id,
                IndividualConfig.user_id == target_user_id
            )
        )
        await session.commit()

        if deleted.rowcount:
            await update.message.reply_text(f"✅ 已删除 {target_name} 的单独配置")
        else:
            await update.message.reply_text(f"ℹ️ {target_name} 没有单独配置")


async def show_configs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看配置"""
    if not update.effective_chat:
        return
    group_id = update.effective_chat.id

    async with async_session() as session:
        configs = (await session.execute(
            select(IndividualConfig).where(IndividualConfig.group_id == group_id)
        )).scalars().all()

    if not configs:
        await update.message.reply_text("ℹ️ 当前没有单独配置")
        return

    lines = ["📋 **单独配置列表**", ""]
    for cfg in configs:
        name = str(cfg.user_id)
        rate_str = f"汇率:{cfg.exchange_rate}" if cfg.exchange_rate is not None else ""
        fee_str = f"费率:{cfg.fee_rate}%" if cfg.fee_rate is not None else ""
        detail = ", ".join(filter(None, [rate_str, fee_str]))
        lines.append(f"• ID:{name} | {detail}")

    await update.message.reply_text("\n".join(lines))


def register_individual_handlers(app):
    """Register individual config handlers."""
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^设置\s*\S+\s*汇率[\d.]+'),
        set_individual_rate
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^设置\s*\S+\s*费率[-]?[\d.]+'),
        set_individual_fee
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.REPLY & filters.Regex(r'^设置汇率[\d.]+'),
        set_individual_rate
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.REPLY & filters.Regex(r'^设置费率[-]?[\d.]+'),
        set_individual_fee
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^删除\s*\S+\s*配置'),
        delete_individual_config
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.REPLY & filters.Regex(r'^删除配置$'),
        delete_individual_config
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^(配置|查看配置)$'),
        show_configs
    ))
