import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Body, HTTPException, Query
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from bson import ObjectId
from typing import List

from database import client, products_collection, carts_collection, orders_collection, users_collection, init_db
from models import ProductModel, product_helper, CartModel, cart_helper, OrderModel, order_helper, UserModel, user_helper


# =====================================================================
# CYKL ŻYCIA APLIKACJI
# =====================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Sklep Rowerowy KuDom - Wersja Pro", lifespan=lifespan)

# =====================================================================
# PRODUCTS ENDPOINTS
# =====================================================================
@app.post("/products/", response_description="Dodaj nowy produkt")
async def add_product(product: ProductModel = Body(...)):
    product_dict = product.model_dump()
    new_product = await products_collection.insert_one(product_dict)
    created_product = await products_collection.find_one({"_id": new_product.inserted_id})
    return product_helper(created_product)

@app.get("/products/", response_description="Wyszukaj produkty")
async def search_products(
    type: str = None, 
    category: str = None, 
    max_price: float = None,
    tag: str = None,
    include_inactive: bool = False
):
    query = {}
    if not include_inactive:
        query["is_active"] = True
        
    if type: query["type"] = type
    if category: query["category"] = category
    if max_price is not None: query["price"] = {"$lte": max_price}
    if tag: query["tags"] = tag

    products = []
    async for prod in products_collection.find(query):
        products.append(product_helper(prod))
    return products

@app.put("/products/{id}/status", response_description="Zmień status aktywności produktu (Soft delete)")
async def toggle_product_status(id: str, is_active: bool):
    await products_collection.update_one({"_id": ObjectId(id)}, {"$set": {"is_active": is_active}})
    return {"status": "success", "is_active": is_active}

@app.put("/products/{id}/promotion", response_description="Ustaw promocję (w %)")
async def set_promotion(id: str, discount_percentage: int):
    await products_collection.update_one({"_id": ObjectId(id)}, {"$set": {"discount_percentage": discount_percentage}})
    return {"status": "success", "discount_percentage": discount_percentage}

# =====================================================================
# CARTS & COMPATIBILITY ENDPOINTS
# =====================================================================
class CompatibilityCheckRequest(BaseModel):
    product_ids: List[str]

@app.post("/carts/check-compatibility")
async def check_compatibility(request: CompatibilityCheckRequest):
    # Prosty system ostrzeżeń: jeśli w koszyku są komponenty, zbieramy ich tagi kompatybilności.
    # W zaawansowanym systemie sprawdzalibyśmy kategorie względem siebie.
    # Tutaj szukamy potencjalnych zgrzytów (np. rama ma suport BB92, a korba BSA).
    products = []
    for pid in request.product_ids:
        p = await products_collection.find_one({"_id": ObjectId(pid)})
        if p: products.append(p)

    warnings = []
    all_compat_tags = []
    for p in products:
        tags = p.get("compatibility_tags", [])
        if tags:
            all_compat_tags.extend(tags)
    
    # Przykładowa banalna reguła: 
    # Jeśli występuje tag "BSA" (wkręcany suport) i "BB92" (wciskany) jednocześnie, to gryzą się:
    if "BSA" in all_compat_tags and "BB92" in all_compat_tags:
        warnings.append("Uwaga: Wybrano komponenty pod suport wkręcany (BSA) oraz wciskany (BB92).")
    
    if "Boost148" in all_compat_tags and "NonBoost142" in all_compat_tags:
        warnings.append("Uwaga: Wybrano standardy piast Boost i Non-Boost. Mogą nie pasować do ramy.")

    return {"warnings": warnings}

@app.post("/carts/save")
async def save_cart(cart: CartModel = Body(...)):
    cart_dict = cart.model_dump()
    new_cart = await carts_collection.insert_one(cart_dict)
    return {"cart_id": str(new_cart.inserted_id)}

@app.get("/carts/{id}")
async def get_cart(id: str):
    cart = await carts_collection.find_one({"_id": ObjectId(id)})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart_helper(cart)

# =====================================================================
# ORDERS & USERS
# =====================================================================
@app.post("/users/login")
async def mock_login(email: str = Body(embed=True), role: str = Body(default="customer", embed=True)):
    user = await users_collection.find_one({"email": email})
    if not user:
        new_user = {"email": email, "role": role, "purchase_history": []}
        inserted = await users_collection.insert_one(new_user)
        user = await users_collection.find_one({"_id": inserted.inserted_id})
    else:
        # Update role for simulation purposes if needed
        await users_collection.update_one({"email": email}, {"$set": {"role": role}})
        user["role"] = role
    return user_helper(user)

@app.post("/orders/", response_description="Złóż zamówienie (Transakcja)")
async def create_order(order: OrderModel = Body(...)):
    async with await client.start_session() as session:
        async with session.start_transaction():
            # 1. Sprawdź i zdejmij ze stanu
            for item in order.items:
                try:
                    p_obj_id = ObjectId(item.product_id)
                except Exception:
                    raise HTTPException(status_code=400, detail=f"Niepoprawny ID: {item.product_id}")

                result = await products_collection.update_one(
                    {"_id": p_obj_id, "stock": {"$gte": item.quantity}},
                    {"$inc": {"stock": -item.quantity}},
                    session=session
                )

                if result.modified_count == 0:
                    raise HTTPException(status_code=400, detail=f"Brak wystarczającej ilości dla {item.brand} {item.model}")

            # 2. Zapisz zamówienie
            order_dict = order.model_dump()
            new_order = await orders_collection.insert_one(order_dict, session=session)
            
            # 3. Zaktualizuj historię użytkownika
            await users_collection.update_one(
                {"email": order.customer_email},
                {"$push": {"purchase_history": str(new_order.inserted_id)}},
                upsert=True,
                session=session
            )

    created_order = await orders_collection.find_one({"_id": new_order.inserted_id})
    return order_helper(created_order)

@app.get("/users/{email}/history")
async def get_user_history(email: str):
    orders = []
    async for order in orders_collection.find({"customer_email": email}).sort("created_at", -1):
        orders.append(order_helper(order))
    return orders

# =====================================================================
# ADMIN REPORTS (Aggregation Framework)
# =====================================================================
@app.get("/admin/reports/sales")
async def get_sales_report():
    pipeline = [
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.brand",
                "total_sold_units": {"$sum": "$items.quantity"},
                "total_revenue": {"$sum": {"$multiply": ["$items.quantity", "$items.price_at_purchase"]}}
            }
        },
        {"$sort": {"total_revenue": -1}}
    ]
    
    report = []
    async for doc in orders_collection.aggregate(pipeline):
        report.append({
            "brand": doc["_id"],
            "total_sold_units": doc["total_sold_units"],
            "total_revenue": doc["total_revenue"]
        })
    return report

# =====================================================================
# STATIC FILES (FRONTEND)
# =====================================================================
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=FileResponse, include_in_schema=False)
async def serve_frontend():
    return "static/index.html"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)