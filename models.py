from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

# ==========================================
# 0. MODEL KATEGORII
# ==========================================
class CategoryModel(BaseModel):
    name: str
    type: str = Field(..., description="bike or component")
    slug: str

def category_helper(category) -> dict:
    return {
        "id": str(category["_id"]),
        "name": category["name"],
        "type": category["type"],
        "slug": category["slug"]
    }

# ==========================================
# 1. MODEL PRODUKTU (Rowery i Części)
# ==========================================
class ProductModel(BaseModel):
    type: str = Field(..., description="bike or component")
    category_id: str = Field(..., description="ObjectId referencyjnej kategorii z kolekcji categories")
    brand: str = Field(...)
    model: str = Field(...)
    price: float = Field(..., gt=0)
    cost_price: float = Field(..., gt=0, description="Hurtowa cena zakupu produktu (do kalkulacji zysków/wydatków)")
    stock: int = Field(..., ge=0)
    compatibility_tags: List[str] = Field(default=[], description="Tags for compatibility checking (e.g. BSA, BB92)")
    specs: Dict[str, Any] = Field(default={}, description="Structured attributes (e.g. material, weight_kg, travel_mm)")
    components: Optional[Dict[str, str]] = Field(default=None, description="Flat map of component category to product ID (only for bikes)")
    is_active: bool = Field(default=True)
    discount_percentage: Optional[int] = Field(default=0, ge=0, le=100)

def product_helper(product) -> dict:
    return {
        "id": str(product["_id"]),
        "type": product.get("type", "component"),
        "category_id": str(product.get("category_id", "")),
        "brand": product["brand"],
        "model": product["model"],
        "price": product["price"],
        "cost_price": product.get("cost_price", product["price"] * 0.6), # domyślny fallback na 60% ceny detalicznej
        "stock": product["stock"],
        "compatibility_tags": product.get("compatibility_tags", []),
        "specs": product.get("specs", {}),
        "components": product.get("components", None),
        "is_active": product.get("is_active", True),
        "discount_percentage": product.get("discount_percentage", 0)
    }

# ==========================================
# 2. MODEL KOSZYKA (Do zapisywania)
# ==========================================
class CartItemModel(BaseModel):
    product_id: str
    brand: str
    model: str
    price_at_purchase: float
    quantity: int = Field(..., gt=0)

class CartModel(BaseModel):
    user_email: str
    name: str = Field(default="Mój Koszyk")
    items: List[CartItemModel]
    created_at: datetime = Field(default_factory=datetime.now)

def cart_helper(cart) -> dict:
    return {
        "id": str(cart["_id"]),
        "user_email": cart["user_email"],
        "name": cart["name"],
        "items": [dict(i) for i in cart.get("items", [])],
        "created_at": cart.get("created_at", datetime.now()).isoformat() if isinstance(cart.get("created_at"), datetime) else cart.get("created_at")
    }

# ==========================================
# 3. MODEL ZAMÓWIENIA
# ==========================================
class OrderItemModel(BaseModel):
    product_id: str
    brand: str
    model: str
    price_at_purchase: float
    cost_price_at_purchase: float = Field(default=0.0, description="Hurtowa cena zakupu w chwili sprzedaży")
    quantity: int

class OrderModel(BaseModel):
    customer_email: str
    items: List[OrderItemModel]
    total_price: float
    status: str = Field(default="opłacone") # opłacone, wysłane, dostarczone
    created_at: datetime = Field(default_factory=datetime.now)

def order_helper(order) -> dict:
    order_id = ""
    if "_id" in order:
        order_id = str(order["_id"])
    elif "id" in order:
        order_id = str(order["id"])
        
    return {
        "id": order_id,
        "customer_email": order["customer_email"],
        "items": [dict(i) if not isinstance(i, dict) else i for i in order.get("items", [])],
        "total_price": order["total_price"],
        "status": order.get("status", "opłacone"),
        "created_at": order.get("created_at", datetime.now()).isoformat() if isinstance(order.get("created_at"), datetime) else order.get("created_at")
    }

# ==========================================
# 4. MODEL UŻYTKOWNIKA (Do uwierzytelniania / historii)
# ==========================================
class UserModel(BaseModel):
    email: str
    role: str = Field(default="customer") # 'admin' or 'customer'
    orders: List[OrderModel] = Field(default=[])

def user_helper(user) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "role": user["role"],
        "orders": [dict(o) if not isinstance(o, dict) else o for o in user.get("orders", [])]
    }