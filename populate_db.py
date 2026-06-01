import asyncio
from database import client, products_collection, users_collection, categories_collection, carts_collection, init_db
from bson import ObjectId

async def populate():
    await init_db()
    
    # 1. Czyszczenie starych danych
    await products_collection.delete_many({})
    await users_collection.delete_many({})
    await carts_collection.delete_many({})

    print("Baza wyczyszczona (Products, Users, Carts). Dodaję mockowe dane...")

    # Pobieramy ID kategorii z bazy
    categories_cursor = categories_collection.find({})
    cats = {}
    async for cat in categories_cursor:
        cats[cat["slug"]] = str(cat["_id"])

    print("Wczytane kategorie z bazy:", list(cats.keys()))

    # 2. Tworzenie Komponentów
    frame = {
        "type": "component",
        "category_id": cats["frame"],
        "brand": "Santa Cruz",
        "model": "Nomad CC",
        "price": 15000.0,
        "cost_price": 9000.0,
        "stock": 2,
        "compatibility_tags": ["Boost148", "BSA"],
        "specs": {
            "material": "Carbon CC",
            "wheel_size": '27.5"',
            "frame_size": "L",
            "weight_kg": 2.8
        },
        "is_active": True,
        "discount_percentage": 10
    }

    fork = {
        "type": "component",
        "category_id": cats["fork"],
        "brand": "Fox",
        "model": "38 Factory",
        "price": 5500.0,
        "cost_price": 3300.0,
        "stock": 5,
        "compatibility_tags": ["Boost110"],
        "specs": {
            "travel_mm": 170,
            "damper_type": "GRIP2",
            "wheel_size": '29"',
            "weight_kg": 2.4
        },
        "is_active": True,
        "discount_percentage": 0
    }

    drivetrain = {
        "type": "component",
        "category_id": cats["drivetrain"],
        "brand": "Shimano",
        "model": "XTR M9100",
        "price": 2000.0,
        "cost_price": 1200.0,
        "stock": 10,
        "compatibility_tags": ["BB92"], # Gryzie się z BSA!
        "specs": {
            "speeds": "12s",
            "crank_length_mm": 170,
            "weight_kg": 0.52
        },
        "is_active": True,
        "discount_percentage": 0
    }

    bb = {
        "type": "component",
        "category_id": cats["bottom_bracket"],
        "brand": "SRAM",
        "model": "DUB BSA",
        "price": 250.0,
        "cost_price": 150.0,
        "stock": 15,
        "compatibility_tags": ["BSA"],
        "specs": {
            "bb_standard": "BSA threaded",
            "spindle_diameter_mm": 28.99,
            "weight_kg": 0.08
        },
        "is_active": True,
        "discount_percentage": 0
    }

    wheelset = {
        "type": "component",
        "category_id": cats["wheelset"],
        "brand": "DT Swiss",
        "model": "EX 1700 Spline",
        "price": 3800.0,
        "cost_price": 2280.0,
        "stock": 4,
        "compatibility_tags": ["Boost148"],
        "specs": {
            "material": "Aluminium",
            "wheel_size": '29"',
            "inner_width_mm": 30,
            "weight_kg": 1.9
        },
        "is_active": True,
        "discount_percentage": 0
    }

    saddle = {
        "type": "component",
        "category_id": cats["saddle"],
        "brand": "Ergon",
        "model": "SM Enduro Comp",
        "price": 450.0,
        "cost_price": 270.0,
        "stock": 12,
        "compatibility_tags": [],
        "specs": {
            "material": "CroMo",
            "size": "M/L",
            "weight_kg": 0.28
        },
        "is_active": True,
        "discount_percentage": 0
    }

    components_list = [frame, fork, drivetrain, bb, wheelset, saddle]
    res = await products_collection.insert_many(components_list)
    p_ids = res.inserted_ids
    print(f"Dodano {len(p_ids)} komponentów z kosztami własnymi i referencjami do kategorii.")

    # 3. Tworzenie roweru ze wskaźnikami na te komponenty
    bike = {
        "type": "bike",
        "category_id": cats["mtb"],
        "brand": "Specialized",
        "model": "Stumpjumper EVO",
        "price": 18000.0,
        "cost_price": 10800.0,
        "stock": 3,
        "compatibility_tags": ["Boost148", "BSA"],
        "specs": {
            "material": "Carbon FACT 11m",
            "wheel_size": '29"',
            "weight_kg": 14.2,
            "frame_size": "S3 (M/L)"
        },
        "components": {
            "frame": str(p_ids[0]),
            "fork": str(p_ids[1]),
            "drivetrain": str(p_ids[2]),
            "bottom_bracket": str(p_ids[3]),
            "wheelset": str(p_ids[4]),
            "saddle": str(p_ids[5])
        },
        "is_active": True,
        "discount_percentage": 0
    }

    bike_res = await products_collection.insert_one(bike)
    bike_id = str(bike_res.inserted_id)
    print(f"Dodano rower Specialized Stumpjumper EVO (ID: {bike_id}) z mapą komponentów.")

    # 4. Tworzenie przykładowego koszyka z pełną kopią (snapshot) danych
    test_cart = {
        "user_email": "jan@kowalski.pl",
        "name": "Mój build enduro",
        "items": [
            {
                "product_id": str(p_ids[0]),
                "brand": "Santa Cruz",
                "model": "Nomad CC",
                "price_at_purchase": 13500.0,  # 15000 - 10%
                "quantity": 1
            },
            {
                "product_id": str(p_ids[3]),
                "brand": "SRAM",
                "model": "DUB BSA",
                "price_at_purchase": 250.0,
                "quantity": 1
            }
        ]
    }
    await carts_collection.insert_one(test_cart)
    print("Dodano przykładowy koszyk testowy ze snapshotem danych.")

    # 5. Dodanie zamówienia do profilu użytkownika
    order = {
        "id": str(ObjectId()),
        "customer_email": "jan@kowalski.pl",
        "items": [
            {
                "product_id": str(p_ids[0]),
                "brand": "Santa Cruz",
                "model": "Nomad CC",
                "price_at_purchase": 13500.0,
                "cost_price_at_purchase": 9000.0,
                "quantity": 1
            },
            {
                "product_id": str(p_ids[2]),
                "brand": "Shimano",
                "model": "XTR M9100",
                "price_at_purchase": 2000.0,
                "cost_price_at_purchase": 1200.0,
                "quantity": 2
            }
        ],
        "total_price": 17500.0,
        "status": "opłacone",
        "created_at": "2026-05-30T12:00:00"
    }
    
    admin = {"email": "admin@shop.com", "role": "admin", "orders": []}
    cust = {"email": "jan@kowalski.pl", "role": "customer", "orders": [order]}
    
    await users_collection.insert_many([admin, cust])
    print("Baza zasilona testowymi użytkownikami i historią zamówień!")

if __name__ == "__main__":
    asyncio.run(populate())
