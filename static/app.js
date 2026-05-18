// State
let cart = [];
let products = [];
let currentUser = null;
let compareList = [];

// DOM Elements
const sections = {
    catalog: document.getElementById('catalog'),
    cart: document.getElementById('cart'),
    history: document.getElementById('history'),
    'admin-panel': document.getElementById('admin-panel')
};

// Navigation
function showSection(sectionId) {
    Object.values(sections).forEach(sec => sec.classList.remove('active'));
    sections[sectionId].classList.add('active');
    
    if(sectionId === 'catalog') loadProducts();
    if(sectionId === 'cart') renderCart();
    if(sectionId === 'history' && currentUser) loadHistory();
    if(sectionId === 'admin-panel' && currentUser?.role === 'admin') loadAdminData();
}

function showToast(message, type = '') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// Login Modal
function openLoginModal() { document.getElementById('login-modal').classList.add('show'); }
function closeLoginModal() { document.getElementById('login-modal').classList.remove('show'); }

async function login(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const role = document.getElementById('login-role').value;
    
    try {
        const res = await fetch('/users/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email, role})
        });
        const user = await res.json();
        currentUser = user;
        
        document.getElementById('user-display').textContent = `${user.email} (${user.role})`;
        document.getElementById('nav-history').style.display = 'block';
        document.getElementById('checkout-btn').disabled = false;
        document.getElementById('checkout-btn').textContent = 'Złóż Zamówienie';
        
        if(user.role === 'admin') {
            document.getElementById('nav-admin').style.display = 'block';
        } else {
            document.getElementById('nav-admin').style.display = 'none';
        }
        
        closeLoginModal();
        showToast('Zalogowano pomyślnie');
        showSection('catalog');
    } catch (err) {
        showToast('Błąd logowania', 'error');
    }
}

// Products
async function loadProducts() {
    const type = document.getElementById('filter-type').value;
    const category = document.getElementById('filter-category').value;
    
    let url = '/products/?';
    if(type) url += `type=${type}&`;
    if(category) url += `category=${category}&`;

    try {
        const response = await fetch(url);
        products = await response.json();
        renderProducts(products, 'products-grid');
    } catch (error) {
        showToast('Błąd pobierania produktów', 'error');
    }
}

function renderProducts(items, containerId) {
    const grid = document.getElementById(containerId);
    grid.innerHTML = '';
    
    items.forEach(p => {
        const isChecked = compareList.includes(p.id) ? 'checked' : '';
        const card = document.createElement('div');
        card.className = 'card product-card';
        
        let priceHtml = '';
        if(p.discount_percentage > 0) {
            const newPrice = p.price * (1 - p.discount_percentage/100);
            priceHtml = `
                <div class="discount-badge">-${p.discount_percentage}%</div>
                <div class="price-container">
                    <span class="old-price">${p.price.toFixed(2)} PLN</span>
                    <span class="new-price">${newPrice.toFixed(2)} PLN</span>
                </div>
            `;
        } else {
            priceHtml = `<div class="price-container"><span class="normal-price">${p.price.toFixed(2)} PLN</span></div>`;
        }

        const compTags = p.compatibility_tags.map(t => `<span class="tag compat-tag">${t}</span>`).join('');

        card.innerHTML = `
            <input type="checkbox" class="compare-checkbox" title="Dodaj do porównania" onchange="toggleCompare('${p.id}', this.checked)" ${isChecked}>
            <div style="text-transform: uppercase; font-size: 0.8rem; color: var(--text-muted); margin-left: 2rem;">${p.category}</div>
            <h3 style="margin-left: 2rem;">${p.brand} ${p.model}</h3>
            ${priceHtml}
            <div class="stock">Dostępność: ${p.stock} szt.</div>
            <div style="margin-bottom: 10px;">${compTags}</div>
            <button onclick="addToCart('${p.id}')" style="width: 100%;" class="btn-primary">Do koszyka</button>
        `;
        grid.appendChild(card);
    });
}

// Compare
function toggleCompare(id, isChecked) {
    if(isChecked) {
        if(compareList.length >= 3) {
            showToast('Możesz porównać max 3 produkty', 'warning');
            event.target.checked = false;
            return;
        }
        compareList.push(id);
    } else {
        compareList = compareList.filter(x => x !== id);
    }
}

