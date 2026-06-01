# TODO

## Mandatory
- [x] Zaplanowanie user flow i stworzenie architektury danych zoptymalizowanej pod profesjonalny sprzęt rowerowy.
- [x] Refaktoryzacja `models.py` i `database.py` (migracja z "bikes" na "products", dodanie "carts", "users").
- [x] Wprowadzenie JSON Schema Validators na poziomie silnika MongoDB dla wszystkich 4 kolekcji.
- [x] Funkcjonalność "Smart Cart" sprawdzająca tagi kompatybilności.
- [x] Funkcjonalność udostępniania i zapisywania koszyka.
- [x] Porównywarka komponentów.
- [x] Panel zarządczy dla Właściciela sklepu (dodawanie produktów, soft-delete, ustawianie promocji, raporty).
- [x] Symulacja systemu logowania bazującego na emailu i rolach.
- [x] diagram (ERD) jak to się ma w MongoDB
- [x] nie może być wszystko przez rekurencję (płaskie komponenty)
- [x] osadzić zamówienia bo zawsze zamówienie jest do użytkownika
- [x] kategorie opisy atrybuty, rozbić rower na komponenty
- [x] Przeniesienie testów do folderu "tests" i użycie profesjonalnej biblioteki testowej (pytest)
### NEW
- [x] Kopia (nazwy, ceny i tylko wymaganych danych) w koszyku zamiast referencji
- [x] Link do produktu w historii zamówienia, żeby było wszystko
- [x] Wyciągnięcie nie referencja (płaska struktura referencji w koszyku/zamówieniu)
- [x] Kategorie to osobna kolekcja powiązana referencją z produktem
- [x] Produkt samoistnie
- [x] Kategoria samoistna
- [x] Znaleźć kategorię i usunąć z produktu
- [x] Object ref do object w tej samej kolekcji

## Suggestions
- [] Pełne wsparcie dla uwierzytelniania JWT.
- [] Zaawansowane filtry po `specs` (np. wyświetlanie tylko ram ze "skokiem > 140mm").
- [] Implementacja Change Streams do wysyłania powiadomień klientom o ponownej dostępności produktu na magazynie.
- [] Oskryptowanie bazy, aby generowała zautomatyzowane tagi na podstawie specyfikacji.
