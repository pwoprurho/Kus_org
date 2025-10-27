# gemini_utils.py
"""Functions for interacting with the Google Gemini API."""

import sys
import json
import re
import time

# --- Dependency Check ---
try:
    from google import genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    print("❌ Missing dependency: Please install with `pip install google-generativeai`")
    sys.exit(1)

# --- Import necessary config variables ---
try:
    # Ensure config.py is in the same directory or Python path
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
        # Use a more robust test prompt
        test_response = model.generate_content("Generate a short test JSON analysis block.",
                                               generation_config=genai.types.GenerationConfig(max_output_tokens=50))
        # More robust check for valid response
        if not hasattr(test_response, 'text') or not test_response.text or "error" in test_response.text.lower():
             # Try checking parts if text is missing
             if not response.candidates or not response.candidates[0].content or not response.candidates[0].content.parts:
                  raise Exception(f"API test call failed or returned empty/error response. Check API Key/Permissions. Response: {test_response}")
             else:
                  print("✅ API test call successful (using parts).") # Indicate success if parts exist
        else:
             print("✅ API test call successful (using text).")

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
    # Use DOTALL (s), IGNORECASE (i), MULTILINE (m) flags
    t_match = re.search(r"\[TRANSCRIPT START\](.*?)\[TRANSCRIPT END\]", text, re.S | re.I | re.M)
    j_match = re.search(r"```json(.*?)```", text, re.S | re.I | re.M)

    if not t_match: print(f"⚠️ Parser Error: Missing [TRANSCRIPT START]...[TRANSCRIPT END] block."); return None
    if not j_match: print(f"⚠️ Parser Error: Missing ```json...``` block."); return None

    transcript = t_match.group(1).strip()
    json_string = j_match.group(1).strip().replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
    # More aggressive cleaning for potential markdown/junk around JSON
    json_string = re.sub(r'^\s*json\s*', '', json_string, flags=re.I).strip()

    parsed_json = None
    try:
        parsed_json = json.loads(json_string)
        # --- Basic Validation ---
        if not isinstance(parsed_json, dict): raise ValueError("Top level JSON not dict.")
        if "analysis" not in parsed_json or not isinstance(parsed_json["analysis"], dict): raise ValueError("Missing/invalid 'analysis'.")
        if "meta" not in parsed_json or not isinstance(parsed_json["meta"], dict): raise ValueError("Missing/invalid 'meta'.")
        # Validate quarantine carefully
        if "quarantine" not in parsed_json : raise ValueError("Missing top-level 'quarantine'.")
        q_val = parsed_json.get("quarantine")
        if not isinstance(q_val, bool):
            q_str = str(q_val).lower()
            if q_str == 'true': parsed_json['quarantine'] = True
            elif q_str == 'false': parsed_json['quarantine'] = False
            else: raise ValueError(f"Invalid 'quarantine' value: {q_val}")
        # Add more validation based on system_prompt.txt if needed (e.g., check nested keys)
        # Example nested check:
        # if "sentiment" not in parsed_json.get("analysis", {}) or "label" not in parsed_json["analysis"]["sentiment"]:
        #     raise ValueError("Missing analysis.sentiment.label")
        return {"transcript": transcript, "parsed_json": parsed_json}
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON Parse Error: {e} | String: {json_string[:300]}...")
        return None
    except ValueError as ve:
        # Provide more context on validation failure
        print(f"⚠️ JSON Validation Error: {ve}")
        if parsed_json: print(f"   Problematic Parsed JSON: {json.dumps(parsed_json, indent=2)}")
        else: print(f"   Problematic Raw JSON String: {json_string[:300]}...")
        return None
    except Exception as e:
        print(f"⚠️ Unexpected Parser Error: {e}")
        return None

def analyze_transcript(client: genai.GenerativeModel, scenario_prompt: str) -> dict | None:
    """
    Sends prompt to Gemini, handles retries, parses output.
    Returns the parsed data structure {'transcript': ..., 'parsed_json': ...} or None.
    """
    retries = 3
    for attempt in range(retries):
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=0.8, # Balance creativity and consistency
                max_output_tokens=2048 # Ensure enough space
            )
            response = client.generate_content(
                scenario_prompt,
                generation_config=generation_config
            )

            # --- Safety/Block Check ---
            finish_reason = None
            safety_blocked = False
            candidate = response.candidates[0] if response.candidates else None

            if candidate:
                # Check safety ratings first
                safety_ratings = getattr(candidate, 'safety_ratings', [])
                if any(rating.category != HarmCategory.HARM_CATEGORY_UNKNOWN and rating.probability >= HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE for rating in safety_ratings):
                    safety_blocked=True; print(f"⚠️ SAFETY Block Detected (Rating). Prompt: {scenario_prompt[:100]}..."); return None

                finish_reason = getattr(candidate, 'finish_reason', None)

            # Check finish reason ONLY if not safety blocked
            # Reason 1 = STOP (Normal), Reason 2 = MAX_TOKENS, Reason 3 = SAFETY, 4=RECITATION, 5=OTHER
            if not safety_blocked and finish_reason != 1:
                print(f"⚠️ Generation Finished Unexpectedly (Reason: {finish_reason}). Prompt: {scenario_prompt[:100]}...");
                # Specific handling based on reason
                if finish_reason == 3: print("   Safety Block explicitly indicated by finish_reason.")
                elif finish_reason == 2: print("   Max Tokens Reached. Output may be truncated.")
                # For now, skip all non-normal completions
                return None

            # Ensure content parts exist and have text
            content = getattr(candidate, 'content', None)
            parts = getattr(content, 'parts', [])
            response_text = parts[0].text if parts and hasattr(parts[0], 'text') else None

            if not response_text:
                print(f"⚠️ Invalid Response Structure (No text content). Prompt: {scenario_prompt[:100]}...");
                return None # Skip empty/invalid responses

            # --- Parse Output ---
            parsed = parse_gemini_output(response_text)
            if parsed: return parsed
            else: print("   Parsing failed."); # Will proceed to retry loop if parsing failed

        except Exception as e:
            error_str = str(e); wait_time = 0
            # Handle specific retryable errors
            if "Resource has been exhausted" in error_str or "429" in error_str or "rate limit" in error_str.lower():
                wait_time = 20 * (attempt + 1); print(f"🚦 Rate Limit (Attempt {attempt + 1}/{retries}). Retrying in {wait_time}s...")
            elif "internal server error" in error_str.lower() or "500" in error_str:
                 wait_time = 10 * (attempt + 1); print(f"🔧 API Internal Error (Attempt {attempt + 1}/{retries}). Retrying in {wait_time}s...")
            else: # General errors
                print(f"🛑 API Error (Attempt {attempt + 1}/{retries}): {e}");
                if attempt < retries - 1: wait_time = 7 * (attempt + 1); print(f"   Retrying in {wait_time}s...")
                else: print("   Max retries reached."); return None # Exit retries

            if wait_time > 0: time.sleep(wait_time) # Sleep only if retrying

    print("   All retry attempts failed."); return None # Return None if all retries fail
