from sqlalchemy import JSON, BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from shared.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from shared.db.enums import (
    EntityType,
    EventCategory,
    EventStatus,
    FinanceRecordType,
    LawUpdateReviewStatus,
    PaymentStatus,
    ReminderStatus,
    ReminderType,
    SubscriptionPlan,
    TaxRegime,
)


class ValueEnum(TypeDecorator):
    impl = String
    cache_ok = True

    def __init__(self, enum_cls):
        super().__init__()
        self.enum_cls = enum_cls
        self.values = [item.value for item in enum_cls]
        self.enum_name = enum_cls.__name__.lower()

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGEnum(*self.values, name=self.enum_name, create_type=False))
        return dialect.type_descriptor(String(length=max(len(value) for value in self.values)))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, self.enum_cls):
            return value.value
        return self.enum_cls(value).value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.enum_cls(value)


def db_enum(enum_cls):
    return ValueEnum(enum_cls)


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    locale: Mapped[str] = mapped_column(String(16), default="ru", nullable=False)
    ai_requests_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")
    ai_requests_date: Mapped[str] = mapped_column(Date, nullable=True)
    referred_by: Mapped[str] = mapped_column(String(64), nullable=True)
    referral_bonus_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")
    last_seen_at = mapped_column(DateTime(timezone=True), nullable=True)
    last_command: Mapped[str] = mapped_column(String(64), nullable=True)
    deactivated_at = mapped_column(DateTime(timezone=True), nullable=True)
    reactivated_at = mapped_column(DateTime(timezone=True), nullable=True)

    business_profile = relationship("BusinessProfile", back_populates="user", uselist=False)
    marketplace_connection = relationship("MarketplaceConnection", back_populates="user", uselist=False)
    user_events = relationship("UserEvent", back_populates="user")
    finance_records = relationship("FinanceRecord", back_populates="user")
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    payments = relationship("Payment", back_populates="user")
    activity = relationship("UserActivity", back_populates="user")


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan = mapped_column(db_enum(SubscriptionPlan), default=SubscriptionPlan.FREE, nullable=False)
    started_at = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at = mapped_column(DateTime(timezone=True), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_requests_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="subscription")


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount_stars: Mapped[int] = mapped_column(Integer, nullable=False)
    plan = mapped_column(db_enum(SubscriptionPlan), nullable=False)
    status = mapped_column(db_enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    telegram_payment_id: Mapped[str] = mapped_column(String(256), nullable=True)
    provider_payment_id: Mapped[str] = mapped_column(String(256), nullable=True)

    user = relationship("User", back_populates="payments")


class BusinessProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_profiles"

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    entity_type = mapped_column(db_enum(EntityType), nullable=False)
    tax_regime = mapped_column(db_enum(TaxRegime), nullable=False)
    has_employees = mapped_column(Boolean, default=False, nullable=False)
    marketplaces_enabled = mapped_column(Boolean, default=False, nullable=False)
    region = mapped_column(String(128), nullable=False)
    industry = mapped_column(String(128), nullable=True)
    reminder_settings = mapped_column(JSON, default=dict, nullable=False)

    user = relationship("User", back_populates="business_profile")


class MarketplaceConnection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "marketplace_connections"

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    provider = mapped_column(String(32), default="ozon", nullable=False)
    seller_id = mapped_column(String(128), nullable=False)
    api_key_secret = mapped_column(Text, nullable=False)
    api_key_masked = mapped_column(String(32), nullable=False)
    status = mapped_column(String(32), default="pending", nullable=False)
    status_message = mapped_column(Text, nullable=True)
    sync_requested_at = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at = mapped_column(DateTime(timezone=True), nullable=True)
    last_error = mapped_column(Text, nullable=True)
    synced_cards = mapped_column(Integer, default=0, nullable=False)
    synced_orders = mapped_column(Integer, default=0, nullable=False)
    synced_stocks = mapped_column(Integer, default=0, nullable=False)
    sync_meta = mapped_column(JSON, default=dict, nullable=False)

    user = relationship("User", back_populates="marketplace_connection")
    products = relationship("OzonProduct", back_populates="connection")
    postings = relationship("OzonPosting", back_populates="connection")
    stocks = relationship("OzonStock", back_populates="connection")


class OzonProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ozon_products"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_ozon_products_user_product"),)

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    connection_id = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), nullable=False)
    product_id = mapped_column(BigInteger, nullable=False)
    offer_id = mapped_column(String(128), nullable=False)
    title = mapped_column(String(512), nullable=True)
    archived = mapped_column(Boolean, default=False, nullable=False)
    has_fbo_stocks = mapped_column(Boolean, default=False, nullable=False)
    has_fbs_stocks = mapped_column(Boolean, default=False, nullable=False)
    visibility = mapped_column(String(64), nullable=True)
    raw_payload = mapped_column(JSON, default=dict, nullable=False)

    connection = relationship("MarketplaceConnection", back_populates="products")


class OzonPosting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ozon_postings"
    __table_args__ = (UniqueConstraint("user_id", "scheme", "posting_number", name="uq_ozon_postings_user_scheme_number"),)

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    connection_id = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), nullable=False)
    scheme = mapped_column(String(16), nullable=False)
    posting_number = mapped_column(String(128), nullable=False)
    order_number = mapped_column(String(128), nullable=True)
    status = mapped_column(String(64), nullable=True)
    in_process_at = mapped_column(DateTime(timezone=True), nullable=True)
    shipment_date = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload = mapped_column(JSON, default=dict, nullable=False)

    connection = relationship("MarketplaceConnection", back_populates="postings")


