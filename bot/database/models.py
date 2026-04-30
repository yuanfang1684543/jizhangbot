import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum

from bot.database.db import Base


class BillType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    PROXY_OUT = "proxy_out"
    PROXY_IN = "proxy_in"
    DEPOSIT = "deposit"
    DEPOSIT_DEDUCT = "deposit_deduct"
    DISTRIBUTE = "distribute"


class DisplayMode(str, enum.Enum):
    DEFAULT = "default"
    SHOW_REPLIER = "show_replier"
    SHOW_CREATOR = "show_creator"
    PURE = "pure"


class StatMode(str, enum.Enum):
    DEFAULT = "default"
    SINGLE = "single"
    DUAL = "dual"


class CategoryType(str, enum.Enum):
    BY_REPLIER = "by_replier"
    BY_CREATOR = "by_creator"


class Operator(Base):
    __tablename__ = "operators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False)
    username = Column(String(255), default="")
    full_name = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AllMembersFlag(Base):
    __tablename__ = "all_members_flags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False, unique=True, index=True)
    is_all_members = Column(Boolean, default=False)


class GroupSetting(Base):
    __tablename__ = "group_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False, unique=True, index=True)

    display_mode = Column(String(20), default=DisplayMode.DEFAULT.value)
    tracking_enabled = Column(Boolean, default=False)
    category_enabled = Column(Boolean, default=False)
    category_type = Column(String(20), default=CategoryType.BY_REPLIER.value)
    category_collapse = Column(Boolean, default=False)
    stat_mode = Column(String(20), default=StatMode.DEFAULT.value)
    currency_name = Column(String(50), default="USDT")
    group_name = Column(String(100), default="")
    day_switch_hour = Column(Integer, nullable=True)
    exchange_rate = Column(Float, default=7.3)
    fee_rate = Column(Float, default=0.0)
    transaction_fee = Column(Float, default=0.0)
    proxy_enabled = Column(Boolean, default=False)
    proxy_fee = Column(Float, default=0.0)
    proxy_rate = Column(Float, default=8.0)
    real_time_rate = Column(Boolean, default=False)
    display_count = Column(Integer, default=10)
    distribute_address = Column(Text, default="")
    welcome_message = Column(Text, default="")
    trial_duration = Column(Integer, default=0)


class IndividualConfig(Base):
    __tablename__ = "individual_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False)
    exchange_rate = Column(Float, nullable=True)
    fee_rate = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False, index=True)
    creator_id = Column(BigInteger, nullable=False)
    creator_name = Column(String(255), default="")
    target_user_id = Column(BigInteger, nullable=True)
    target_name = Column(String(255), default="")
    reply_user_id = Column(BigInteger, nullable=True)
    reply_name = Column(String(255), default="")
    bill_type = Column(String(20), nullable=False, default=BillType.INCOME.value)
    amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String(50), default="USDT")
    exchange_rate = Column(Float, nullable=True)
    fee_rate = Column(Float, nullable=True)
    fee_amount = Column(Float, default=0.0)
    note = Column(Text, default="")
    reply_message_id = Column(BigInteger, nullable=True)
    is_deleted = Column(Boolean, default=False)
    day_switch_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class UserAlias(Base):
    __tablename__ = "user_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False)
    alias_name = Column(String(255), nullable=False)


class AdSchedule(Base):
    __tablename__ = "ad_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False, index=True)
    content = Column(Text, default="")
    cron_expression = Column(String(100), default="")
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AutoReply(Base):
    __tablename__ = "auto_replies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False, index=True)
    keyword = Column(String(255), nullable=False)
    reply_content = Column(Text, default="")
    button_color = Column(String(50), default="")
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
