// State
let cart = [];
let products = [];
let categories = [];
let currentUser = null;
let compareList = [];

// Categories Helpers
async function loadCategories() {
    try {
        const res = await fetch('/categories/');
        categories = await res.json();
        populateCategorySelects();
    } catch (err) {
        console.error('Błąd pobierania kategorii:', err);
    }
}

function getCategoryName(categoryId) {
    const c = categories.find(x => x.id === categoryId);
    return c ? c.name : 'Nieznana';
}

function populateCategorySelects() {
    const filterSelect = document.getElementById('filter-category');
    const addSelect = document.getElementById('add-category');
    const editSelect = document.getElementById('edit-category');
    
    const bikeCats = categories.filter(c => c.type === 'bike');
    const compCats = categories.filter(c => c.type === 'component');
    
    const buildOptionsHtml = (includeAny = false) => {
        let html = includeAny ? `<option value="">Dowolna Kategoria</option>` : `<option value="">Wybierz kategorię...</option>`;
        html += `<optgroup label="Rowery">`;
        bikeCats.forEach(c => {
            html += `<option value="${c.id}">${c.name}</option>`;
        });
        html += `</optgroup>`;
        html += `<optgroup label="Części">`;
        compCats.forEach(c => {
            html += `<option value="${c.id}">${c.name}</option>`;
        });
        html += `</optgroup>`;
        return html;
    };
    
    if (filterSelect) filterSelect.innerHTML = buildOptionsHtml(true);
    if (addSelect) addSelect.innerHTML = buildOptionsHtml(false);
    if (editSelect) editSelect.innerHTML = buildOptionsHtml(false);
}

// History to Catalog highlighting navigation
async function highlightProductInCatalog(productId) {
    showSection('catalog', false);
    
    // Wyczyść filtry, aby produkt na pewno był widoczny
    document.getElementById('filter-type').value = '';
    document.getElementById('filter-category').value = '';
    
    let url = '/products/?';
    try {
        const response = await fetch(url);
        products = await response.json();
        renderProducts(products, 'products-grid');
        
        setTimeout(async () => {
            const card = document.getElementById(`product-card-${productId}`);
            if (card) {
                card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                card.classList.add('highlight-glow');
                setTimeout(() => {
                    card.classList.remove('highlight-glow');
                }, 2500);
            } else {
                // Jeśli nie ma karty, sprawdzamy status produktu w bazie (w locie)
                try {
                    const resAll = await fetch('/products/?include_inactive=true');
                    const allProds = await resAll.json();
                    const foundInDb = allProds.find(x => x.id === productId);
                    
                    if (foundInDb) {
                        if (!foundInDb.is_active) {
                            showToast('Ten produkt został wycofany ze sprzedaży (jest nieaktywny).', 'warning');
                        } else {
                            showToast('Produkt jest obecnie niedostępny w katalogu głównym.', 'warning');
                        }
                    } else {
                        showToast('Ten produkt nie istnieje już w ofercie sklepu.', 'error');
                    }
                } catch (e) {
                    showToast('Nie znaleziono produktu w katalogu.', 'warning');
                }
            }
        }, 150);
    } catch (error) {
        showToast('Błąd pobierania produktów', 'error');
    }
}

// DOM Elements
const sections = {
    catalog: document.getElementById('catalog'),
    cart: document.getElementById('cart'),
    history: document.getElementById('history'),
    'admin-panel': document.getElementById('admin-panel')
};

