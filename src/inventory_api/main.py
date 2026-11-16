"""HTTP routes and transactional order workflow."""

from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Order, OrderItem, Product
from .schemas import (
    InventorySummary,
    OrderCreate,
    OrderOut,
    ProductCreate,
    ProductOut,
    StockChange,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Inventory & Order Management API",
    description=(
        "A practical portfolio API: SQL inventory, order transactions, "
        "and automated tests."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    product = Product(**payload.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="SKU already exists") from exc
    db.refresh(product)
    return product


@app.get("/products", response_model=list[ProductOut])
def list_products(
    low_stock: bool = False,
    search: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
) -> list[Product]:
    statement = select(Product).order_by(Product.id)
    if low_stock:
        statement = statement.where(Product.stock <= Product.reorder_level)
    if search:
        statement = statement.where(Product.name.ilike(f"%{search}%"))
    return list(db.scalars(statement).all())


@app.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.patch("/products/{product_id}/stock", response_model=ProductOut)
def change_stock(
    product_id: int, payload: StockChange, db: Session = Depends(get_db)
) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock + payload.change < 0:
        raise HTTPException(status_code=409, detail="Insufficient stock")
    product.stock += payload.change
    db.commit()
    db.refresh(product)
    return product


@app.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def place_order(payload: OrderCreate, db: Session = Depends(get_db)) -> Order:
    """Validate every line before making a single atomic database commit."""
    product_ids = [line.product_id for line in payload.items]
    products = {
        product.id: product
        for product in db.scalars(select(Product).where(Product.id.in_(product_ids))).all()
    }

    for line in payload.items:
        product = products.get(line.product_id)
        if product is None:
            raise HTTPException(status_code=404, detail=f"Product {line.product_id} not found")
        if product.stock < line.quantity:
            raise HTTPException(
                status_code=409, detail=f"Insufficient stock for SKU {product.sku}"
            )

    total = Decimal("0.00")
    order = Order(total=total)
    for line in payload.items:
        product = products[line.product_id]
        line_total = product.price * line.quantity
        total += line_total
        product.stock -= line.quantity
        order.items.append(
            OrderItem(
                product_id=product.id,
                quantity=line.quantity,
                unit_price=product.price,
                line_total=line_total,
            )
        )
    order.total = total
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/metrics/inventory", response_model=InventorySummary)
def inventory_summary(db: Session = Depends(get_db)) -> InventorySummary:
    return InventorySummary(
        products=db.scalar(select(func.count(Product.id))) or 0,
        low_stock_products=db.scalar(
            select(func.count(Product.id)).where(Product.stock <= Product.reorder_level)
        )
        or 0,
        units_in_stock=db.scalar(select(func.sum(Product.stock))) or 0,
        orders=db.scalar(select(func.count(Order.id))) or 0,
    )
