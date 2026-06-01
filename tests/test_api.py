import os
import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

# Ustawiamy bazę testową PRZED importem aplikacji main/database
os.environ["MONGO_DB_NAME"] = "bike_shop_test_db"

from main import app
from database import products_collection, users_collection

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Fixture czyszczący bazę testową przed i po uruchomieniu testów z użyciem synchronicznego pymongo."""
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/?replicaSet=rs0")
    client = MongoClient(mongo_uri)
    
    # Czyszczenie przed testami
    client.drop_database("bike_shop_test_db")
    yield
    # Czyszczenie po testach
    client.drop_database("bike_shop_test_db")
    client.close()

@pytest.fixture(scope="module")
def client():
    """Fixture dostarczający TestClient dla FastAPI z poprawną obsługą cyklu życia."""
    with TestClient(app) as c:
        yield c

def test_full_bike_shop_workflow(client):
    # 0. Pobieramy domyślne kategorie, które są automatycznie dodawane w init_db
    categories_resp = client.get("/categories/")
    assert categories_resp.status_code == 200
    categories = categories_resp.json()
    assert len(categories) > 0
    
    mtb_cat_id = next(c for c in categories if c["slug"] == "mtb")["id"]

    # 1. DODAWANIE PRODUKTU (Rower z referencją do kategorii mtb i ceną hurtową)
    bike_data = {
        "type": "bike",
        "category_id": mtb_cat_id,
        "brand": "Trek",
        "model": "Marlin 7",
        "price": 3500.0,
        "cost_price": 2100.0,
        "stock": 10,
        "compatibility_tags": ["BSA"],
        "specs": {"material": "Aluminium", "wheel_size": '29"'}
    }
    response = client.post("/products/", json=bike_data)
    assert response.status_code == 200
    bike_json = response.json()
    assert bike_json["brand"] == "Trek"
    assert bike_json["model"] == "Marlin 7"
    assert bike_json["category_id"] == mtb_cat_id
    assert bike_json["cost_price"] == 2100.0
    assert bike_json["stock"] == 10
    bike_id = bike_json["id"]

    # 2. EDYCJA PRODUKTU (PUT /products/{id})
    updated_bike_data = {
        "type": "bike",
        "category_id": mtb_cat_id,
        "brand": "Trek",
        "model": "Marlin 7 Pro",
        "price": 4000.0,
        "cost_price": 2400.0,
        "stock": 20,
        "compatibility_tags": ["BSA", "Boost148"],
        "specs": {"material": "Aluminium Alpha Gold", "wheel_size": '29"'},
        "is_active": True,
        "discount_percentage": 5
    }
    response = client.put(f"/products/{bike_id}", json=updated_bike_data)
    assert response.status_code == 200
    updated_json = response.json()
    assert updated_json["model"] == "Marlin 7 Pro"
    assert updated_json["price"] == 4000.0
    assert updated_json["cost_price"] == 2400.0
    assert updated_json["stock"] == 20
    assert "Boost148" in updated_json["compatibility_tags"]
    assert updated_json["discount_percentage"] == 5

    # 3. SKŁADANIE ZAMÓWIENIA (POST /orders/)
    order_data = {
        "customer_email": "jan.kowalski@example.com",
        "items": [
            {
                "product_id": bike_id,
                "brand": "Trek",
                "model": "Marlin 7 Pro",
                "price_at_purchase": 3800.0,  # 4000 - 5% = 3800
                "quantity": 2
            }
        ],
        "total_price": 7600.0
    }
    response = client.post("/orders/", json=order_data)
    assert response.status_code == 200
    order_json = response.json()
    assert order_json["status"] == "opłacone"
    assert len(order_json["items"]) == 1
    assert order_json["items"][0]["cost_price_at_purchase"] == 2400.0  # Utrwalony cost_price w bazie
    order_id = order_json["id"]

    # Zweryfikowanie stanu magazynowego po zamówieniu (powinno być 20 - 2 = 18)
    prod_resp = client.get("/products/?type=bike")
    assert prod_resp.status_code == 200
    products = prod_resp.json()
    matching_bike = next(p for p in products if p["id"] == bike_id)
    assert matching_bike["stock"] == 18

    # 4. ZMIANA STATUSU ZAMÓWIENIA (PUT /admin/orders/{id}/status)
    response = client.put(f"/admin/orders/{order_id}/status?status=wysłane")
    assert response.status_code == 200
    status_json = response.json()
    assert status_json["status"] == "success"
    assert status_json["new_status"] == "wysłane"

    # 5. POBIERANIE RAPORTU SPRZEDAŻY Z FILTRAMI (GET /admin/reports/sales)
    response = client.get("/admin/reports/sales?start_date=2026-05-01&end_date=2026-06-01")
    assert response.status_code == 200
    report_json = response.json()
    assert len(report_json) > 0
    trek_report = next(r for r in report_json if r["brand"] == "Trek")
    assert trek_report["total_sold_units"] == 2
    assert trek_report["total_revenue"] == 7600.0
    assert trek_report["total_cost"] == 4800.0  # 2 * 2400.0

    # 6. HISTORIA ZAMÓWIEŃ UŻYTKOWNIKA (GET /users/{email}/history)
    response = client.get("/users/jan.kowalski@example.com/history")
    assert response.status_code == 200
    history_json = response.json()
    assert len(history_json) >= 1
    user_order = next(o for o in history_json if o["id"] == order_id)
    assert user_order["status"] == "wysłane"
    assert user_order["items"][0]["cost_price_at_purchase"] == 2400.0

def test_bike_breakdown_and_cart_operations(client):
    # 0. Pobieramy kategorie z bazy
    categories_resp = client.get("/categories/")
    assert categories_resp.status_code == 200
    categories = categories_resp.json()
    
    frame_cat_id = next(c for c in categories if c["slug"] == "frame")["id"]
    fork_cat_id = next(c for c in categories if c["slug"] == "fork")["id"]
    bb_cat_id = next(c for c in categories if c["slug"] == "bottom_bracket")["id"]
    mtb_cat_id = next(c for c in categories if c["slug"] == "mtb")["id"]

    # 1. Tworzymy komponenty (rama, widelec)
    frame_data = {
        "type": "component",
        "category_id": frame_cat_id,
        "brand": "Santa Cruz",
        "model": "Chameleon Frame",
        "price": 4000.0,
        "cost_price": 2400.0,
        "stock": 5,
        "compatibility_tags": ["BSA", "Boost148"],
        "specs": {"material": "Carbon", "weight_kg": 2.1}
    }
    res_frame = client.post("/products/", json=frame_data)
    assert res_frame.status_code == 200
    frame_id = res_frame.json()["id"]

    fork_data = {
        "type": "component",
        "category_id": fork_cat_id,
        "brand": "Fox",
        "model": "34 Float Performance",
        "price": 3000.0,
        "cost_price": 1800.0,
        "stock": 4,
        "compatibility_tags": ["Boost110"],
        "specs": {"travel_mm": 130, "wheel_size": '29"'}
    }
    res_fork = client.post("/products/", json=fork_data)
    assert res_fork.status_code == 200
    fork_id = res_fork.json()["id"]

    # 2. Tworzymy komponent wchodzący w konflikt (PressFit BB92 bottom bracket do ramy BSA)
    bb_data = {
        "type": "component",
        "category_id": bb_cat_id,
        "brand": "SRAM",
        "model": "DUB PressFit BB92",
        "price": 200.0,
        "cost_price": 120.0,
        "stock": 10,
        "compatibility_tags": ["BB92"],
        "specs": {"shell_width": 92}
    }
    res_bb = client.post("/products/", json=bb_data)
    assert res_bb.status_code == 200
    bb_id = res_bb.json()["id"]

    # 3. Tworzymy rower Custom Build, który referencjonuje ramę i widelec (płaska struktura referencji)
    bike_data = {
        "type": "bike",
        "category_id": mtb_cat_id,
        "brand": "Santa Cruz",
        "model": "Chameleon Custom Build",
        "price": 8000.0,
        "cost_price": 4800.0,
        "stock": 2,
        "compatibility_tags": ["BSA", "Boost148"],
        "specs": {"color": "Bronze"},
        "components": {
            "frame": frame_id,
            "fork": fork_id
        }
    }
    res_bike = client.post("/products/", json=bike_data)
    assert res_bike.status_code == 200
    bike_json = res_bike.json()
    assert bike_json["components"]["frame"] == frame_id
    assert bike_json["components"]["fork"] == fork_id
    bike_id = bike_json["id"]

    # 4. WERYFIKACJA BREAKDOWN (Rozbicie na części)
    # Frontend pobierze komponenty na podstawie referencji bike.components
    fetched_bike_resp = client.get("/products/?type=bike")
    assert fetched_bike_resp.status_code == 200
    all_bikes = fetched_bike_resp.json()
    fetched_bike = next(b for b in all_bikes if b["id"] == bike_id)
    
    # Symulujemy rozbicie roweru na części: pobranie każdego komponentu po ID
    retrieved_components = []
    for comp_role, comp_id in fetched_bike["components"].items():
        comp_resp = client.get(f"/products/")
        assert comp_resp.status_code == 200
        all_prods = comp_resp.json()
        comp = next(p for p in all_prods if p["id"] == comp_id)
        assert comp is not None
        retrieved_components.append(comp)
        
    assert len(retrieved_components) == 2
    assert any(c["category_id"] == frame_cat_id for c in retrieved_components)
    assert any(c["category_id"] == fork_cat_id for c in retrieved_components)

    # 5. SMART CART & WERYFIKACJA KOMPATYBILNOŚCI
    # A. Sprawdzamy kompatybilność poprawnych, składowych części roweru (frame + fork)
    compat_resp = client.post("/carts/check-compatibility", json={"product_ids": [frame_id, fork_id]})
    assert compat_resp.status_code == 200
    assert len(compat_resp.json()["warnings"]) == 0

    # B. Sprawdzamy kompatybilność z elementem wchodzącym w konflikt (rama BSA + suport PressFit BB92)
    conflict_resp = client.post("/carts/check-compatibility", json={"product_ids": [frame_id, bb_id]})
    assert conflict_resp.status_code == 200
    warnings = conflict_resp.json()["warnings"]
    assert len(warnings) > 0
    assert any("BSA" in w and "BB92" in w for w in warnings)

def test_cart_snapshots(client):
    # 0. Pobierz kategorię
    categories_resp = client.get("/categories/")
    categories = categories_resp.json()
    mtb_id = next(c for c in categories if c["slug"] == "mtb")["id"]

    # 1. Dodaj produkt
    bike_data = {
        "type": "bike",
        "category_id": mtb_id,
        "brand": "Specialized",
        "model": "Stumpjumper Evo",
        "price": 18000.0,
        "cost_price": 10800.0,
        "stock": 5,
        "compatibility_tags": []
    }
    r = client.post("/products/", json=bike_data)
    assert r.status_code == 200
    bike_id = r.json()["id"]

    # 2. Zapisz koszyk z pełnym snapshotem produktu (brand, model, price_at_purchase)
    cart_data = {
        "user_email": "jan@kowalski.pl",
        "name": "Mój koszyk z kopią danych",
        "items": [
            {
                "product_id": bike_id,
                "brand": "Specialized",
                "model": "Stumpjumper Evo",
                "price_at_purchase": 18000.0,
                "quantity": 1
            }
        ]
    }
    r_cart = client.post("/carts/save", json=cart_data)
    assert r_cart.status_code == 200
    cart_id = r_cart.json()["cart_id"]

    # 3. Pobierz koszyk i zweryfikuj czy dane (kopia) są zachowane
    r_get = client.get(f"/carts/{cart_id}")
    assert r_get.status_code == 200
    cart_json = r_get.json()
    assert cart_json["items"][0]["brand"] == "Specialized"
    assert cart_json["items"][0]["model"] == "Stumpjumper Evo"
    assert cart_json["items"][0]["price_at_purchase"] == 18000.0
