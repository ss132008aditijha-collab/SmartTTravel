import express from "express";
import { createProxyMiddleware } from "http-proxy-middleware";
import { spawn, ChildProcess, execSync } from "child_process";
import path from "path";
import fs from "fs";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";

async function startServer() {
  const app = express();
  const PORT = 3000;
  const FLASK_PORT = 5001;

  // Path to TrainBusBooking
  const appletDir = process.cwd();
  const sitePackages = path.join(appletDir, "TrainBusBooking", "venv", "Lib", "site-packages");
  const appPy = path.join(appletDir, "TrainBusBooking", "app.py");

  // Preflight check: Ensure werkzeug, flask, and jinja2 are unpacked
  const werkzeugLocal = path.join(sitePackages, "werkzeug", "local.py");
  if (!fs.existsSync(werkzeugLocal)) {
    console.log("[SmartTravel Bridge] Restoring Python package dependencies...");
    try {
      execSync(`python3 -c "
import zipfile, os
zip_path = 'public/assets/aistudio/TrainBusBooking_d5f93d5f.zip'
if os.path.exists(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for m in zf.namelist():
            if 'werkzeug' in m or 'flask' in m or 'jinja2' in m:
                zf.extract(m, '.')
"`, { stdio: "inherit" });
      console.log("[SmartTravel Bridge] Python packages restored successfully.");
    } catch (e) {
      console.warn("[SmartTravel Bridge] Preflight package unpack warning:", e);
    }
  }

  console.log("[SmartTravel Bridge] Spawning Flask backend on port", FLASK_PORT);

  // Spawn Python Flask process
  const pythonEnv = {
    ...process.env,
    PYTHONPATH: sitePackages + (process.env.PYTHONPATH ? `:${process.env.PYTHONPATH}` : ""),
    PORT: String(FLASK_PORT),
    PYTHONUNBUFFERED: "1",
  };

  let flaskProcess: ChildProcess | null = null;

  function startFlask() {
    flaskProcess = spawn("python3", [appPy], {
      env: pythonEnv,
      cwd: path.join(appletDir, "TrainBusBooking"),
      stdio: "inherit",
    });

    flaskProcess.on("error", (err) => {
      console.error("[SmartTravel Bridge] Failed to start Flask process:", err);
    });

    flaskProcess.on("exit", (code, signal) => {
      console.log(`[SmartTravel Bridge] Flask process exited with code ${code}, signal ${signal}`);
    });
  }

  startFlask();

  // Clean shutdown
  process.on("SIGINT", () => {
    if (flaskProcess) flaskProcess.kill();
    process.exit();
  });
  process.on("SIGTERM", () => {
    if (flaskProcess) flaskProcess.kill();
    process.exit();
  });

  // JSON Body parsing for API routes
  app.use(express.json());

  // Initialize Gemini AI Client (Server-side only)
  const ai = new GoogleGenAI({
    apiKey: process.env.GEMINI_API_KEY,
    httpOptions: {
      headers: {
        "User-Agent": "aistudio-build",
      },
    },
  });

  // ==========================================================
  // API HEALTH CHECK ENDPOINT
  // ==========================================================
  app.get("/api/health", (_req, res) => {
    res.json({
      status: "ok",
      timestamp: new Date().toISOString(),
      services: {
        node_bridge: "running",
        flask: `http://127.0.0.1:${FLASK_PORT}`,
        gemini_ai: process.env.GEMINI_API_KEY ? "active" : "fallback_mode",
        database: "sqlite (smarttravel.db)"
      }
    });
  });

  // ==========================================================
  // GOOGLE GEMINI AI - SMARTTRAVEL TRAVEL CHATBOT
  // ==========================================================
  app.post("/api/ai/chat", async (req, res) => {
    try {
      const { message, language = "en" } = req.body;
      if (!message || typeof message !== "string") {
        return res.status(400).json({ error: "Missing required parameter 'message'" });
      }

      const isHindi = language === "hi" || /[\u0900-\u097F]/.test(message);

      const systemInstruction = `You are "SmartTravel AI", the friendly and expert travel assistant for the SmartTravel Train and Bus Ticket Booking System.
You help passengers with:
1. Indian Railways train classes:
   - 1A (AC First Class): Private lockable coupe/cabin, luxury bedding, highest comfort.
   - 2A (AC 2-Tier): 2-tier berths with privacy curtains, AC, blankets, reading lights.
   - 3A (AC 3-Tier): 3-tier berths, air conditioned, bedroll kit.
   - 3E (AC 3 Economy): Modern affordable 3-tier AC coach.
   - SL (Sleeper Class - Non-AC): 3-tier open window sleeper with ceiling fans.
   - CC / EC (AC Chair Car / Executive): Reclining seats with meals for Vande Bharat & Shatabdi.
2. Quotas: General (GN), Tatkal (TQ), Ladies (LD), Senior Citizen (SS).
3. Bus Types: Volvo Multi-Axle A/C, Scania Luxury Sleeper (Lower and Upper decks), Non-AC Sleeper, Non-AC Seater, Electric AC (EV).
4. Rules: Original photo ID proof (Aadhaar / Voter ID / Passport) required during travel. Reporting 20 minutes prior. Free cancellation before chart preparation.
5. Tone: Helpful, accurate, clear, and professional. Use markdown formatting with bullet points.
${isHindi ? "Respond in clear, natural Hindi (Devanagari script)." : "Respond in clear, concise English."}`;

      try {
        const response = await ai.models.generateContent({
          model: "gemini-3.8-flash",
          contents: message,
          config: {
            systemInstruction,
            temperature: 0.7,
          },
        });

        const reply = response.text || (isHindi ? "नमस्ते! मैं आपकी यात्रा में कैसे सहायता कर सकता हूँ?" : "Hello! How can I assist you with your SmartTravel journey today?");
        return res.json({ reply, source: "gemini" });
      } catch (aiErr) {
        console.warn("[SmartTravel Bridge] Gemini API call note, using intelligent assistant fallback:", aiErr);
        // Resilient Travel Knowledge Base Fallback
        const lower = message.toLowerCase();
        let fallbackReply = "";

        if (lower.includes("class") || lower.includes("1a") || lower.includes("2a") || lower.includes("3a") || lower.includes("sl")) {
          fallbackReply = isHindi
            ? "भारतीय रेल में उपलब्ध श्रेणियाँ:\n- **1A**: वातानुकूलित प्रथम श्रेणी (निजी केबिन)\n- **2A**: 2-टियर एसी (पर्दे व बेडरोल)\n- **3A**: 3-टियर एसी (किफायती एसी)\n- **SL**: स्लीपर क्लास (नॉन-एसी खुला स्लीपर)\n- **CC/EC**: वंदे भारत व शताब्दी में चेयर कार।"
            : "Here is the quick guide to Indian Railways travel classes on SmartTravel:\n\n- **1A (AC First Class)**: Private lockable coupe with luxury linen\n- **2A (AC 2-Tier)**: 2 berths per bay with privacy curtains\n- **3A (AC 3-Tier)**: Popular air-conditioned sleeper with bedrolls\n- **SL (Sleeper)**: Open-window economical sleeper class\n- **CC / EC**: Chair car comfort for Vande Bharat & Shatabdi day trains.";
        } else if (lower.includes("cancel") || lower.includes("refund")) {
          fallbackReply = isHindi
            ? "आप 'My Bookings' पेज पर जाकर अपना टिकट आसानी से रद्द (Cancel) कर सकते हैं। चार्ट तैयार होने से पहले पूरा रिफंड तुरंत प्रोसेस किया जाता है।"
            : "You can cancel your booking anytime from the **My Bookings** dashboard. Click 'Cancel Booking' on any confirmed trip. Eligible demo refunds are processed instantly.";
        } else if (lower.includes("bus") || lower.includes("sleeper") || lower.includes("volvo")) {
          fallbackReply = isHindi
            ? "SmartTravel पर वोल्वो मल्टी-एक्सल एसी, स्कैनिया एसी स्लीपर (लोअर व अपर डेक) और नॉन-एसी बसें उपलब्ध हैं। आप मनपसंद सीट व पिक-अप पॉइंट चुन सकते हैं।"
            : "SmartTravel offers Volvo Multi-Axle A/C, Scania Luxury Sleepers (featuring Lower & Upper Deck selection), and budget Non-AC buses with designated boarding landmarks.";
        } else if (lower.includes("pdf") || lower.includes("print") || lower.includes("ticket")) {
          fallbackReply = isHindi
            ? "बुकिंग पूरी होने पर ई-टिकट पेज से 'Download Official PDF Ticket' बटन दबाकर असली PDF डाउनलोड करें या 'Print Ticket' से प्रिंट करें।"
            : "Once booked, click **'Download Official PDF Ticket'** on your confirmation page to download a vector PDF directly, or click **'Open PDF in New Tab'** to view it.";
        } else {
          fallbackReply = isHindi
            ? "नमस्ते! मैं SmartTravel AI सहायक हूँ। आप ट्रेन/बस समय, सीट बुकिंग, एसी श्रेणियाँ, या टिकट डाउनलोड के बारे में कोई भी प्रश्न पूछ सकते हैं।"
            : "Hello! I am your SmartTravel AI Assistant. You can ask me about train & bus timings, AC vs Non-AC classes, berth selection (LB, MB, UB, SL), food ordering, and booking policies.";
        }

        return res.json({ reply: fallbackReply, source: "knowledge_base" });
      }
    } catch (err: any) {
      console.error("[SmartTravel Bridge] Chat endpoint error:", err);
      return res.status(500).json({ error: "Internal server error in AI chat" });
    }
  });

  // ==========================================================
  // GOOGLE GEMINI AI - SMART JOURNEY RECOMMENDATIONS
  // ==========================================================
  app.post("/api/ai/recommend", async (req, res) => {
    try {
      const { source = "Bengaluru", destination = "Chennai", budget = 1500, transport = "all", available_schedules } = req.body;

      const scheduleContext = available_schedules && Array.isArray(available_schedules) && available_schedules.length > 0
        ? JSON.stringify(available_schedules).slice(0, 1800)
        : "Vande Bharat Express (20608, CC: Rs 890, Duration: 4h 30m), Karnataka Superfast (12627, 3A: Rs 1120, SL: Rs 460), IntrCity SmartBus (Scania AC Sleeper: Rs 950, 7h 45m), KSRTC Airavat (Volvo AC: Rs 850), KSRTC Rajahamsa (Non-AC: Rs 520)";

      const prompt = `You are evaluating verified travel options for a passenger traveling from ${source} to ${destination} with a target budget of INR ${budget} for ${transport} travel.
GROUNDING REQUIREMENT: You must ONLY select from the real schedules provided below. Never invent non-existent trains, buses, timings, or fares.

Verified Schedules List:
${scheduleContext}

Return a structured JSON recommendation with:
1. "cheapest_option": { "vehicle": name, "fare": number, "reason": reason from real data }
2. "fastest_option": { "vehicle": name, "duration": duration, "fare": number }
3. "best_value_option": { "vehicle": name, "fare": number, "reason": reason }
4. "pro_tip": 1 actionable travel tip for this route.`;

      try {
        const response = await ai.models.generateContent({
          model: "gemini-3.8-flash",
          contents: prompt,
          config: {
            responseMimeType: "application/json",
          },
        });

        const data = JSON.parse(response.text || "{}");
        return res.json({ recommendations: data, source: "gemini_grounded" });
      } catch (e) {
        // Fallback structured recommendation
        return res.json({
          recommendations: {
            cheapest_option: {
              vehicle: transport === "bus" ? "KSRTC Rajahamsa Non-AC" : "Karnataka Express (Sleeper SL)",
              type: transport === "bus" ? "Non-AC Seater" : "Non-AC Sleeper",
              fare: transport === "bus" ? 520 : 460,
              reason: "Maximum cost savings with dependable schedule."
            },
            fastest_option: {
              vehicle: "Vande Bharat Express (20608)",
              type: "AC Chair Car",
              duration: "4h 30m",
              fare: 890
            },
            best_value_option: {
              vehicle: transport === "bus" ? "IntrCity SmartBus Premium A/C Sleeper" : "Karnataka Superfast (3A AC 3-Tier)",
              type: transport === "bus" ? "Luxury A/C Sleeper (2+1)" : "AC 3-Tier with Bedrolls",
              fare: transport === "bus" ? 950 : 1120,
              reason: "Ideal balance of overnight sleep comfort, climate control AC, and onboard amenities."
            },
            pro_tip: `Book at least 3-4 days ahead for ${source} to ${destination} weekend travel to secure preferred lower berths or single window bus sleepers.`
          },
          source: "smart_engine"
        });
      }
    } catch (err: any) {
      console.error("[SmartTravel Bridge] Recommend error:", err);
      return res.status(500).json({ error: "Failed to generate recommendations" });
    }
  });

  // ==========================================================
  // GOOGLE GEMINI AI - DESTINATION TRAVEL PLANNER
  // ==========================================================
  app.post("/api/ai/plan", async (req, res) => {
    try {
      const { destination = "Chennai", days = 2, budget = 5000, travelers = 1 } = req.body;

      const prompt = `Create a realistic ${days}-day travel itinerary for visiting ${destination} with a budget of INR ${budget} for ${travelers} traveler(s).
Include top 4-5 attractions, estimated daily expenses, local street food recommendations, and packing essentials.`;

      try {
        const response = await ai.models.generateContent({
          model: "gemini-3.8-flash",
          contents: prompt,
        });

        return res.json({ plan: response.text, destination, days });
      } catch (e) {
        return res.json({
          plan: `### 🌟 ${days}-Day Travel Itinerary for ${destination}\n\n` +
            `**Day 1: Heritage & Highlights**\n` +
            `- Morning: Visit famous historical landmarks and heritage temples.\n` +
            `- Afternoon: Savor authentic regional lunch thali at an iconic eatery.\n` +
            `- Evening: Enjoy sunset promenade walk along the waterfront.\n\n` +
            `**Day 2: Culture, Markets & Cuisine**\n` +
            `- Morning: Architectural exploration and art gallery tour.\n` +
            `- Afternoon: Shopping for handicrafts and regional specialties.\n` +
            `- Evening: Relax at a café and board your SmartTravel return trip.\n\n` +
            `**Budget Breakdown (Approx. ₹${budget} total)**:\n` +
            `- Local Transport: ₹600 - ₹1,000\n` +
            `- Food & Snacks: ₹1,200 - ₹1,800\n` +
            `- Entry & Activities: ₹400 - ₹800\n\n` +
            `**Packing Tips**: Light cotton clothing, comfortable walking footwear, power bank, and your SmartTravel digital e-ticket.`,
          destination,
          days
        });
      }
    } catch (err: any) {
      console.error("[SmartTravel Bridge] Plan error:", err);
      return res.status(500).json({ error: "Failed to generate travel plan" });
    }
  });

  // Create Vite in middleware mode to handle AI Studio control plane
  const vite = await createViteServer({
    server: { middlewareMode: true },
    appType: "custom",
  });
  app.use(vite.middlewares);

  // Create proxy to Flask
  const flaskProxy = createProxyMiddleware({
    target: `http://127.0.0.1:${FLASK_PORT}`,
    changeOrigin: true,
    ws: true,
    xfwd: true,
  });

  // Route requests: Keep AI Studio internal control plane and vite internals on Vite;
  // Send everything else to Flask
  app.use((req, res, next) => {
    const url = req.url || "";
    if (
      url.startsWith("/__aistudio") ||
      url.startsWith("/@vite") ||
      url.startsWith("/@fs") ||
      url.startsWith("/@id") ||
      url.startsWith("/src/") ||
      url.startsWith("/node_modules/")
    ) {
      return next();
    }
    return flaskProxy(req, res, next);
  });

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`[SmartTravel Bridge] Server running on http://0.0.0.0:${PORT} (proxying to Flask :${FLASK_PORT})`);
  });
}

startServer().catch((err) => {
  console.error("Failed to start server:", err);
  process.exit(1);
});
