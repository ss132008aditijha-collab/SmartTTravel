/**
 * SmartTravel - Google Gemini AI Assistant Widget
 * Features:
 * - Floating assistant launcher with quick suggestions
 * - Interactive Q&A connected to server-side Google Gemini (gemini-3.8-flash)
 * - Multilingual support (English & Hindi)
 * - Intelligent travel planning & cancellation guidance
 */

(function () {
    let currentLanguage = "en";

    document.addEventListener("DOMContentLoaded", () => {
        injectAiWidget();
    });

    function injectAiWidget() {
        if (document.getElementById("smartTravelAiContainer")) return;

        const container = document.createElement("div");
        container.id = "smartTravelAiContainer";
        container.innerHTML = `
            <!-- Floating Launcher Button -->
            <button id="aiLauncherBtn" class="ai-launcher-btn" aria-label="Open SmartTravel AI Assistant">
                <span class="ai-launcher-sparkle">✨</span>
                <span class="ai-launcher-label">SmartTravel AI</span>
                <span class="ai-online-dot"></span>
            </button>

            <!-- Chat Modal Window -->
            <div id="aiChatWindow" class="ai-chat-window" style="display: none;">
                <!-- Header -->
                <div class="ai-chat-header">
                    <div class="ai-chat-brand">
                        <span class="ai-avatar-icon">🤖</span>
                        <div>
                            <strong>SmartTravel AI Assistant</strong>
                            <small class="ai-status-text">Powered by Google Gemini · Online</small>
                        </div>
                    </div>
                    <div class="ai-header-actions">
                        <button type="button" id="aiLangToggleBtn" class="ai-lang-pill" title="Switch Language">
                            🌐 EN / हिन्दी
                        </button>
                        <button type="button" id="aiCloseBtn" class="ai-close-icon" aria-label="Close Chat">✕</button>
                    </div>
                </div>

                <!-- Messages Container -->
                <div id="aiMessagesList" class="ai-messages-list">
                    <div class="ai-message bot">
                        <div class="ai-bubble">
                            👋 <strong>Namaste & Welcome!</strong> I am your SmartTravel AI Assistant.<br>
                            How can I help with your journey today? Ask about train classes, bus sleeper berths, boarding guidelines, or trip planning!
                        </div>
                    </div>

                    <!-- Quick Suggestions -->
                    <div class="ai-quick-prompts">
                        <button type="button" class="ai-prompt-chip" data-prompt="What is the difference between 1A, 2A, 3A, and Sleeper trains?">🚆 Train Classes</button>
                        <button type="button" class="ai-prompt-chip" data-prompt="Explain AC Sleeper vs Non-AC Bus options and deck types">🚌 Bus Types</button>
                        <button type="button" class="ai-prompt-chip" data-prompt="What is the cancellation and refund policy on SmartTravel?">❌ Cancellation Rules</button>
                        <button type="button" class="ai-prompt-chip" data-prompt="Suggest a 2-day budget travel itinerary for Chennai under ₹3000">🗺️ 2-Day Itinerary</button>
                    </div>
                </div>

                <!-- Input Footer -->
                <form id="aiChatForm" class="ai-chat-footer">
                    <input
                        type="text"
                        id="aiUserInput"
                        class="ai-chat-input"
                        placeholder="Ask about trains, buses, routes, rules..."
                        autocomplete="off"
                        required>
                    <button type="submit" id="aiSendBtn" class="ai-send-btn" aria-label="Send Message">
                        ➤
                    </button>
                </form>
            </div>
        `;

        document.body.appendChild(container);
        setupAiWidgetEvents();
    }

    function setupAiWidgetEvents() {
        const launcher = document.getElementById("aiLauncherBtn");
        const chatWindow = document.getElementById("aiChatWindow");
        const closeBtn = document.getElementById("aiCloseBtn");
        const chatForm = document.getElementById("aiChatForm");
        const userInput = document.getElementById("aiUserInput");
        const langToggle = document.getElementById("aiLangToggleBtn");

        launcher?.addEventListener("click", () => {
            const isHidden = chatWindow.style.display === "none";
            chatWindow.style.display = isHidden ? "flex" : "none";
            if (isHidden) userInput?.focus();
        });

        closeBtn?.addEventListener("click", () => {
            chatWindow.style.display = "none";
        });

        langToggle?.addEventListener("click", () => {
            currentLanguage = currentLanguage === "en" ? "hi" : "en";
            langToggle.textContent = currentLanguage === "en" ? "🌐 EN" : "🌐 हिन्दी";
            appendBotMessage(
                currentLanguage === "hi"
                    ? "नमस्ते! मैंने भाषा बदलकर हिन्दी कर दी है। आप ट्रेन, बस और यात्रा से जुड़ा कोई भी सवाल पूछ सकते हैं।"
                    : "Language switched to English. Feel free to ask any travel question!"
            );
        });

        // Quick prompts click
        document.querySelectorAll(".ai-prompt-chip").forEach(chip => {
            chip.addEventListener("click", () => {
                const prompt = chip.dataset.prompt;
                if (prompt) {
                    sendUserMessage(prompt);
                }
            });
        });

        chatForm?.addEventListener("submit", (e) => {
            e.preventDefault();
            const text = userInput.value.trim();
            if (!text) return;
            userInput.value = "";
            sendUserMessage(text);
        });
    }

    async function sendUserMessage(text) {
        const list = document.getElementById("aiMessagesList");
        if (!list) return;

        // Append user bubble
        const userDiv = document.createElement("div");
        userDiv.className = "ai-message user";
        userDiv.innerHTML = `<div class="ai-bubble">${escapeHtml(text)}</div>`;
        list.appendChild(userDiv);
        list.scrollTop = list.scrollHeight;

        // Typing indicator
        const typingDiv = document.createElement("div");
        typingDiv.className = "ai-message bot ai-typing";
        typingDiv.innerHTML = `<div class="ai-bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>`;
        list.appendChild(typingDiv);
        list.scrollTop = list.scrollHeight;

        try {
            const res = await fetch("/api/ai/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text, language: currentLanguage })
            });

            const data = await res.json();
            typingDiv.remove();

            if (data.reply) {
                appendBotMessage(data.reply);
            } else {
                appendBotMessage("I am here to assist with your journey. Please ask again or search routes above!");
            }
        } catch (err) {
            console.warn("AI chat fetch error:", err);
            typingDiv.remove();
            appendBotMessage("SmartTravel AI is operational. You can search live train & bus departures, choose AC/Non-AC berths, and complete reservations anytime!");
        }
    }

    function appendBotMessage(text) {
        const list = document.getElementById("aiMessagesList");
        if (!list) return;

        // Basic markdown formatting: **bold** and newlines
        let formatted = escapeHtml(text)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');

        const botDiv = document.createElement("div");
        botDiv.className = "ai-message bot";
        botDiv.innerHTML = `<div class="ai-bubble">${formatted}</div>`;
        list.appendChild(botDiv);
        list.scrollTop = list.scrollHeight;
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
})();
