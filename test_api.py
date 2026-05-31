import requests
import time

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("Oczekiwanie na start serwera...")
    time.sleep(1)

    # 1. Dodaj produkt (rower) z cost_price
    print("1. Dodaję rower Trek Marlin 7...")
    bike_data = {
        "type": "bike",
        "category": "mtb",
        "brand": "Trek",
        "model": "Marlin 7",
        "price": 3500.0,
        "cost_price": 2100.0,
        "stock": 10,
        "compatibility_tags": ["BSA"],
        "specs": {"material": "Aluminium", "wheel_size": '29"'}
    }
    r = requests.post(f"{BASE_URL}/products/", json=bike_data)
    print("Add product response:", r.status_code)
    if r.status_code != 200:
        print("Error:", r.text)
        return
    
    bike_json = r.json()
    print("Created bike:", bike_json)
    bike_id = bike_json["id"]

    # 2. Edytuj produkt (zwiększ stan magazynowy i zmień cenę)
    print("\n2. Testuję pełną edycję produktu Trek Marlin 7 (PUT)...")
    updated_bike_data = {
        "type": "bike",
        "category": "mtb",
        "brand": "Trek",
        "model": "Marlin 7 Pro", # Zmiana modelu na Pro
        "price": 4000.0,          # Zmiana ceny na 4000.0
        "cost_price": 2400.0,     # Zmiana kosztu na 2400.0
        "stock": 20,              # Zmiana stanu na 20
        "compatibility_tags": ["BSA", "Boost148"], # Dodanie tagu
        "specs": {"material": "Aluminium Alpha Gold", "wheel_size": '29"'},
        "is_active": True,
        "discount_percentage": 5 # Dodanie zniżki
    }
    r = requests.put(f"{BASE_URL}/products/{bike_id}", json=updated_bike_data)
    print("Edit product response:", r.status_code)
    if r.status_code != 200:
        print("Error:", r.text)
        return
    print("Updated bike data:", r.json())

    # 3. Utwórz zamówienie (zweryfikuj automatyczne przypisanie cost_price_at_purchase i statusu)
    print("\n3. Składam zamówienie na Trek Marlin 7 Pro...")
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
    r = requests.post(f"{BASE_URL}/orders/", json=order_data)
    print("Create order response:", r.status_code)
    if r.status_code != 200:
        print("Error:", r.text)
        return
    
    order_json = r.json()
    print("Created order:", order_json)
    order_id = order_json["id"]

    # 4. Zmień status zamówienia na 'wysłane' (PUT)
    print("\n4. Testuję zmianę statusu zamówienia na 'wysłane'...")
    r = requests.put(f"{BASE_URL}/admin/orders/{order_id}/status?status=wysłane")
    print("Update order status response:", r.status_code)
    if r.status_code != 200:
        print("Error:", r.text)
        return
    print("Update status data:", r.json())

    # 5. Pobierz raport sprzedaży z filtrami dat i kalkulacją zysków/wydatków
    print("\n5. Pobieram raport sprzedaży (Filtrowany czasowo)...")
    r = requests.get(f"{BASE_URL}/admin/reports/sales?start_date=2026-05-01&end_date=2026-06-01")
    print("Sales report response:", r.status_code)
    if r.status_code != 200:
        print("Error:", r.text)
        return
    print("Sales report data:", r.json())

    # 6. Zobacz całą historię użytkownika
    print("\n6. Pobieram historię zamówień użytkownika...")
    r = requests.get(f"{BASE_URL}/users/jan.kowalski@example.com/history")
    print("User history response:", r.status_code)
    if r.status_code != 200:
        print("Error:", r.text)
        return
    print("User history data (z nowym statusem wysłane):", r.json())

if __name__ == "__main__":
    run_tests()
