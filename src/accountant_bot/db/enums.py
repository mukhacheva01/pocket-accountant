from enum import Enum


class EntityType(str, Enum):
    INDIVIDUAL_ENTREPRENEUR = "ip"
    LIMITED_COMPANY = "ooo"
    SELF_EMPLOYED = "self_employed"


class TaxRegime(str, Enum):
    USN_INCOME = "usn_income"
    USN_INCOME_EXPENSE = "usn_income_expense"
    OSNO = "osno"
    NPD = "npd"


class EventCategory(str, Enum):
    TAX = "tax"
    CONTRIBUTION = "contribution"
    DECLARATION = "declaration"
    NOTICE = "notice"
    REPORT = "report"
    HR = "hr"
    EMPLOYEE = "employee"
    MARKETPLACE = "marketplace"
    OTHER = "other"


class EventStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    DISMISSED = "dismissed"
    OVERDUE = "overdue"


class ReminderType(str, Enum):
    DAYS_7 = "days_7"
    DAYS_3 = "days_3"
    DAYS_1 = "days_1"
    SAME_DAY = "same_day"
    OVERDUE = "overdue"


class ReminderStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELED = "canceled"


class LawUpdateReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


class FinanceRecordType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class SubscriptionPlan(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ANNUAL = "annual"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
