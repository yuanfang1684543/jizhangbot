from telegram import Update, Message
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from bot.database.db import async_session
from bot.database.models import Operator, AllMembersFlag
from bot.services.utils import is_operator
from sqlalchemy import select, delete, insert


async def add_operator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """添加操作人 - 命令 / 或 回复消息"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        targets = []
        if update.message.reply_to_message:
            t_user = update.message.reply_to_message.from_user
            if t_user:
                targets.append((t_user.id, t_user.username or "", t_user.full_name or ""))
        elif context.args:
            for entity in update.message.entities or []:
                if entity.type == "mention":
                    mention_text = update.message.text[entity.offset:entity.offset + entity.length]
                    username = mention_text.lstrip("@")
                    targets.append((0, username, username))
            if not targets:
                for arg in context.args:
                    name = arg.lstrip("@")
                    targets.append((0, name, name))
        else:
            await update.message.reply_text("ℹ️ 请回复目标用户消息，或在命令后 @用户")
            return

        added = []
        for t_uid, t_uname, t_fname in targets:
            if t_uid > 0:
                existing = await session.scalar(
                    select(Operator.id).where(Operator.group_id == group_id, Operator.user_id == t_uid)
                )
            else:
                existing = await session.scalar(
                    select(Operator.id).where(Operator.group_id == group_id, Operator.username == t_uname)
                )
            if not existing:
                session.add(Operator(group_id=group_id, user_id=t_uid, username=t_uname, full_name=t_fname))
                added.append(t_fname or t_uname)

        await session.commit()

    if added:
        await update.message.reply_text(f"✅ 已添加操作人：{'、'.join(added)}")
    else:
        await update.message.reply_text("ℹ️ 目标用户已是操作人或未找到")


async def delete_operator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """删除操作人"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            await update.message.reply_text("❌ 您不是操作人，无权执行此命令")
            return

        targets = []
        if update.message.reply_to_message:
            t_user = update.message.reply_to_message.from_user
            if t_user:
                targets.append((t_user.id, t_user.username or ""))
        elif context.args:
            for arg in context.args:
                targets.append((0, arg.lstrip("@")))
        else:
            await update.message.reply_text("ℹ️ 请回复目标用户消息，或在命令后 @用户")
            return

        removed = []
        for t_uid, t_uname in targets:
            if t_uid > 0:
                await session.execute(
                    delete(Operator).where(Operator.group_id == group_id, Operator.user_id == t_uid)
                )
                removed.append(str(t_uid))
            elif t_uname:
                await session.execute(
                    delete(Operator).where(Operator.group_id == group_id, Operator.username == t_uname)
                )
                removed.append(t_uname)

        await session.commit()

    if removed:
        await update.message.reply_text(f"✅ 已删除操作人：{'、'.join(removed)}")
    else:
        await update.message.reply_text("ℹ️ 未找到指定操作人")


async def list_operators(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看记员 / 显示操作人"""
    if not update.effective_chat:
        return
    group_id = update.effective_chat.id

    async with async_session() as session:
        all_flag = await session.scalar(
            select(AllMembersFlag.is_all_members).where(AllMembersFlag.group_id == group_id)
        )
        ops = (await session.execute(
            select(Operator).where(Operator.group_id == group_id)
        )).scalars().all()

    if all_flag:
        await update.message.reply_text("👥 当前为【全员模式】，所有成员均为操作人")
        return

    if not ops:
        await update.message.reply_text("ℹ️ 当前没有操作人")
        return

    lines = ["📋 **操作人列表**", ""]
    for op in ops:
        name = op.full_name or op.username or str(op.user_id)
        lines.append(f"• {name}")
    text = "\n".join(lines)
    await update.message.reply_text(text)


async def set_all_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置全员为操作人"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    async with async_session() as session:
        flag = await session.scalar(
            select(AllMembersFlag).where(AllMembersFlag.group_id == group_id)
        )
        if not flag:
            flag = AllMembersFlag(group_id=group_id, is_all_members=True)
            session.add(flag)
        else:
            flag.is_all_members = True
        await session.commit()
    await update.message.reply_text("✅ 已开启【全员模式】，所有群成员均为操作人")


async def cancel_all_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """取消全员"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    async with async_session() as session:
        flag = await session.scalar(
            select(AllMembersFlag).where(AllMembersFlag.group_id == group_id)
        )
        if flag:
            flag.is_all_members = False
            await session.commit()
    await update.message.reply_text("✅ 已取消【全员模式】，仅列表中操作人可操作")


async def handle_add_operator_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理文本消息：添加操作人"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            return

    if not update.message.reply_to_message:
        return

    t_user = update.message.reply_to_message.from_user
    if not t_user:
        return

    async with async_session() as session:
        existing = await session.scalar(
            select(Operator.id).where(Operator.group_id == group_id, Operator.user_id == t_user.id)
        )
        if existing:
            await update.message.reply_text("ℹ️ 该用户已是操作人")
            return
        session.add(Operator(
            group_id=group_id,
            user_id=t_user.id,
            username=t_user.username or "",
            full_name=t_user.full_name or ""
        ))
        await session.commit()

    await update.message.reply_text(f"✅ 已添加操作人：{t_user.full_name or t_user.username}")


async def handle_delete_operator_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理文本消息：删除操作人"""
    if not update.effective_chat or not update.effective_user:
        return
    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    async with async_session() as session:
        if not await is_operator(session, group_id, user_id):
            return

    if not update.message.reply_to_message:
        return

    t_user = update.message.reply_to_message.from_user
    if not t_user:
        return

    async with async_session() as session:
        await session.execute(
            delete(Operator).where(Operator.group_id == group_id, Operator.user_id == t_user.id)
        )
        await session.commit()

    await update.message.reply_text(f"✅ 已删除操作人：{t_user.full_name or t_user.username}")


def register_admin_handlers(app):
    """Register admin-related handlers."""
    app.add_handler(CommandHandler("addop", add_operator))
    app.add_handler(CommandHandler("delop", delete_operator))
    app.add_handler(CommandHandler("ops", list_operators))
    app.add_handler(CommandHandler("setall", set_all_members))
    app.add_handler(CommandHandler("cancelall", cancel_all_members))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.REPLY & filters.Regex(r'^添加操作人$'),
        handle_add_operator_text
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.REPLY & filters.Regex(r'^删除操作人$'),
        handle_delete_operator_text
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^添加操作人(\s+@\w+)+$'),
        add_operator
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^删除操作人(\s+@\w+)+$'),
        delete_operator
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^显示操作人$'),
        list_operators
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^(设置全员|全部记员)$'),
        set_all_members
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^(取消全员)$'),
        cancel_all_members
    ))
