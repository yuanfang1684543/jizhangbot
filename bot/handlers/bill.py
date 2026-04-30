import datetime
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.database.db import async_session
from bot.database.models import (
    Bill, BillType, GroupSetting, IndividualConfig, DisplayMode
)
from bot.services.utils import (
    is_operator, get_group_setting, get_individual_config,
    find_user_by_alias, parse_bill_input, format_amount_for_display,
    calculate_cny_amount
)
from sqlalchemy import select, func


async def handle_bill_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理记账消息"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    creator_name = update.effective_user.full_name or update.effective_user.username or str(user_id)
    text = update.message.text.strip() if update.message.text else ""
    if not text:
        return

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            return

        setting = await get_group_setting(session, group_id)

    parsed = parse_bill_input(text)
    if not parsed:
        return

    bill_type = parsed["type"]
    amount = parsed["amount"]
    currency = parsed.get("currency", "USDT")
    input_rate = parsed.get("rate")
    input_fee = parsed.get("fee")
    note = parsed.get("note", "")

    target_user_id = None
    target_name = parsed.get("target_name", "")
    reply_user_id = None
    reply_name = ""

    if update.message.reply_to_message:
        reply_user = update.message.reply_to_message.from_user
        if reply_user:
            reply_user_id = reply_user.id
            reply_name = reply_user.full_name or reply_user.username or str(reply_user_id)

    if not target_name and reply_user_id:
        target_user_id = reply_user_id
        target_name = reply_name
    elif target_name:
        async with async_session() as session:
            matched_ids = await find_user_by_alias(session, group_id, target_name)
        if matched_ids:
            target_user_id = matched_ids[0]

    async with async_session() as session:
        setting = await get_group_setting(session, group_id)

        active_exchange_rate = setting.exchange_rate or 7.3
        active_fee_rate = 0.0
        proxy_enabled = setting.proxy_enabled
        proxy_rate = setting.proxy_rate or 8.0
        proxy_fee_rate = setting.proxy_fee or 0.0

        if target_user_id:
            ind_config = await get_individual_config(session, group_id, target_user_id)
            if ind_config:
                if ind_config.exchange_rate is not None:
                    active_exchange_rate = ind_config.exchange_rate
                if ind_config.fee_rate is not None:
                    active_fee_rate = ind_config.fee_rate

        if input_rate:
            active_exchange_rate = input_rate
        if input_fee is not None:
            active_fee_rate = input_fee

        fee_amount = amount * active_fee_rate / 100.0 if active_fee_rate else 0.0

        if bill_type == "income":
            db_bill_type = BillType.INCOME.value
            bill_amount = amount
        elif bill_type == "proxy_out":
            db_bill_type = BillType.PROXY_OUT.value
            active_exchange_rate = active_exchange_rate or proxy_rate
            fee_amount = amount * (active_fee_rate or proxy_fee_rate) / 100.0 if (active_fee_rate or proxy_fee_rate) else 0.0
            bill_amount = amount
        elif bill_type == "deposit":
            db_bill_type = BillType.DEPOSIT.value if amount >= 0 else BillType.DEPOSIT_DEDUCT.value
            bill_amount = abs(amount)
        elif bill_type == "distribute":
            db_bill_type = BillType.DISTRIBUTE.value
            bill_amount = amount
            if amount < 0:
                bill_type = "income"
                db_bill_type = BillType.INCOME.value
                bill_amount = abs(amount)
                note = note or "下发修正"
        else:
            return

        new_bill = Bill(
            group_id=group_id,
            creator_id=user_id,
            creator_name=creator_name,
            target_user_id=target_user_id,
            target_name=target_name or "",
            reply_user_id=reply_user_id,
            reply_name=reply_name,
            bill_type=db_bill_type,
            amount=bill_amount,
            currency=currency,
            exchange_rate=active_exchange_rate if db_bill_type in (BillType.INCOME.value, BillType.DEPOSIT.value) else None,
            fee_rate=active_fee_rate or 0.0,
            fee_amount=fee_amount,
            note=note,
            reply_message_id=update.message.message_id,
            day_switch_time=setting.day_switch_hour is not None and (
                datetime.datetime.utcnow().replace(hour=setting.day_switch_hour, minute=0, second=0, microsecond=0)
                or None
            ) or None
        )
        session.add(new_bill)
        await session.commit()
        await session.refresh(new_bill)

        bill_id = new_bill.id
        setting = await get_group_setting(session, group_id)

    type_emoji = {
        "income": "💰", "expense": "💸", "proxy_out": "🔴",
        "proxy_in": "🟢", "distribute": "📤", "deposit": "🏦",
        "deposit_deduct": "🏧"
    }
    type_label = {
        "income": "入账", "expense": "出款", "proxy_out": "代付出款",
        "proxy_in": "代付入款", "distribute": "下发", "deposit": "寄存",
        "deposit_deduct": "寄存扣除"
    }

    emoji = type_emoji.get(db_bill_type, "📌")
    label = type_label.get(db_bill_type, "记录")

    amount_str = format_amount_for_display(bill_amount, currency)
    response_text = f"#{bill_id} {emoji} {label} {amount_str}"

    if active_exchange_rate and db_bill_type in (BillType.INCOME.value, BillType.DEPOSIT.value, BillType.DISTRIBUTE.value):
        cny = calculate_cny_amount(bill_amount, active_exchange_rate)
        response_text += f" (¥{cny:,.2f})"

    if setting.display_mode == DisplayMode.SHOW_REPLIER.value:
        response_text += f" | 📝 {creator_name}"
    elif setting.display_mode == DisplayMode.SHOW_CREATOR.value and target_name:
        response_text += f" | 👤 {target_name}"
    elif setting.display_mode == DisplayMode.DEFAULT.value:
        if target_name:
            response_text += f" | {target_name}"

    if active_fee_rate:
        response_text += f" [费率:{active_fee_rate}%]"

    if note:
        response_text += f" 💬 {note}"

    await update.message.reply_text(response_text)


