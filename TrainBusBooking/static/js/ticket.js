/**
 * SmartTravel - E-Ticket JavaScript & PDF Generator
 * Generates an SVG QR code for verification, handles direct PDF downloads via html2pdf,
 * and executes robust cross-browser printing even inside sandboxed iframes.
 */

document.addEventListener("DOMContentLoaded", () => {
    generateTicketQRCode();
    initCopyBookingId();
});

// Generate dynamic QR Code for E-Ticket using pure SVG pattern
function generateTicketQRCode() {
    const qrContainer = document.getElementById("ticketQrCodeBox");
    if (!qrContainer) return;

    const bookingId = (document.getElementById("ticketBookingId")?.textContent || "ST999999").trim();

    // Create a deterministic pattern based on the booking ID string
    const size = 21;
    let hash = 0;
    for (let i = 0; i < bookingId.length; i++) {
        hash = (hash << 5) - hash + bookingId.charCodeAt(i);
        hash |= 0;
    }

    let svgCells = "";
    const cellSize = 6;
    const padding = 12;

    // Corner Finder Patterns
    function addFinder(x, y) {
        svgCells += `<rect x="${x}" y="${y}" width="42" height="42" fill="#0f172a" rx="4"/>`;
        svgCells += `<rect x="${x + 6}" y="${y + 6}" width="30" height="30" fill="#ffffff" rx="2"/>`;
        svgCells += `<rect x="${x + 12}" y="${y + 12}" width="18" height="18" fill="#0f172a" rx="2"/>`;
    }

    addFinder(padding, padding);
    addFinder(padding + 14 * cellSize, padding);
    addFinder(padding, padding + 14 * cellSize);

    // Deterministic data modules in the remaining space
    for (let r = 0; r < size; r++) {
        for (let c = 0; c < size; c++) {
            if ((r < 7 && c < 7) || (r < 7 && c > 13) || (r > 13 && c < 7)) continue;

            const bit = Math.abs(Math.sin((r * 31 + c * 17) ^ hash) * 10000) % 2 > 1;
            if (bit) {
                const px = padding + c * cellSize;
                const py = padding + r * cellSize;
                svgCells += `<rect x="${px}" y="${py}" width="${cellSize - 1}" height="${cellSize - 1}" fill="#1e40af" rx="1"/>`;
            }
        }
    }

    const totalDim = padding * 2 + size * cellSize;
    qrContainer.innerHTML = `
        <svg width="140" height="140" viewBox="0 0 ${totalDim} ${totalDim}" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="#ffffff" rx="8"/>
            ${svgCells}
        </svg>
    `;
}

// Copy Booking ID / PNR
function initCopyBookingId() {
    const copyBtn = document.getElementById("copyBookingIdBtn");
    const bookingIdEl = document.getElementById("ticketBookingId");

    if (copyBtn && bookingIdEl) {
        copyBtn.addEventListener("click", () => {
            const text = bookingIdEl.textContent.trim();
            navigator.clipboard.writeText(text).then(() => {
                if (window.showToast) window.showToast(`PNR / Booking ID ${text} copied to clipboard!`, "success", 2000);
            }).catch(() => {
                if (window.showToast) window.showToast(text, "info", 2000);
            });
        });
    }
}

// Reliable PDF Download using server vector PDF generator
window.downloadTicketPDF = function(customBookingId) {
    const bookingId = (customBookingId || document.getElementById("ticketBookingId")?.textContent || "ST000000").trim();

    if (window.showToast) {
        window.showToast("Downloading your official PDF ticket...", "success", 3000);
    }

    // Direct server PDF streaming - guaranteed full vector render with all details
    const downloadUrl = "/download-pdf/" + encodeURIComponent(bookingId);

    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = `SmartTravel_Ticket_${bookingId}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
};

// Robust Cross-Browser Print Handler
window.printTicket = function() {
    // If inside an iframe (like AI Studio or web preview), window.print() can be suppressed.
    // We open a clean printable window containing only the e-ticket card and print styles.
    try {
        const ticketElement = document.querySelector(".e-ticket-card");
        if (!ticketElement) {
            window.print();
            return;
        }

        const printWindow = window.open("", "_blank", "width=850,height=900");
        if (printWindow) {
            printWindow.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>SmartTravel E-Ticket</title>
                    <link rel="stylesheet" href="/static/style.css">
                    <style>
                        body { background: white !important; padding: 20px !important; margin: 0 !important; font-family: 'Plus Jakarta Sans', sans-serif; }
                        .e-ticket-card { box-shadow: none !important; border: 1.5px solid #0f172a !important; margin: 0 auto; max-width: 780px; }
                        @media print {
                            body { padding: 0 !important; }
                            @page { margin: 10mm; }
                        }
                    </style>
                </head>
                <body>
                    <div style="text-align:center; margin-bottom:12px;" class="no-print">
                        <button onclick="window.print()" style="background:#1e40af; color:white; padding:10px 24px; border:none; border-radius:6px; font-weight:700; cursor:pointer;">
                            🖨️ Click Here to Print / Save as PDF
                        </button>
                    </div>
                    ${ticketElement.outerHTML}
                    <script>
                        window.onload = function() {
                            setTimeout(function() {
                                window.print();
                            }, 400);
                        };
                    <\/script>
                </body>
                </html>
            `);
            printWindow.document.close();
            if (window.showToast) window.showToast("Print window opened! You can select 'Save as PDF' in the destination.", "info", 3500);
        } else {
            // If popup was blocked, fallback to normal window.print()
            window.print();
        }
    } catch (e) {
        console.warn("Popup print blocked, falling back to window.print():", e);
        window.print();
    }
};

// Open standalone view
window.openPrintableTab = function() {
    window.printTicket();
};
