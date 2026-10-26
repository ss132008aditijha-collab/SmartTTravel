/**
 * SmartTravel - Main Core JavaScript
 * Handles navigation, mobile menu, toast notifications, and global helpers.
 */

document.addEventListener("DOMContentLoaded", () => {
    initMobileNav();
    initToasts();
    autoDismissBanners();
});

// Mobile Navigation Toggle
function initMobileNav() {
    const mobileBtn = document.getElementById("mobileMenuBtn");
    const navLinks = document.getElementById("mainNav");

    if (mobileBtn && navLinks) {
        mobileBtn.addEventListener("click", () => {
            const isOpen = navLinks.classList.toggle("menu-open");
            mobileBtn.setAttribute("aria-expanded", String(isOpen));
            mobileBtn.innerHTML = isOpen
                ? `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>`
                : `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M4 6h16M4 12h16M4 18h16"/></svg>`;
        });

        // Close menu on clicking outside
        document.addEventListener("click", (e) => {
            if (!navLinks.contains(e.target) && !mobileBtn.contains(e.target) && navLinks.classList.contains("menu-open")) {
                navLinks.classList.remove("menu-open");
                mobileBtn.setAttribute("aria-expanded", "false");
                mobileBtn.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M4 6h16M4 12h16M4 18h16"/></svg>`;
            }
        });
    }
}

// User-friendly Toast Notification System (replaces window.alert)
function initToasts() {
    if (!document.getElementById("smartToastContainer")) {
        const container = document.createElement("div");
        container.id = "smartToastContainer";
        container.className = "toast-container";
        document.body.appendChild(container);
    }
}

window.showToast = function(message, type = "info", duration = 3500) {
    let container = document.getElementById("smartToastContainer");
    if (!container) {
        initToasts();
        container = document.getElementById("smartToastContainer");
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    let icon = "ℹ️";
    if (type === "success") icon = "✓";
    else if (type === "error" || type === "danger") icon = "✕";
    else if (type === "warning") icon = "⚠️";

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <div class="toast-message">${message}</div>
        <button class="toast-close" type="button" aria-label="Close">&times;</button>
    `;

    container.appendChild(toast);

    // Animate entrance
    requestAnimationFrame(() => {
        toast.classList.add("toast-show");
    });

    const closeBtn = toast.querySelector(".toast-close");
    const removeToast = () => {
        toast.classList.remove("toast-show");
        toast.classList.add("toast-hide");
        setTimeout(() => toast.remove(), 300);
    };

    closeBtn.addEventListener("click", removeToast);
    if (duration > 0) {
        setTimeout(removeToast, duration);
    }
};

// Auto dismiss banner alerts after 6 seconds
function autoDismissBanners() {
    const banners = document.querySelectorAll(".alert-banner");
    banners.forEach((banner) => {
        setTimeout(() => {
            banner.style.transition = "opacity 0.4s ease, transform 0.4s ease";
            banner.style.opacity = "0";
            banner.style.transform = "translateY(-6px)";
            setTimeout(() => banner.remove(), 400);
        }, 6000);
    });
}
