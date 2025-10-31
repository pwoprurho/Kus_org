# config.py
"""Configuration settings and data loading for the Kusmus Data Generator."""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# --- Dependency Check ---
try:
    from google import generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    print("✅ google-generativeai library and safety types imported successfully.")
except ImportError:
    print("❌ Missing dependency: Please install/upgrade `pip install --upgrade google-generativeai`")
    sys.exit(1)

# --- Base Paths ---
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "kusmus_gold_standard_raw_v3"
OUTPUT_DIR.mkdir(exist_ok=True)
print(f"📂 Output directory set to: {OUTPUT_DIR}")

# --- Load API Key Pool (NEW) ---
print("🔑 Loading API Key Pool from .env file...")
load_dotenv(BASE_DIR / ".env")

API_KEY_POOL = []
# Load all keys starting with GEMINI_API_KEY_...
for i in range(1, 10):  # Will check for keys 1 through 9
    key = os.getenv(f"GEMINI_API_KEY_{i}")
    if key:
        API_KEY_POOL.append(key)

# Fallback to the original single key if pool is empty
if not API_KEY_POOL:
    key = os.getenv("GEMINI_API_KEY") # Check for the old single key
    if key:
        API_KEY_POOL.append(key)
    else:
        print("❌ FATAL: No API keys found in .env file.")
        print("   Please add at least one key as GEMINI_API_KEY_1")
        sys.exit(1)

print(f"🔑 Loaded {len(API_KEY_POOL)} API Key(s) into the pool

# --- Model & Generation Settings ---
GEMINI_MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash") # Using 1.5-flash
NUM_PER_SCENARIO = int(os.getenv("TRANSCRIPTS_PER_SCENARIO", "10")) 
print(f"🤖 Using Gemini Model: {GEMINI_MODEL_NAME}")
print(f"🔢 Target: {NUM_PER_SCENARIO} transcripts per scenario.")


# --- Load External Specification Files ---
SYSTEM_PROMPT_FILE = BASE_DIR / "system_prompt.txt"
# IMPORTANT: Make sure you are using your full scenarios.json file
SCENARIOS_FILE = BASE_DIR / "scenarios.json" 

# Load System Prompt
SYSTEM_PROMPT = ""
try:
    print(f"📜 Loading system prompt from: {SYSTEM_PROMPT_FILE}")
    with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
    if not SYSTEM_PROMPT.strip():
        raise ValueError("System prompt file is empty.")
    print("📜 System prompt loaded successfully.")
except FileNotFoundError:
    print(f"❌ FATAL: System prompt file not found at '{SYSTEM_PROMPT_FILE}'")
    sys.exit(1)
except Exception as e:
    print(f"❌ FATAL: Error loading system prompt file '{SYSTEM_PROMPT_FILE}': {e}")
    sys.exit(1)

# Load Scenarios
SCENARIOS = []
try:
    print(f"📚 Loading scenarios from: {SCENARIOS_FILE}")
    with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
        SCENARIOS = json.load(f)
        if not isinstance(SCENARIOS, list) or not SCENARIOS:
             raise ValueError("Scenarios file is empty or not a valid JSON list.")
    print(f"📚 {len(SCENARIOS)} scenarios loaded successfully.")
except FileNotFoundError:
     print(f"❌ FATAL: Scenarios file not found at '{SCENARIOS_FILE}'")
     sys.exit(1)
except Exception as e:
    print(f"❌ FATAL: Error loading or parsing scenarios file '{SCENARIOS_FILE}': {e}")
    sys.exit(1)


# --- Safety Settings ---
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}
print("🛡️ Safety settings configured.")

print("✅ Configuration loaded and validated.")