// Navigation
function showSection(sectionId, triggerLoad = true) {
    Object.values(sections).forEach(sec => sec.classList.remove('active'));
    sections[sectionId].classList.add('active');

    if (triggerLoad) {
        if (sectionId === 'catalog') loadProducts();
        if (sectionId === 'cart') renderCart();
        if (sectionId === 'history' && currentUser) loadHistory();
        if (sectionId === 'admin-panel' && currentUser?.role === 'admin') loadAdminData();
    }
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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, role })
        });
        const user = await res.json();
        currentUser = user;

        document.getElementById('user-display').textContent = `${user.email} (${user.role})`;
        document.getElementById('nav-history').style.display = 'block';
        document.getElementById('checkout-btn').disabled = false;
        document.getElementById('checkout-btn').textContent = 'Złóż Zamówienie';

        if (user.role === 'admin') {
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
    const categoryId = document.getElementById('filter-category').value;
    
    let url = '/products/?';
    if (type) url += `type=${type}&`;
    if (categoryId) url += `category_id=${categoryId}&`;

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
        card.id = `product-card-${p.id}`;

        let priceHtml = '';
        if (p.discount_percentage > 0) {
            const newPrice = p.price * (1 - p.discount_percentage / 100);
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

        let breakdownBtn = '';
        if (p.type === 'bike' && p.components) {
            breakdownBtn = `<button onclick="openBreakdownModal('${p.id}')" style="width: 100%; margin-top: 5px; background: var(--success);" class="btn-success">🔧 Rozbij na części</button>`;
        }

        let specsHtml = Object.entries(p.specs || {}).map(([k, v]) => `<div><strong>${k}:</strong> ${v}</div>`).join('');

        card.innerHTML = `
            <label class="compare-label">
                <input type="checkbox" class="compare-checkbox" onchange="toggleCompare('${p.id}', this.checked)" ${isChecked}>
                <span>Porównaj</span>
            </label>
            <div style="text-transform: uppercase; font-size: 0.8rem; color: var(--text-muted); margin-top: 2rem;">${getCategoryName(p.category_id)}</div>
            <h3 style="margin-top: 0.2rem;">${p.brand} ${p.model}</h3>
            ${priceHtml}
            <div class="stock">Dostępność: ${p.stock} szt.</div>
            <div style="margin-bottom: 10px;">${compTags}</div>
            <div class="specs-mini" style="font-size:0.85rem; color: var(--text-muted); margin-bottom: 15px; border-top: 1px solid var(--border); padding-top: 10px;">
                ${specsHtml || '<em>Brak specyfikacji</em>'}
            </div>
            <button onclick="addToCart('${p.id}')" style="width: 100%;" class="btn-primary">Do koszyka</button>
            ${breakdownBtn}
        `;
        grid.appendChild(card);
    });
}

