"""Validated request and response schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductCreate(BaseModel):
    sku: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=120)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=5, ge=0)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be blank")
        return value.strip()


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    price: Decimal
    stock: int
    reorder_level: int


class StockChange(BaseModel):
    change: int = Field(description="Positive to restock, negative to reduce stock")

    @field_validator("change")
    @classmethod
    def nonzero_change(cls, value: int) -> int:
        if value == 0:
            raise ValueError("stock change cannot be zero")
        return value


class OrderLineCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    items: list[OrderLineCreate] = Field(min_length=1)

    @field_validator("items")
    @classmethod
    def distinct_products(cls, items: list[OrderLineCreate]) -> list[OrderLineCreate]:
        ids = [item.product_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("product_id may only appear once per order")
        return items


class OrderLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    total: Decimal
    items: list[OrderLineOut]


class InventorySummary(BaseModel):
    products: int
    low_stock_products: int
    units_in_stock: int
    orders: int
