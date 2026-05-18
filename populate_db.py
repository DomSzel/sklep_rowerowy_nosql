import asyncio
from database import client, products_collection, orders_collection, users_collection, init_db
from bson import ObjectId

async def populate():
    await init_db()
    
    # 1. Czyszczenie starych danych
    await products_collection.delete_many({})
    await orders_collection.delete_many({})
    await users_collection.delete_many({})

    print("Baza wyczyszczona. Dodaję mockowe dane...")

    # 2. Produkty
    products = [
        {
            "type": "bike",
            "category": "mtb",
            "brand": "Specialized",
            "model": "Stumpjumper EVO",
            "price": 18000.0,
            "stock": 3,
            "tags": ["enduro", "full-suspension"],
            "compatibility_tags": ["Boost148", "BSA"],
            "specs": {"travel_front": "160mm", "travel_rear": "150mm", "wheel_size": "29"},
            "is_active": True,
            "discount_percentage": 0
        },
        {
            "type": "component",
            "category": "frame",
            "brand": "Santa Cruz",
            "model": "Nomad CC",
            "price": 15000.0,
            "stock": 2,
            "tags": ["frame", "carbon"],
            "compatibility_tags": ["Boost148", "BSA"],
            "specs": {"material": "Carbon CC", "wheel_size": "27.5"},
            "is_active": True,
            "discount_percentage": 10
        },
        {
            "type": "component",
            "category": "crankset",
            "brand": "Shimano",
            "model": "XTR M9100",
            "price": 2000.0,
            "stock": 10,
            "tags": ["drivetrain", "cranks"],
            "compatibility_tags": ["BB92"], # Gryzie się z BSA!
            "specs": {"speed": "12s", "q_factor": "162mm"},
            "is_active": True,
            "discount_percentage": 0
        },
        {
            "type": "component",
            "category": "bottom_bracket",
            "brand": "SRAM",
            "model": "DUB BSA",
            "price": 250.0,
            "stock": 15,
            "tags": ["drivetrain", "bb"],
            "compatibility_tags": ["BSA"],
            "specs": {"standard": "BSA threaded", "spindle": "28.99mm"},
            "is_active": True,
            "discount_percentage": 0
        },
        {
            "type": "component",
            "category": "fork",
            "brand": "Fox",
            "model": "38 Factory",
            "price": 5500.0,
            "stock": 5,
            "tags": ["suspension", "fork"],
            "compatibility_tags": ["Boost110"],
            "specs": {"travel": "170mm", "damper": "GRIP2", "offset": "44mm"},
            "is_active": True,
            "discount_percentage": 0
        }
    ]

    res = await products_collection.insert_many(products)
    p_ids = res.inserted_ids
    print(f"Dodano {len(p_ids)} produktów.")

    # 3. Użytkownik i zamówienie testowe
    admin = {"email": "admin@shop.com", "role": "admin", "purchase_history": []}
    cust = {"email": "jan@kowalski.pl", "role": "customer", "purchase_history": []}
    
    await users_collection.insert_many([admin, cust])

    # 4. Dodaj 1 zamówienie do statystyk (np. kupiono korbę Shimano i ramę Santa Cruz)
    order = {
        "customer_email": "jan@kowalski.pl",
        "items": [
            {
                "product_id": str(p_ids[1]),
                "brand": "Santa Cruz",
                "model": "Nomad CC",
                "price_at_purchase": 13500.0, # (15000 - 10%)
                "quantity": 1
            },
            {
                "product_id": str(p_ids[2]),
                "brand": "Shimano",
                "model": "XTR M9100",
                "price_at_purchase": 2000.0,
                "quantity": 2
            }
        ],
        "total_price": 17500.0
    }
    
    o_res = await orders_collection.insert_one(order)
    await users_collection.update_one({"email": "jan@kowalski.pl"}, {"$push": {"purchase_history": str(o_res.inserted_id)}})
    
    print("Baza zasiliona testowymi danymi!")

if __name__ == "__main__":
    asyncio.run(populate())