function openCompareModal() {
    if(compareList.length === 0) {
        showToast('Wybierz przynajmniej jeden produkt do porównania', 'warning');
        return;
    }
    const grid = document.getElementById('compare-grid');
    grid.innerHTML = '';
    
    compareList.forEach(id => {
        const p = products.find(x => x.id === id);
        const col = document.createElement('div');
        col.className = 'compare-column';
        
        let specsHtml = Object.entries(p.specs || {}).map(([k,v]) => `<li><strong>${k}:</strong> ${v}</li>`).join('');
        
        col.innerHTML = `
            <h4 style="color:var(--primary);">${p.brand} ${p.model}</h4>
            <p><strong>Cena:</strong> ${p.price} PLN</p>
            <p><strong>Zniżka:</strong> ${p.discount_percentage}%</p>
            <p><strong>Kompatybilność:</strong> ${p.compatibility_tags.join(', ') || 'Brak'}</p>
            <hr style="border-color:var(--border); margin: 10px 0;">
            <ul style="margin-left: 15px; font-size: 0.9rem; color: var(--text-muted);">${specsHtml}</ul>
        `;
        grid.appendChild(col);
    });
    
    document.getElementById('compare-modal').classList.add('show');
}
function closeCompareModal() { document.getElementById('compare-modal').classList.remove('show'); }

// Cart
function addToCart(pid) {
    const p = products.find(x => x.id === pid);
    if (!p) return;
    if (p.stock <= 0) { showToast('Brak w magazynie', 'error'); return; }

    const item = cart.find(i => i.product_id === pid);
    if (item) {
        if (item.quantity >= p.stock) { showToast('Max ilość w magazynie', 'warning'); return; }
        item.quantity += 1;
    } else {
        cart.push({
            product_id: p.id,
            brand: p.brand,
            model: p.model,
            price_at_purchase: p.price * (1 - p.discount_percentage/100),
            quantity: 1
        });
    }
    updateCartCount();
    checkCompatibility();
    showToast('Dodano do koszyka');
}

function updateCartCount() {
    const total = cart.reduce((s, i) => s + i.quantity, 0);
    document.getElementById('cart-count').textContent = total;
}

async function checkCompatibility() {
    if(cart.length < 2) {
        document.getElementById('compatibility-warnings').style.display = 'none';
        return;
    }
    try {
        const res = await fetch('/carts/check-compatibility', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({product_ids: cart.map(i => i.product_id)})
        });
        const data = await res.json();
        const box = document.getElementById('compatibility-warnings');
        if(data.warnings.length > 0) {
            box.style.display = 'block';
            box.innerHTML = `<strong>Zagrożenie Kompatybilności:</strong><ul>` + 
                data.warnings.map(w => `<li>${w}</li>`).join('') + `</ul>`;
        } else {
            box.style.display = 'none';
        }
    } catch(err) {
        console.error(err);
    }
}

function renderCart() {
    const list = document.getElementById('cart-items');
    list.innerHTML = '';
    if (cart.length === 0) {
        list.innerHTML = '<p>Koszyk jest pusty.</p>';
        document.getElementById('cart-total-price').textContent = '0.00';
        return;
    }

    let total = 0;
    cart.forEach((item, idx) => {
        const itemTotal = item.price_at_purchase * item.quantity;
        total += itemTotal;
        list.innerHTML += `
            <div class="cart-item">
                <div><strong>${item.brand} ${item.model}</strong><br>${item.quantity} szt. x ${item.price_at_purchase.toFixed(2)} PLN</div>
                <div>
                    <strong>${itemTotal.toFixed(2)} PLN</strong>
                    <button onclick="removeFromCart(${idx})" class="btn-secondary" style="margin-left:1rem; background: var(--danger); padding: 5px 10px;">X</button>
                </div>
            </div>`;
    });
    document.getElementById('cart-total-price').textContent = total.toFixed(2);
    checkCompatibility();
}

function removeFromCart(idx) {
    cart.splice(idx, 1);
    updateCartCount();
    renderCart();
}

async function saveCart() {
    if(!currentUser) { showToast('Musisz być zalogowany by zapisać', 'error'); return; }
    if(cart.length === 0) { showToast('Koszyk pusty', 'warning'); return; }
    
    try {
        const res = await fetch('/carts/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_email: currentUser.email,
                name: `Koszyk z ${new Date().toLocaleDateString()}`,
                items: cart.map(i => ({product_id: i.product_id, quantity: i.quantity}))
            })
        });
        const data = await res.json();
        showToast('Skopiuj to ID koszyka: ' + data.cart_id, 'success');
        prompt("ID Koszyka - zapisz by wczytać później:", data.cart_id);
    } catch(err) { showToast('Błąd zapisu', 'error'); }
}

async function loadCart() {
    const id = document.getElementById('load-cart-id').value;
    if(!id) return;
    try {
        const res = await fetch(`/carts/${id}`);
        if(!res.ok) throw new Error();
        const data = await res.json();
        
        // Musimy pobrać pełne dane produktów, bo koszyk w bazie ma tylko id i quantity
        cart = [];
        await loadProducts(); // ensures products are loaded
        data.items.forEach(i => {
            const p = products.find(x => x.id === i.product_id);
            if(p) {
                cart.push({
                    product_id: p.id,
                    brand: p.brand,
                    model: p.model,
                    price_at_purchase: p.price * (1 - p.discount_percentage/100),
                    quantity: i.quantity
                });
            }
        });
        updateCartCount();
        renderCart();
        showToast('Koszyk wczytany');
    } catch(err) { showToast('Nie znaleziono koszyka', 'error'); }
}

