# gemini_utils.py
"""Functions for interacting with the Google Gemini API."""

import sys
import json
import re
import time

# --- Dependency Check ---
try:
    from google import generativeai as genai # Correct import alias
    from google.generativeai.types import HarmCategory, HarmBlockThreshold # Correct import path
    print("✅ google-generativeai imported correctly in gemini_utils.")
except ImportError:
    print("❌ Missing dependency: Please install/upgrade `pip install --upgrade google-generativeai`")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error importing google.generativeai in gemini_utils: {e}")
    sys.exit(1)

# --- Import necessary config variables ---
try:
    from config import GEMINI_MODEL_NAME, SYSTEM_PROMPT, SAFETY_SETTINGS # Keep SYSTEM_PROMPT import
except ImportError:
    print("❌ FATAL: Cannot import from config.py in gemini_utils. Ensure it exists.")
    sys.exit(1)

def get_gemini_client():
    """Initializes the Gemini model WITHOUT system prompt.""" # <<< MODIFIED DOCSTRING
    try:
        model = genai.GenerativeModel(
            GEMINI_MODEL_NAME,
            # system_instruction=SYSTEM_PROMPT, # <<< REMOVED THIS LINE
            safety_settings=SAFETY_SETTINGS
        )
        print("🧪 Performing quick API test call...")
        # Test call remains the same
        test_response = model.generate_content("test", generation_config=genai.types.GenerationConfig(max_output_tokens=10))
        # More robust check for valid response
        candidate = test_response.candidates[0] if hasattr(test_response, 'candidates') and test_response.candidates else None
        content = getattr(candidate, 'content', None)
        parts = getattr(content, 'parts', [])
        response_text = parts[0].text if parts and hasattr(parts[0], 'text') else getattr(test_response,'text', None) # Fallback

        if not response_text or "error" in response_text.lower():
             finish_reason = getattr(candidate, 'finish_reason', None)
             safety_ratings = getattr(candidate, 'safety_ratings', [])
             raise Exception(f"API test call failed or returned empty/error. FinishReason: {finish_reason}. SafetyRatings: {safety_ratings}. Response: {test_response}")
        else:
             print("✅ API test call successful.")

        print(f"✅ Gemini client initialized successfully for model: {GEMINI_MODEL_NAME}")
        return model
    except Exception as e:
        print(f"❌ FATAL: Failed to initialize Gemini client: {e}")
        print("   Please check your API Key (in .env), internet connection, and model name.")
        sys.exit(1)

def parse_gemini_output(text: str) -> dict | None:
    """
    Safely parses the raw Gemini output string based on the expected structure.
    Returns {'transcript': ..., 'parsed_json': ...} or None.
    (Code remains the same as previous version)
    """
    if not text: print("⚠️ Parser Warning: Received empty text from API."); return None
    t_match = re.search(r"\[TRANSCRIPT START\](.*?)\[TRANSCRIPT END\]", text, re.S | re.I | re.M)
    j_match = re.search(r"```json(.*?)```", text, re.S | re.I | re.M)
    if not t_match: print(f"⚠️ Parser Error: Missing [TRANSCRIPT START]...[TRANSCRIPT END] block."); return None
    if not j_match: print(f"⚠️ Parser Error: Missing ```json...``` block."); return None

    transcript = t_match.group(1).strip()
    json_string = j_match.group(1).strip().replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
    json_string = re.sub(r'^\s*json\s*', '', json_string, flags=re.I).strip()
    parsed_json = None
    try:
        parsed_json = json.loads(json_string)
        if not isinstance(parsed_json, dict): raise ValueError("Top level JSON not dict.")
        if "analysis" not in parsed_json or not isinstance(parsed_json["analysis"], dict): raise ValueError("Missing/invalid 'analysis'.")
        if "meta" not in parsed_json or not isinstance(parsed_json["meta"], dict): raise ValueError("Missing/invalid 'meta'.")
        if "quarantine" not in parsed_json : raise ValueError("Missing top-level 'quarantine'.")
        q_val = parsed_json.get("quarantine")
        if not isinstance(q_val, bool):
            q_str = str(q_val).lower()
            if q_str == 'true': parsed_json['quarantine'] = True
            elif q_str == 'false': parsed_json['quarantine'] = False
            else: raise ValueError(f"Invalid 'quarantine' value: {q_val}")
        return {"transcript": transcript, "parsed_json": parsed_json}
    except Exception as e: print(f"⚠️ Parser/Validation Error: {e} | JSON: {json_string[:300]}..."); return None


