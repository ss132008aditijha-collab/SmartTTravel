/**
 * SmartTravel - Payment Checkout JavaScript
 * Handles payment method tab selection, card input formatting, and demo payment confirmation.
 */

document.addEventListener("DOMContentLoaded", () => {
    initPaymentTabs();
    initCardInputFormatting();
});

function initPaymentTabs() {
    const methodRadios = document.querySelectorAll('input[name="payment_method"]');
    const optionContainers = document.querySelectorAll(".payment-subform");

    function updateMethodViews(selectedValue) {
        optionContainers.forEach(container => {
            if (container.dataset.method === selectedValue) {
                container.style.display = "block";
            } else {
                container.style.display = "none";
            }
        });
    }

    methodRadios.forEach(radio => {
        radio.addEventListener("change", () => {
            updateMethodViews(radio.value);
            document.querySelectorAll(".payment-method-card").forEach(c => c.classList.remove("active"));
            const parentCard = radio.closest(".payment-method-card");
            if (parentCard) parentCard.classList.add("active");
        });
    });

    // Make entire method card clickable
    document.querySelectorAll(".payment-method-card").forEach(card => {
        card.addEventListener("click", (e) => {
            const radio = card.querySelector('input[name="payment_method"]');
            if (radio && e.target !== radio && !e.target.closest("input") && !e.target.closest("select")) {
                radio.checked = true;
                updateMethodViews(radio.value);
                document.querySelectorAll(".payment-method-card").forEach(c => c.classList.remove("active"));
                card.classList.add("active");
            }
        });
    });

    const activeRadio = document.querySelector('input[name="payment_method"]:checked');
    if (activeRadio) {
        updateMethodViews(activeRadio.value);
    }
}

// Auto format card number and expiry
function initCardInputFormatting() {
    const cardInput = document.getElementById("demoCardNumber");
    const expiryInput = document.getElementById("demoCardExpiry");
    const cvvInput = document.getElementById("demoCardCvv");

    if (cardInput) {
        cardInput.addEventListener("input", (e) => {
            let val = cardInput.value.replace(/\D/g, "").slice(0, 16);
            cardInput.value = val.replace(/(\d{4})/g, "$1 ").trim();
        });
    }

    if (expiryInput) {
        expiryInput.addEventListener("input", (e) => {
            let val = expiryInput.value.replace(/\D/g, "").slice(0, 4);
            if (val.length >= 2) {
                expiryInput.value = `${val.slice(0, 2)}/${val.slice(2)}`;
            } else {
                expiryInput.value = val;
            }
        });
    }

    if (cvvInput) {
        cvvInput.addEventListener("input", (e) => {
            cvvInput.value = cvvInput.value.replace(/\D/g, "").slice(0, 3);
        });
    }
}

// Submit payment with professional loading animation
window.submitSmartPayment = function(event) {
    if (event) event.preventDefault();

    const form = document.getElementById("completeBookingForm");
    if (!form) return;

    // Show processing modal
    const overlay = document.getElementById("paymentProcessingOverlay");
    if (overlay) {
        overlay.classList.add("show");
    }

    // Simulate safe demo processing before server commit
    setTimeout(() => {
        HTMLFormElement.prototype.submit.call(form);
    }, 1000);
};
