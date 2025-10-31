# gemini_utils.py
"""Functions for interacting with the Google Gemini API."""

import sys
import json
import re
import time
import itertools # <-- NEW: For cycling through keys

# --- Dependency Check & Import ---
try:
    from google import generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    print("✅ google-generativeai imported correctly in gemini_utils.")
except ImportError:
    print("❌ Missing dependency: Ensure google-generativeai is installed.")
    sys.exit(1)

# --- Import necessary config variables ---
try:
    # NOW imports the API_KEY_POOL
    from config import GEMINI_MODEL_NAME, SYSTEM_PROMPT, SAFETY_SETTINGS, API_KEY_POOL 
except ImportError:
    print("❌ FATAL: Cannot import from config.py in gemini_utils.")
    sys.exit(1)

# --- NEW: Key Pool Management ---
if not API_KEY_POOL:
    print("❌ FATAL: API Key Pool is empty. Please check your .env and config.py")
    sys.exit(1)

# Create a permanent cycle of the keys
KEY_ITERATOR = itertools.cycle(API_KEY_POOL)
CURRENT_KEY = next(KEY_ITERATOR)
# This will be our globally managed client
model_client = None
# -------------------------------


def rotate_client_and_key():
    """Rotates to the next API key and re-initializes the global client."""
    global model_client, CURRENT_KEY, KEY_ITERATOR
    
    try:
        next_key = next(KEY_ITERATOR)
        
        # Check if we've looped all the way around
        if next_key == API_KEY_POOL[0]:
            print("🚦 All keys in pool have been rate-limited. Sleeping for 60s before retrying pool.")
            time.sleep(60)

        CURRENT_KEY = next_key
        key_index = API_KEY_POOL.index(CURRENT_KEY) + 1
        
        print(f"\n🔄 Rotating to API Key #{key_index}...")
        genai.configure(api_key=CURRENT_KEY)
        model_client = genai.GenerativeModel(
            model_name=GEMINI_MODEL_NAME,
            safety_settings=SAFETY_SETTINGS
        )
        print(f"✅ Client re-initialized with new key.")
        return model_client
    except Exception as e:
        print(f"❌ FAILED to rotate to new key: {e}")
        return None # This is a critical failure


def get_gemini_client():
    """Initializes the *first* client in the pool."""
    global model_client, CURRENT_KEY
    try:
        key_index = API_KEY_POOL.index(CURRENT_KEY) + 1
        print(f"🔑 Configuring Gemini with initial Key #{key_index}...")
        genai.configure(api_key=CURRENT_KEY)
        model_client = genai.GenerativeModel(
            model_name=GEMINI_MODEL_NAME,
            safety_settings=SAFETY_SETTINGS
        )
        print(f"✅ Gemini client object created successfully.")
        return model_client # Return it for the main script
    except Exception as e:
        print(f"❌ FATAL: Failed to initialize Gemini client with Key #{key_index}: {e}")
        sys.exit(1)


def parse_gemini_output(text: str) -> dict | None:
    """Safely parses Gemini output."""
    # This function [parse_gemini_output from gemini_utils.py] remains unchanged.
    if not text: print("⚠️ Parser Warning: Empty API text."); return None
    t_match = re.search(r"\[TRANSCRIPT START\](.*?)\[TRANSCRIPT END\]", text, re.S | re.I | re.M)
    j_match = re.search(r"```json(.*?)```", text, re.S | re.I | re.M)
    if not t_match or not j_match: print(f"⚠️ Parser Error: Missing [TRANSCRIPT] or ```json``` block."); return None
    transcript = t_match.group(1).strip()
    json_string = j_match.group(1).strip().replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
    json_string = re.sub(r'^\s*json\s*', '', json_string, flags=re.I).strip()
    parsed_json = None
    try:
        parsed_json = json.loads(json_string)
        if not isinstance(parsed_json, dict): raise ValueError("Top level JSON not dict.")
        if "analysis" not in parsed_json or not isinstance(parsed_json["analysis"], dict): raise ValueError("Missing/invalid 'analysis'.")
        if "meta" not in parsed_json or not isinstance(parsed_json["meta"], dict): raise ValueError("Missing/invalid 'meta'.")
        if "quarantine" not in parsed_json : raise ValueError("Missing 'quarantine'.")
        q_val = parsed_json.get("quarantine")
        if not isinstance(q_val, bool):
            q_str = str(q_val).lower(); parsed_json['quarantine']=True if q_str=='true' else False if q_str=='false' else (_ for _ in ()).throw(ValueError(f"Invalid 'quarantine': {q_val}"))
        return {"transcript": transcript, "parsed_json": parsed_json}
    except Exception as e: print(f"⚠️ Parser/Validation Error: {e} | JSON: {json_string[:300]}..."); return None


