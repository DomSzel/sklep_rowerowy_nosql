from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

# ==========================================
# 1. MODEL PRODUKTU (Rowery i Części)
# ==========================================
class ProductModel(BaseModel):
    type: str = Field(..., description="bike or component")
    category: str = Field(..., description="np. drivetrain, frame, mtb")
    brand: str = Field(...)
    model: str = Field(...)
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    tags: List[str] = Field(default=[], description="Normal tags for searching")
    compatibility_tags: List[str] = Field(default=[], description="Hidden tags for compatibility checking")
    specs: Dict[str, Any] = Field(default={})
    is_active: bool = Field(default=True)
    discount_percentage: Optional[int] = Field(default=0, ge=0, le=100)

def product_helper(product) -> dict:
    return {
        "id": str(product["_id"]),
        "type": product.get("type", "component"),
        "category": product.get("category", ""),
        "brand": product["brand"],
        "model": product["model"],
        "price": product["price"],
        "stock": product["stock"],
        "tags": product.get("tags", []),
        "compatibility_tags": product.get("compatibility_tags", []),
        "specs": product.get("specs", {}),
        "is_active": product.get("is_active", True),
        "discount_percentage": product.get("discount_percentage", 0)
    }

# ==========================================
# 2. MODEL KOSZYKA (Do zapisywania)
# ==========================================
class CartItemModel(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)

class CartModel(BaseModel):
    user_email: str
    name: str = Field(default="Mój Koszyk")
    items: List[CartItemModel]
    created_at: datetime = Field(default_factory=datetime.utcnow)

def cart_helper(cart) -> dict:
    return {
        "id": str(cart["_id"]),
        "user_email": cart["user_email"],
        "name": cart["name"],
        "items": [dict(i) for i in cart.get("items", [])],
        "created_at": cart.get("created_at", datetime.utcnow()).isoformat() if isinstance(cart.get("created_at"), datetime) else cart.get("created_at")
    }

# ==========================================
# 3. MODEL ZAMÓWIENIA
# ==========================================
class OrderItemModel(BaseModel):
    product_id: str
    brand: str
    model: str
    price_at_purchase: float
    quantity: int

class OrderModel(BaseModel):
    customer_email: str
    items: List[OrderItemModel]
    total_price: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

def order_helper(order) -> dict:
    return {
        "id": str(order["_id"]),
        "customer_email": order["customer_email"],
        "items": [dict(i) for i in order.get("items", [])],
        "total_price": order["total_price"],
        "created_at": order.get("created_at", datetime.utcnow()).isoformat() if isinstance(order.get("created_at"), datetime) else order.get("created_at")
    }

# ==========================================
# 4. MODEL UŻYTKOWNIKA (Do uwierzytelniania / historii)
# ==========================================
class UserModel(BaseModel):
    email: str
    role: str = Field(default="customer") # 'admin' or 'customer'
    purchase_history: List[str] = Field(default=[])

def user_helper(user) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "role": user["role"],
        "purchase_history": user.get("purchase_history", [])
    }