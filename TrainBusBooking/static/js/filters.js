/**
 * SmartTravel - Search Results Filtering & Sorting JavaScript
 * Provides real-time client-side sorting and filtering for train and bus cards,
 * including AC / Non-AC selection, departure time slots, price slider, and classes.
 */

document.addEventListener("DOMContentLoaded", () => {
    initSearchResultsFilter();
});

function initSearchResultsFilter() {
    const container = document.getElementById("resultsCardsList");
    if (!container) return;

    const cards = Array.from(container.querySelectorAll(".transport-card"));
    const countDisplay = document.getElementById("resultsCountBadge");
    const sortSelect = document.getElementById("sortBySelect");
    const priceSlider = document.getElementById("priceFilterSlider");
    const priceValueDisplay = document.getElementById("priceSliderValue");
    const acCheckboxes = document.querySelectorAll('input[name="acFilter"]');
    const departureTimeCheckboxes = document.querySelectorAll('input[name="departureTimeFilter"]');
    const classCheckboxes = document.querySelectorAll('input[name="classFilter"]');
    const availableOnlyCheckbox = document.getElementById("availableOnlyFilter");
    const resetBtn = document.getElementById("resetFiltersBtn");

    // Initialize Max Price from cards
    let maxPriceFound = 0;
    cards.forEach(card => {
        const p = parseFloat(card.dataset.price || "0");
        if (p > maxPriceFound) maxPriceFound = p;
    });

    if (priceSlider && maxPriceFound > 0) {
        priceSlider.max = String(Math.max(3000, Math.ceil(maxPriceFound / 100) * 100));
        priceSlider.value = priceSlider.max;
        if (priceValueDisplay) priceValueDisplay.textContent = `₹${priceSlider.value}`;
    }

    function applyFilters() {
        const maxPrice = priceSlider ? parseFloat(priceSlider.value) : Infinity;
        const availableOnly = availableOnlyCheckbox ? availableOnlyCheckbox.checked : false;

        // Selected AC Filters
        const selectedAc = [];
        acCheckboxes.forEach(cb => {
            if (cb.checked) selectedAc.push(cb.value);
        });

        // Selected Departure Time Slots
        const selectedTimes = [];
        departureTimeCheckboxes.forEach(cb => {
            if (cb.checked) selectedTimes.push(cb.value);
        });

        // Selected Classes
        const selectedClasses = [];
        classCheckboxes.forEach(cb => {
            if (cb.checked) selectedClasses.push(cb.value.toLowerCase());
        });

        let visibleCount = 0;

        cards.forEach(card => {
            const price = parseFloat(card.dataset.price || "0");
            const seats = parseInt(card.dataset.seats || "0", 10);
            const depHour = parseInt((card.dataset.departure || "00:00").split(":")[0], 10);
            const cardClass = (card.dataset.class || "").toLowerCase();
            const hasAc = card.dataset.hasAc === "1";
            const hasNonac = card.dataset.hasNonac === "1";

            let matchPrice = price <= maxPrice;
            let matchSeats = !availableOnly || seats > 0;

            // AC match
            let matchAc = selectedAc.length === 0;
            if (selectedAc.length > 0) {
                if (selectedAc.includes("ac") && hasAc) matchAc = true;
                if (selectedAc.includes("nonac") && hasNonac) matchAc = true;
            }

            // Time match
            let matchTime = selectedTimes.length === 0;
            if (selectedTimes.length > 0) {
                if (selectedTimes.includes("morning") && depHour >= 6 && depHour < 12) matchTime = true;
                if (selectedTimes.includes("afternoon") && depHour >= 12 && depHour < 18) matchTime = true;
                if (selectedTimes.includes("evening") && depHour >= 18 && depHour < 24) matchTime = true;
                if (selectedTimes.includes("night") && depHour >= 0 && depHour < 6) matchTime = true;
            }

            // Class match
            let matchClass = selectedClasses.length === 0;
            if (selectedClasses.length > 0) {
                matchClass = selectedClasses.some(cls => cardClass.includes(cls));
            }

            if (matchPrice && matchSeats && matchAc && matchTime && matchClass) {
                card.style.display = "";
                visibleCount++;
            } else {
                card.style.display = "none";
            }
        });

        // Update count
        if (countDisplay) {
            countDisplay.textContent = `${visibleCount} Options Available`;
        }

        // Toggle No Results Message
        const noFilterMatch = document.getElementById("noFilterMatchesBox");
        if (noFilterMatch) {
            noFilterMatch.style.display = visibleCount === 0 && cards.length > 0 ? "block" : "none";
        }
    }

    function applySorting() {
        if (!sortSelect) return;
        const sortValue = sortSelect.value;

        const visibleCards = cards.slice().sort((a, b) => {
            const priceA = parseFloat(a.dataset.price || "0");
            const priceB = parseFloat(b.dataset.price || "0");
            const seatsA = parseInt(a.dataset.seats || "0", 10);
            const seatsB = parseInt(b.dataset.seats || "0", 10);
            const depA = (a.dataset.departure || "00:00");
            const depB = (b.dataset.departure || "00:00");
            const durA = parseInt(a.dataset.durationMinutes || "0", 10);
            const durB = parseInt(b.dataset.durationMinutes || "0", 10);

            if (sortValue === "price_asc") return priceA - priceB;
            if (sortValue === "price_desc") return priceB - priceA;
            if (sortValue === "departure_asc") return depA.localeCompare(depB);
            if (sortValue === "duration_asc") return durA - durB;
            if (sortValue === "seats_desc") return seatsB - seatsA;
            return 0;
        });

        visibleCards.forEach(card => container.appendChild(card));
        applyFilters();
    }

    // Event Listeners
    if (priceSlider) {
        priceSlider.addEventListener("input", () => {
            if (priceValueDisplay) priceValueDisplay.textContent = `₹${priceSlider.value}`;
            applyFilters();
        });
    }

    acCheckboxes.forEach(cb => cb.addEventListener("change", applyFilters));
    departureTimeCheckboxes.forEach(cb => cb.addEventListener("change", applyFilters));
    classCheckboxes.forEach(cb => cb.addEventListener("change", applyFilters));
    if (availableOnlyCheckbox) availableOnlyCheckbox.addEventListener("change", applyFilters);
    if (sortSelect) sortSelect.addEventListener("change", applySorting);

    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            if (priceSlider) {
                priceSlider.value = priceSlider.max;
                if (priceValueDisplay) priceValueDisplay.textContent = `₹${priceSlider.value}`;
            }
            acCheckboxes.forEach(cb => cb.checked = false);
            departureTimeCheckboxes.forEach(cb => cb.checked = false);
            classCheckboxes.forEach(cb => cb.checked = false);
            if (availableOnlyCheckbox) availableOnlyCheckbox.checked = false;
            if (sortSelect) sortSelect.value = "departure_asc";
            applySorting();
            applyFilters();
            if (window.showToast) window.showToast("Filters reset", "info", 1500);
        });
    }

    // Initial run
    applySorting();
    applyFilters();
}