// Compare
function toggleCompare(id, isChecked) {
    if (isChecked) {
        if (compareList.length >= 3) {
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
    if (compareList.length === 0) {
        showToast('Wybierz przynajmniej jeden produkt do porównania', 'warning');
        return;
    }
    const grid = document.getElementById('compare-grid');
    grid.innerHTML = '';

    const selectedProducts = compareList.map(id => products.find(x => x.id === id)).filter(p => p);

    const allKeys = new Set();
    selectedProducts.forEach(p => {
        Object.keys(p.specs || {}).forEach(k => allKeys.add(k));
    });

    let tableHtml = `
        <table class="styled-table" style="width: 100%; text-align: left;">
            <thead>
                <tr>
                    <th>Parametr</th>
                    ${selectedProducts.map(p => `<th>${p.brand} ${p.model}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Cena</strong></td>
                    ${selectedProducts.map(p => `<td>${(p.price * (1 - (p.discount_percentage || 0) / 100)).toFixed(2)} PLN ${p.discount_percentage > 0 ? `<br><small style="text-decoration:line-through;color:var(--text-muted);">${p.price.toFixed(2)} PLN (-${p.discount_percentage}%)</small>` : ''}</td>`).join('')}
                </tr>
                <tr>
                    <td><strong>Kategoria</strong></td>
                    ${selectedProducts.map(p => `<td>${getCategoryName(p.category_id)}</td>`).join('')}
                </tr>
                <tr>
                    <td><strong>Kompatybilność</strong></td>
                    ${selectedProducts.map(p => `<td>${p.compatibility_tags.map(t => `<span class="tag compat-tag" style="margin:2px;">${t}</span>`).join('') || 'Brak'}</td>`).join('')}
                </tr>
    `;

    Array.from(allKeys).forEach(key => {
        tableHtml += `
            <tr>
                <td><strong>${key}</strong></td>
                ${selectedProducts.map(p => `<td>${p.specs && p.specs[key] !== undefined ? p.specs[key] : '-'}</td>`).join('')}
            </tr>
        `;
    });

    tableHtml += `
            </tbody>
        </table>
    `;

    grid.innerHTML = tableHtml;
    document.getElementById('compare-modal').classList.add('show');
}
function closeCompareModal() { document.getElementById('compare-modal').classList.remove('show'); }

// Breakdown Modal Functions
function closeBreakdownModal() {
    document.getElementById('breakdown-modal').classList.remove('show');
}

async function openBreakdownModal(bikeId) {
    const bike = products.find(x => x.id === bikeId);
    if (!bike) return;

    document.getElementById('breakdown-title').textContent = `${bike.brand} ${bike.model}`;
    const list = document.getElementById('breakdown-list');
    list.innerHTML = '<p>Ładowanie komponentów...</p>';

    document.getElementById('breakdown-modal').classList.add('show');

    const componentIds = Object.values(bike.components || {});
    const loadedComponents = [];

    for (const compId of componentIds) {
        try {
            let p = products.find(x => x.id === compId);
            if (!p) {
                const res = await fetch(`/products/?include_inactive=true`);
                const allProds = await res.json();
                p = allProds.find(x => x.id === compId);
                if (p) {
                    products.push(p);
                }
            }
            if (p) loadedComponents.push(p);
        } catch (e) {
            console.error('Błąd pobierania komponentu', compId, e);
        }
    }

    list.innerHTML = '';
    if (loadedComponents.length === 0) {
        list.innerHTML = '<p>Brak dostępnych komponentów dla tego roweru.</p>';
        return;
    }

    loadedComponents.forEach(c => {
        const finalPrice = c.price * (1 - (c.discount_percentage || 0) / 100);
        const specsText = Object.entries(c.specs || {}).map(([k, v]) => `${k}: ${v}`).join(', ');
        const compTags = c.compatibility_tags.map(t => `<span class="tag compat-tag" style="font-size:0.7rem; padding: 1px 4px;">${t}</span>`).join('');

        list.innerHTML += `
            <div class="cart-item" style="display:flex; justify-content:space-between; align-items:center; padding:10px; background:var(--bg-dark); border-radius:8px;">
                <div>
                    <span style="font-size:0.75rem; text-transform:uppercase; color:var(--primary); font-weight:600;">${getCategoryName(c.category_id)}</span>
                    <h4 style="margin: 2px 0;">${c.brand} ${c.model}</h4>
                    <small style="color:var(--text-muted);">${specsText}</small>
                    <div style="margin-top:4px;">${compTags}</div>
                </div>
                <div style="text-align:right;">
                    <strong style="color:var(--success);">${finalPrice.toFixed(2)} PLN</strong>
                    ${c.discount_percentage > 0 ? `<br><small style="text-decoration:line-through; font-size:0.8rem; color:var(--text-muted);">${c.price.toFixed(2)} PLN</small>` : ''}
                    <br><button onclick="addToCart('${c.id}'); closeBreakdownModal();" class="btn-primary" style="padding: 4px 8px; font-size:0.8rem; margin-top:5px;">Dodaj tę część</button>
                </div>
            </div>
        `;
    });

    const buyAllBtn = document.getElementById('btn-add-all-components');
    buyAllBtn.onclick = () => {
        loadedComponents.forEach(c => {
            addToCart(c.id);
        });
        closeBreakdownModal();
        showToast('Wszystkie komponenty dodane do koszyka!', 'success');
        showSection('cart');
    };
}

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
            price_at_purchase: p.price * (1 - p.discount_percentage / 100),
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
    if (cart.length < 2) {
        document.getElementById('compatibility-warnings').style.display = 'none';
        return;
    }
    try {
        const res = await fetch('/carts/check-compatibility', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_ids: cart.map(i => i.product_id) })
        });
        const data = await res.json();
        const box = document.getElementById('compatibility-warnings');
        if (data.warnings.length > 0) {
            box.style.display = 'block';
            box.innerHTML = `<strong>Zagrożenie Kompatybilności:</strong><ul>` +
                data.warnings.map(w => `<li>${w}</li>`).join('') + `</ul>`;
        } else {
            box.style.display = 'none';
        }
    } catch (err) {
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
    if (!currentUser) { showToast('Musisz być zalogowany by zapisać', 'error'); return; }
    if (cart.length === 0) { showToast('Koszyk pusty', 'warning'); return; }

    try {
        const res = await fetch('/carts/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_email: currentUser.email,
                name: `Koszyk z ${new Date().toLocaleDateString()}`,
                items: cart.map(i => ({ 
                    product_id: i.product_id, 
                    brand: i.brand,
                    model: i.model,
                    price_at_purchase: i.price_at_purchase,
                    quantity: i.quantity 
                }))
            })
        });
        const data = await res.json();
        showToast('Skopiuj to ID koszyka: ' + data.cart_id, 'success');
        prompt("ID Koszyka - zapisz by wczytać później:", data.cart_id);
    } catch (err) { showToast('Błąd zapisu', 'error'); }
}

async function loadCart() {
    const id = document.getElementById('load-cart-id').value;
    if (!id) return;
    try {
        const res = await fetch(`/carts/${id}`);
        if (!res.ok) throw new Error();
        const data = await res.json();

        // Musimy pobrać pełne dane produktów, bo koszyk w bazie ma tylko id i quantity
        cart = [];
        data.items.forEach(i => {
            cart.push({
                product_id: i.product_id,
                brand: i.brand,
                model: i.model,
                price_at_purchase: i.price_at_purchase,
                quantity: i.quantity
            });
        });
        updateCartCount();
        renderCart();
        showToast('Koszyk wczytany');
    } catch (err) { showToast('Nie znaleziono koszyka', 'error'); }
}

async function placeOrder(e) {
    e.preventDefault();
    if (!currentUser) return;
    if (cart.length === 0) return;

    const total = cart.reduce((s, i) => s + (i.price_at_purchase * i.quantity), 0);
    try {
        const res = await fetch('/orders/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                customer_email: currentUser.email,
                items: cart,
                total_price: total
            })
        });
        if (res.ok) {
            showToast('Zamówienie w drodze!', 'success');
            cart = []; updateCartCount(); renderCart();
        } else {
            const data = await res.json();
            showToast(data.detail, 'error');
        }
    } catch (err) { showToast('Błąd sieci', 'error'); }
}

// History
async function loadHistory() {
    try {
        const res = await fetch(`/users/${currentUser.email}/history`);
        const data = await res.json();
        const list = document.getElementById('history-list');
        list.innerHTML = '';
        data.forEach(order => {
            const itemsHtml = order.items.map(i => `
                <li>
                    <a href="javascript:void(0)" onclick="highlightProductInCatalog('${i.product_id}')" style="color: var(--primary); text-decoration: underline; cursor: pointer; font-weight: 500;">
                        ${i.brand} ${i.model}
                    </a>
                    - ${i.quantity}szt. @ ${(i.price_at_purchase).toFixed(2)} PLN
                </li>
            `).join('');
            list.innerHTML += `
                <div class="cart-item" style="flex-direction: column; align-items: flex-start; gap: 10px;">
                    <div><strong>Data:</strong> ${new Date(order.created_at).toLocaleString()} | <strong>Suma:</strong> ${order.total_price.toFixed(2)} PLN</div>
                    <ul style="margin-left: 20px; color: var(--text-muted); font-size: 0.9rem;">${itemsHtml}</ul>
                </div>
            `;
        });
    } catch (err) { showToast('Błąd pobierania historii', 'error'); }
}

// Admin
async function addProduct(e) {
    e.preventDefault();
    const type = document.getElementById('add-type').value;
    const cat = document.getElementById('add-category').value;
    const tagsRaw = document.getElementById('add-compat-tags').value;
    const compatTags = tagsRaw.split(',').map(t => t.trim()).filter(t => t);

    let specs = {};
    try {
        const specsRaw = document.getElementById('add-specs').value;
        if (specsRaw.trim()) {
            specs = JSON.parse(specsRaw);
        }
    } catch (err) {
        showToast('Niepoprawny format JSON w specyfikacji', 'error');
        return;
    }

    const price = parseFloat(document.getElementById('add-price').value);
    const prod = {
        type: type,
        category_id: cat,
        brand: document.getElementById('add-brand').value,
        model: document.getElementById('add-model').value,
        price: price,
        cost_price: price * 0.6, // Ustawiamy 60% ceny detalicznej jako koszt hurtowy dla nowych produktów
        stock: parseInt(document.getElementById('add-stock').value),
        compatibility_tags: compatTags,
        specs: specs
    };

    try {
        const res = await fetch('/products/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(prod)
        });
        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.detail || 'Błąd serwera');
        }
        showToast('Produkt dodany', 'success');
        document.getElementById('add-product-form').reset();
        loadAdminData();
    } catch (err) { showToast('Błąd zapisu: ' + err.message, 'error'); }
}

async function loadAdminData() {
    // 1. Raport sprzedaży z filtrami dat
    try {
        const start = document.getElementById('report-start-date').value;
        const end = document.getElementById('report-end-date').value;
        let url = '/admin/reports/sales?';
        if (start) url += `start_date=${start}&`;
        if (end) url += `end_date=${end}&`;

        const res = await fetch(url);
        const data = await res.json();
        const tbody = document.getElementById('reports-body');
        tbody.innerHTML = '';

        let sumRevenue = 0;
        let sumCost = 0;
        let sumProfit = 0;

        data.forEach(r => {
            const profit = r.total_revenue - r.total_cost;
            sumRevenue += r.total_revenue;
            sumCost += r.total_cost;
            sumProfit += profit;

            tbody.innerHTML += `
                <tr>
                    <td>${r.brand}</td>
                    <td>${r.total_sold_units}</td>
                    <td>${r.total_revenue.toFixed(2)} PLN</td>
                    <td>${r.total_cost.toFixed(2)} PLN</td>
                    <td style="color: ${profit >= 0 ? 'var(--success)' : 'var(--danger)'}; font-weight:800;">${profit.toFixed(2)} PLN</td>
                </tr>
            `;
        });

        document.getElementById('sum-revenue').textContent = sumRevenue.toFixed(2) + ' PLN';
        document.getElementById('sum-cost').textContent = sumCost.toFixed(2) + ' PLN';
        document.getElementById('sum-profit').textContent = sumProfit.toFixed(2) + ' PLN';
    } catch (err) { console.error('Błąd pobierania raportów:', err); }

    // 2. Zarządzanie produktami + przycisk "Edytuj"
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
                        <input type="number" min="0" max="100" value="${p.discount_percentage}" style="width:50px; padding:2px; margin:0;" id="disc-${p.id}">
                        <button onclick="setDisc('${p.id}')" class="btn-success" style="padding:2px 5px; font-size:0.8rem;">%</button>
                    </td>
                    <td>
                        <button onclick="openEditModal('${p.id}')" class="btn-primary" style="padding:2px 8px; font-size:0.8rem; background:var(--primary);">Edytuj</button>
                    </td>
                </tr>
            `;
        });
    } catch (err) { console.error('Błąd pobierania produktów:', err); }

    // 3. Zarządzanie zamówieniami i statusami
    try {
        const res = await fetch('/admin/orders');
        const orders = await res.json();
        const tbody = document.getElementById('admin-orders-body');
        tbody.innerHTML = '';

        orders.forEach(o => {
            const dateStr = new Date(o.created_at).toLocaleString('pl-PL');
            const itemsSummary = o.items.map(i => `${i.brand} ${i.model} (${i.quantity}szt)`).join(', ');

            const selectedPaid = o.status === 'opłacone' ? 'selected' : '';
            const selectedShipped = o.status === 'wysłane' ? 'selected' : '';
            const selectedDelivered = o.status === 'dostarczone' ? 'selected' : '';

            let statusStyle = 'color: var(--primary); font-weight: bold;';
            if (o.status === 'wysłane') statusStyle = 'color: var(--warning); font-weight: bold;';
            if (o.status === 'dostarczone') statusStyle = 'color: var(--success); font-weight: bold;';

            tbody.innerHTML += `
                <tr>
                    <td><small style="font-family: monospace;">${o.id.substring(0, 8)}...</small></td>
                    <td>${o.customer_email}</td>
                    <td><small>${dateStr}</small></td>
                    <td><small>${itemsSummary}</small></td>
                    <td><strong>${o.total_price.toFixed(2)} PLN</strong></td>
                    <td><span style="${statusStyle}">${o.status}</span></td>
                    <td>
                        <select onchange="changeOrderStatus('${o.id}', this.value)" class="select-input" style="width:auto; margin-top:0; padding:2px; height:28px; font-size:0.85rem;">
                            <option value="opłacone" ${selectedPaid}>Opłacone</option>
                            <option value="wysłane" ${selectedShipped}>Wysłane</option>
                            <option value="dostarczone" ${selectedDelivered}>Dostarczone</option>
                        </select>
                    </td>
                </tr>
            `;
        });
    } catch (err) { console.error('Błąd pobierania zamówień:', err); }
}

