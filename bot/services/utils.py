import re
import math
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    Operator, AllMembersFlag, GroupSetting, IndividualConfig,
    Bill, BillType, UserAlias, DisplayMode, StatMode, CategoryType
)
from bot.database.db import async_session


async def is_operator(session: AsyncSession, group_id: int, user_id: int) -> bool:
    all_flag = await session.scalar(
        select(AllMembersFlag.is_all_members).where(AllMembersFlag.group_id == group_id)
    )
    if all_flag:
        return True
    op = await session.scalar(
        select(Operator.id).where(Operator.group_id == group_id, Operator.user_id == user_id)
    )
    return op is not None


async def get_group_setting(session: AsyncSession, group_id: int) -> GroupSetting:
    setting = await session.scalar(
        select(GroupSetting).where(GroupSetting.group_id == group_id)
    )
    if not setting:
        setting = GroupSetting(group_id=group_id)
        session.add(setting)
        await session.flush()
    return setting


async def get_individual_config(session: AsyncSession, group_id: int, user_id: int) -> IndividualConfig | None:
    return await session.scalar(
        select(IndividualConfig).where(
            IndividualConfig.group_id == group_id,
            IndividualConfig.user_id == user_id
        )
    )


async def find_user_by_alias(session: AsyncSession, group_id: int, name: str) -> list[int]:
    """Find user IDs matching an alias name."""
    alias_rows = await session.execute(
        select(UserAlias).where(
            UserAlias.group_id == group_id,
            UserAlias.alias_name.ilike(f"{name}%")
        )
    )
    aliases = alias_rows.scalars().all()
    user_ids = [a.user_id for a in aliases]
    op_rows = await session.execute(
        select(Operator).where(
            Operator.group_id == group_id,
            Operator.full_name.ilike(f"{name}%")
        )
    )
    for op in op_rows.scalars().all():
        if op.user_id not in user_ids:
            user_ids.append(op.user_id)
    return user_ids


async def find_operator_by_alias(session: AsyncSession, group_id: int, name: str) -> int | None:
    """Find exactly one operator by name."""
    alias_row = await session.execute(
        select(UserAlias).where(
            UserAlias.group_id == group_id,
            UserAlias.alias_name == name
        )
    )
    alias = alias_row.scalar()
    if alias:
        return alias.user_id

    op_row = await session.execute(
        select(Operator).where(
            Operator.group_id == group_id,
            Operator.full_name == name
        )
    )
    op = op_row.scalar()
    if op:
        return op.user_id
    return None


def safe_eval(expression: str) -> float | None:
    """Safely evaluate a mathematical expression."""
    allowed = set("0123456789.+-*/()%^ ")
    expression = expression.replace(" ", "")
    expression = expression.replace("^", "**")
    if not all(c in allowed for c in expression):
        return None
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return float(result)
    except Exception:
        return None


