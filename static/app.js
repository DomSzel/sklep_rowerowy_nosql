// State
let cart = [];
let bikes = [];

// DOM Elements
const sections = {
    catalog: document.getElementById('catalog'),
    addBike: document.getElementById('add-bike'),
    cart: document.getElementById('cart'),
    reports: document.getElementById('reports')
};

// Navigation
function showSection(sectionId) {
    Object.values(sections).forEach(sec => sec.classList.remove('active'));
    sections[sectionId].classList.add('active');
    
    if(sectionId === 'catalog') loadBikes();
    if(sectionId === 'reports') loadReports();
    if(sectionId === 'cart') renderCart();
}

// Show Toast
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast show ${isError ? 'error' : ''}`;
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Fetch and render bikes
async function loadBikes() {
    const maxPrice = document.getElementById('filter-price').value;
    const tag = document.getElementById('filter-tag').value;
    
    let url = '/bikes/search/?';
    if(maxPrice) url += `max_price=${maxPrice}&`;
    if(tag) url += `tag=${tag}&`;

    try {
        const response = await fetch(url);
        bikes = await response.json();
        
        const grid = document.getElementById('bikes-grid');
        grid.innerHTML = '';
        
        bikes.forEach(bike => {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <h3>${bike.brand} ${bike.model}</h3>
                <div class="price">${bike.price.toFixed(2)} PLN</div>
                <div class="stock">Dostępność: ${bike.stock} szt.</div>
                <div class="tags-container">
                    ${bike.tags.map(t => `<span class="tag">${t}</span>`).join('')}
                </div>
                <button onclick="addToCart('${bike.id}')" style="margin-top: 1rem; width: 100%;">
                    Dodaj do koszyka
                </button>
            `;
            grid.appendChild(card);
        });
    } catch (error) {
        showToast('Błąd pobierania rowerów', true);
    }
}

// Add new bike
async function addBike(e) {
    e.preventDefault();
    
    const newBike = {
        brand: document.getElementById('add-brand').value,
        model: document.getElementById('add-model').value,
        price: parseFloat(document.getElementById('add-price').value),
        stock: parseInt(document.getElementById('add-stock').value),
        tags: document.getElementById('add-tags').value.split(',').map(t => t.trim()).filter(t => t),
        specs: {}
    };

    try {
        const response = await fetch('/bikes/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newBike)
        });

        if (response.ok) {
            showToast('Rower dodany pomyślnie!');
            document.getElementById('add-bike-form').reset();
            showSection('catalog');
        } else {
            showToast('Błąd podczas dodawania roweru', true);
        }
    } catch (error) {
        showToast('Błąd sieci', true);
    }
}

// Cart logic
function addToCart(bikeId) {
    const bike = bikes.find(b => b.id === bikeId);
    if (!bike) return;

    if (bike.stock <= 0) {
        showToast('Brak roweru w magazynie!', true);
        return;
    }

    const cartItem = cart.find(item => item.bike_id === bikeId);
    if (cartItem) {
        if (cartItem.quantity >= bike.stock) {
            showToast('Nie możesz dodać więcej niż jest w magazynie!', true);
            return;
        }
        cartItem.quantity += 1;
    } else {
        cart.push({
            bike_id: bike.id,
            brand: bike.brand,
            model: bike.model,
            price_at_purchase: bike.price,
            quantity: 1
        });
    }
    
    updateCartCount();
    showToast(`Dodano ${bike.brand} ${bike.model} do koszyka`);
}

function updateCartCount() {
    const total = cart.reduce((sum, item) => sum + item.quantity, 0);
    document.getElementById('cart-count').textContent = total;
}

function renderCart() {
    const cartList = document.getElementById('cart-items');
    cartList.innerHTML = '';
    
    if (cart.length === 0) {
        cartList.innerHTML = '<p>Twój koszyk jest pusty.</p>';
        document.getElementById('cart-total-price').textContent = '0.00';
        return;
    }

    let totalPrice = 0;

    cart.forEach((item, index) => {
        const itemTotal = item.price_at_purchase * item.quantity;
        totalPrice += itemTotal;
        
        const el = document.createElement('div');
        el.className = 'cart-item';
        el.innerHTML = `
            <div>
                <strong>${item.brand} ${item.model}</strong><br>
                ${item.quantity} szt. x ${item.price_at_purchase.toFixed(2)} PLN
            </div>
            <div>
                <strong>${itemTotal.toFixed(2)} PLN</strong>
                <button onclick="removeFromCart(${index})" style="margin-left: 1rem; padding: 0.3rem 0.6rem; background: #ef4444;">X</button>
            </div>
        `;
        cartList.appendChild(el);
    });

    document.getElementById('cart-total-price').textContent = totalPrice.toFixed(2);
}

function removeFromCart(index) {
    cart.splice(index, 1);
    updateCartCount();
    renderCart();
}

// Place order
async function placeOrder(e) {
    e.preventDefault();
    
    if (cart.length === 0) {
        showToast('Koszyk jest pusty!', true);
        return;
    }

    const email = document.getElementById('order-email').value;
    const totalPrice = cart.reduce((sum, item) => sum + (item.price_at_purchase * item.quantity), 0);

    const orderData = {
        customer_email: email,
        items: cart,
        total_price: totalPrice
    };

    try {
        const response = await fetch('/orders/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(orderData)
        });

        if (response.ok) {
            showToast('Zamówienie złożone pomyślnie!');
            cart = [];
            updateCartCount();
            renderCart();
            document.getElementById('order-form').reset();
        } else {
            const data = await response.json();
            showToast(data.detail || 'Błąd składania zamówienia', true);
        }
    } catch (error) {
        showToast('Błąd sieci', true);
    }
}

// Fetch Reports
async function loadReports() {
    try {
        const response = await fetch('/reports/sales');
        const reports = await response.json();
        
        const tbody = document.getElementById('reports-body');
        tbody.innerHTML = '';
        
        reports.forEach(report => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${report.brand}</strong></td>
                <td>${report.total_sold_units}</td>
                <td>${report.total_revenue.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        showToast('Błąd pobierania raportów', true);
    }
}

// Initial load
window.onload = loadBikes;