def analyze_transcript(scenario_prompt: str) -> dict | None: # <-- 'client' argument removed
    """
    Sends prompt using the global client, handles key rotation on rate limits.
    Returns parsed data {'transcript': ..., 'parsed_json': ...} or None.
    """
    global model_client # <-- Uses the global client
    
    retries = 3 # Retries *per key*
    full_prompt = f"{SYSTEM_PROMPT}\n\n---\n\n**NOW, GENERATE FOR THIS SPECIFIC SCENARIO:**\n{scenario_prompt}"
    generation_config_dict = { "temperature": 0.8, "max_output_tokens": 2048 }

    for attempt in range(retries):
        response_text = None
        try:
            if model_client is None: # Safety check
                print("❌ Client not initialized. Attempting to initialize...")
                initialize_client()
                if model_client is None: return None # Failed
            
            response = model_client.generate_content(
                full_prompt,
                generation_config=generation_config_dict
            )

            # --- Meticulous Safety & Content Validation (Unchanged) ---
            if not hasattr(response, 'candidates') or not response.candidates:
                print(f"⚠️ API Warning: No candidates returned. Check prompt feedback: {getattr(response, 'prompt_feedback', 'N/A')}. Prompt: {scenario_prompt[:100]}...")
                continue 
            candidate = response.candidates[0]
            safety_ratings = getattr(candidate, 'safety_ratings', [])
            blocked_categories = []
            for rating in safety_ratings:
                if rating.category != HarmCategory.HARM_CATEGORY_UNKNOWN and \
                   rating.probability >= HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE:
                    blocked_categories.append((rating.category.name, rating.probability.name))
            if blocked_categories:
                print(f"⚠️ SAFETY Block Detected (Rating). Blocked: {blocked_categories}. Prompt: {scenario_prompt[:100]}...")
                return None 
            finish_reason = getattr(candidate, 'finish_reason', None)
            if finish_reason != 1: # 1 = STOP
                print(f"⚠️ Generation Finished Unexpectedly (Reason: {finish_reason}). Prompt: {scenario_prompt[:100]}...");
                if finish_reason == 3: print("   Safety Block explicitly indicated.")
                elif finish_reason == 2: print("   Max Tokens Reached. Output truncated?")
                return None 
            content = getattr(candidate, 'content', None)
            parts = getattr(content, 'parts', [])
            if parts and hasattr(parts[0], 'text'):
                response_text = parts[0].text
            if not response_text:
                print(f"⚠️ Invalid Response Structure (No text content found despite normal finish). Prompt: {scenario_prompt[:100]}...");
                continue 

            # --- Parsing (Unchanged) ---
            parsed = parse_gemini_output(response_text)
            if parsed:
                return parsed # Success!
            else:
                print("   Parsing failed. Retrying if possible...")
                
        # --- !! MODIFIED Error Handling !! ---
        except Exception as e:
            error_str = str(e); 
            
            # --- THIS IS THE NEW LOGIC ---
            if "Resource has been exhausted" in error_str or "429" in error_str or "rate limit" in error_str.lower():
                print(f"🚦 Rate Limit Hit (Attempt {attempt + 1}/{retries}).")
                new_client = rotate_client_and_key() # Rotate the global client
                if new_client:
                    print("   Retrying with new key...")
                    continue # Retry the loop immediately with the new client
                else:
                    print("   Max retries reached after key rotation failure. Skipping transcript."); 
                    return None
            # ---------------------------
            
            elif "internal server error" in error_str.lower() or "500" in error_str or "service unavailable" in error_str.lower():
                 wait_time = 10 * (attempt + 1); print(f"🔧 API Internal/Unavailable Error (Attempt {attempt + 1}/{retries}). Retrying in {wait_time}s...")
                 time.sleep(wait_time)
            else:
                print(f"🛑 API Error (Attempt {attempt + 1}/{retries}): {e}");
                if attempt < retries - 1:
                    wait_time = 7 * (attempt + 1); print(f"   Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print("   Max retries reached for general error. Skipping transcript."); return None

    print("   All retry attempts failed after loop completion."); return None