async def handle_show_bills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示账单"""
    if not update.effective_chat:
        return
    group_id = update.effective_chat.id
    text = update.message.text.strip() if update.message.text else ""

    async with async_session() as session:
        setting = await get_group_setting(session, group_id)
        limit = setting.display_count or 10

        query = select(Bill).where(
            Bill.group_id == group_id,
            Bill.is_deleted == False
        ).order_by(Bill.id.desc()).limit(limit)
        result = await session.execute(query)
        bills = result.scalars().all()

    if not bills:
        await update.message.reply_text("ℹ️ 暂无账单记录")
        return

    lines = ["📋 **近期账单**", ""]
    for bill in reversed(bills):
        type_emoji = {"income": "💰", "proxy_out": "🔴", "distribute": "📤", "deposit": "🏦", "deposit_deduct": "🏧"}
        emoji = type_emoji.get(bill.bill_type, "📌")
        amount_str = format_amount_for_display(bill.amount, bill.currency)
        line = f"#{bill.id} {emoji} {amount_str}"

        if setting.display_mode == DisplayMode.SHOW_REPLIER.value:
            line += f" | 📝 {bill.creator_name}"
        elif setting.display_mode == DisplayMode.SHOW_CREATOR.value:
            line += f" | 👤 {bill.target_name or bill.creator_name}"
        elif setting.display_mode == DisplayMode.PURE.value:
            pass
        else:
            if bill.target_name and bill.target_name != bill.creator_name:
                line += f" | {bill.target_name}"

        if bill.note:
            line += f" 💬 {bill.note}"
        lines.append(line)

    await update.message.reply_text("\n".join(lines))


async def handle_delete_bill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """删除当前周期账单"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        setting = await get_group_setting(session, group_id)

        if setting.day_switch_hour is not None:
            now = datetime.datetime.utcnow()
            cutoff = now.replace(hour=setting.day_switch_hour, minute=0, second=0, microsecond=0)
            if now < cutoff:
                cutoff = cutoff - datetime.timedelta(days=1)
            bills = (await session.execute(
                select(Bill).where(Bill.group_id == group_id, Bill.created_at >= cutoff, Bill.is_deleted == False)
            )).scalars().all()
        else:
            bills = (await session.execute(
                select(Bill).where(Bill.group_id == group_id, Bill.is_deleted == False)
            )).scalars().all()

        deleted_count = 0
        for bill in bills:
            bill.is_deleted = True
            deleted_count += 1
        await session.commit()

    await update.message.reply_text(f"✅ 已删除 {deleted_count} 条当前周期账单")


async def handle_delete_all_bills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """删除全部历史账单"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        bills = (await session.execute(
            select(Bill).where(Bill.group_id == group_id, Bill.is_deleted == False)
        )).scalars().all()

        count = 0
        for bill in bills:
            bill.is_deleted = True
            count += 1
        await session.commit()

    await update.message.reply_text(f"✅ 已删除全部 {count} 条历史账单")


async def handle_undo_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """撤销上次入款或下发"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    is_income_undo = "入款" in text or "撤销入款" in text
    is_distribute_undo = "下发" in text or "撤销下发" in text

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        query = select(Bill).where(Bill.group_id == group_id, Bill.is_deleted == False)
        if is_income_undo:
            query = query.where(Bill.bill_type == BillType.INCOME.value)
        elif is_distribute_undo:
            query = query.where(Bill.bill_type == BillType.DISTRIBUTE.value)
        query = query.order_by(Bill.id.desc()).limit(1)
        bill = await session.scalar(query)

        if not bill:
            await update.message.reply_text("ℹ️ 没有可撤销的记录")
            return

        bill.is_deleted = True
        await session.commit()

    type_label = "入款" if is_income_undo else ("下发" if is_distribute_undo else "记录")
    await update.message.reply_text(f"✅ 已撤销 {type_label} #{bill.id} {format_amount_for_display(bill.amount, bill.currency)}")


async def handle_undo_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """回复指定记录撤销"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not update.message.reply_to_message:
        return

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        reply_msg_id = update.message.reply_to_message.message_id
        bill = await session.scalar(
            select(Bill).where(Bill.reply_message_id == reply_msg_id, Bill.is_deleted == False)
        )
        if not bill:
            bill = await session.scalar(
                select(Bill).where(Bill.group_id == group_id, Bill.is_deleted == False)
                .order_by(Bill.id.desc()).limit(1)
            )

        if not bill:
            await update.message.reply_text("ℹ️ 没有可撤销的记录")
            return

        bill.is_deleted = True
        await session.commit()

    await update.message.reply_text(f"✅ 已撤销 #{bill.id}")


class BillFilter(filters.MessageFilter):
    def filter(self, message):
        if not message.text:
            return False
        from bot.services.utils import parse_bill_input
        return parse_bill_input(message.text.strip()) is not None


def register_bill_handlers(app):
    """Register bill-related handlers."""
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^(显示账单|\+0)$'),
        handle_show_bills
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^删除账单$'),
        handle_delete_bill
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^删除全部账单$'),
        handle_delete_all_bills
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^(撤销入款|撤销下发)$'),
        handle_undo_last
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.REPLY & filters.Regex(r'^撤销$'),
        handle_undo_reply
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & BillFilter(),
        handle_bill_record
    ))
