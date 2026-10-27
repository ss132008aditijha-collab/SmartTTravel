/**
 * SmartTravel - Food & Meal Selection JavaScript
 * Manages category filters, item quantity increments, dynamic cart totals, and skip/add actions.
 */

const cart = {
    veg_thali: { name: "Deluxe Veg Thali", price: 160, qty: 0 },
    chicken_biryani: { name: "Hyderabadi Chicken Biryani", price: 220, qty: 0 },
    paneer_meal: { name: "Paneer Butter Masala Box", price: 180, qty: 0 },
    snack_combo: { name: "Tea & Samosa Combo", price: 70, qty: 0 },
    south_breakfast: { name: "Idli & Vada Combo", price: 90, qty: 0 },
    mineral_water: { name: "Packaged Water (1L)", price: 20, qty: 0 }
};

document.addEventListener("DOMContentLoaded", () => {
    initFoodCategories();
    updateFoodTotal();
});

// Category filtering (All, Veg, Non-Veg, Snacks)
function initFoodCategories() {
    const tabs = document.querySelectorAll(".food-cat-btn");
    const cards = document.querySelectorAll(".food-card-item");

    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");

            const filter = tab.dataset.filter;
            cards.forEach(card => {
                if (filter === "all" || card.dataset.category === filter) {
                    card.style.display = "";
                } else {
                    card.style.display = "none";
                }
            });
        });
    });
}

// Quantity changes (+1 / -1)
window.changeFoodQty = function(itemKey, delta) {
    if (!cart[itemKey]) return;

    cart[itemKey].qty = Math.max(0, Math.min(10, cart[itemKey].qty + delta));

    const qtySpan = document.getElementById(`qty_${itemKey}`);
    if (qtySpan) {
        qtySpan.textContent = String(cart[itemKey].qty);
    }

    const card = document.getElementById(`card_${itemKey}`);
    if (card) {
        if (cart[itemKey].qty > 0) {
            card.classList.add("in-cart");
        } else {
            card.classList.remove("in-cart");
        }
    }

    updateFoodTotal();
};

function updateFoodTotal() {
    let subtotal = 0;
    let totalItems = 0;
    const itemsListContainer = document.getElementById("cartItemsSummary");

    if (itemsListContainer) {
        itemsListContainer.innerHTML = "";
    }

    for (const key in cart) {
        const item = cart[key];
        if (item.qty > 0) {
            const itemTotal = item.qty * item.price;
            subtotal += itemTotal;
            totalItems += item.qty;

            if (itemsListContainer) {
                const li = document.createElement("div");
                li.className = "cart-summary-line";
                li.innerHTML = `
                    <span>${item.name} × ${item.qty}</span>
                    <strong>₹${itemTotal}</strong>
                `;
                itemsListContainer.appendChild(li);
            }
        }
    }

    // Update displays
    const countDisplay = document.getElementById("cartTotalItems");
    const priceDisplay = document.getElementById("cartTotalPrice");
    const hiddenTotalInput = document.getElementById("hiddenFoodTotal");
    const proceedBtn = document.getElementById("proceedPaymentBtn");

    if (countDisplay) countDisplay.textContent = String(totalItems);
    if (priceDisplay) priceDisplay.textContent = `₹${subtotal.toFixed(2)}`;
    if (hiddenTotalInput) hiddenTotalInput.value = String(subtotal);

    if (proceedBtn) {
        if (subtotal > 0) {
            proceedBtn.innerHTML = `<span>Add Meals & Proceed to Payment (₹${subtotal})</span> <span class="arrow">→</span>`;
            proceedBtn.classList.add("btn-has-food");
        } else {
            proceedBtn.innerHTML = `<span>Proceed to Payment</span> <span class="arrow">→</span>`;
            proceedBtn.classList.remove("btn-has-food");
        }
    }
}

// Proceed to payment with chosen food total
// Proceed to payment with item quantities for server-side validation
window.proceedWithFood = function(skip = false) {
    const params = new URLSearchParams(window.location.search);

    const selectedFood = {};

    if (!skip) {
        for (const [key, item] of Object.entries(cart)) {
            if (item.qty > 0) {
                selectedFood[key] = item.qty;
            }
        }
    }

    // Quantities are sent for validation.
    // The backend must calculate prices independently.
    params.set("food_items", JSON.stringify(selectedFood));

    // Keep this for displaying the estimated amount in the UI.
    const estimatedFoodTotal = skip
        ? 0
        : Object.values(cart).reduce(
            (sum, item) => sum + item.price * item.qty,
            0
        );

    params.set("food_total", String(estimatedFoodTotal));

    window.location.href = `/payment?${params.toString()}`;
};
