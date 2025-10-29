# gemini_utils.py
"""Functions for interacting with the Google Gemini API."""

import sys
import json
import re
import time

# --- Dependency Check & Import ---
try:
    from google import generativeai as genai # Correct import alias
    # Import safety types directly (assuming latest library version or compatible structure)
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    print("✅ google-generativeai imported correctly in gemini_utils.")
except ImportError:
    print("❌ Missing dependency in gemini_utils: Please install/upgrade `pip install --upgrade google-generativeai`")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error importing google.generativeai in gemini_utils: {e}")
    sys.exit(1)

# --- Import necessary config variables ---
try:
    # Ensure config.py is in the same directory or Python path
    from config import GEMINI_MODEL_NAME, SYSTEM_PROMPT, SAFETY_SETTINGS
except ImportError:
    print("❌ FATAL: Cannot import from config.py in gemini_utils. Ensure it exists.")
    sys.exit(1)

def get_gemini_client():
    """Initializes the Gemini model WITHOUT system prompt."""
    try:
        # Initialize model WITHOUT system_instruction for flash model compatibility
        model = genai.GenerativeModel(
            GEMINI_MODEL_NAME,
            # system_instruction=SYSTEM_PROMPT, # REMOVED
            safety_settings=SAFETY_SETTINGS
        )
        print("🧪 Performing quick API test call...")
        # Use a more robust test prompt
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
    except ValueError as ve:
         # Catch the specific ValueError related to system instruction if it still occurs
         if "System instruction is not supported" in str(ve):
              print(f"❌ FATAL: Model '{GEMINI_MODEL_NAME}' does not support system_instruction at initialization. Code needs adjustment.")
         else:
              print(f"❌ FATAL: ValueError during Gemini client initialization: {ve}")
         sys.exit(1)
    except Exception as e:
        print(f"❌ FATAL: Failed to initialize Gemini client: {e}")
        print("   Please check your API Key (in .env), internet connection, model name.")
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
    # More aggressive cleaning
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
            q_str = str(q_val).lower(); parsed_json['quarantine']=True if q_str=='true' else False if q_str=='false' else (_ for _ in ()).throw(ValueError(f"Invalid 'quarantine' value: {q_val}"))
        # Add more specific nested validation if needed
        # e.g., check analysis["sentiment"]["label"] exists
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
    Sends prompt to Gemini (prepending SYSTEM_PROMPT), handles retries,
    robustly checks safety ratings and response structure, parses output.
    Returns the parsed data structure {'transcript': ..., 'parsed_json': ...} or None.
    """
    retries = 3
    # --- PREPEND SYSTEM PROMPT ---
    # Combine the loaded system prompt with the specific scenario prompt
    full_prompt = f"{SYSTEM_PROMPT}\n\n---\n\n**NOW, GENERATE FOR THIS SPECIFIC SCENARIO:**\n{scenario_prompt}"

    for attempt in range(retries):
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=0.8, # Balance creativity and consistency
                max_output_tokens=2048 # Ensure enough space
            )
            # --- USE FULL PROMPT HERE ---
            response = client.generate_content(
                full_prompt, # Pass the combined prompt
                generation_config=generation_config
            )

            # --- Robust Safety/Block Check ---
            finish_reason = None
            safety_blocked = False
            candidate = response.candidates[0] if hasattr(response, 'candidates') and response.candidates else None
            response_text = None # Initialize response_text

            if candidate:
                # 1. Check Safety Ratings FIRST
                safety_ratings = getattr(candidate, 'safety_ratings', [])
                if any(rating.category != HarmCategory.HARM_CATEGORY_UNKNOWN and rating.probability >= HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE for rating in safety_ratings):
                    safety_blocked = True
                    print(f"⚠️ SAFETY Block Detected (Rating). Prompt: {scenario_prompt[:100]}...")
                    # Optionally log more details about the specific rating
                    # for rating in safety_ratings:
                    #     if rating.probability >= HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE:
                    #         print(f"   Blocked Category: {rating.category}, Probability: {rating.probability}")
                    return None # Critical: Exit immediately if blocked by rating

                # 2. Get Finish Reason (if not blocked by rating)
                finish_reason = getattr(candidate, 'finish_reason', None)

                # 3. Check Finish Reason (if not blocked by rating)
                # Reason 1 = STOP (Normal), 2 = MAX_TOKENS, 3 = SAFETY, 4=RECITATION, 5=OTHER
                if not safety_blocked and finish_reason != 1:
                    print(f"⚠️ Generation Finished Unexpectedly (Reason: {finish_reason}). Prompt: {scenario_prompt[:100]}...");
                    # Specific handling based on reason
                    if finish_reason == 3: print("   Safety Block explicitly indicated by finish_reason.")
                    elif finish_reason == 2: print("   Max Tokens Reached. Output truncated?")
                    # Treat other non-STOP reasons as failures for now
                    return None # Skip non-normal completions

                # 4. Extract Text Content (if finished normally)
                content = getattr(candidate, 'content', None)
                parts = getattr(content, 'parts', [])
                # --- THIS IS THE KEY FIX ---
                if parts and hasattr(parts[0], 'text'):
                    response_text = parts[0].text # Primary way to get text
                elif hasattr(response, 'text'): # Fallback just in case
                    print("   Falling back to response.text")
                    response_text = response.text
                # --- END OF KEY FIX ---

            # If after all checks, we still don't have text, it's an invalid response
            if not response_text:
                print(f"⚠️ Invalid Response Structure (No text content extracted). Prompt: {scenario_prompt[:100]}...");
                return None # Skip empty/invalid responses

            # --- Parse Output ---
            # Now we are reasonably sure response_text contains the expected output
            parsed = parse_gemini_output(response_text)
            if parsed: return parsed # Success!
            else:
                print("   Parsing failed. Retrying if possible...")
                # Optional: Add small delay specific to parsing failure before retry
                # time.sleep(1)


        # --- Error Handling (remains the same) ---
        except Exception as e:
            error_str = str(e); wait_time = 0
            # Handle specific retryable errors more granularly
            if "Resource has been exhausted" in error_str or "429" in error_str or "rate limit" in error_str.lower():
                wait_time = 20 * (attempt + 1); print(f"🚦 Rate Limit (Attempt {attempt + 1}/{retries}). Retrying in {wait_time}s...")
            elif "internal server error" in error_str.lower() or "500" in error_str or "service unavailable" in error_str.lower():
                 wait_time = 10 * (attempt + 1); print(f"🔧 API Internal/Unavailable Error (Attempt {attempt + 1}/{retries}). Retrying in {wait_time}s...")
            else: # General errors
                print(f"🛑 API Error (Attempt {attempt + 1}/{retries}): {e}");
                # Only retry general errors if it's not the last attempt
                if attempt < retries - 1:
                    wait_time = 7 * (attempt + 1); print(f"   Retrying in {wait_time}s...")
                else:
                    print("   Max retries reached."); return None # Exit retries

            if wait_time > 0: time.sleep(wait_time) # Sleep only if retrying

    print("   All retry attempts failed after loop completion."); return None            generation_config = genai.types.GenerationConfig(
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
