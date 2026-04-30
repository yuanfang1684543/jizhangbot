import re
import httpx
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.database.db import async_session
from bot.database.models import GroupSetting
from bot.services.utils import safe_eval, get_group_setting


async def fetch_htx_price() -> str:
    """获取火币USDT价格"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.huobi.pro/market/detail/merged?symbol=usdtcny")
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "ok":
                    price = float(data["tick"]["close"])
                    return f"🔥 火币USDT/CNY: ¥{price:.4f}"
    except Exception:
        pass
    return "❌ 获取火币价格失败"


async def fetch_okx_price() -> str:
    """获取欧易USDT价格"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://www.okx.com/api/v5/market/ticker?instId=USDT-CNY")
            if r.status_code == 200:
                data = r.json()
                if data.get("code") == "0":
                    price = float(data["data"][0]["last"])
                    return f"🟢 欧易USDT/CNY: ¥{price:.4f}"
    except Exception:
        pass
    return "❌ 获取欧易价格失败"


async def handle_htx_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """h0 - 火币U价"""
    result = await fetch_htx_price()
    await update.message.reply_text(result)


async def handle_okx_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """z0 - 欧易U价"""
    result = await fetch_okx_price()
    await update.message.reply_text(result)


async def handle_tron_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查U/信息 - 直接发送Tron地址"""
    text = update.message.text.strip() if update.message.text else ""
    tron_pattern = re.compile(r'^T[a-zA-Z0-9]{33}$')
    if not tron_pattern.match(text):
        return
    await update.message.reply_text(
        f"🔍 Tron地址查询\n"
        f"地址: `{text}`\n"
        f"⚠️ 详细链上数据请在浏览器中查看: https://tronscan.org/#/address/{text}",
        parse_mode="Markdown"
    )


async def handle_price_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """币价计算"""
    text = update.message.text.strip() if update.message.text else ""

    match = re.match(r'^币价\s*([\d.]+)\s*(?:汇率|费率)\s*([\d.]+)\s*\((?:计算|转)\?([%\u6c47\u7387]*)\)', text)
    if not match:
        return

    price = float(match.group(1))
    param = float(match.group(2))
    q_type = match.group(3)

    if "率" in q_type:
        result = price * (1 + param / 100)
        await update.message.reply_text(
            f"💱 币价计算\n"
            f"币价: {price}\n"
            f"费率: {param}%\n"
            f"结果汇率: {result:.4f}"
        )
        return

    result_pct = ((param / price) - 1) * 100
    await update.message.reply_text(
        f"💱 币价计算\n"
        f"币价: {price}\n"
        f"汇率: {param}\n"
        f"费率: {result_pct:+.2f}%"
    )


async def handle_phone_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查询手机号"""
    text = update.message.text.strip() if update.message.text else ""
    match = re.match(r'^查询\s*(1[3-9]\d{9})$', text)
    if not match:
        match = re.match(r'^查询\s*(\d{11})$', text)
    if not match:
        return
    phone = match.group(1)
    await update.message.reply_text(f"📱 手机号查询\n号码: {phone}\n⚠️ 此为敏感信息，请勿滥用")


async def handle_id_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查询身份证"""
    text = update.message.text.strip() if update.message.text else ""
    match = re.match(r'^查询\s*(\d{6}[\d*]{12})$', text)
    if not match:
        match = re.match(r'^查询\s*(\d{17}[\dXx])$', text)
    if not match:
        return
    id_num = match.group(1)
    await update.message.reply_text(f"🪪 身份证查询\n号码: {id_num}\n⚠️ 此为敏感信息，请勿滥用")


async def handle_bank_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查询银行卡"""
    text = update.message.text.strip() if update.message.text else ""
    match = re.match(r'^查询\s*(\d{6}[\d*]+)$', text)
    if not match:
        return
    card = match.group(1)
    await update.message.reply_text(f"💳 银行卡查询\n卡号: {card}\n⚠️ 此为敏感信息，请勿滥用")


