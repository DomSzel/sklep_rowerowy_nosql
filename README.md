# Projekt Sklepu Rowerowego - Architektura NoSQL

## Cel projektu
Aplikacja ta symuluje backend sklepu rowerowego, wykorzystując zalety bazy **MongoDB (NoSQL)**. W przeciwieństwie do tradycyjnych, relacyjnych baz danych (SQL), ten projekt demonstruje zaawansowane wzorce projektowe dedykowane do środowisk nierelacyjnych.

## Zaawansowane funkcjonalności akademickie
Aby sprostać najwyższym wymaganiom projektowym, system zawiera następujące mechanizmy:

1. **Transakcje ACID (Multi-document Transactions)**:
   Mimo elastyczności NoSQL, kluczowe operacje, takie jak składanie zamówienia (`POST /orders/`) i modyfikacja stanów magazynowych, działają w ścisłych transakcjach. Zapobiega to tzw. "race conditions" i niespójnościom. Całość oparta jest na architekturze *Replica Set*.
2. **Aggregation Framework (Odpowiednik SQL JOIN / GROUP BY)**:
   Rozbudowane raporty (np. `GET /reports/sales`) generowane są z wykorzystaniem natywnych pipelinów agregacji MongoDB. Narzędzia takie jak `$unwind`, `$group` i `$multiply` przetwarzają gigantyczne ilości danych bezpośrednio w bazie.
3. **Change Streams (Odpowiednik Wyzwalaczy / Triggers)**:
   System aktywnie nasłuchuje na poziomie bazy na wstawianie dużych zamówień (tzw. wyzwalacze asynchroniczne). Po przekroczeniu progu 10 000 PLN, wyzwalany jest kod dodający klienta do prestiżowej kolekcji `vip_customers`.
4. **Indeksowanie i Optymalizacja Zapytań**:
   - *Compound Index* dla pól mark i cenie znacząco przyspiesza sortowane zapytania.
   - *Text Index* na modelu i tagach pozwala na "inteligentne" wyszukiwanie słów kluczowych.
5. **Schema Validation na poziomie bazy**:
   Oprócz walidacji Pydantic w kodzie Pythona, uruchomiona jest twarda walidacja schematu (JSON Schema) narzucona bezpośrednio na silnik MongoDB (odporność na dodawanie błędnych danych z innych klientów).

## Architektura Modeli: Embedded vs Referenced
Podstawą oceny systemów NoSQL jest właściwy dobór formy powiązań między dokumentami. W tym projekcie świadomie zastosowano hybrydę dwóch podejść:

### 1. Wzorzec "Embedded Documents" (Zagnieżdżanie)
Wykorzystano w modelu koszyka zakupowego (encja `Order`).
```json
{
  "customer_email": "klient@example.com",
  "items": [
     {"bike_id": "...", "brand": "Kross", "price_at_purchase": 2500, "quantity": 1}
  ],
  "total_price": 2500
}
```
**Uzasadnienie:**
Dane dotyczące szczegółów zamówienia rzadko (lub wcale) się nie zmieniają po zakupie (tzw. wzorzec "Point in Time"). Zagnieżdżenie dokumentów `items` bezpośrednio w zamówieniu optymalizuje odczyt (tylko 1 operacja dyskowa) i gwarantuje, że zmiana ceny katalogowej roweru w przyszłości nie wpłynie na wyliczoną historyczną fakturę.

### 2. Wzorzec "Referenced Documents" (Referencje)
Zastosowano do wiązania `items` w koszyku z faktyczną tabelą `bikes` (poprzez klucz `bike_id`).
**Uzasadnienie:**
Katalog rowerów jest odrębnym bytem, edytowanym przez administratorów (zmiana opisu, stanu magazynowego). Trzymanie referencji ułatwia synchronizację stanów (robimy to za pośrednictwem transakcji podczas zakupu). Powoduje to minimalną redundancję danych i pozwala na swobodne przeglądanie katalogu bez wczytywania całej historii zamówień.
