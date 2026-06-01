from motor.motor_asyncio import AsyncIOMotorClient
import pymongo

import os

MONGO_DETAILS = os.getenv("MONGO_URI", "mongodb://localhost:27017/?replicaSet=rs0")
DB_NAME = os.getenv("MONGO_DB_NAME", "bike_shop_db")

client = AsyncIOMotorClient(MONGO_DETAILS)
database = client[DB_NAME]

categories_collection = database.get_collection("categories")
products_collection = database.get_collection("products")
carts_collection = database.get_collection("carts")
orders_collection = database.get_collection("orders")
users_collection = database.get_collection("users")

async def init_db():
    # ==========================================
    # WALIDACJA DLA KOLEKCJI CATEGORIES
    # ==========================================
    category_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name", "type", "slug"],
            "properties": {
                "name": {"bsonType": "string"},
                "type": {"bsonType": "string", "enum": ["bike", "component"]},
                "slug": {"bsonType": "string"}
            }
        }
    }
    try:
        await database.create_collection("categories", validator=category_validator)
    except Exception:
        await database.command("collMod", "categories", validator=category_validator)

    await categories_collection.create_index("slug", unique=True)

    # Zasiedlanie domyślnych kategorii
    default_categories = [
        # Bikes
        {"name": "MTB", "type": "bike", "slug": "mtb"},
        {"name": "Road", "type": "bike", "slug": "road"},
        {"name": "Gravel", "type": "bike", "slug": "gravel"},
        {"name": "E-Bike", "type": "bike", "slug": "ebike"},
        # Components
        {"name": "Frame", "type": "component", "slug": "frame"},
        {"name": "Fork", "type": "component", "slug": "fork"},
        {"name": "Drivetrain", "type": "component", "slug": "drivetrain"},
        {"name": "Bottom Bracket", "type": "component", "slug": "bottom_bracket"},
        {"name": "Wheelset", "type": "component", "slug": "wheelset"},
        {"name": "Handlebar", "type": "component", "slug": "handlebar"},
        {"name": "Saddle", "type": "component", "slug": "saddle"}
    ]
    for cat in default_categories:
        await categories_collection.update_one(
            {"slug": cat["slug"]},
            {"$setOnInsert": cat},
            upsert=True
        )

    # ==========================================
    # WALIDACJA DLA KOLEKCJI PRODUCTS
    # ==========================================
    product_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["type", "category_id", "brand", "model", "price", "cost_price", "stock"],
            "properties": {
                "type": {"bsonType": "string", "enum": ["bike", "component"]},
                "category_id": {"bsonType": "string"},
                "brand": {"bsonType": "string"},
                "model": {"bsonType": "string"},
                "price": {"bsonType": "double", "minimum": 0},
                "cost_price": {"bsonType": "double", "minimum": 0},
                "stock": {"bsonType": "int", "minimum": 0},
                "compatibility_tags": {"bsonType": "array", "items": {"bsonType": "string"}},
                "specs": {"bsonType": "object"},
                "components": {"bsonType": ["object", "null"]},
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
    try:
        await products_collection.create_index([("model", pymongo.TEXT), ("brand", pymongo.TEXT)])
    except Exception:
        # Jeśli istnieje stary tekstowy indeks (np. model_text_tags_text), usuwamy go i tworzymy nowy
        try:
            await products_collection.drop_index("model_text_tags_text")
        except Exception:
            try:
                await products_collection.drop_indexes()
            except Exception:
                pass
        await products_collection.create_index([("brand", pymongo.ASCENDING), ("price", pymongo.ASCENDING)])
        await products_collection.create_index([("model", pymongo.TEXT), ("brand", pymongo.TEXT)])
    
    await products_collection.create_index("category_id")
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
                        "required": ["product_id", "brand", "model", "price_at_purchase", "quantity"],
                        "properties": {
                            "product_id": {"bsonType": "string"},
                            "brand": {"bsonType": "string"},
                            "model": {"bsonType": "string"},
                            "price_at_purchase": {"bsonType": "double", "minimum": 0},
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
                "orders": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": ["id", "customer_email", "items", "total_price", "status"],
                        "properties": {
                            "id": {"bsonType": "string"},
                            "customer_email": {"bsonType": "string", "pattern": "^.+@.+$"},
                            "total_price": {"bsonType": "double", "minimum": 0},
                            "status": {"bsonType": "string", "enum": ["opłacone", "wysłane", "dostarczone"]},
                            "created_at": {"bsonType": "string"},
                            "items": {
                                "bsonType": "array",
                                "minItems": 1,
                                "items": {
                                    "bsonType": "object",
                                    "required": ["product_id", "brand", "model", "price_at_purchase", "cost_price_at_purchase", "quantity"],
                                    "properties": {
                                        "product_id": {"bsonType": "string"},
                                        "brand": {"bsonType": "string"},
                                        "model": {"bsonType": "string"},
                                        "price_at_purchase": {"bsonType": "double", "minimum": 0},
                                        "cost_price_at_purchase": {"bsonType": "double", "minimum": 0},
                                        "quantity": {"bsonType": "int", "minimum": 1}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    try:
        await database.create_collection("users", validator=user_validator)
    except Exception:
        await database.command("collMod", "users", validator=user_validator)

    await users_collection.create_index("email", unique=True)
    
    print("Inicjalizacja bazy MongoDB (Products, Carts, Orders, Users) zakończona.")