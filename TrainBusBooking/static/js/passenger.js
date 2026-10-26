/**
 * SmartTravel - Passenger Details Validation JavaScript
 * Validates passenger names, age, gender, phone number, and email.
 * Supports multiple passenger cards for co-travellers.
 */

let coPassengerCount = 0;

document.addEventListener("DOMContentLoaded", () => {
    initPassengerValidation();
    initMultiPassengerAutoDetection();
    initAddCoPassengerButton();
});

// Detect multiple seats from URL (e.g. seat=A1, A2) and auto-render forms
function initMultiPassengerAutoDetection() {
    const params = new URLSearchParams(window.location.search);
    const seatParam = params.get("seat") || "";
    const seatList = seatParam.split(",").map(s => s.trim()).filter(Boolean);

    // If more than 1 seat is present, add forms for seats 2, 3, etc.
    if (seatList.length > 1) {
        for (let i = 1; i < seatList.length; i++) {
            addCoPassengerCard(seatList[i]);
        }
    }
}

function initAddCoPassengerButton() {
    const addBtn = document.getElementById("addCoPassengerBtn");
    if (!addBtn) return;

    addBtn.addEventListener("click", () => {
        addCoPassengerCard();
        if (window.showToast) window.showToast("Added co-passenger form card", "info", 1500);
    });
}

function addCoPassengerCard(seatNumber = "") {
    coPassengerCount++;
    const container = document.getElementById("coPassengersContainer");
    if (!container) return;

    const card = document.createElement("div");
    card.id = `coPass_${coPassengerCount}`;
    card.className = "co-passenger-block";
    card.style.cssText = "background: var(--surface-subtle); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 18px; margin-bottom: 14px;";

    const seatBadge = seatNumber ? `<span class="route-meta-pill" style="background: var(--primary-subtle); color: var(--primary);">Seat ${seatNumber}</span>` : "";

    card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <strong style="font-size: 15px;">Passenger ${coPassengerCount + 1} (Co-Traveller)</strong>
                ${seatBadge}
            </div>
            <button type="button" onclick="document.getElementById('coPass_${coPassengerCount}')?.remove();" style="background: none; border: none; color: var(--danger); font-size: 13px; font-weight: 700; cursor: pointer;">
                ✕ Remove
            </button>
        </div>
        <div class="form-grid-2">
            <div class="form-group" style="grid-column: span 2; margin-bottom: 12px;">
                <label style="font-size: 12px; font-weight: 700;">Full Name *</label>
                <input type="text" class="form-control co-passenger-name" placeholder="Co-passenger name" required>
            </div>
            <div class="form-group" style="margin-bottom: 0;">
                <label style="font-size: 12px; font-weight: 700;">Age *</label>
                <input type="number" class="form-control co-passenger-age" placeholder="Age" min="1" max="120" value="26" required>
            </div>
            <div class="form-group" style="margin-bottom: 0;">
                <label style="font-size: 12px; font-weight: 700;">Gender *</label>
                <select class="form-control co-passenger-gender">
                    <option value="Female">Female</option>
                    <option value="Male" selected>Male</option>
                    <option value="Other">Other</option>
                </select>
            </div>
        </div>
    `;

    container.appendChild(card);
}

function initPassengerValidation() {
    const form = document.getElementById("passengerForm");
    if (!form) return;

    const phoneInput = form.querySelector('input[name="phone"]');
    const ageInput = form.querySelector('input[name="age"]');

    if (phoneInput) {
        phoneInput.addEventListener("input", () => {
            phoneInput.value = phoneInput.value.replace(/[^0-9]/g, "").slice(0, 10);
        });
    }

    if (ageInput) {
        ageInput.addEventListener("input", () => {
            ageInput.value = ageInput.value.replace(/[^0-9]/g, "").slice(0, 3);
        });
    }

    form.addEventListener("submit", (e) => {
        const primaryNameInput = form.querySelector('input[name="passenger_name"]');
        const primaryName = (primaryNameInput?.value || "").trim();
        const age = parseInt(form.querySelector('input[name="age"]')?.value || "0", 10);
        const gender = form.querySelector('input[name="gender"]:checked')?.value || form.querySelector('select[name="gender"]')?.value;
        const phone = (phoneInput?.value || "").trim();
        const email = (form.querySelector('input[name="email"]')?.value || "").trim();

        if (!primaryName || primaryName.length < 3) {
            e.preventDefault();
            if (window.showToast) window.showToast("Please enter a valid primary passenger full name.", "warning");
            return;
        }

        if (isNaN(age) || age < 1 || age > 120) {
            e.preventDefault();
            if (window.showToast) window.showToast("Please enter a valid age between 1 and 120.", "warning");
            return;
        }

        if (!gender) {
            e.preventDefault();
            if (window.showToast) window.showToast("Please select passenger gender.", "warning");
            return;
        }

        const phoneRegex = /^\d{10}$/;
        if (!phoneRegex.test(phone)) {
            e.preventDefault();
            if (window.showToast) window.showToast("Please enter a valid 10-digit mobile number.", "warning");
            return;
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            e.preventDefault();
            if (window.showToast) window.showToast("Please enter a valid email address.", "warning");
            return;
        }

        // Validate any co-passenger cards
        const coNames = Array.from(form.querySelectorAll(".co-passenger-name"));
        for (const coInput of coNames) {
            if (!coInput.value.trim() || coInput.value.trim().length < 3) {
                e.preventDefault();
                if (window.showToast) window.showToast("Please enter full names for all co-passengers.", "warning");
                coInput.focus();
                return;
            }
        }

        // If co-passengers are present, combine names for the booking flow
        if (coNames.length > 0 && primaryNameInput) {
            const allNames = [primaryName, ...coNames.map(c => c.value.trim())];
            primaryNameInput.value = allNames.join(", ");
        }
    });
}
