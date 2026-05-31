# Diagram Architektury Danych NoSQL (ERD) - Sklep Rowerowy PRO

Poniższy diagram przedstawia relacje oraz strukturę danych w bazie danych MongoDB (NoSQL) dla profesjonalnego sklepu rowerowego. W NoSQL relacje są realizowane hybrydowo: poprzez **osadzanie (Embedding)** dla danych o wysokiej spójności (np. zamówienia w profilu użytkownika) oraz **referencje (References)** dla elementów o dynamicznej strukturze i stanie magazynowym (np. części składowe roweru).

```mermaid
classDiagram
    class User {
        +ObjectId _id
        +string email
        +string role
        +array orders [Embedded Order]
    }

    class Order {
        +string id
        +datetime created_at
        +double total_price
        +array items [Embedded OrderItem]
    }

    class OrderItem {
        +string product_id
        +string brand
        +string model
        +double price_at_purchase
        +int quantity
    }

    class Product {
        +ObjectId _id
        +string type ("bike" | "component")
        +string category
        +string brand
        +string model
        +double price
        +int stock
        +array compatibility_tags [Strictly for compatibility]
        +object specs [Structured attributes for easy comparison]
        +object components [Referenced Product IDs (flat map)]
        +bool is_active
        +int discount_percentage
    }

    class Cart {
        +ObjectId _id
        +string user_email
        +string name
        +array items [Embedded CartItem]
        +datetime created_at
    }

    class CartItem {
        +string product_id
        +int quantity
    }

    User "1" *-- "many" Order : Embedded (Zagnieżdżone w dokumencie użytkownika)
    Order "1" *-- "many" OrderItem : Embedded (Zrzut ceny i modelu z chwili zakupu)
    Cart "1" *-- "many" CartItem : Embedded (Zawartość koszyka)
    CartItem "many" --> "1" Product : Referenced (Odnośnik do produktu)
    Product "1 (bike)" --> "many (components)" Product : Referenced (Płaska mapa referencji bez rekurencji)
```

## Opis Wzorców Projektowych

1.  **Osadzenie Zamówień (Embedded Orders)**:
    Zamówienia są osadzone bezpośrednio w kolekcji `users` jako tablica `orders`. Ponieważ zamówienie jest zawsze przypisane do konkretnego użytkownika, pozwala to na błyskawiczny odczyt historii zamówień (jednym zapytaniem do profilu użytkownika) oraz gwarantuje wysoką spójność danych.
2.  **Migawka Pozycji Zamówienia (OrderItem Snapshot)**:
    Każda pozycja zamówienia (`OrderItem`) przechowuje aktualną cenę z chwili zakupu (`price_at_purchase`) oraz model i markę. Chroni to dane przed zmianami cen w katalogu produktów w przyszłości.
3.  **Płaskie Referencje Komponentów (Flat Referenced Components)**:
    Rower (`type: "bike"`) przechowuje słownik `components` zawierający płaskie odnośniki tekstowe `ObjectId` do części składowych w kolekcji `products`. Zapobiega to stosowaniu kosztownej rekurencji podczas pobierania buildów rowerów oraz ułatwia klientom rozbijanie roweru na części.
4.  **Tagi Kompatybilności (Compatibility Tags)**:
    Pole `compatibility_tags` jest wykorzystywane wyłącznie przez system "Smart Cart" do weryfikacji kompatybilności standardów (np. standard mufy suportu `BSA` vs `BB92`).
