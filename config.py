# config.py
"""Configuration settings and data loading for the Kusmus Data Generator."""

import os
import sys
import json
import re
from pathlib import Path
from dotenv import load_dotenv

# --- Dependency Check ---
try:
    from google import generativeai as genai # Correct import
    from google.generativeai.types import HarmCategory, HarmBlockThreshold # Correct import path
    print("✅ google-generativeai library and safety types imported successfully.")
except ImportError:
    print("❌ Missing dependency: Please install/upgrade `pip install --upgrade google-generativeai`")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error importing google.generativeai: {e}")
    sys.exit(1)


# --- Base Paths ---
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "kusmus_gold_standard_raw_v3"
OUTPUT_DIR.mkdir(exist_ok=True)
print(f"📂 Output directory set to: {OUTPUT_DIR}")

# --- Load API Key ---
print("🔑 Loading API Key from .env file...")
load_dotenv(BASE_DIR / ".env")
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
if not API_KEY:
    print("❌ FATAL: GEMINI_API_KEY missing in .env. Please create a .env file.")
    sys.exit(1)
print("🔑 API Key loaded successfully.")

# --- Configure Gemini Client ---
# Explicitly pass the API key here
try:
    genai.configure(api_key=API_KEY)
    print("✅ Gemini client configured with provided API key.")
except Exception as e:
    print(f"❌ FATAL: Failed to configure Gemini client with API key: {e}")
    sys.exit(1)


# --- Model & Generation Settings ---
GEMINI_MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash-latest") # Use -latest alias
# <<<<<<<<<<< UPDATED TO 40 PER SCENARIO >>>>>>>>>>>
NUM_PER_SCENARIO = int(os.getenv("TRANSCRIPTS_PER_SCENARIO", "40")) # Target 40
print(f"🤖 Using Gemini Model: {GEMINI_MODEL_NAME}")
print(f"🔢 Target: {NUM_PER_SCENARIO} transcripts per scenario.")

# --- Load External Specification Files ---
SYSTEM_PROMPT_FILE = BASE_DIR / "system_prompt.txt"
SCENARIOS_FILE = BASE_DIR / "scenarios.json" # Using JSON spec file

# Load System Prompt
SYSTEM_PROMPT = "" # Initialize
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
SCENARIOS = [] # Initialize
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
except json.JSONDecodeError as e:
    print(f"❌ FATAL: Error decoding scenarios JSON file '{SCENARIOS_FILE}': {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ FATAL: Error loading or parsing scenarios file '{SCENARIOS_FILE}': {e}")
    sys.exit(1)


# --- Safety Settings ---
# Uses the correctly imported enums
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}
print("🛡️ Safety settings configured.")

# --- Final Validation ---
if not all(isinstance(s, dict) and s.get("id") and s.get("prompt") for s in SCENARIOS):
     print("❌ FATAL: Loaded scenarios list seems invalid (missing 'id' or 'prompt' in some items). Check scenarios.json.")
     sys.exit(1)

print("✅ Configuration loaded and validated.")
