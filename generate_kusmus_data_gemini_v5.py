#!/usr/bin/env python3
"""
generate_kusmus_data_gemini_v5.py
Full Gemini-powered data generator for Kusmus Data Sprint v5.

✓ Uses Gemini 2.5 Flash via google-genai SDK
✓ Enforces phone-first identity (never BVN)
✓ Detects prompt-injection & social-engineering attempts
✓ Performs sentiment, emotion & tone analysis
✓ Saves JSON, CSV, TXT outputs in ./output
"""

import os, sys, json, csv, re, time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

try:
    from google import genai
except Exception:
    print("❌ Missing dependency: install with `pip install python-genai`")
    sys.exit(1)

# ──────────────────────────────
# CONFIGURATION
# ──────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
if not API_KEY:
    print("❌ GEMINI_API_KEY missing in .env")
    sys.exit(1)

genai.configure(api_key=API_KEY)

GEMINI_MODEL = os.getenv("MODEL_NAME", "gemini-2.5-flash")
NUM_PER_SCENARIO = int(os.getenv("TRANSCRIPTS_PER_SCENARIO", "2"))

SCENARIOS = [
    {"id": "UnauthorizedDebit", "industry": "Banking", "direction": "Inbound"},
    {"id": "ReservationBooking", "industry": "Hospitality", "direction": "Inbound"},
]
LANGUAGES = ["Pidgin", "English", "Yoruba", "Igbo", "Hausa"]

PROMPT_INJECTION_PATTERNS = [
    r"forget everything", r"ignore previous instructions",
    r"give me (the )?(account|card|card number|pin|password)",
    r"bypass security", r"override policy", r"disclose .* sensitive"
]
SOCIAL_ENGINEERING_PATTERNS = [
    r"i forgot", r"i no remember", r"i don forget",
    r"it's urgent", r"i'm in a hurry", r"please just help me",
    r"not with my (card|phone|details|information)",
    r"no need verification", r"skip verification",
    r"don't want to talk to a human", r"just tell me now"
]

# ──────────────────────────────
# HELPERS
# ──────────────────────────────
def now_iso(): return datetime.utcnow().isoformat() + "Z"

def mask_account(a): return "XXXX" + str(a)[-4:] if a else None

def mask_phone(p):
    if not p: return None
    digits = re.sub(r"\D", "", p)
    return digits[:4] + "XXXX" + digits[-3:] if len(digits) >= 7 else "XXXX" + digits

def detect(text, patterns):
    t = text.lower()
    for pat in patterns:
        if re.search(pat, t): return True, pat
    return False, None

def generate_case_id(prefix="UBD"):
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

# ──────────────────────────────
# PROMPTS
# ──────────────────────────────
SYSTEM_INSTRUCTIONS = {
    "Banking": (
        "You are a Nigerian bank customer-service agent. "
        "Start with greeting + recording consent, apologise if issue, "
        "then request details *one at a time*: phone number first, "
        "then account number if necessary. Never ask BVN. "
        "Never use 'verify', 'verification' or 'for security'. "
        "Politely de-escalate rude clients. If client refuses to talk to a human, "
        "label social-engineering as true. Produce natural multi-turn dialogue."
    ),
    "Hospitality": (
        "You are a polite hotel reservations agent. Start with greeting + consent, "
        "then ask guest name, then phone/booking reference. "
        "No 'verification' word. De-escalate politely if rude."
    ),
}

def build_prompt(scenario, industry, language):
    sys_inst = SYSTEM_INSTRUCTIONS.get(industry, "")
    user = (
        f"Language: {language}\n"
        f"Scenario: {scenario}\n"
        "Generate one realistic inbound call (8-18 turns):\n"
        "- Agent greets and requests recording consent\n"
        "- Collect details sequentially (phone → account or booking ref)\n"
        "- Handle rude or suspicious callers gracefully\n"
        "- End with summary or case ID\n"
        "- Use 100% authentic tone for specified language.\n"
        "Output between [TRANSCRIPT START] and [TRANSCRIPT END]."
    )
    return sys_inst + "\n\n" + user

# ──────────────────────────────
# ANALYSIS PROMPT
# ──────────────────────────────
ANALYZE_PROMPT = f"""
You are a compliance AI.
Analyse the transcript and return ONLY JSON with:

sentiment: {{score: float (-1..1), label: "positive|neutral|negative"}},
emotion: {{dominant: str, intensity: 0..1}},
tone_classifier: str,
contains_profanity: bool,
agent_note: short summary,
identity_confirmation: {{confirmed: bool, method: str|null}},
social_engineering: {{detected: bool, trigger_phrase: str|null, action_taken: str|null}},
prompt_injection: {{detected: bool, trigger_phrase: str|null}},
compliance: {{
  regulatory: {{jurisdiction:"NG", industry_rules:["CBN","NDPR"], recording_consent: bool}},
  ai: {{model_name:"{GEMINI_MODEL}", version:"v5", prompt_template:"kusmus_v5_txn_v1"}}
}}
"""