function clearReportFilters() {
    document.getElementById('report-start-date').value = '';
    document.getElementById('report-end-date').value = '';
    loadAdminData();
}

async function toggleStatus(id, newStatus) {
    await fetch(`/products/${id}/status?is_active=${newStatus}`, { method: 'PUT' });
    loadAdminData();
    loadProducts();
}

async function setDisc(id) {
    const val = document.getElementById(`disc-${id}`).value;
    await fetch(`/products/${id}/promotion?discount_percentage=${val}`, { method: 'PUT' });
    showToast('Zniżka zaktualizowana', 'success');
    loadAdminData();
    loadProducts();
}

// Funkcje Edytora Produktów
function closeEditModal() {
    document.getElementById('edit-product-modal').classList.remove('show');
}

async function openEditModal(productId) {
    const res = await fetch('/products/?include_inactive=true');
    const allProds = await res.json();
    const p = allProds.find(x => x.id === productId);

    if (!p) {
        showToast('Nie znaleziono produktu o tym ID', 'error');
        return;
    }

    document.getElementById('edit-id').value = p.id;
    document.getElementById('edit-type').value = p.type;
    document.getElementById('edit-category').value = p.category_id;
    document.getElementById('edit-brand').value = p.brand;
    document.getElementById('edit-model').value = p.model;
    document.getElementById('edit-price').value = p.price;
    document.getElementById('edit-cost-price').value = p.cost_price || (p.price * 0.6);
    document.getElementById('edit-stock').value = p.stock;
    document.getElementById('edit-compat-tags').value = p.compatibility_tags.join(', ');
    document.getElementById('edit-specs').value = JSON.stringify(p.specs || {}, null, 2);

    document.getElementById('edit-product-modal').classList.add('show');
}

