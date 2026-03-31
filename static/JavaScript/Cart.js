/* ===========================
   CART STATE
=========================== */
let cart = {};

/* ===========================
   ADD TO CART
=========================== */
function addToCart(product_id) {
    fetch("/add-to-cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ product_id })
    })
    .then(res => {
        if (!res.ok) {
            if (res.status === 401) {
                if (typeof openAuthModal === 'function') {
                    openAuthModal('login');
                    showToast('Please sign in to add items to cart ☕');
                }
            }
            throw new Error("Failed to add item");
        }
        return res.json();
    })
    .then(() => {
        loadCart();
        const box = document.getElementById("cartBox");
        if (box) box.style.display = "block";
        showToast("Added to cart! ☕");
    })
    .catch(err => console.error(err));
}

/* ===========================
   CHANGE QTY
=========================== */
function changeQty(product_id, delta) {
    fetch("/update-cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ product_id, delta })
    })
    .then(res => res.json())
    .then(() => loadCart())
    .catch(err => console.error(err));
}

/* ===========================
   LOAD CART
=========================== */
function loadCart() {
    fetch("/get-cart", { credentials: "include" })
    .then(res => {
        if (!res.ok) {
            cart = {};
            renderCart();
            return null;
        }
        return res.json();
    })
    .then(data => {
        if (!data) return;
        cart = data.cart || {};
        renderCart();
    })
    .catch(err => console.error(err));
}

/* ===========================
   RENDER CART
=========================== */
function renderCart() {
    const cartItemsEl = document.getElementById("cartItems");
    const cartCountEl = document.getElementById("cartCount");
    if (!cartItemsEl) return;

    let totalQty   = 0;
    let totalPrice = 0;
    let html       = "";

    for (let id in cart) {
        totalQty   += cart[id].qty;
        totalPrice += cart[id].qty * cart[id].price;
        html += `
        <div class="cart-line">
            <div class="cart-line-info">
                <div class="cart-item-name">${cart[id].name}</div>
                <div class="cart-item-price">₹${cart[id].price} each</div>
            </div>
            <div class="cart-qty">
                <button onclick="changeQty(${cart[id].product_id}, -1)">&#8722;</button>
                <span>${cart[id].qty}</span>
                <button onclick="changeQty(${cart[id].product_id}, 1)">+</button>
            </div>
        </div>`;
    }

    if (totalQty > 0) {
        html += `
        <div class="cart-total-row">
            <span>Total</span>
            <span>&#8377;${totalPrice}</span>
        </div>
        <button class="checkout-btn" onclick="goToPayment()">Checkout &#8594;</button>`;
    }

    cartItemsEl.innerHTML = html || `<div class="cart-empty">Your cart is empty &#9749;</div>`;
    if (cartCountEl) cartCountEl.innerText = totalQty;
}

/* ===========================
   TOGGLE CART
=========================== */
function toggleCart() {
    const box = document.getElementById("cartBox");
    if (!box) return;
    box.style.display = box.style.display === "block" ? "none" : "block";
}

/* ===========================
   GO TO PAYMENT
=========================== */
function goToPayment() {
    if (typeof isLoggedIn !== 'undefined' && !isLoggedIn) {
        if (typeof openAuthModal === 'function') openAuthModal('login');
        showToast('Please sign in to checkout &#9749;');
        return;
    }
    window.location.href = "/payment";
}

/* ===========================
   TOAST
=========================== */
function showToast(msg) {
    const t = document.getElementById("toast");
    if (!t) return;
    t.textContent = msg;
    t.classList.add("show");
    setTimeout(() => t.classList.remove("show"), 2500);
}

/* ===========================
   INIT
=========================== */
document.addEventListener("DOMContentLoaded", () => {
    document.addEventListener("click", e => {
        const wrapper = document.querySelector(".cart-wrapper");
        if (wrapper && !wrapper.contains(e.target)) {
            const box = document.getElementById("cartBox");
            if (box) box.style.display = "none";
        }
    });
});
