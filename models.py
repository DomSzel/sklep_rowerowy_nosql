from pydantic import BaseModel, Field
from typing import Dict, Any, List
from datetime import datetime

# ==========================================
# 1. MODEL ROWERU (KATALOG PRODUKTÓW)
# ==========================================
class BikeModel(BaseModel):
    brand: str = Field(..., example="Kross")
    model: str = Field(..., example="Hexagon 5.0")
    price: float = Field(..., gt=0, example=2499.00)
    stock: int = Field(..., ge=0, example=10)
    tags: List[str] = Field(default=[], example=["górski", "MTB"])
    specs: Dict[str, Any] = Field(default={}, example={"rama": "Aluminium", "rozmiar_kol": 29})

def bike_helper(bike) -> dict:
    return {
        "id": str(bike["_id"]),
        "brand": bike["brand"],
        "model": bike["model"],
        "price": bike["price"],
        "stock": bike["stock"],
        "tags": bike["tags"],
        "specs": bike["specs"]
    }

# ==========================================
# 2. MODEL ZAMÓWIENIA (KOSZYK ZAKUPOWY)
# ==========================================
class OrderItemModel(BaseModel):
    bike_id: str = Field(..., example="tu_wkleisz_id_z_bazy")
    brand: str = Field(..., example="Kross")
    model: str = Field(..., example="Hexagon")
    price_at_purchase: float = Field(..., gt=0, example=2499.00)
    quantity: int = Field(..., gt=0, example=1)

class OrderModel(BaseModel):
    customer_email: str = Field(..., example="klient@rowery.pl")
    items: List[OrderItemModel]
    total_price: float = Field(..., gt=0, example=2499.00)
    created_at: datetime = Field(default_factory=datetime.utcnow)

def order_helper(order) -> dict:
    return {
        "id": str(order["_id"]),
        "customer_email": order["customer_email"],
        "items": order["items"],
        "total_price": order["total_price"],
        "created_at": order["created_at"].isoformat()
    }