def analyze_transcript(client: genai.GenerativeModel, scenario_prompt: str) -> dict | None:
    """
    Sends prompt to Gemini (prepending SYSTEM_PROMPT), handles retries, parses output.
    Returns the parsed data structure {'transcript': ..., 'parsed_json': ...} or None.
    """
    retries = 3
    # --- PREPEND SYSTEM PROMPT TO SCENARIO PROMPT ---
    full_prompt = f"{SYSTEM_PROMPT}\n\n---\n\n**NOW, GENERATE FOR THIS SPECIFIC SCENARIO:**\n{scenario_prompt}"
    # ---

    for attempt in range(retries):
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=0.8,
                max_output_tokens=2048
            )
            # --- USE FULL PROMPT HERE ---
            response = client.generate_content(
                full_prompt, # Pass the combined prompt
                generation_config=generation_config
            )
            # ---

            # --- Safety/Block Check (remains the same) ---
            finish_reason = None
            safety_blocked = False
            candidate = response.candidates[0] if hasattr(response, 'candidates') and response.candidates else None

            if candidate:
                safety_ratings = getattr(candidate, 'safety_ratings', [])
                if any(rating.category != HarmCategory.HARM_CATEGORY_UNKNOWN and rating.probability >= HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE for rating in safety_ratings):
                    safety_blocked=True; print(f"⚠️ SAFETY Block Detected (Rating). Prompt: {scenario_prompt[:100]}..."); return None
                finish_reason = getattr(candidate, 'finish_reason', None)

            if not safety_blocked and finish_reason != 1:
                print(f"⚠️ Generation Finished Unexpectedly (Reason: {finish_reason}). Prompt: {scenario_prompt[:100]}...");
                if finish_reason == 3: print("   Safety Block explicitly indicated.")
                elif finish_reason == 2: print("   Max Tokens Reached. Output truncated?")
                return None

            content = getattr(candidate, 'content', None)
            parts = getattr(content, 'parts', [])
            response_text = parts[0].text if parts and hasattr(parts[0], 'text') else getattr(response,'text', None) # Fallback

            if not response_text:
                print(f"⚠️ Invalid Response Structure (No text content). Prompt: {scenario_prompt[:100]}...");
                return None

            # --- Parse Output (remains the same) ---
            parsed = parse_gemini_output(response_text)
            if parsed: return parsed
            else: print("   Parsing failed.");

        # --- Error Handling (remains the same) ---
        except Exception as e:
            error_str = str(e); wait_time = 0
            if "Resource has been exhausted" in error_str or "429" in error_str or "rate limit" in error_str.lower():
                wait_time = 20 * (attempt + 1); print(f"🚦 Rate Limit (Attempt {attempt + 1}/{retries}). Retrying in {wait_time}s...")
            elif "internal server error" in error_str.lower() or "500" in error_str or "service unavailable" in error_str.lower():
                 wait_time = 10 * (attempt + 1); print(f"🔧 API Internal/Unavailable Error (Attempt {attempt + 1}/{retries}). Retrying in {wait_time}s...")
            else:
                print(f"🛑 API Error (Attempt {attempt + 1}/{retries}): {e}");
                if attempt < retries - 1: wait_time = 7 * (attempt + 1); print(f"   Retrying in {wait_time}s...")
                else: print("   Max retries reached."); return None

            if wait_time > 0: time.sleep(wait_time)

    print("   All retry attempts failed."); return None
