/**
 * SmartTravel - My Bookings Dashboard JavaScript
 * Filters bookings by status and handles cancellation confirmation.
 */

document.addEventListener("DOMContentLoaded", () => {
    initBookingsFilterTabs();
    initCancelBookingModal();
});

function initBookingsFilterTabs() {
    const tabs = document.querySelectorAll(".booking-tab-btn");
    const cards = document.querySelectorAll(".history-booking-card");

    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");

            const filter = tab.dataset.filter;
            let visibleCount = 0;

            cards.forEach(card => {
                const status = (card.dataset.status || "").toLowerCase();
                const journeyDateStr = card.dataset.date;
                const todayStr = new Date().toISOString().split("T")[0];

                let match = false;
                if (filter === "all") {
                    match = true;
                } else if (filter === "cancelled") {
                    match = status === "cancelled";
                } else if (filter === "completed") {
                    match = status === "confirmed" && journeyDateStr && journeyDateStr < todayStr;
                } else if (filter === "upcoming") {
                    match = status === "confirmed" && (!journeyDateStr || journeyDateStr >= todayStr);
                }

                if (match) {
                    card.style.display = "";
                    visibleCount++;
                } else {
                    card.style.display = "none";
                }
            });

            const emptyNotice = document.getElementById("emptyFilteredBookingsNotice");
            if (emptyNotice) {
                emptyNotice.style.display = visibleCount === 0 && cards.length > 0 ? "block" : "none";
            }
        });
    });
}

function initCancelBookingModal() {
    const modal = document.getElementById("cancelBookingModal");
    const confirmCancelBtn = document.getElementById("confirmCancelActionBtn");
    const closeModalBtns = document.querySelectorAll(".close-cancel-modal");
    let targetBookingId = null;

    window.openCancelModal = function(bookingId) {
        targetBookingId = bookingId;
        const idDisplay = document.getElementById("modalBookingIdTarget");
        if (idDisplay) idDisplay.textContent = bookingId;
        if (modal) {
            modal.classList.add("show");
            modal.classList.add("modal-open");
        }
    };

    function closeModal() {
        if (modal) {
            modal.classList.remove("show");
            modal.classList.remove("modal-open");
        }
        targetBookingId = null;
    }

    closeModalBtns.forEach(btn => btn.addEventListener("click", closeModal));

    if (confirmCancelBtn) {
        confirmCancelBtn.addEventListener("click", () => {
            if (targetBookingId) {
                const form = document.createElement("form");
                form.method = "POST";
                form.action = `/cancel-booking/${encodeURIComponent(targetBookingId)}`;
                document.body.appendChild(form);
                form.submit();
            }
        });
    }
}
