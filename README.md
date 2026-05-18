# Sklep Rowerowy PRO - Architektura NoSQL

## Cel projektu
Aplikacja symuluje zaawansowany backend i frontend sklepu rowerowego przeznaczonego dla profesjonalistów. Projekt wykorzystuje pełnię możliwości bazy **MongoDB (NoSQL)**, koncentrując się na elastycznych schematach, zagnieżdżaniu danych, oraz walidacji zaawansowanych algorytmów na poziomie bazy danych.

## Nowe Funkcjonalności Sklepu PRO
1. **Zarządzanie asortymentem (Rowery i Komponenty)**:
   Kolekcja `products` przechowuje zarówno rowery, jak i setki różnego rodzaju części (drivetrain, frame, wheels). Zamiast relacyjnych tabel dla każdej kategorii, elastyczny dokument NoSQL pozwala na przechowywanie zróżnicowanej specyfikacji (`specs` jako mapa `Dict[str, Any]`).
   
2. **Algorytm Weryfikacji Kompatybilności**:
   Kluczową funkcją biznesową dla profesjonalistów jest tzw. "Smart Cart". Każdy produkt w bazie przechowuje ukryte tagi kompatybilności (np. `BB92`, `Boost148`). Podczas przeglądania koszyka, system weryfikuje tagi. Jeśli np. w koszyku znajdzie się rama korzystająca ze standardu wkręcanego `BSA` oraz suport pod standard wciskany `BB92`, system zgłosi konflikt.

3. **Zapisywanie i udostępnianie koszyka**:
   Klienci mogą pracować nad "wymarzonym buildem", zapisać koszyk i otrzymać unikalne ID. Koszyk zapisuje się jako osobny dokument, co ułatwia jego udostępnianie innym użytkownikom.

4. **Porównywarka Komponentów**:
   Klienci mogą zaznaczać wiele komponentów z katalogu, by w modalnym oknie przejrzeć i porównać ich niestandardowe parametry (`specs`), wspierając się przy tym odmiennymi typami danych.

5. **Panel Zarządzania (Właściciel)**:
   Admin może nakładać promocje na produkty (np. -20%). Promocja jest od razu przeliczana na froncie. Admin może także miękko usuwać (soft-delete) produkty oraz generować raporty sprzedaży, co wykorzystuje potężne potoki aggregacji MongoDB (Aggregation Pipelines).

## Zaawansowane wzorce NoSQL

1. **Transakcje ACID (Multi-document Transactions)**:
   Mimo elastyczności NoSQL, składanie zamówienia modyfikuje stany magazynowe w kolekcji `products` oraz zapisuje dane w `orders` oraz profilu użytkownika `users` - to wszystko działa w obrębie transakcji na infrastrukturze Replica Set, by zapobiec ujemnym stanom magazynowym.

2. **Aggregation Framework**:
   Generowanie raportów dla admina używa natywnych pipelinów (`$unwind`, `$group`, `$multiply`, `$sort`) do wyciągnięcia kluczowych metryk o sprzedaży z dużych wolumenów danych wewnątrz silnika bazy.

3. **Indeksy i Text Search**:
   Kolekcja produktów posiada odpowiednie indeksy na pola `brand`, `price`, `type`, `category` oraz potężny Text Index na `model` i `tags`.

4. **JSON Schema Validator**:
   Projekt wdraża na poziomie bazy restrykcyjne zasady wstawiania (walidacja typów `enum`, `array` z ukrytymi tagami, limity liczbowe `minimum`, itp.).

## Architektura Modeli: Embedded vs Referenced
Projekt wykorzystuje hybrydę:
- **Embedded (Zagnieżdżone)**: Zawartość zamówień (`items` wewnątrz `Order`) korzysta ze wstrzykniętych aktualnych cen i nazw. Daje to nam tzw. "Snapshot" point-in-time, niezależny od zmian cen w głównym katalogu.
- **Referenced (Referencje)**: Profil użytkownika przechowuje historię zamówień tylko w postaci referencji (lista ObjectId w `purchase_history`). Zabezpiecza to profil przed pęcznieniem ponad limit 16MB na pojedynczy dokument MongoDB, szczególnie dla stałych i lojalnych klientów (wzorzec *Subset* / referencje w jedną stronę).
