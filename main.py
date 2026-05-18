import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Body, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from bson import ObjectId
from database import client, bikes_collection, orders_collection, vip_customers_collection, init_db
from models import BikeModel, bike_helper, OrderModel, order_helper


# =====================================================================
# CHANGE STREAMS
# =====================================================================
async def watch_orders():
    pipeline = [{"$match": {"operationType": "insert"}}]
    print("Nasłuchiwanie na nowe zamówienia (Change Stream) uruchomione...")
    try:
        async with orders_collection.watch(pipeline) as stream:
            async for change in stream:
                order = change["fullDocument"]
                if order.get("total_price", 0) > 10000:
                    email = order.get("customer_email")
                    print(f"TRIGGER: Wykryto duże zamówienie! Dodaję do VIP: {email}")
                    await vip_customers_collection.update_one(
                        {"email": email},
                        {
                            "$inc": {"total_spent": order["total_price"]},
                            "$set": {"last_order": order["created_at"]}
                        },
                        upsert=True
                    )
    except Exception as e:
        print(f"Change stream został zamknięty lub wystąpił błąd: {e}")


# =====================================================================
# CYKL ŻYCIA APLIKACJI
# =====================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(watch_orders())
    yield
    task.cancel()

app = FastAPI(title="Sklep Rowerowy KuDom - NoSQL Advanced", lifespan=lifespan)


# =====================================================================
# ENDPOINT 1: DODAWANIE NOWEGO ROWERU
# =====================================================================
@app.post("/bikes/", response_description="Dodaj nowy rower do katalogu")
async def add_bike(bike: BikeModel = Body(...)):
    bike_dict = bike.model_dump()
    new_bike = await bikes_collection.insert_one(bike_dict)
    created_bike = await bikes_collection.find_one({"_id": new_bike.inserted_id})
    return bike_helper(created_bike)


# =====================================================================
# ENDPOINT 2: WYSZUKIWANIE
# =====================================================================
@app.get("/bikes/search/", response_description="Wyszukaj rowery po filtrach")
async def search_bikes(max_price: float = None, tag: str = None):
    query = {}
    if max_price is not None:
        query["price"] = {"$lte": max_price}
    if tag:
        query["tags"] = tag

    bikes = []
    async for bike in bikes_collection.find(query):
        bikes.append(bike_helper(bike))
    return bikes


# =====================================================================
# ENDPOINT 3: SKŁADANIE ZAMÓWIEŃ
# =====================================================================
@app.post("/orders/", response_description="Złóż nowe zamówienie (Transakcyjnie)")
async def create_order(order: OrderModel = Body(...)):
    async with await client.start_session() as session:
        async with session.start_transaction():
            
            for item in order.items:
                try:
                    bike_obj_id = ObjectId(item.bike_id)
                except Exception:
                    raise HTTPException(status_code=400, detail=f"Niepoprawny format ID: {item.bike_id}")

                result = await bikes_collection.update_one(
                    {"_id": bike_obj_id, "stock": {"$gte": item.quantity}},
                    {"$inc": {"stock": -item.quantity}},
                    session=session
                )

                if result.modified_count == 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Brak wystarczającej ilości roweru o ID {item.bike_id} w magazynie!"
                    )

            order_dict = order.model_dump()
            new_order = await orders_collection.insert_one(order_dict, session=session)

    created_order = await orders_collection.find_one({"_id": new_order.inserted_id})
    return order_helper(created_order)


# =====================================================================
# ENDPOINT 4: RAPORT SPRZEDAŻY (Aggregation Framework)
# =====================================================================
@app.get("/reports/sales", response_description="Raport sprzedaży z użyciem Agregacji")
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

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=FileResponse, include_in_schema=False)
async def serve_frontend():
    return "static/index.html"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)