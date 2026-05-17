import requests
import time

BASE_URL = "http://127.0.0.1:8001"

def run_tests():
    print("Oczekiwanie na start serwera...")
    time.sleep(3)

    # 1. Dodaj rower
    print("Dodaję rower...")
    bike_data = {
        "brand": "Trek",
        "model": "Marlin 7",
        "price": 3500.0,
        "stock": 10,
        "tags": ["MTB", "Górski"],
        "specs": {"color": "red"}
    }
    r = requests.post(f"{BASE_URL}/bikes/", json=bike_data)
    print("Add bike response:", r.status_code, r.text)
    bike_id = r.json()["id"]

    # 2. Utwórz duże zamówienie (aby wyzwolić VIP Trigger)
    print("Składam duże zamówienie...")
    order_data = {
        "customer_email": "jan.kowalski@example.com",
        "items": [
            {
                "bike_id": bike_id,
                "brand": "Trek",
                "model": "Marlin 7",
                "price_at_purchase": 3500.0,
                "quantity": 3  # 3 * 3500 = 10500 PLN (Więcej niż 10000, trigger powinien zadziałać)
            }
        ],
        "total_price": 10500.0
    }
    r = requests.post(f"{BASE_URL}/orders/", json=order_data)
    print("Create order response:", r.status_code, r.text)

    # 3. Zobacz raport sprzedaży
    print("Pobieram raport sprzedaży...")
    r = requests.get(f"{BASE_URL}/reports/sales")
    print("Sales report:", r.status_code, r.text)

if __name__ == "__main__":
    run_tests()
