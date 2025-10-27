# gemini_utils.py
"""Functions for interacting with the Google Gemini API."""

import sys
import json
import re
import time

try:
    from google import genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    print("❌ Missing dependency: Please install with `pip install google-generativeai`")
    sys.exit(1)

# Import necessary config variables
try:
    from config import GEMINI_MODEL_NAME, SYSTEM_PROMPT, SAFETY_SETTINGS
except ImportError:
    print("❌ FATAL: Cannot import from config.py. Ensure it exists in the same directory.")
    sys.exit(1)

def get_gemini_client():
    """Initializes the Gemini model with system prompt and safety."""
    try:
        model = genai.GenerativeModel(
            GEMINI_MODEL_NAME,
            system_instruction=SYSTEM_PROMPT, # Loaded from config
            safety_settings=SAFETY_SETTINGS
        )
        print("🧪 Performing quick API test call...")
        test_response = model.generate_content("test", generation_config=genai.types.GenerationConfig(max_output_tokens=10))
        if not test_response.text or "error" in test_response.text.lower():
             raise Exception(f"API test call failed or returned error. Response: {test_response.text}")
        print(f"✅ Gemini client initialized successfully for model: {GEMINI_MODEL_NAME}")
        return model
    except Exception as e:
        print(f"❌ FATAL: Failed to initialize Gemini client: {e}")
        print("   Please check your API Key (in .env), internet connection, model name, and system prompt validity.")
        sys.exit(1)

def parse_gemini_output(text: str) -> dict | None:
    """
    Safely parses the raw Gemini output string based on the expected structure.
    Returns {'transcript': ..., 'parsed_json': ...} or None.
    """
    if not text: print("⚠️ Parser Warning: Received empty text from API."); return None
    t_match = re.search(r"\[TRANSCRIPT START\](.*?)\[TRANSCRIPT END\]", text, re.DOTALL | re.I | re.M)
    j_match = re.search(r"```json(.*?)```", text, re.DOTALL | re.I | re.M)
    if not t_match or not j_match: print(f"⚠️ Parser Error: Missing [TRANSCRIPT START]...[TRANSCRIPT END] or ```json...``` block."); return None

    transcript = t_match.group(1).strip()
    json_string = j_match.group(1).strip().replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
    json_string = re.sub(r'^\s*json\s*', '', json_string, flags=re.I).strip()

    parsed_json = None
    try:
        parsed_json = json.loads(json_string)
        # Basic Validation
        if not isinstance(parsed_json, dict): raise ValueError("Top level JSON not dict.")
        if "analysis" not in parsed_json or not isinstance(parsed_json["analysis"], dict): raise ValueError("Missing/invalid 'analysis'.")
        if "meta" not in parsed_json or not isinstance(parsed_json["meta"], dict): raise ValueError("Missing/invalid 'meta'.")
        if "quarantine" not in parsed_json or not isinstance(parsed_json.get("quarantine"), bool):
            q_val = str(parsed_json.get("quarantine","false")).lower(); parsed_json['quarantine']=True if q_val=='true' else False if q_val=='false' else (_ for _ in ()).throw(ValueError("Invalid 'quarantine'."))
        # Add more specific validation based on system_prompt.txt if needed
        return {"transcript": transcript, "parsed_json": parsed_json}
    except Exception as e: print(f"⚠️ Parser/Validation Error: {e} | JSON: {json_string[:200]}..."); return None


def analyze_transcript(client: genai.GenerativeModel, scenario_prompt: str) -> dict | None:
    """
    Sends prompt to Gemini, handles retries, parses output.
    Returns the parsed data structure {'transcript': ..., 'parsed_json': ...} or None.
    """
    retries = 3
    for attempt in range(retries):
        try:
            generation_config = genai.types.GenerationConfig(temperature=0.8, max_output_tokens=2048) # Increased tokens
            response = client.generate_content(scenario_prompt, generation_config=generation_config)

            finish_reason, safety_blocked = None, False
            if response.candidates:
                # Check safety ratings first - more robust check
                safety_ratings = getattr(response.candidates[0], 'safety_ratings', [])
                if any(rating.category != HarmCategory.HARM_CATEGORY_UNKNOWN and rating.probability >= HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE for rating in safety_ratings):
                    safety_blocked=True; print(f"⚠️ SAFETY Block Detected (Rating). Prompt: {scenario_prompt[:100]}..."); return None
                finish_reason = getattr(response.candidates[0], 'finish_reason', None)

            # Check finish reason ONLY if not safety blocked
            if not safety_blocked and finish_reason != 1: # 1 = STOP
                print(f"⚠️ Generation Finished Unexpectedly (Reason: {finish_reason}). Prompt: {scenario_prompt[:100]}...");
                # Specifically check if finish_reason indicates safety AFTER checking ratings
                if finish_reason == 3: print("   Safety Block explicitly indicated by finish_reason.")
                return None # Skip non-normal completions

            # Ensure content parts exist
            content_parts = getattr(getattr(getattr(response.candidates[0], 'content', None), 'parts', None), '__len__', 0) > 0 if response.candidates else False
            if not content_parts :
                print(f"⚠️ Invalid Response Structure (No content parts). Prompt: {scenario_prompt[:100]}...");
                return None # Skip empty/invalid responses

            parsed = parse_gemini_output(response.text) # response.text should be safe now
            if parsed: return parsed
            else: print("   Parsing failed."); # Will proceed to retry loop if parsing failed

        except Exception as e:
            error_str = str(e); wait_time = 0
            # Handle specific retryable errors
            if "Resource has been exhausted" in error_str or "429" in error_str or "rate limit" in error_str.lower():
                wait_time = 20 * (attempt + 1); print(f"🚦 Rate Limit (Attempt {attempt + 1}/{retries}). Retrying in {wait_time}s...")
            # Add checks for other potential transient errors if observed
            elif "internal server error" in error_str.lower() or "500" in error_str:
                 wait_time = 10 * (attempt + 1); print(f"🔧 API Internal Error (Attempt {attempt + 1}/{retries}). Retrying in {wait_time}s...")
            else: # General errors
                print(f"🛑 API Error (Attempt {attempt + 1}/{retries}): {e}");
                if attempt < retries - 1: wait_time = 7 * (attempt + 1); print(f"   Retrying in {wait_time}s...")
                else: print("   Max retries reached."); return None # Exit retries

            if wait_time > 0: time.sleep(wait_time) # Sleep only if retrying

    print("   All retry attempts failed."); return None # Return None if all retries fail
