from motor.motor_asyncio import AsyncIOMotorClient

# 1. Adres pod którym domyślnie uruchamia się lokalne MongoDB na Twoim komputerze
MONGO_DETAILS = "mongodb://localhost:27017"

# 2. Tworzymy asynchronicznego klienta bazy danych
client = AsyncIOMotorClient(MONGO_DETAILS)

# 3. Wskazujemy konkretną bazę danych (jeśli nie istnieje, Mongo samo ją stworzy przy pierwszym zapisie)
database = client.bike_shop_db

# 4. Definiujemy kolekcje – odpowiedniki tabel z baz relacyjnych
bikes_collection = database.get_collection("bikes")
orders_collection = database.get_collection("orders")