class OzonStock(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ozon_stocks"
    __table_args__ = (UniqueConstraint("user_id", "product_id", "offer_id", name="uq_ozon_stocks_user_product_offer"),)

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    connection_id = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), nullable=False)
    product_id = mapped_column(BigInteger, nullable=False)
    offer_id = mapped_column(String(128), nullable=False)
    sku = mapped_column(BigInteger, nullable=True)
    present = mapped_column(Integer, default=0, nullable=False)
    reserved = mapped_column(Integer, default=0, nullable=False)
    raw_payload = mapped_column(JSON, default=dict, nullable=False)

    connection = relationship("MarketplaceConnection", back_populates="stocks")


class CalendarEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "calendar_events"

    slug = mapped_column(String(128), unique=True, nullable=False)
    title = mapped_column(String(255), nullable=False)
    description = mapped_column(Text, nullable=False)
    category = mapped_column(db_enum(EventCategory), nullable=False)
    due_date = mapped_column(Date, nullable=False)
    applies_to_entity_types = mapped_column(ARRAY(String), default=list, nullable=False)
    applies_to_tax_regimes = mapped_column(ARRAY(String), default=list, nullable=False)
    applies_if_has_employees = mapped_column(Boolean, nullable=True)
    applies_if_marketplaces = mapped_column(Boolean, nullable=True)
    applies_to_regions = mapped_column(ARRAY(String), default=list, nullable=False)
    priority = mapped_column(Integer, default=50, nullable=False)
    legal_basis = mapped_column(Text, nullable=True)
    recurrence_rule = mapped_column(String(255), nullable=True)
    notification_offsets = mapped_column(JSON, default=list, nullable=False)
    active = mapped_column(Boolean, default=True, nullable=False)
    requires_manual_review = mapped_column(Boolean, default=True, nullable=False)


class UserEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_events"
    __table_args__ = (
        UniqueConstraint("user_id", "calendar_event_id", "due_date", name="uq_user_event_by_template_due_date"),
    )

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    calendar_event_id = mapped_column(ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False)
    due_date = mapped_column(Date, nullable=False)
    status = mapped_column(db_enum(EventStatus), default=EventStatus.PENDING, nullable=False)
    dismissed = mapped_column(Boolean, default=False, nullable=False)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)
    snoozed_until = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="user_events")
    calendar_event = relationship("CalendarEvent")
    reminders = relationship("Reminder", back_populates="user_event")


class Reminder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reminders"
    __table_args__ = (UniqueConstraint("user_event_id", "reminder_type", name="uq_reminder_per_type"),)

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_event_id = mapped_column(ForeignKey("user_events.id", ondelete="CASCADE"), nullable=False)
    scheduled_at = mapped_column(DateTime(timezone=True), nullable=False)
    reminder_type = mapped_column(db_enum(ReminderType), nullable=False)
    sent_at = mapped_column(DateTime(timezone=True), nullable=True)
    status = mapped_column(db_enum(ReminderStatus), default=ReminderStatus.PENDING, nullable=False)
    delivery_payload = mapped_column(JSON, default=dict, nullable=False)

    user_event = relationship("UserEvent", back_populates="reminders")


class LawUpdate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "law_updates"

    source = mapped_column(String(128), nullable=False)
    source_url = mapped_column(String(1024), nullable=False)
    title = mapped_column(String(512), nullable=False)
    summary = mapped_column(Text, nullable=False)
    full_text = mapped_column(Text, nullable=True)
    published_at = mapped_column(DateTime(timezone=True), nullable=False)
    effective_date = mapped_column(Date, nullable=True)
    tags = mapped_column(ARRAY(String), default=list, nullable=False)
    importance_score = mapped_column(Integer, default=0, nullable=False)
    affected_entity_types = mapped_column(ARRAY(String), default=list, nullable=False)
    affected_tax_regimes = mapped_column(ARRAY(String), default=list, nullable=False)
    affected_marketplaces = mapped_column(Boolean, nullable=True)
    action_required = mapped_column(Text, nullable=True)
    is_active = mapped_column(Boolean, default=True, nullable=False)
    review_status = mapped_column(
        db_enum(LawUpdateReviewStatus),
        default=LawUpdateReviewStatus.UNREVIEWED,
        nullable=False,
    )


class LawUpdateDelivery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "law_update_deliveries"
    __table_args__ = (UniqueConstraint("law_update_id", "user_id", name="uq_law_delivery_once"),)

    law_update_id = mapped_column(ForeignKey("law_updates.id", ondelete="CASCADE"), nullable=False)
    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    delivered_at = mapped_column(DateTime(timezone=True), nullable=True)
    status = mapped_column(String(32), default="pending", nullable=False)


class FinanceRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "finance_records"

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    record_type = mapped_column(db_enum(FinanceRecordType), nullable=False)
    amount = mapped_column(Numeric(12, 2), nullable=False)
    currency = mapped_column(String(8), default="RUB", nullable=False)
    category = mapped_column(String(128), nullable=False)
    subcategory = mapped_column(String(128), nullable=True)
    operation_date = mapped_column(Date, nullable=False)
    source_text = mapped_column(Text, nullable=False)
    parsed_payload = mapped_column(JSON, default=dict, nullable=False)

    user = relationship("User", back_populates="finance_records")


class AIDialog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_dialogs"

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question = mapped_column(Text, nullable=False)
    answer = mapped_column(Text, nullable=False)
    sources = mapped_column(JSON, default=list, nullable=False)


class AdminLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_logs"

    action = mapped_column(String(128), nullable=False)
    actor = mapped_column(String(128), nullable=False)
    payload = mapped_column(JSON, default=dict, nullable=False)


class UserActivity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_activity"

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type = mapped_column(String(64), nullable=False)
    payload = mapped_column(JSON, default=dict, nullable=False)

    user = relationship("User", back_populates="activity")
