import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Body, HTTPException
from bson import ObjectId

from database import client, bikes_collection, orders_collection, vip_customers_collection, init_db
from models import BikeModel, bike_helper, OrderModel, order_helper


# =====================================================================
# CHANGE STREAMS (NoSQL Triggers)
# =====================================================================
async def watch_orders():
    """
    Funkcja działająca w tle (Change Stream).
    Zastępuje klasyczne wyzwalacze (Triggery) z baz relacyjnych.
    Gdy ktoś złoży zamówienie powyżej 10000 zł, klient dodawany jest do VIP.
    """
    pipeline = [{"$match": {"operationType": "insert"}}]
    print("Nasłuchiwanie na nowe zamówienia (Change Stream) uruchomione...")
    try:
        async with orders_collection.watch(pipeline) as stream:
            async for change in stream:
                order = change["fullDocument"]
                if order.get("total_price", 0) > 10000:
                    email = order.get("customer_email")
                    print(f"🏆 TRIGGER: Wykryto duże zamówienie! Dodaję do VIP: {email}")
                    # Aktualizacja (lub wstawienie) klienta VIP
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
# CYKL ŻYCIA APLIKACJI (Lifespan)
# =====================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Inicjalizacja schematów i indeksów w bazie
    await init_db()
    # 2. Uruchomienie triggera w tle
    task = asyncio.create_task(watch_orders())
    
    yield  # Aplikacja działa
    
    # 3. Zakończenie pracy
    task.cancel()


# Inicjalizujemy naszą aplikację FastAPI z menedżerem cyklu życia
app = FastAPI(title="Sklep Rowerowy KuDom - NoSQL Advanced", lifespan=lifespan)


# =====================================================================
# ENDPOINT 1: DODAWANIE NOWEGO ROWERU (Katalog produktów)
# =====================================================================
@app.post("/bikes/", response_description="Dodaj nowy rower do katalogu")
async def add_bike(bike: BikeModel = Body(...)):
    bike_dict = bike.model_dump()
    new_bike = await bikes_collection.insert_one(bike_dict)
    created_bike = await bikes_collection.find_one({"_id": new_bike.inserted_id})
    return bike_helper(created_bike)


# =====================================================================
# ENDPOINT 2: ZAAWANSOWANE WYSZUKIWANIE (Moc elastycznego NoSQL)
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
# ENDPOINT 3: BEZPIECZNE SKŁADANIE ZAMÓWIEŃ (Transakcje ACID)
# =====================================================================
@app.post("/orders/", response_description="Złóż nowe zamówienie (Transakcyjnie)")
async def create_order(order: OrderModel = Body(...)):
    """
    Używamy transakcji wielodokumentowej. Jeśli podczas pomniejszania magazynu
    okaże się, że dla jednego z rowerów zabrakło sztuk - cała transakcja zostanie
    anulowana (rollback) i żaden rower nie zostanie zdjęty ze stanu!
    """
    # Rozpoczynamy sesję MongoDB
    async with await client.start_session() as session:
        # Uruchamiamy transakcję
        async with session.start_transaction():
            
            for item in order.items:
                try:
                    bike_obj_id = ObjectId(item.bike_id)
                except Exception:
                    raise HTTPException(status_code=400, detail=f"Niepoprawny format ID: {item.bike_id}")

                # Pomniejszamy stan z przekazaniem parametru session
                result = await bikes_collection.update_one(
                    {"_id": bike_obj_id, "stock": {"$gte": item.quantity}},
                    {"$inc": {"stock": -item.quantity}},
                    session=session
                )

                if result.modified_count == 0:
                    # Rzucenie wyjątku automatycznie przerywa (rollback) transakcję!
                    raise HTTPException(
                        status_code=400,
                        detail=f"Brak wystarczającej ilości roweru o ID {item.bike_id} w magazynie!"
                    )

            # Jeśli stany magazynowe zostały poprawnie zaktualizowane, zapisujemy zamówienie
            order_dict = order.model_dump()
            new_order = await orders_collection.insert_one(order_dict, session=session)

    created_order = await orders_collection.find_one({"_id": new_order.inserted_id})
    return order_helper(created_order)


# =====================================================================
# ENDPOINT 4: RAPORT SPRZEDAŻY (Aggregation Framework)
# =====================================================================
@app.get("/reports/sales", response_description="Raport sprzedaży z użyciem Agregacji")
async def get_sales_report():
    """
    To NoSQL-owy odpowiednik potężnych zapytań JOIN i GROUP BY.
    Rozbija zamówienia na poszczególne rowery i grupuje przychody według marki.
    """
    pipeline = [
        {"$unwind": "$items"}, # Rozpakuj tablicę 'items' z zamówień do pojedynczych dokumentów
        {
            "$group": {
                "_id": "$items.brand", # Pogrupuj po marce roweru
                "total_sold_units": {"$sum": "$items.quantity"}, # Zlicz sprzedane sztuki
                "total_revenue": {"$sum": {"$multiply": ["$items.quantity", "$items.price_at_purchase"]}} # Sumuj wartość
            }
        },
        {"$sort": {"total_revenue": -1}} # Posortuj malejąco od najbardziej dochodowej marki
    ]
    
    report = []
    async for doc in orders_collection.aggregate(pipeline):
        report.append({
            "brand": doc["_id"],
            "total_sold_units": doc["total_sold_units"],
            "total_revenue": doc["total_revenue"]
        })
        
    return report

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)