async def handle_forex_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """法币汇率"""
    text = update.message.text.strip() if update.message.text else ""
    match = re.match(r'^法币汇率\s*(\w+)', text)
    if not match:
        return
    currency = match.group(1).upper()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"https://api.exchangerate-api.com/v4/latest/USD")
            if r.status_code == 200:
                data = r.json()
                rates = data.get("rates", {})
                if currency in rates:
                    rate = rates[currency]
                    await update.message.reply_text(f"💱 法币汇率\n1 USD = {rate:.4f} {currency}")
                    return
    except Exception:
        pass

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"https://api.it120.cc/gooking/forex/rate?fromCode=USD&toCode={currency}")
            if r.status_code == 200:
                data = r.json()
                if data.get("code") == 0:
                    rate = data.get("data", {}).get("rate", 0)
                    await update.message.reply_text(f"💱 法币汇率\n1 USD = {rate} {currency}")
                    return
    except Exception:
        pass

    await update.message.reply_text(f"❌ 获取 {currency} 汇率失败")


class MathCalcFilter(filters.MessageFilter):
    def filter(self, message):
        if not message.text:
            return False
        text = message.text.strip()
        if re.match(r'^[\d\s+\-*/().%^]+$', text) and any(c in text for c in "+-*/^"):
            return True
        if re.match(r'^\([\d\s+\-*/().%^]+\)$', text):
            return True
        return False


async def handle_math_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """数学计算"""
    text = update.message.text.strip() if update.message.text else ""
    result = safe_eval(text)
    if result is not None:
        await update.message.reply_text(f"🧮 计算结果\n{text} = {result:,.6f}".rstrip("0").rstrip("."))


async def handle_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """账单汇总"""
    if not update.effective_chat:
        return
    group_id = update.effective_chat.id

    from bot.database.models import Bill, BillType
    from sqlalchemy import select, func

    async with async_session() as session:
        setting = await get_group_setting(session, group_id)

        income_total = await session.scalar(
            select(func.sum(Bill.amount)).where(
                Bill.group_id == group_id,
                Bill.bill_type == BillType.INCOME.value,
                Bill.is_deleted == False
            )
        ) or 0

        proxy_out_total = await session.scalar(
            select(func.sum(Bill.amount)).where(
                Bill.group_id == group_id,
                Bill.bill_type == BillType.PROXY_OUT.value,
                Bill.is_deleted == False
            )
        ) or 0

        distribute_total = await session.scalar(
            select(func.sum(Bill.amount)).where(
                Bill.group_id == group_id,
                Bill.bill_type == BillType.DISTRIBUTE.value,
                Bill.is_deleted == False
            )
        ) or 0

        deposit_total = await session.scalar(
            select(func.sum(Bill.amount)).where(
                Bill.group_id == group_id,
                Bill.bill_type == BillType.DEPOSIT.value,
                Bill.is_deleted == False
            )
        ) or 0

    lines = ["📊 **账单汇总**", ""]
    if income_total:
        cny = income_total * (setting.exchange_rate or 7.3)
        lines.append(f"💰 入款: {income_total:,.2f} {setting.currency_name} (¥{cny:,.2f})")
    if proxy_out_total:
        cny = proxy_out_total * (setting.proxy_rate or 8.0)
        lines.append(f"🔴 代付出款: {proxy_out_total:,.2f} {setting.currency_name} (¥{cny:,.2f})")
    if distribute_total:
        cny = distribute_total * (setting.exchange_rate or 7.3)
        lines.append(f"📤 下发: {distribute_total:,.2f} {setting.currency_name} (¥{cny:,.2f})")
    if deposit_total:
        cny = deposit_total * (setting.exchange_rate or 7.3)
        lines.append(f"🏦 寄存: {deposit_total:,.2f} {setting.currency_name} (¥{cny:,.2f})")

    if not lines or len(lines) <= 1:
        lines.append("ℹ️ 暂无账单数据")

    await update.message.reply_text("\n".join(lines))


def register_query_handlers(app):
    """Register query-related handlers."""
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^h0$'), handle_htx_price))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^z0$'), handle_okx_price))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^T[a-zA-Z0-9]{33}$'), handle_tron_lookup))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^币价\s*[\d.]+\s*(?:汇率|费率)\s*[\d.]+\s*\(.*\)'),
        handle_price_calc
    ))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^查询\s*\d{11}'), handle_phone_lookup))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^查询\s*\d{6}[\d*]{12}'),
        handle_id_lookup
    ))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^查询\s*\d{6}[\d*]+'), handle_bank_lookup))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^法币汇率\s*\w+'), handle_forex_rate))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^汇总$'), handle_summary))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & MathCalcFilter(),
        handle_math_calc
    ))
