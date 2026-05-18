from motor.motor_asyncio import AsyncIOMotorClient
import pymongo

MONGO_DETAILS = "mongodb://localhost:27017/?replicaSet=rs0"
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.bike_shop_db

products_collection = database.get_collection("products")
carts_collection = database.get_collection("carts")
orders_collection = database.get_collection("orders")
users_collection = database.get_collection("users")

async def init_db():
    # ==========================================
    # WALIDACJA DLA KOLEKCJI PRODUCTS
    # ==========================================
    product_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["type", "category", "brand", "model", "price", "stock"],
            "properties": {
                "type": {"bsonType": "string", "enum": ["bike", "component"]},
                "category": {"bsonType": "string"},
                "brand": {"bsonType": "string"},
                "model": {"bsonType": "string"},
                "price": {"bsonType": "double", "minimum": 0},
                "stock": {"bsonType": "int", "minimum": 0},
                "tags": {"bsonType": "array", "items": {"bsonType": "string"}},
                "compatibility_tags": {"bsonType": "array", "items": {"bsonType": "string"}},
                "specs": {"bsonType": "object"},
                "is_active": {"bsonType": "bool"},
                "discount_percentage": {"bsonType": "int", "minimum": 0, "maximum": 100}
            }
        }
    }
    
    try:
        await database.create_collection("products", validator=product_validator)
    except Exception:
        await database.command("collMod", "products", validator=product_validator)

    await products_collection.create_index([("brand", pymongo.ASCENDING), ("price", pymongo.ASCENDING)])
    await products_collection.create_index([("model", pymongo.TEXT), ("tags", pymongo.TEXT)])
    await products_collection.create_index("category")
    await products_collection.create_index("type")

    # ==========================================
    # WALIDACJA DLA KOLEKCJI CARTS
    # ==========================================
    cart_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_email", "name", "items"],
            "properties": {
                "user_email": {"bsonType": "string"},
                "name": {"bsonType": "string"},
                "items": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": ["product_id", "quantity"],
                        "properties": {
                            "product_id": {"bsonType": "string"},
                            "quantity": {"bsonType": "int", "minimum": 1}
                        }
                    }
                }
            }
        }
    }
    try:
        await database.create_collection("carts", validator=cart_validator)
    except Exception:
        await database.command("collMod", "carts", validator=cart_validator)

    # ==========================================
    # WALIDACJA DLA KOLEKCJI ORDERS
    # ==========================================
    order_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["customer_email", "items", "total_price"],
            "properties": {
                "customer_email": {"bsonType": "string", "pattern": "^.+@.+$"},
                "items": {"bsonType": "array", "minItems": 1},
                "total_price": {"bsonType": "double", "minimum": 0}
            }
        }
    }
    try:
        await database.create_collection("orders", validator=order_validator)
    except Exception:
        await database.command("collMod", "orders", validator=order_validator)

    # ==========================================
    # WALIDACJA DLA KOLEKCJI USERS
    # ==========================================
    user_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["email", "role"],
            "properties": {
                "email": {"bsonType": "string", "pattern": "^.+@.+$"},
                "role": {"bsonType": "string", "enum": ["customer", "admin"]},
                "purchase_history": {"bsonType": "array", "items": {"bsonType": "string"}}
            }
        }
    }
    try:
        await database.create_collection("users", validator=user_validator)
    except Exception:
        await database.command("collMod", "users", validator=user_validator)

    await users_collection.create_index("email", unique=True)
    
    print("Inicjalizacja bazy MongoDB (Products, Carts, Orders, Users) zakończona.")