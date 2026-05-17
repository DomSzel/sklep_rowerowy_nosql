from fastapi import FastAPI, Body, HTTPException
from bson import ObjectId
from database import bikes_collection, orders_collection
from models import BikeModel, bike_helper, OrderModel, order_helper

# Inicjalizujemy naszą aplikację FastAPI
app = FastAPI(title="Sklep Rowerowy KuDom")


# =====================================================================
# ENDPOINT 1: DODAWANIE NOWEGO ROWERU (Katalog produktów)
# =====================================================================
@app.post("/bikes/", response_description="Dodaj nowy rower do katalogu")
async def add_bike(bike: BikeModel = Body(...)):
    # Zamieniamy model Pydantic na zwykły słownik Pythona (JSON)
    bike_dict = bike.model_dump()

    # Wstawiamy dokument do MongoDB
    new_bike = await bikes_collection.insert_one(bike_dict)

    # Pobieramy stworzony rower z bazy, żeby potwierdzić zapis
    created_bike = await bikes_collection.find_one({"_id": new_bike.inserted_id})
    return bike_helper(created_bike)


# =====================================================================
# ENDPOINT 2: ZAAWANSOWANE WYSZUKIWANIE (Moc elastycznego NoSQL)
# =====================================================================
@app.get("/bikes/search/", response_description="Wyszukaj rowery po filtrach")
async def search_bikes(max_price: float = None, tag: str = None):
    query = {}

    # Budujemy zapytanie do bazy w zależności od tego, co wpisze użytkownik
    if max_price is not None:
        query["price"] = {"$lte": max_price}  # $lte = mniejsze lub równe (Less Than or Equal)
    if tag:
        query["tags"] = tag  # MongoDB samo wie, jak przeszukać listę wewnątrz dokumentu!

    bikes = []
    # Przeszukujemy bazę asynchronicznie
    async for bike in bikes_collection.find(query):
        bikes.append(bike_helper(bike))

    return bikes


# =====================================================================
# ENDPOINT 3: BEZPIECZNE SKŁADANIE ZAMÓWIEŃ (Kontrola magazynu)
# =====================================================================
@app.post("/orders/", response_description="Złóż nowe zamówienie")
async def create_order(order: OrderModel = Body(...)):
    # Sprawdzamy i rezerwujemy każdy rower z koszyka
    for item in order.items:
        try:
            bike_obj_id = ObjectId(item.bike_id)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Niepoprawny format ID: {item.bike_id}")

        # Zmniejszamy stan magazynowy (stock) o wybraną ilość, 
        # ale tylko jeśli obecny stan jest większy bądź równy zamówieniu ($gte)
        result = await bikes_collection.update_one(
            {"_id": bike_obj_id, "stock": {"$gte": item.quantity}},
            {"$inc": {"stock": -item.quantity}}
        )

        # Jeśli nic się nie zmieniło, to znaczy, że roweru nie ma na magazynie
        if result.modified_count == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Brak wystarczającej ilości roweru o ID {item.bike_id} w magazynie!"
            )

    # Gdy stany magazynowe zostały pomyślnie zaktualizowane, zapisujemy zamówienie
    order_dict = order.model_dump()
    new_order = await orders_collection.insert_one(order_dict)

    created_order = await orders_collection.find_one({"_id": new_order.inserted_id})
    return order_helper(created_order)