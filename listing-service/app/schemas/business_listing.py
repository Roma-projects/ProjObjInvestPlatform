"""Строгие входные модели формы продажи бизнеса из ТЗ."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BusinessType(str, Enum):
    food = "food"
    retail = "retail"
    services = "services"
    beauty = "beauty"
    entertainment = "entertainment"
    education = "education"
    logistics = "logistics"
    auto = "auto"
    hospitality = "hospitality"
    manufacturing = "manufacturing"
    itd = "itd"
    vending = "vending"
    other = "other"


class DealComposition(str, Enum):
    owner = "owner"
    owner_with_rent = "owner_with_rent"
    with_stock = "with_stock"
    with_contracts = "with_contracts"


class PropertyType(str, Enum):
    free_purpose = "free_purpose"
    production = "production"
    kiosk = "kiosk"


class PropertyCondition(str, Enum):
    needs_repair = "needs_repair"
    cosmetic_repair = "cosmetic_repair"
    good_condition = "good_condition"
    excellent_condition = "excellent_condition"


class TransferMethod(str, Enum):
    full_transfer_training = "full_transfer_training"
    transfer_no_training = "transfer_no_training"
    assets_only = "assets_only"


class EquipmentCondition(str, Enum):
    repair_needed = "требует замены/ремонта"
    good = "хорошее"
    excellent = "отличное"


class SellerStatus(str, Enum):
    ip = "ip"
    self_employed = "self_employed"


class EquipmentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    equipment_name: str = Field(min_length=1, max_length=200)
    equipment_brand: str | None = Field(default=None, max_length=200)
    equipment_condition: EquipmentCondition | None = None
    equipment_purchase_year: int | None = Field(default=None, ge=1900, le=2100)
    equipment_value: Decimal | None = Field(default=None, ge=0)


class StaffDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position: str = Field(min_length=1, max_length=100)
    count: int = Field(ge=0, le=10000)
    salary: Decimal = Field(ge=0)


class MonthlyFinancial(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    revenue: Decimal = Field(ge=0)
    total_expenses: Decimal = Field(ge=0)
    utilities_expenses: Decimal = Field(default=Decimal(0), ge=0)
    rent_expenses: Decimal = Field(default=Decimal(0), ge=0)
    payroll_expenses: Decimal = Field(default=Decimal(0), ge=0)
    purchases_expenses: Decimal = Field(default=Decimal(0), ge=0)
    taxes_expenses: Decimal = Field(default=Decimal(0), ge=0)
    marketing_expenses: Decimal = Field(default=Decimal(0), ge=0)
    other_expenses: Decimal = Field(default=Decimal(0), ge=0)
    net_profit: Decimal


class BusinessListingDraft(BaseModel):
    # Пустые значения допустимы во время заполнения многостраничного черновика.
    model_config = ConfigDict(extra="forbid")

    business_type: BusinessType | None = None
    property_type: PropertyType | None = None
    transfer_method: TransferMethod | None = None
    deal_composition: DealComposition | None = None
    business_name: str | None = Field(default=None, max_length=200)
    short_description: str | None = Field(default=None, max_length=500)
    full_description: str | None = None
    sale_price: Decimal | None = Field(default=None, ge=0)
    stock_included: bool | None = None
    stock_value: Decimal | None = Field(default=None, ge=0)
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    street: str | None = Field(default=None, max_length=200)
    house: str | None = Field(default=None, max_length=50)
    query: str | None = Field(default=None, max_length=500)
    area_sqm: float | None = Field(default=None, gt=0)
    floor_number: int | None = None
    has_separate_entrance: bool | None = None
    parking_spaces: int | None = Field(default=None, ge=0)
    ceiling_height: float | None = Field(default=None, gt=0)
    property_condition: PropertyCondition | None = None
    equipment_list: list[EquipmentItem] = Field(default_factory=list)
    staff_count: int | None = Field(default=None, ge=0)
    staff_details: list[StaffDetail] = Field(default_factory=list)
    working_hours: str | None = Field(default=None, max_length=100)
    business_age_months: int | None = Field(default=None, ge=0)
    has_licenses: bool | None = None
    has_contracts: bool | None = None
    sale_reason: str | None = Field(default=None, max_length=200)
    stay_as_consultant_months: int | None = Field(default=None, ge=0)
    video_url: str | None = Field(default=None, max_length=2048)
    tax_system: str | None = Field(default=None, max_length=100)
    monthly_financials: list[MonthlyFinancial] = Field(default_factory=list)
    average_check: Decimal | None = Field(default=None, ge=0)
    monthly_orders: int | None = Field(default=None, ge=0)
    monthly_clients_unique: int | None = Field(default=None, ge=0)
    cost_structure: list[str] = Field(default_factory=list)
    seasonality_months: list[int] = Field(default_factory=list, max_length=12)
    peak_hours: list[str] = Field(default_factory=list)
    supplier_contracts: bool | None = None
    supplier_details: str | None = None
    debts_receivable: Decimal | None = Field(default=None, ge=0)
    debts_payable: Decimal | None = Field(default=None, ge=0)
    legal_claims: bool | None = None
    legal_claims_details: str | None = None
    equipment_lease: bool | None = None
    monthly_loan_payments: Decimal | None = Field(default=None, ge=0)
    customer_base_size: int | None = Field(default=None, ge=0)
    repeat_customer_rate: float | None = Field(default=None, ge=0, le=1)
    seller_status: SellerStatus | None = None
    seller_name: str | None = Field(default=None, max_length=200)
    seller_phone: str | None = Field(default=None, max_length=32)
    seller_email: EmailStr | None = None
    seller_inn: str | None = Field(default=None, pattern=r"^(?:\d{10}|\d{12})$")
    seller_ogrnip: str | None = Field(default=None, pattern=r"^\d{15}$")


class BusinessListingResponse(BaseModel):
    id: UUID
    status: str
    verification_status: str | None
    created_at: datetime
    updated_at: datetime


class BusinessListingDetail(BusinessListingDraft):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    verification_status: str | None
    files: dict[str, object]
    document_fields: list[str]
    created_at: datetime
    updated_at: datetime


class ModeratorDecisionBody(BaseModel):
    """Короткий вердикт модератора; причина отказа показывается продавцу."""
    verdict: Literal["approve", "reject"]
    user_safe_reason: str | None = Field(default=None, min_length=3, max_length=500)


class CursorListingResponse(BaseModel):
    items: list[BusinessListingDetail]
    next_cursor: str | None
