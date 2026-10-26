/**
 * SmartTravel - Authentication JavaScript
 * Handles password visibility toggling, password matching, and strength checking.
 */

document.addEventListener("DOMContentLoaded", () => {
    initPasswordToggles();
    initPasswordStrengthChecker();
    initConfirmPasswordValidation();
});

// Show / Hide Password Toggle
function initPasswordToggles() {
    const toggleBtns = document.querySelectorAll(".toggle-password-btn");

    toggleBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const inputId = btn.dataset.target;
            const input = document.getElementById(inputId) || btn.previousElementSibling;
            if (!input) return;

            const isPassword = input.type === "password";
            input.type = isPassword ? "text" : "password";

            btn.innerHTML = isPassword
                ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24M1 1l22 22"/></svg>`
                : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
        });
    });
}

// Password strength indicator
function initPasswordStrengthChecker() {
    const passwordInput = document.getElementById("password") || document.getElementById("newPassword");
    const strengthBar = document.getElementById("passwordStrengthBar");
    const strengthLabel = document.getElementById("passwordStrengthLabel");

    if (!passwordInput || !strengthBar) return;

    passwordInput.addEventListener("input", () => {
        const val = passwordInput.value;
        let score = 0;

        if (val.length >= 6) score++;
        if (val.length >= 10) score++;
        if (/[A-Z]/.test(val) && /[a-z]/.test(val)) score++;
        if (/\d/.test(val) || /[^A-Za-z0-9]/.test(val)) score++;

        strengthBar.className = "strength-meter-bar";
        if (val.length === 0) {
            strengthBar.style.width = "0%";
            if (strengthLabel) strengthLabel.textContent = "";
        } else if (score <= 1) {
            strengthBar.style.width = "25%";
            strengthBar.classList.add("strength-weak");
            if (strengthLabel) strengthLabel.textContent = "Weak";
        } else if (score === 2) {
            strengthBar.style.width = "50%";
            strengthBar.classList.add("strength-fair");
            if (strengthLabel) strengthLabel.textContent = "Fair";
        } else if (score === 3) {
            strengthBar.style.width = "75%";
            strengthBar.classList.add("strength-good");
            if (strengthLabel) strengthLabel.textContent = "Good";
        } else {
            strengthBar.style.width = "100%";
            strengthBar.classList.add("strength-strong");
            if (strengthLabel) strengthLabel.textContent = "Strong";
        }
    });
}

// Confirm Password Validation
function initConfirmPasswordValidation() {
    const form = document.getElementById("registerForm") || document.getElementById("resetPasswordForm");
    if (!form) return;

    const pwd = form.querySelector('input[name="password"]');
    const confirmPwd = form.querySelector('input[name="confirm_password"]') || document.getElementById("confirm_password");

    form.addEventListener("submit", (e) => {
        if (pwd && confirmPwd) {
            if (pwd.value !== confirmPwd.value) {
                e.preventDefault();
                if (window.showToast) {
                    window.showToast("Passwords do not match. Please re-enter.", "warning");
                } else {
                    alert("Passwords do not match.");
                }
                confirmPwd.focus();
            }
        }
    });
}