def analyze_transcript(text):
    client = genai.Client()
    prompt = ANALYZE_PROMPT + "\n\nTranscript:\n" + text
    try:
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        raw = resp.text if hasattr(resp, "text") else str(resp)
        start = raw.find("{")
        if start >= 0:
            return json.loads(raw[start:])
    except Exception as e:
        print("⚠️ analysis error:", e)
    return {
        "sentiment": {"score": 0.0, "label": "neutral"},
        "emotion": {"dominant": "neutral", "intensity": 0.0},
        "tone_classifier": "neutral",
        "contains_profanity": False,
        "agent_note": "analysis fallback",
        "identity_confirmation": {"confirmed": False, "method": None},
        "social_engineering": {"detected": False, "trigger_phrase": None, "action_taken": None},
        "prompt_injection": {"detected": False, "trigger_phrase": None},
        "compliance": {"regulatory": {"jurisdiction": "NG", "industry_rules": ["CBN","NDPR"], "recording_consent": True},
                       "ai": {"model_name": GEMINI_MODEL, "version": "v5", "prompt_template": "kusmus_v5_txn_v1"}}
    }

# ──────────────────────────────
# CORE GENERATION
# ──────────────────────────────
def generate_all():
    client = genai.Client()
    records = []
    count = 0
    for sc in SCENARIOS:
        for lang in LANGUAGES:
            for i in range(NUM_PER_SCENARIO):
                count += 1
                prompt = build_prompt(sc["id"], sc["industry"], lang)
                try:
                    resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
                    text = resp.text if hasattr(resp, "text") else str(resp)
                except Exception as e:
                    print("❌ generation error:", e)
                    text = "[TRANSCRIPT START]\nAgent: error generating\n[TRANSCRIPT END]"

                pi, pi_phrase = detect(text, PROMPT_INJECTION_PATTERNS)
                se, se_phrase = detect(text, SOCIAL_ENGINEERING_PATTERNS)

                analysis = analyze_transcript(text)

                if pi:
                    analysis["prompt_injection"] = {"detected": True, "trigger_phrase": pi_phrase}
                if se:
                    analysis["social_engineering"] = {"detected": True, "trigger_phrase": se_phrase,
                                                     "action_taken": "offered_transfer_to_human_agent"}

                sentiment = analysis.get("sentiment", {})
                quarantine = analysis.get("social_engineering", {}).get("detected") or \
                             analysis.get("prompt_injection", {}).get("detected")

                record = {
                    "id": count,
                    "language": lang,
                    "scenario": sc["id"],
                    "industry": sc["industry"],
                    "call_direction": sc["direction"],
                    "transcript": text,
                    "analysis": analysis,
                    "sentiment_score": sentiment.get("score"),
                    "sentiment_label": sentiment.get("label"),
                    "emotion": analysis.get("emotion"),
                    "tone_classifier": analysis.get("tone_classifier"),
                    "agent_note": analysis.get("agent_note"),
                    "meta": {"case_id": generate_case_id(), "timestamp": now_iso()},
                    "quarantine": quarantine,
                }
                records.append(record)
                time.sleep(0.5)
    return records

# ──────────────────────────────
# OUTPUTS
# ──────────────────────────────
def write_outputs(records):
    (OUTPUT_DIR / "AllTranscripts.json").write_text(json.dumps(records, indent=2, ensure_ascii=False), "utf-8")

    with open(OUTPUT_DIR / "kusmus_dataset.csv", "w", newline="", encoding="utf-8") as cf:
        w = csv.writer(cf)
        w.writerow(["id","language","scenario","industry","sentiment_score","sentiment_label","tone_classifier","agent_note","quarantine"])
        for r in records:
            w.writerow([
                r["id"], r["language"], r["scenario"], r["industry"],
                r["sentiment_score"], r["sentiment_label"],
                r["tone_classifier"], r["agent_note"], r["quarantine"]
            ])

    with open(OUTPUT_DIR / "samples.txt", "w", encoding="utf-8") as tf:
        for r in records:
            tf.write(r["transcript"] + "\n\n")

    print(f"✅ {len(records)} transcripts saved in {OUTPUT_DIR}")

# ──────────────────────────────
# MAIN
# ──────────────────────────────
def main():
    print(f"🚀 Generating transcripts with {GEMINI_MODEL} ...")
    data = generate_all()
    write_outputs(data)
    print("✅ Done.")

if __name__ == "__main__":
    main()