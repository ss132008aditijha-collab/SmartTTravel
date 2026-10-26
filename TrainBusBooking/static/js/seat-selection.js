/**
 * SmartTravel - Interactive Seat Selection JavaScript
 * Supports both Train berths/coach layout and Bus 2x2 / 2x1 sleeper layouts.
 * Computes price dynamically and prevents choosing booked seats.
 */

let selectedSeatsList = [];
let baseTicketPrice = 0;

document.addEventListener("DOMContentLoaded", () => {
    initSeatSelection();
});

function initSeatSelection() {
    const seatContainer = document.querySelector(".seat-layout");
    if (!seatContainer) return;

    // Read base price from data attribute or hidden input
    const priceEl = document.getElementById("basePriceVal");
    if (priceEl) {
        baseTicketPrice = parseFloat(priceEl.value || priceEl.textContent || "0");
    }

    // Attach click handlers to all available seats
    const allSeats = seatContainer.querySelectorAll(".seat-item");
    allSeats.forEach(seatBtn => {
        if (seatBtn.classList.contains("occupied") || seatBtn.classList.contains("booked")) {
            seatBtn.setAttribute("disabled", "true");
            seatBtn.setAttribute("aria-disabled", "true");
            seatBtn.title = "Seat already booked";
            return;
        }

        seatBtn.addEventListener("click", () => {
            const seatNo = seatBtn.dataset.seat || seatBtn.textContent.trim();
            const seatType = seatBtn.dataset.type || "Standard";

            toggleSeat(seatBtn, seatNo, seatType);
        });
    });
}

function toggleSeat(btn, seatNumber, seatType) {
    const isSelected = btn.classList.contains("selected");

    if (isSelected) {
        // Deselect
        btn.classList.remove("selected");
        selectedSeatsList = selectedSeatsList.filter(s => s.number !== seatNumber);
    } else {
        // For single-passenger selection or multi-passenger
        // If max is 1 (standard single ticket flow)
        const maxSeatsAllowed = parseInt(document.getElementById("maxSeatsLimit")?.value || "1", 10);

        if (maxSeatsAllowed === 1) {
            // Deselect any previous
            document.querySelectorAll(".seat-item.selected").forEach(s => s.classList.remove("selected"));
            selectedSeatsList = [];
        } else if (selectedSeatsList.length >= maxSeatsAllowed) {
            if (window.showToast) {
                window.showToast(`You can select a maximum of ${maxSeatsAllowed} seat(s).`, "warning");
            }
            return;
        }

        btn.classList.add("selected");
        selectedSeatsList.push({ number: seatNumber, type: seatType });
    }

    updateSeatSummary();
}

function updateSeatSummary() {
    const displayBadge = document.getElementById("selectedSeatDisplay");
    const countDisplay = document.getElementById("selectedSeatCount");
    const priceDisplay = document.getElementById("totalSeatPriceDisplay");
    const continueBtn = document.getElementById("continueToPassengerBtn");

    const typeDisplay = document.getElementById("selectedSeatTypeDisplay");

    if (selectedSeatsList.length === 0) {
        if (displayBadge) displayBadge.textContent = "None Selected";
        if (typeDisplay) typeDisplay.textContent = "—";
        if (countDisplay) countDisplay.textContent = "0";
        if (priceDisplay) priceDisplay.textContent = "₹0";
        if (continueBtn) continueBtn.classList.add("btn-disabled");
    } else {
        const seatNumbers = selectedSeatsList.map(s => s.number).join(", ");
        const seatTypes = selectedSeatsList.map(s => s.type).join(", ");
        const totalPrice = selectedSeatsList.length * baseTicketPrice;

        if (displayBadge) displayBadge.textContent = seatNumbers;
        if (typeDisplay) typeDisplay.textContent = seatTypes;
        if (countDisplay) countDisplay.textContent = String(selectedSeatsList.length);
        if (priceDisplay) priceDisplay.textContent = `₹${totalPrice.toFixed(2)}`;
        if (continueBtn) continueBtn.classList.remove("btn-disabled");
    }
}

// Continue to passenger details
window.continueToPassenger = function() {
    if (selectedSeatsList.length === 0) {
        if (window.showToast) {
            window.showToast("Please choose an available seat on the layout to proceed.", "warning");
        } else {
            alert("Please choose a seat first.");
        }
        return;
    }

    const firstSeat = selectedSeatsList.map(s => s.number).join(",");
    const params = new URLSearchParams(window.location.search);
    params.set("seat", firstSeat);

    window.location.href = `/passenger-details?${params.toString()}`;
};
