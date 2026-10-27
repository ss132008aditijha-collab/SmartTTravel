import test from "node:test";
import assert from "node:assert/strict";

// Pure logic unit tests for SmartTravel Transit & Pricing Rules

function extractClassCode(rawClass: string): string {
  if (!rawClass) return "STANDARD";
  const match = rawClass.match(/\b(1A|2A|3A|3E|CC|EC|SL|2S)\b/i);
  return match ? match[1].toUpperCase() : rawClass.trim().toUpperCase();
}

function getTrainSupportedClasses(trainNumber: string, trainName: string, basePrice: number) {
  const isVande = trainNumber === "20608" || trainName.toLowerCase().includes("vande bharat");
  const isShatabdi = trainNumber === "12028" || trainName.toLowerCase().includes("shatabdi");

  if (isVande) {
    return [
      { code: "CC", name: "AC Chair Car", price: 890 },
      { code: "EC", name: "Exec Chair Car (AC)", price: 1650 },
    ];
  }

  if (isShatabdi) {
    return [
      { code: "CC", name: "AC Chair Car", price: 850 },
      { code: "EC", name: "Exec Chair Car (AC)", price: 1590 },
    ];
  }

  return [
    { code: "1A", name: "AC First Class", price: Math.round(basePrice * 2.8) },
    { code: "2A", name: "AC 2 Tier", price: Math.round(basePrice * 1.8) },
    { code: "3A", name: "AC 3 Tier", price: Math.round(basePrice * 1.3) },
    { code: "3E", name: "AC 3 Economy", price: Math.round(basePrice * 1.15) },
    { code: "SL", name: "Sleeper Class (Non-AC)", price: Math.round(basePrice * 0.7) },
  ];
}

test("Vande Bharat Express (Train 20608) strictly restricts to CC and EC classes only", () => {
  const classes = getTrainSupportedClasses("20608", "Vande Bharat Express", 890);
  const codes = classes.map((c) => c.code);

  assert.deepEqual(codes, ["CC", "EC"]);
  assert.equal(codes.includes("2A"), false);
  assert.equal(codes.includes("3A"), false);
  assert.equal(codes.includes("SL"), false);

  const cc = classes.find((c) => c.code === "CC");
  const ec = classes.find((c) => c.code === "EC");
  assert.equal(cc?.price, 890);
  assert.equal(ec?.price, 1650);
});

test("extractClassCode reliably extracts clean codes from legacy and descriptive labels", () => {
  assert.equal(extractClassCode("CC"), "CC");
  assert.equal(extractClassCode("CC (AC Chair Car)"), "CC");
  assert.equal(extractClassCode("2A (AC 2 Tier)"), "2A");
  assert.equal(extractClassCode("3A (AC 3 Tier)"), "3A");
  assert.equal(extractClassCode("SL (Sleeper Class)"), "SL");
  assert.equal(extractClassCode("1A"), "1A");
  assert.equal(extractClassCode("EC"), "EC");
});

test("Superfast trains provide full tier breakdown including AC and Non-AC classes", () => {
  const classes = getTrainSupportedClasses("12627", "Karnataka Superfast Express", 650);
  const codes = classes.map((c) => c.code);

  assert.deepEqual(codes, ["1A", "2A", "3A", "3E", "SL"]);
});
