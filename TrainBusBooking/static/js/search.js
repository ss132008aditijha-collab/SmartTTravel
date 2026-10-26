/**
 * SmartTravel - Search Page & Widget JavaScript
 * Handles transport switching, city swapping, date controls, and search validation.
 */

document.addEventListener("DOMContentLoaded", () => {
    initSearchDate();
    initQuickDateButtons();
});

// Switch Between Train and Bus Modes
window.selectTransport = function(type) {
    const input = document.getElementById("transport");
    const trainTab = document.getElementById("trainTab");
    const busTab = document.getElementById("busTab");
    const searchBtn = document.getElementById("searchSubmitBtn");

    if (input) input.value = type;

    if (type === "train") {
        if (trainTab) trainTab.classList.add("active");
        if (busTab) busTab.classList.remove("active");
        if (searchBtn) searchBtn.innerHTML = `<span>Search Trains</span> <span class="arrow">→</span>`;
    } else {
        if (busTab) busTab.classList.add("active");
        if (trainTab) trainTab.classList.remove("active");
        if (searchBtn) searchBtn.innerHTML = `<span>Search Buses</span> <span class="arrow">→</span>`;
    }
};

// Swap Source and Destination with visual flip animation
window.swapLocations = function() {
    const fromInput = document.getElementById("source") || document.querySelector('input[name="source"]');
    const toInput = document.getElementById("destination") || document.querySelector('input[name="destination"]');
    const swapBtn = document.querySelector(".swap-btn");

    if (!fromInput || !toInput) return;

    if (swapBtn) {
        swapBtn.classList.add("rotating");
        setTimeout(() => swapBtn.classList.remove("rotating"), 300);
    }

    const temp = fromInput.value;
    fromInput.value = toInput.value;
    toInput.value = temp;

    if (window.showToast) {
        window.showToast("Cities swapped!", "info", 1500);
    }
};

// Quick Route Select from popular routes section
window.setRoute = function(source, destination, transportType = null) {
    const fromInput = document.getElementById("source") || document.querySelector('input[name="source"]');
    const toInput = document.getElementById("destination") || document.querySelector('input[name="destination"]');

    if (fromInput) fromInput.value = source;
    if (toInput) toInput.value = destination;

    if (transportType && window.selectTransport) {
        window.selectTransport(transportType);
    }

    const searchCard = document.querySelector(".search-card") || fromInput;
    if (searchCard) {
        searchCard.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    if (fromInput) fromInput.focus();

    if (window.showToast) {
        window.showToast(`Selected route: ${source} → ${destination}`, "success", 2000);
    }
};

// Set Minimum Date to Today
function initSearchDate() {
    const dateInput = document.getElementById("journeyDate");
    if (!dateInput) return;

    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, "0");
    const dd = String(today.getDate()).padStart(2, "0");
    const minDate = `${yyyy}-${mm}-${dd}`;

    dateInput.min = minDate;
    if (!dateInput.value) {
        dateInput.value = minDate;
    }
}

// Quick Date Buttons: Today, Tomorrow
function initQuickDateButtons() {
    const todayBtn = document.getElementById("quickTodayBtn");
    const tomorrowBtn = document.getElementById("quickTomorrowBtn");
    const dateInput = document.getElementById("journeyDate");

    if (!dateInput) return;

    const formatDate = (date) => {
        const yyyy = date.getFullYear();
        const mm = String(date.getMonth() + 1).padStart(2, "0");
        const dd = String(date.getDate()).padStart(2, "0");
        return `${yyyy}-${mm}-${dd}`;
    };

    if (todayBtn) {
        todayBtn.addEventListener("click", () => {
            dateInput.value = formatDate(new Date());
            highlightQuickDate(todayBtn, tomorrowBtn);
        });
    }

    if (tomorrowBtn) {
        tomorrowBtn.addEventListener("click", () => {
            const tmrw = new Date();
            tmrw.setDate(tmrw.getDate() + 1);
            dateInput.value = formatDate(tmrw);
            highlightQuickDate(tomorrowBtn, todayBtn);
        });
    }

    dateInput.addEventListener("change", () => {
        const todayStr = formatDate(new Date());
        const tmrw = new Date();
        tmrw.setDate(tmrw.getDate() + 1);
        const tmrwStr = formatDate(tmrw);

        if (dateInput.value === todayStr) {
            highlightQuickDate(todayBtn, tomorrowBtn);
        } else if (dateInput.value === tmrwStr) {
            highlightQuickDate(tomorrowBtn, todayBtn);
        } else {
            if (todayBtn) todayBtn.classList.remove("active");
            if (tomorrowBtn) tomorrowBtn.classList.remove("active");
        }
    });
}

function highlightQuickDate(activeBtn, inactiveBtn) {
    if (activeBtn) activeBtn.classList.add("active");
    if (inactiveBtn) inactiveBtn.classList.remove("active");
}

// Search Validation before form submission
window.validateSearch = function() {
    const fromInput = document.getElementById("source") || document.querySelector('input[name="source"]');
    const toInput = document.getElementById("destination") || document.querySelector('input[name="destination"]');
    const dateInput = document.getElementById("journeyDate");

    if (!fromInput || !toInput) return true;

    const fromVal = fromInput.value.trim();
    const toVal = toInput.value.trim();

    if (!fromVal || !toVal) {
        if (window.showToast) {
            window.showToast("Please enter both departure and destination cities.", "warning");
        } else {
            alert("Please enter both departure and destination cities.");
        }
        return false;
    }

    if (fromVal.toLowerCase() === toVal.toLowerCase()) {
        if (window.showToast) {
            window.showToast("Departure and destination cities cannot be identical.", "warning");
        } else {
            alert("Departure and destination cities cannot be identical.");
        }
        return false;
    }

    if (dateInput && dateInput.value && dateInput.min && dateInput.value < dateInput.min) {
        if (window.showToast) {
            window.showToast("Journey date cannot be in the past.", "warning");
        } else {
            alert("Journey date cannot be in the past.");
        }
        return false;
    }

    return true;
};
