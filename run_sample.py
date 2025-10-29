#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_api_connection.py
Standalone script to test basic Gemini API connectivity and generation.
Does NOT depend on other project modules (config.py, gemini_utils.py, etc.).
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# --- Dependency Check ---
try:
    from google import generativeai as genai
    # Import necessary types directly for safety settings
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    print("✅ google-generativeai library found and types imported.")
except ImportError:
    print("❌ Missing dependency: Please ensure google-generativeai is installed (`pip install google-generativeai`)")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error during import: {e}")
    sys.exit(1)

# --- Configuration (Local to this script) ---
BASE_DIR = Path(__file__).resolve().parent
print(f"📂 Running from base directory: {BASE_DIR}")

# Load API Key directly from .env in the current directory
print("🔑 Loading API Key from .env file...")
load_dotenv(BASE_DIR / ".env")
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
if not API_KEY:
    print("❌ FATAL: GEMINI_API_KEY missing in .env. Please create a .env file in this directory.")
    sys.exit(1)
print("🔑 API Key loaded successfully.")

# Configure the Gemini client directly
try:
    genai.configure(api_key=API_KEY)
    print("✅ Gemini client configured with API key.")
except Exception as e:
    print(f"❌ FATAL: Failed to configure Gemini client with API key: {e}")
    sys.exit(1)

# Define Model and Basic Safety Settings Locally
# Use the recommended latest alias
TEST_MODEL_NAME = "gemini-2.5-flash"
print(f"🤖 Target Test Model: {TEST_MODEL_NAME}")

# Basic Safety Settings (using correct import path)
try:
    TEST_SAFETY_SETTINGS = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    print("🛡️ Basic safety settings defined.")
except NameError:
    print("❌ FATAL: Could not define safety settings. Import failed earlier?")
    sys.exit(1)
except Exception as e:
    print(f"❌ FATAL: Error defining safety settings: {e}")
    sys.exit(1)


# --- Main Test Function ---
def run_test():
    """Initializes the client and runs a simple test prompt."""
    start_time = time.time()
    print(f"\n🚀 Starting Standalone API Connection Test at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    print("="*80)

    # 1. Initialize Client Directly
    client = None
    try:
        # Initialize model WITHOUT system prompt (as required by flash)
        client = genai.GenerativeModel(
            model_name=TEST_MODEL_NAME,
            safety_settings=TEST_SAFETY_SETTINGS # Pass safety settings here
        )
        print(f"✅ Gemini client object created for model: {TEST_MODEL_NAME}")
    except ValueError as ve:
         # Catch potential errors related to model name or settings during init
         print(f"❌ FATAL: ValueError during Gemini client initialization: {ve}")
         sys.exit(1)
    except Exception as e:
        print(f"❌ FATAL: Failed to initialize Gemini client object: {e}")
        sys.exit(1)

    # 2. Run Simple Test Prompt
    test_prompt = "Say hello 👋🏽"
    print(f"🧪 Sending test prompt: '{test_prompt}'")
    try:
        # Define minimal config for the test call
        test_generation_config = {"max_output_tokens": 50}
        # Call generate_content
        test_response = client.generate_content(
            test_prompt,
            generation_config=test_generation_config
            # No need to pass safety_settings again if passed during init
        )

        # 3. Check Response Robustly
        candidate = test_response.candidates[0] if hasattr(test_response, 'candidates') and test_response.candidates else None
        content = getattr(candidate, 'content', None)
        parts = getattr(content, 'parts', [])
        response_text = parts[0].text if parts and hasattr(parts[0], 'text') else getattr(test_response, 'text', None) # Fallback
        finish_reason = getattr(candidate, 'finish_reason', 'UNKNOWN')
        safety_ratings = getattr(candidate, 'safety_ratings', [])
        blocked = any(r.category != HarmCategory.HARM_CATEGORY_UNKNOWN and r.probability >= HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE for r in safety_ratings)

        if response_text and response_text.strip() and not blocked and finish_reason == 1:
            print(f"✅ Test SUCCESSFUL!")
            print(f"   Response Text: '{response_text.strip()}'")
        else:
            # If no text or blocked or finished abnormally, report failure
            print(f"❌ Test FAILED.")
            if not response_text or not response_text.strip():
                 print("   Reason: No valid text content returned.")
            if blocked:
                blocked_categories = [(r.category.name, r.probability.name) for r in safety_ratings if r.probability >= HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE]
                print(f"   Reason: SAFETY Block Detected - {blocked_categories}")
            if finish_reason != 1:
                print(f"   Reason: Generation Finished Unexpectedly (Reason Code: {finish_reason})")
            print(f"   Full Response Object (for debugging): {test_response}")

    except Exception as e:
        print(f"❌ Test FAILED during generate_content call: {e}")
        # Optionally add traceback here for more detail
        # import traceback
        # traceback.print_exc()

    end_time = time.time()
    print("\n" + "="*80)
    print(f"🏁 Standalone API Connection Test finished in {end_time - start_time:.2f} seconds.")
    print("="*80)


if __name__ == "__main__":
    run_test()
