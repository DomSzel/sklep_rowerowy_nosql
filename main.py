import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Body, HTTPException, Query
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from bson import ObjectId
from typing import List
from datetime import datetime

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
    if tag: query["compatibility_tags"] = tag

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

@app.put("/products/{id}", response_description="Aktualizuj cały produkt")
async def update_product(id: str, product: ProductModel = Body(...)):
    try:
        p_obj_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Niepoprawny ID produktu")
    
    product_dict = product.model_dump()
    result = await products_collection.replace_one({"_id": p_obj_id}, product_dict)
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produkt nie znaleziony")
    
    updated_prod = await products_collection.find_one({"_id": p_obj_id})
    return product_helper(updated_prod)

# =====================================================================
# CARTS & COMPATIBILITY ENDPOINTS
# =====================================================================
class CompatibilityCheckRequest(BaseModel):
    product_ids: List[str]

@app.post("/carts/check-compatibility")
async def check_compatibility(request: CompatibilityCheckRequest):
    products = []
    for pid in request.product_ids:
        try:
            p = await products_collection.find_one({"_id": ObjectId(pid)})
            if p: products.append(p)
        except Exception:
            pass

    warnings = []
    all_compat_tags = []
    for p in products:
        # Dodaj tagi głównego produktu
        tags = p.get("compatibility_tags", [])
        if tags:
            all_compat_tags.extend(tags)
            
        # Jeśli to rower, dołącz tagi jego komponentów składowych
        if p.get("type") == "bike" and p.get("components"):
            for comp_id in p.get("components", {}).values():
                try:
                    comp = await products_collection.find_one({"_id": ObjectId(comp_id)})
                    if comp:
                        comp_tags = comp.get("compatibility_tags", [])
                        if comp_tags:
                            all_compat_tags.extend(comp_tags)
                except Exception:
                    pass

    # Usunięcie duplikatów
    all_compat_tags = list(set(all_compat_tags))
    
    # Przykładowe reguły weryfikacji kompatybilności:
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
        new_user = {"email": email, "role": role, "orders": []}
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
            # 1. Sprawdź, zdejmij ze stanu i pobierz cost_price
            items_with_cost = []
            for item in order.items:
                try:
                    p_obj_id = ObjectId(item.product_id)
                except Exception:
                    raise HTTPException(status_code=400, detail=f"Niepoprawny ID: {item.product_id}")

                # Pobierz aktualny produkt, aby poznać jego hurtową cenę cost_price
                prod = await products_collection.find_one({"_id": p_obj_id}, session=session)
                if not prod:
                    raise HTTPException(status_code=404, detail=f"Nie znaleziono produktu o ID {item.product_id}")

                result = await products_collection.update_one(
                    {"_id": p_obj_id, "stock": {"$gte": item.quantity}},
                    {"$inc": {"stock": -item.quantity}},
                    session=session
                )

                if result.modified_count == 0:
                    raise HTTPException(status_code=400, detail=f"Brak wystarczającej ilości dla {item.brand} {item.model}")

                # Zapisujemy pozycję z utrwalonym cost_price w chwili zakupu
                item_dict = item.model_dump()
                item_dict["cost_price_at_purchase"] = prod.get("cost_price", item.price_at_purchase * 0.6)
                items_with_cost.append(item_dict)

            # 2. Przygotuj zamówienie z unikalnym ID i statusami
            order_id = str(ObjectId())
            order_dict = order.model_dump()
            order_dict["id"] = order_id
            order_dict["items"] = items_with_cost
            order_dict["status"] = "opłacone"
            
            if isinstance(order_dict.get("created_at"), datetime):
                order_dict["created_at"] = order_dict["created_at"].isoformat()
            elif "created_at" not in order_dict:
                order_dict["created_at"] = datetime.utcnow().isoformat()

            # 3. Zapisz zamówienie bezpośrednio w dokumencie użytkownika
            await users_collection.update_one(
                {"email": order.customer_email},
                {
                    "$push": {"orders": order_dict},
                    "$setOnInsert": {"role": "customer"}
                },
                upsert=True,
                session=session
            )

    return order_helper(order_dict)

@app.get("/users/{email}/history")
async def get_user_history(email: str):
    user = await users_collection.find_one({"email": email})
    if not user:
        return []
    orders = user.get("orders", [])
    # Sortuj po dacie malejąco
    orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return [order_helper(o) for o in orders]

# =====================================================================
# ADMIN REPORTS & MANAGEMENT
# =====================================================================
@app.get("/admin/reports/sales")
async def get_sales_report(start_date: str = None, end_date: str = None):
    match_stage = {}
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = start_date + "T00:00:00" if "T" not in start_date else start_date
        if end_date:
            date_filter["$lte"] = end_date + "T23:59:59" if "T" not in end_date else end_date
        match_stage["orders.created_at"] = date_filter

    pipeline = [
        {"$unwind": "$orders"},
    ]
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline.extend([
        {"$unwind": "$orders.items"},
        {
            "$group": {
                "_id": "$orders.items.brand",
                "total_sold_units": {"$sum": "$orders.items.quantity"},
                "total_revenue": {"$sum": {"$multiply": ["$orders.items.quantity", "$orders.items.price_at_purchase"]}},
                "total_cost": {"$sum": {"$multiply": ["$orders.items.quantity", "$orders.items.cost_price_at_purchase"]}}
            }
        },
        {"$sort": {"total_revenue": -1}}
    ])
    
    report = []
    async for doc in users_collection.aggregate(pipeline):
        report.append({
            "brand": doc["_id"],
            "total_sold_units": doc["total_sold_units"],
            "total_revenue": doc["total_revenue"],
            "total_cost": doc.get("total_cost", doc["total_revenue"] * 0.6)
        })
    return report

@app.get("/admin/orders", response_description="Pobierz wszystkie zamówienia wszystkich użytkowników")
async def get_all_orders():
    pipeline = [
        {"$unwind": "$orders"},
        {"$project": {
            "_id": 0,
            "id": "$orders.id",
            "customer_email": "$orders.customer_email",
            "items": "$orders.items",
            "total_price": "$orders.total_price",
            "status": "$orders.status",
            "created_at": "$orders.created_at"
        }},
        {"$sort": {"created_at": -1}}
    ]
    orders = []
    async for doc in users_collection.aggregate(pipeline):
        orders.append(doc)
    return orders

@app.put("/admin/orders/{order_id}/status", response_description="Zmień status zamówienia")
async def update_order_status(order_id: str, status: str = Query(..., enum=["opłacone", "wysłane", "dostarczone"])):
    result = await users_collection.update_one(
        {"orders.id": order_id},
        {"$set": {"orders.$.status": status}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Nie znaleziono zamówienia o podanym ID")
    return {"status": "success", "order_id": order_id, "new_status": status}

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