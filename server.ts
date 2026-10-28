import express from "express";
import { createProxyMiddleware } from "http-proxy-middleware";
import { spawn, ChildProcess, execSync } from "child_process";
import path from "path";
import fs from "fs";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";

function getPythonExecutable(): string {
  if (process.env.PYTHON_PATH && fs.existsSync(process.env.PYTHON_PATH)) {
    return process.env.PYTHON_PATH;
  }
  if (process.platform === "win32") {
    const candidates = [
      "python.exe",
      "C:\\Python315\\python.exe",
      "C:\\Python310\\python.exe",
      "C:\\Python311\\python.exe",
      "C:\\Python312\\python.exe",
    ];
    for (const c of candidates) {
      if (fs.existsSync(c)) return c;
    }
    return "python";
  }
  // Linux / POSIX
  for (const c of ["/usr/bin/python3", "/usr/local/bin/python3", "python3", "python"]) {
    try {
      execSync(`${c} --version`, { stdio: "ignore" });
      return c;
    } catch {
      // try next
    }
  }
  return "python3";
}

async function startServer() {
  const app = express();
  const PORT = Number(process.env.PORT) || 3000;
  const FLASK_PORT = 5001;

  const appletDir = process.cwd();
  const sitePackages = path.join(appletDir, "TrainBusBooking", "venv", "Lib", "site-packages");
  const appPy = path.join(appletDir, "TrainBusBooking", "app.py");

  const pythonCmd = getPythonExecutable();
  console.log(`[SmartTravel Bridge] Detected Python executable: ${pythonCmd}`);
  console.log(`[SmartTravel Bridge] Bundled site-packages: ${sitePackages}`);

  // Build python environment
  const pythonEnv = {
    ...process.env,
    PYTHONPATH: [
      sitePackages,
      path.join(appletDir, "TrainBusBooking"),
      process.env.PYTHONPATH || ""
    ].filter(Boolean).join(process.platform === "win32" ? ";" : ":"),
    PORT: String(FLASK_PORT),
    PYTHONUNBUFFERED: "1",
  };

  let flaskProcess: ChildProcess | null = null;
  let isRestarting = false;

  function startFlask() {
    console.log(`[SmartTravel Bridge] Spawning Flask backend on port ${FLASK_PORT}...`);
    flaskProcess = spawn(pythonCmd, [appPy], {
      env: pythonEnv,
      cwd: path.join(appletDir, "TrainBusBooking"),
      stdio: "inherit",
    });

    flaskProcess.on("error", (err) => {
      console.error("[SmartTravel Bridge] Failed to start Flask process:", err);
    });

    flaskProcess.on("exit", (code, signal) => {
      console.log(`[SmartTravel Bridge] Flask process exited with code ${code}, signal ${signal}`);
      if (!isRestarting && code !== 0 && code !== null) {
        console.log("[SmartTravel Bridge] Attempting auto-restart of Flask in 2 seconds...");
        setTimeout(() => {
          if (!isRestarting) startFlask();
        }, 2000);
      }
    });
  }

  startFlask();

  // Clean shutdown
  const cleanup = () => {
    isRestarting = true;
    if (flaskProcess) {
      try {
        flaskProcess.kill();
      } catch {}
    }
    process.exit();
  };
  process.on("SIGINT", cleanup);
  process.on("SIGTERM", cleanup);

  // Body parsing for JSON APIs
  app.use(express.json());

  // Initialize Google Gemini AI
  const apiKey = process.env.GEMINI_API_KEY || "";
  const ai = apiKey ? new GoogleGenAI({ apiKey }) : null;

  // ==========================================================
  // API HEALTH CHECK ENDPOINT
  // ==========================================================
  app.get("/api/health", (_req, res) => {
    res.json({
      status: "ok",
      timestamp: new Date().toISOString(),
      services: {
        node_bridge: "running on :3000",
        flask: `http://127.0.0.1:${FLASK_PORT}`,
        gemini_ai: apiKey ? "active" : "offline_knowledge_base",
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

      const systemInstruction = `You are "SmartTravel AI", the friendly, knowledgeable travel assistant for the SmartTravel Train and Bus Ticket Booking System.
You help passengers with:
1. Indian Railways train classes:
   - 1A (AC First Class): Private lockable coupe/cabin, luxury bedding, highest comfort.
   - 2A (AC 2-Tier): 2-tier berths with privacy curtains, AC, blankets, reading lights.
   - 3A (AC 3-Tier): 3-tier berths, air conditioned, bedroll kit.
   - 3E (AC 3 Economy): Modern affordable 3-tier AC coach.
   - SL (Sleeper Class - Non-AC): 3-tier open window sleeper with ceiling fans.
   - CC / EC (AC Chair Car / Executive): Reclining seats with meals for Vande Bharat & Shatabdi. Note that Vande Bharat Express (Train #20608) operates exclusively with Executive Class (EC) and AC Chair Car (CC).
2. Quotas: General (GN), Tatkal (TQ), Ladies (LD), Senior Citizen (SS).
3. Bus Types: Volvo Multi-Axle A/C, Scania Luxury Sleeper (Lower and Upper decks), Non-AC Sleeper, Non-AC Seater, Electric AC (EV).
4. Station pick-ups, verified demo fare policies, e-catering ordering, and cancellation refunds.
Tone: Helpful, polite, concise, professional.
If the passenger asks in Hindi or requests Hindi, reply in fluent polite Hindi. Otherwise reply in clear English.`;

      if (ai) {
        try {
          const response = await ai.models.generateContent({
            model: "gemini-2.5-flash",
            contents: `${systemInstruction}\n\nPassenger Question: ${message}`,
          });
          const reply = response.text || "";
          return res.json({ reply, source: "gemini_live" });
        } catch (apiErr: any) {
          console.warn("[SmartTravel Bridge] Gemini API call failed, falling back to local KB:", apiErr?.message);
        }
      }

      // Fallback local expert knowledge base
      const lower = message.toLowerCase();
      let fallbackReply = "";

      if (lower.includes("1a") || lower.includes("2a") || lower.includes("3a") || lower.includes("sleeper") || lower.includes("coach") || lower.includes("class")) {
        fallbackReply = isHindi
          ? "भारतीय रेलवे में श्रेणियाँ:\n• **1A (प्रथम वातानुकूलित)**: निजी कूप/केबिन और शानदार बिस्तर।\n• **2A (2-टियर एसी)**: पर्दे और रीडिंग लाइट के साथ दो स्तर की बर्थ।\n• **3A (3-टियर एसी)**: 3-स्तरीय वातानुकूलित बर्थ, चादर व कंबल सहित।\n• **CC / EC (वंदे भारत / शताब्दी)**: आरामदायक रिक्लाइनिंग सीटें और गर्म भोजन सेवा। ध्यान दें: वंदे भारत (ट्रेन 20608) में केवल CC और EC सीटें उपलब्ध हैं।"
          : "Here is the Indian Railways coach breakdown:\n• **1A (AC First Class)**: Private lockable 2/4-berth coupe, luxury linens & privacy.\n• **2A (AC 2 Tier)**: Spacious 2-tier berths with curtains, personal reading lamp & bedding.\n• **3A (AC 3 Tier)**: 3-tier air-conditioned sleeper berths with complimentary bedrolls.\n• **SL (Sleeper Class)**: Economical non-AC open-window berths with ceiling fans.\n• **CC & EC (Vande Bharat / Shatabdi)**: Ergonomic chair cars with catering. (Train 20608 Vande Bharat runs exclusively with CC and EC coaches).";
      } else if (lower.includes("vande bharat") || lower.includes("20608")) {
        fallbackReply = isHindi
          ? "वंदे भारत एक्सप्रेस (ट्रेन 20608) बेंगलुरु और चेन्नई के बीच केवल 4 घंटे 30 मिनट में चलती है। इसमें केवल दो प्रीमियम श्रेणियाँ हैं: **CC (एसी चेयर कार - ₹890)** और **EC (एग्जीक्यूटिव चेयर कार - ₹1650)** जिसमें 180° घूमने वाली सीटें मिलती हैं।"
          : "The **Vande Bharat Express (Train #20608)** connects Bengaluru (SBC) and Chennai (MAS) in 4h 30m. It offers two classes: **AC Chair Car (CC at ₹890)** and **Executive Chair Car (EC at ₹1650)** featuring 180° rotatable seats and onboard dining.";
      } else if (lower.includes("cancel") || lower.includes("refund")) {
        fallbackReply = isHindi
          ? "आप 'My Bookings' पेज पर जाकर किसी भी समय अपनी बुकिंग रद्द कर सकते हैं। रद्द करने पर सीट पुनः उपलब्ध हो जाती है और पूर्ण डेमो रिफंड तुरंत क्रेडिट हो जाता है।"
          : "You can cancel any confirmed ticket under **'My Bookings'** by clicking **'Cancel Booking'**. Your seat is immediately released back to the reservation pool, and 100% demo refund is recorded.";
      } else if (lower.includes("bus") || lower.includes("sleeper") || lower.includes("volvo")) {
        fallbackReply = isHindi
          ? "SmartTravel पर वोल्वो मल्टी-एक्सल एसी, स्कैनिया लक्ज़री स्लीपर (निचली और ऊपरी बर्थ), और बजट नॉन-एसी बसें उपलब्ध हैं।"
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

      if (ai) {
        try {
          const response = await ai.models.generateContent({
            model: "gemini-2.5-flash",
            contents: prompt,
            config: {
              responseMimeType: "application/json",
            },
          });
          const data = JSON.parse(response.text || "{}");
          return res.json({ recommendations: data, source: "gemini_grounded" });
        } catch (e) {
          // Fall back to rule-based recommendation below
        }
      }

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
    } catch (err: any) {
      console.error("[SmartTravel Bridge] Recommend error:", err);
      return res.status(500).json({ error: "Failed to generate recommendations" });
    }
  });

  // ==========================================================
  // VITE & FLASK PROXY
  // ==========================================================
  
  // Enable Vite only during local development.
  // In production, Flask serves the main website.
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "custom",
    });
    app.use(vite.middlewares);
  }


  const flaskProxy = createProxyMiddleware({
    target: `http://127.0.0.1:${FLASK_PORT}`,
    changeOrigin: true,
    ws: true,
    xfwd: true,
    on: {
      error: (err: Error, _req: any, res: any) => {
        console.error("[SmartTravel Bridge] Proxy error contacting Flask:", err.message);
        if (res && res.writeHead) {
          res.writeHead(503, { "Content-Type": "text/html" });
          res.end(`
            <div style="font-family:sans-serif; text-align:center; padding:50px;">
              <h2>Starting SmartTravel Backend Services...</h2>
              <p>The Python Flask transit booking service is starting up. Please refresh in a moment.</p>
              <script>setTimeout(() => location.reload(), 2500);</script>
            </div>
          `);
        }
      }
    }
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
