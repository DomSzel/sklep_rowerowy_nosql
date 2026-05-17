from motor.motor_asyncio import AsyncIOMotorClient
import pymongo

# 1. Adres pod którym domyślnie uruchamia się lokalne MongoDB
# Dodajemy ?replicaSet=rs0 aby klient wiedział, że łączy się z klastrem (wymagane do transakcji)
MONGO_DETAILS = "mongodb://localhost:27017/?replicaSet=rs0"

# 2. Tworzymy asynchronicznego klienta bazy danych
client = AsyncIOMotorClient(MONGO_DETAILS)

# 3. Wskazujemy konkretną bazę danych
database = client.bike_shop_db

# 4. Definiujemy kolekcje
bikes_collection = database.get_collection("bikes")
orders_collection = database.get_collection("orders")
vip_customers_collection = database.get_collection("vip_customers")

async def init_db():
    """
    Funkcja inicjalizująca bazę danych: 
    - dodaje walidację JSON Schema,
    - tworzy indeksy optymalizujące wyszukiwanie.
    """
    # ==========================================
    # WALIDACJA JSON SCHEMA DLA KOLEKCJI BIKES
    # ==========================================
    bike_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["brand", "model", "price", "stock"],
            "properties": {
                "brand": {"bsonType": "string", "description": "must be a string and is required"},
                "model": {"bsonType": "string", "description": "must be a string and is required"},
                "price": {"bsonType": "double", "minimum": 0, "description": "must be a positive double and is required"},
                "stock": {"bsonType": "int", "minimum": 0, "description": "must be a non-negative integer and is required"},
                "tags": {"bsonType": "array", "items": {"bsonType": "string"}},
                "specs": {"bsonType": "object"}
            }
        }
    }
    
    try:
        await database.create_collection("bikes", validator=bike_validator)
    except Exception:
        # Jeśli kolekcja już istnieje, modyfikujemy jej zasady
        await database.command("collMod", "bikes", validator=bike_validator)

    # ==========================================
    # INDEKSY DLA KOLEKCJI BIKES
    # ==========================================
    # 1. Compound Index (Indeks złożony) do szybkiego wyszukiwania po marce i cenie
    await bikes_collection.create_index([("brand", pymongo.ASCENDING), ("price", pymongo.ASCENDING)])
    
    # 2. Text Index (Indeks tekstowy) do inteligentnego wyszukiwania słów kluczowych
    await bikes_collection.create_index([("model", pymongo.TEXT), ("tags", pymongo.TEXT)])

    # ==========================================
    # WALIDACJA JSON SCHEMA DLA KOLEKCJI ORDERS
    # ==========================================
    order_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["customer_email", "items", "total_price"],
            "properties": {
                "customer_email": {"bsonType": "string", "pattern": "^.+@.+$"}, # Prosty regex na email
                "items": {"bsonType": "array", "minItems": 1},
                "total_price": {"bsonType": "double", "minimum": 0}
            }
        }
    }

    try:
        await database.create_collection("orders", validator=order_validator)
    except Exception:
        await database.command("collMod", "orders", validator=order_validator)
    
    print("Inicjalizacja bazy MongoDB zakończona (Indeksy i Schema Validation założone).")