async function saveProductEdit(e) {
    e.preventDefault();
    const id = document.getElementById('edit-id').value;

    let specs = {};
    try {
        const specsRaw = document.getElementById('edit-specs').value;
        if (specsRaw.trim()) {
            specs = JSON.parse(specsRaw);
        }
    } catch (err) {
        showToast('Niepoprawny format JSON w specyfikacji', 'error');
        return;
    }

    const tagsRaw = document.getElementById('edit-compat-tags').value;
    const compatTags = tagsRaw.split(',').map(t => t.trim()).filter(t => t);

    // Pobieramy dane, by nie utracić komponentów lub statusu is_active
    const resGet = await fetch('/products/?include_inactive=true');
    const allProds = await resGet.json();
    const origProd = allProds.find(x => x.id === id);
    const origComponents = origProd ? origProd.components : null;

    const prod = {
        type: document.getElementById('edit-type').value,
        category_id: document.getElementById('edit-category').value,
        brand: document.getElementById('edit-brand').value,
        model: document.getElementById('edit-model').value,
        price: parseFloat(document.getElementById('edit-price').value),
        cost_price: parseFloat(document.getElementById('edit-cost-price').value),
        stock: parseInt(document.getElementById('edit-stock').value),
        compatibility_tags: compatTags,
        specs: specs,
        components: origComponents,
        is_active: origProd ? origProd.is_active : true,
        discount_percentage: origProd ? origProd.discount_percentage : 0
    };

    try {
        const res = await fetch(`/products/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(prod)
        });

        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.detail || 'Błąd zapisu');
        }

        showToast('Produkt pomyślnie zaktualizowany', 'success');
        closeEditModal();
        loadAdminData();
        loadProducts();
    } catch (err) {
        showToast('Błąd zapisu: ' + err.message, 'error');
    }
}

// Funkcje Zarządzania Statusami Zamówień
async function changeOrderStatus(orderId, newStatus) {
    try {
        const res = await fetch(`/admin/orders/${orderId}/status?status=${newStatus}`, {
            method: 'PUT'
        });

        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.detail || 'Błąd serwera');
        }

        showToast('Status zamówienia zaktualizowany', 'success');
        loadAdminData();
    } catch (err) {
        showToast('Błąd aktualizacji statusu: ' + err.message, 'error');
    }
}

// Init
window.onload = async () => {
    await loadCategories();
    await loadProducts();
};
