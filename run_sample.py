# test_api_connection.py
"""
Dedicated script to test the Gemini API connection and basic generation.
Imports the client initialization function from gemini_utils.
"""

import sys
import time
from datetime import datetime

# --- Import necessary modules ---
try:
    # Ensure Python can find the modules in the current directory
    from config import GEMINI_MODEL_NAME # Import model name for logging
    from gemini_utils import get_gemini_client
    # Import safety types directly if needed for interpreting results (optional here)
    # from google.generativeai.types import HarmCategory, HarmBlockThreshold
    print("✅ Modules imported successfully.")
except ImportError as e:
    print(f"❌ FATAL: Could not import necessary modules: {e}")
    print("   Ensure config.py and gemini_utils.py are in the same directory.")
    sys.exit(1)

# --- Main Test Function ---
def run_test():
    """Initializes the client and runs a simple test prompt."""
    start_time = time.time()
    print(f"🚀 Starting API Connection Test (Model: {GEMINI_MODEL_NAME}) at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    print("="*80)

    # 1. Initialize Client (This now only creates the object)
    client = get_gemini_client()
    if not client:
        print("❌ Test Failed: Client initialization returned None.")
        return # Exit if client fails

    # 2. Run Simple Test Prompt
    test_prompt = "Say a joke 🙂"
    print(f"🧪 Sending test prompt: '{test_prompt}'")
    try:
        # Define minimal config for the test
        test_generation_config = {"max_output_tokens": 50}
        # Call generate_content (no system prompt needed for this simple test)
        test_response = client.generate_content(
            test_prompt,
            generation_config=test_generation_config
            # safety_settings=... # Pass safety settings here if they weren't passed during init
        )

        # 3. Check Response Robustly
        candidate = test_response.candidates[0] if hasattr(test_response, 'candidates') and test_response.candidates else None
        content = getattr(candidate, 'content', None)
        parts = getattr(content, 'parts', [])
        response_text = parts[0].text if parts and hasattr(parts[0], 'text') else getattr(test_response, 'text', None) # Fallback
        finish_reason = getattr(candidate, 'finish_reason', None)
        safety_ratings = getattr(candidate, 'safety_ratings', [])

        if response_text and response_text.strip():
            print(f"✅ Test SUCCESSFUL!")
            print(f"   Response Text: '{response_text.strip()}'")
        else:
            # If no text, report failure reasons
            print(f"❌ Test FAILED: No valid text content returned.")
            print(f"   Finish Reason: {finish_reason}")
            blocked_categories = [r.category.name for r in safety_ratings if r.probability >= HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE]
            if blocked_categories:
                print(f"   Safety Block Detected: {blocked_categories}")
            print(f"   Full Response Object: {test_response}") # Log full response for debugging

    except Exception as e:
        print(f"❌ Test FAILED during generate_content call: {e}")
        # Optionally add traceback here for more detail
        # import traceback
        # traceback.print_exc()

    end_time = time.time()
    print("\n" + "="*80)
    print(f"🏁 API Connection Test finished in {end_time - start_time:.2f} seconds.")
    print("="*80)


if __name__ == "__main__":
    run_test()