async function placeOrder(e) {
    e.preventDefault();
    if (!currentUser) return;
    if (cart.length === 0) return;

    const total = cart.reduce((s, i) => s + (i.price_at_purchase * i.quantity), 0);
    try {
        const res = await fetch('/orders/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                customer_email: currentUser.email,
                items: cart,
                total_price: total
            })
        });
        if(res.ok) {
            showToast('Zamówienie w drodze!', 'success');
            cart = []; updateCartCount(); renderCart();
        } else {
            const data = await res.json();
            showToast(data.detail, 'error');
        }
    } catch(err) { showToast('Błąd sieci', 'error'); }
}

// History
async function loadHistory() {
    try {
        const res = await fetch(`/users/${currentUser.email}/history`);
        const data = await res.json();
        const list = document.getElementById('history-list');
        list.innerHTML = '';
        data.forEach(order => {
            const itemsHtml = order.items.map(i => `<li>${i.brand} ${i.model} (${i.quantity}szt)</li>`).join('');
            list.innerHTML += `
                <div class="cart-item" style="flex-direction: column; align-items: flex-start; gap: 10px;">
                    <div><strong>Data:</strong> ${new Date(order.created_at).toLocaleString()} | <strong>Suma:</strong> ${order.total_price.toFixed(2)} PLN</div>
                    <ul style="margin-left: 20px; color: var(--text-muted); font-size: 0.9rem;">${itemsHtml}</ul>
                </div>
            `;
        });
    } catch(err) { showToast('Błąd pobierania historii', 'error'); }
}

// Admin
async function addProduct(e) {
    e.preventDefault();
    const type = document.getElementById('add-type').value;
    const cat = document.getElementById('add-category').value;
    const tagsRaw = document.getElementById('add-compat-tags').value;
    const compatTags = tagsRaw.split(',').map(t=>t.trim()).filter(t=>t);
    
    const prod = {
        type: type,
        category: cat,
        brand: document.getElementById('add-brand').value,
        model: document.getElementById('add-model').value,
        price: parseFloat(document.getElementById('add-price').value),
        stock: parseInt(document.getElementById('add-stock').value),
        compatibility_tags: compatTags,
        tags: [], specs: {}
    };

    try {
        await fetch('/products/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(prod)
        });
        showToast('Produkt dodany', 'success');
        document.getElementById('add-product-form').reset();
        loadAdminData();
    } catch(err) { showToast('Błąd zapisu', 'error'); }
}

async function loadAdminData() {
    // Raporty
    try {
        const res = await fetch('/admin/reports/sales');
        const data = await res.json();
        const tbody = document.getElementById('reports-body');
        tbody.innerHTML = '';
        data.forEach(r => {
            tbody.innerHTML += `<tr><td>${r.brand}</td><td>${r.total_sold_units}</td><td>${r.total_revenue.toFixed(2)} PLN</td></tr>`;
        });
    } catch(err) { console.error(err); }

    // Zarządzanie produktami
    try {
        const res = await fetch('/products/?include_inactive=true');
        const prods = await res.json();
        const tbody = document.getElementById('admin-products-body');
        tbody.innerHTML = '';
        prods.forEach(p => {
            tbody.innerHTML += `
                <tr>
                    <td>${p.brand} ${p.model}</td>
                    <td><button onclick="toggleStatus('${p.id}', ${!p.is_active})" class="btn-secondary" style="padding:2px 5px; font-size:0.8rem;">${p.is_active ? 'Ukryj' : 'Aktywuj'}</button></td>
                    <td>
                        <input type="number" min="0" max="100" value="${p.discount_percentage}" style="width:60px; padding:2px; margin:0;" id="disc-${p.id}">
                        <button onclick="setDisc('${p.id}')" class="btn-success" style="padding:2px 5px; font-size:0.8rem;">Zapisz</button>
                    </td>
                    <td>---</td>
                </tr>
            `;
        });
    } catch(err) { console.error(err); }
}

async function toggleStatus(id, newStatus) {
    await fetch(`/products/${id}/status?is_active=${newStatus}`, {method:'PUT'});
    loadAdminData();
}

async function setDisc(id) {
    const val = document.getElementById(`disc-${id}`).value;
    await fetch(`/products/${id}/promotion?discount_percentage=${val}`, {method:'PUT'});
    showToast('Zniżka zaktualizowana', 'success');
    loadAdminData();
}

// Init
window.onload = loadProducts;