def parse_bill_input(text: str) -> dict | None:
    """Parse bill input like +1000, +1000u/7.3*0.12, 张三+1000, etc."""
    text = text.strip()

    deposit_match = re.match(r'^[Pp][+-]\s*([\d.]+)\s*(u|r)?\s*(.*)', text)
    if deposit_match:
        amount = float(deposit_match.group(1))
        if text[1] == '-':
            amount = -amount
        unit = deposit_match.group(2) or "USDT"
        if unit == "r":
            unit = "CNY"
        note = deposit_match.group(3).strip()
        return {"type": "deposit", "amount": amount, "currency": unit.upper(), "note": note}

    income_match = re.match(
        r'^([\u4e00-\u9fa5\w]+)?\+(\d+(?:\.\d+)?)\s*(u|r)?\s*(?:/([\d.]+))?\s*(?:\*([\d.]+))?\s*(.*)',
        text
    )
    if income_match:
        target_name = income_match.group(1)
        amount = float(income_match.group(2))
        unit = income_match.group(3) or "USDT"
        if unit == "r":
            unit = "CNY"
        rate = float(income_match.group(4)) if income_match.group(4) else None
        fee = float(income_match.group(5)) if income_match.group(5) else None
        note = income_match.group(6).strip() if income_match.group(6) else ""
        return {
            "type": "income",
            "target_name": target_name,
            "amount": amount,
            "currency": unit.upper(),
            "rate": rate,
            "fee": fee,
            "note": note
        }

    expense_match = re.match(
        r'^([\u4e00-\u9fa5\w]+)?-(\d+(?:\.\d+)?)\s*(u|r)?\s*(?:\*([\d.]+))?\s*(?:/([\d.]+))?\s*(.*)',
        text
    )
    if expense_match:
        target_name = expense_match.group(1)
        amount = float(expense_match.group(2))
        unit = expense_match.group(3) or "USDT"
        if unit == "r":
            unit = "CNY"
        rate = float(expense_match.group(5)) if expense_match.group(5) else None
        fee = float(expense_match.group(4)) if expense_match.group(4) else None
        note = expense_match.group(6).strip() if expense_match.group(6) else ""
        return {
            "type": "proxy_out",
            "target_name": target_name,
            "amount": amount,
            "currency": unit.upper(),
            "rate": rate,
            "fee": fee,
            "note": note
        }

    distribute_match = re.match(
        r'^下发\s*(-?[\d.]+)\s*(u|r)?\s*(?:/([\d.]+))?\s*(.*)',
        text
    )
    if distribute_match:
        amount = float(distribute_match.group(1))
        unit = distribute_match.group(2) or "USDT"
        if unit == "r":
            unit = "CNY"
        rate = float(distribute_match.group(3)) if distribute_match.group(3) else None
        note = distribute_match.group(4).strip()
        return {
            "type": "distribute",
            "amount": amount,
            "currency": unit.upper(),
            "rate": rate,
            "note": note
        }

    named_distribute_match = re.match(
        r'^([\u4e00-\u9fa5\w]+)下发\s*(-?[\d.]+)\s*(u|r)?\s*(?:/([\d.]+))?\s*(.*)',
        text
    )
    if named_distribute_match:
        target_name = named_distribute_match.group(1)
        amount = float(named_distribute_match.group(2))
        unit = named_distribute_match.group(3) or "USDT"
        if unit == "r":
            unit = "CNY"
        rate = float(named_distribute_match.group(4)) if named_distribute_match.group(4) else None
        note = named_distribute_match.group(5).strip()
        return {
            "type": "distribute",
            "target_name": target_name,
            "amount": amount,
            "currency": unit.upper(),
            "rate": rate,
            "note": note
        }

    return None


def format_amount_for_display(amount: float, currency: str = "USDT") -> str:
    """Format amount with currency."""
    if currency == "CNY":
        return f"¥{amount:,.2f}"
    return f"{amount:,.2f} {currency}"


def calculate_cny_amount(amount: float, rate: float = 7.3) -> float:
    return amount * rate


def format_bill_display(bill: Bill, setting: GroupSetting) -> str:
    """Format a single bill for display."""
    bill_id = f"#{bill.id}"
    type_emoji = {"income": "💰", "expense": "💸", "proxy_out": "🔴", "proxy_in": "🟢", "distribute": "📤", "deposit": "🏦", "deposit_deduct": "🏧"}
    emoji = type_emoji.get(bill.bill_type, "📌")

    amount_str = format_amount_for_display(bill.amount, bill.currency)
    line = f"{bill_id} {emoji} {amount_str}"

    if bill.exchange_rate and bill.bill_type in ("income", "deposit", "distribute"):
        cny = calculate_cny_amount(bill.amount, bill.exchange_rate)
        line += f" (¥{cny:,.2f})"

    if setting.display_mode == DisplayMode.SHOW_REPLIER.value and bill.creator_name:
        line += f" | 📝 {bill.creator_name}"
    elif setting.display_mode == DisplayMode.SHOW_CREATOR.value and bill.target_name:
        line += f" | 👤 {bill.target_name}"
    elif setting.display_mode == DisplayMode.DEFAULT.value:
        if bill.target_name and bill.target_name != bill.creator_name:
            line += f" | {bill.target_name}"

    if bill.fee_rate and bill.fee_amount:
        line += f" [费率:{bill.fee_rate}% 费:{bill.fee_amount:,.2f}]"

    if bill.note:
        line += f" 💬 {bill.note}"

    return line
