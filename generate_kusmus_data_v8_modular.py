#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_kusmus_data_v8_modular.py
Main orchestrator for Kusmus Data Sprint using modular functions.
Reads config, generates data via Gemini, and saves JSON output.
"""

import sys
import time
import argparse # <-- Keep this for your batching
from datetime import datetime

# --- Import configurations and utility functions ---
try:
    from config import SCENARIOS, NUM_PER_SCENARIO, GEMINI_MODEL_NAME
    from utils import generate_case_id, now_iso
    # Import the *new* analyze_transcript (which manages its own client)
    from gemini_utils import get_gemini_client, analyze_transcript 
    from file_utils import write_json_output
    print("✅ All modules imported successfully.")
except ImportError as e:
    print(f"❌ FATAL: Could not import necessary modules: {e}")
    print("   Ensure config.py, utils.py, gemini_utils.py, and file_utils.py are in the same directory as this script.")
    sys.exit(1)


def generate_scenarios(scenarios_to_run: list, sleep_time: float) -> list: # <-- Removed 'client'
    """
    Main loop using scenarios provided to it.
    Calls analyze_transcript from gemini_utils, which manages its own client.
    """
    all_records = []
    total_expected = len(scenarios_to_run) * NUM_PER_SCENARIO
    print(f"\n--- Starting generation ({total_expected} total transcripts)... ---")
    print(f"--- Using sleep delay: {sleep_time:.2f}s between requests ---")
    
    global_id_counter = 1
    start_time_total = time.time()

    for scenario_index, scenario in enumerate(scenarios_to_run):
        scenario_id = scenario.get('id', f'UnknownScenario_{scenario_index+1}')
        scenario_lang = scenario.get('language', 'Unknown')
        scenario_industry = scenario.get('industry', 'Unknown')
        scenario_direction = scenario.get('direction', 'Unknown')
        scenario_prompt = scenario.get('prompt', '')

        if not scenario_prompt:
            print(f"⚠️ Skipping scenario '{scenario_id}': missing 'prompt' in config.")
            continue

        print(f"\n🎬 [{scenario_index+1}/{len(scenarios_to_run)}] Generating {NUM_PER_SCENARIO} for: {scenario_id} ({scenario_lang})...")
        success_count = 0
        scenario_start_time = time.time()
        
        for i in range(NUM_PER_SCENARIO):
            # --- MODIFIED: No client argument passed ---
            parsed = analyze_transcript(scenario_prompt) 

            if parsed and parsed.get("transcript") and parsed.get("parsed_json"):
                full_json = parsed["parsed_json"]
                
                record = {
                    "id": global_id_counter,
                    "language": scenario_lang, 
                    "scenario": scenario_id, 
                    "industry": scenario_industry, 
                    "call_direction": scenario_direction, 
                    "transcript": parsed["transcript"],
                    **full_json
                }

                meta = record.setdefault("meta", {})
                analysis = record.get("analysis", {})

                is_sec_threat = analysis.get("prompt_injection", {}).get("detected", False) or \
                                analysis.get("social_engineering", {}).get("detected", False)

                if scenario_id not in ["AccountInfoRequest", "PromptInjectionAttack"] and not is_sec_threat:
                    meta.setdefault("case_id", generate_case_id(prefix=scenario_id))
                
                meta.setdefault("timestamp", now_iso())

                all_records.append(record)
                success_count += 1
                global_id_counter += 1
            else:
                print(f"   > Skipping generation {i+1}/{NUM_PER_SCENARIO} due to error.", end="\r")

            elapsed = time.time() - scenario_start_time
            avg_t = elapsed / (i + 1) if (i + 1) > 0 else 0
            eta = avg_t * (NUM_PER_SCENARIO - (i + 1)) if avg_t > 0 else 0
            print(f"   > Progress: {success_count}/{i+1} attempted ({i+1}/{NUM_PER_SCENARIO}) | Avg: {avg_t:.2f}s | ETA Scen: {eta:.0f}s ", end="\r")
            
            # --- Use the controlled sleep time ---
            time.sleep(sleep_time) # This sleep is now for courtesy, not just rate limiting

        scen_dur = time.time() - scenario_start_time
        print(" " * 100, end="\r") 
        print(f"   > Done: {scenario_id}. Generated {success_count}/{NUM_PER_SCENARIO} successfully in {scen_dur:.2f}s.")

    total_dur = time.time() - start_time_total
    print(f"\n--- Generation Complete ---")
    print(f"Success: {len(all_records)}/{total_expected} transcripts generated in {total_dur:.2f}s.")
    if len(all_records) < total_expected:
        print(f"⚠️ Missed {total_expected - len(all_records)} transcripts due to errors or skips.")
    return all_records

# --- Main Execution (MODIFIED) ---
def main():
    # --- Argument Parsing (Unchanged) ---
    parser = argparse.ArgumentParser(description="Kusmus Modular Data Factory")
    parser.add_argument(
        "-l", "--language", 
        type=str, 
        help="Filter scenarios by a specific language name (e.g., 'Nigerian Pidgin')."
    )
    parser.add_argument(
        "-s", "--sleep", 
        type=float, 
        default=1.5, 
        help="Override sleep time between requests (in seconds). Default: 1.5s"
    )
    parser.add_argument(
        "-r", "--rpm",
        type=int,
        help="Set sleep time by Requests Per Minute (RPM). Overrides --sleep."
    )
    args = parser.parse_args()

    # --- Calculate Sleep Time (Unchanged) ---
    sleep_time = args.sleep
    if args.rpm:
        if args.rpm <= 0:
            print("❌ RPM must be greater than 0.")
            sys.exit(1)
        sleep_time = 60.0 / args.rpm
        
    # --- Filter Scenarios (Unchanged) ---
    scenarios_to_run = SCENARIOS
    if args.language:
        print(f"Filtering scenarios for language: '{args.language}'")
        scenarios_to_run = [s for s in SCENARIOS if s.get("language") == args.language]
        if not scenarios_to_run:
            print(f"❌ No scenarios found for language '{args.language}'. Check scenarios.json.")
            all_langs = sorted(list(set(s.get("language") for s in SCENARIOS)))
            for lang in all_langs: print(f"     - {lang}")
            sys.exit(1)
    
    start_time = time.time()
    print(f"🚀 Initializing Kusmus Modular Data Factory (Model: {GEMINI_MODEL_NAME}) at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    print(f"   Batch: {args.language or 'ALL Languages'}")
    print(f"   Config: {len(scenarios_to_run)} scenarios, {NUM_PER_SCENARIO} transcripts/scenario")
    print(f"   Rate: {sleep_time:.2f}s sleep ({60.0/sleep_time:.1f} RPM)")
    print("="*80)

    # --- MODIFIED: Initialize the global client pool ---
    client = get_gemini_client() 
    if not client:
        print("❌ Exiting due to client initialization failure.")
        return 

    # --- MODIFIED: Pass filtered scenarios and sleep time ---
    records = generate_scenarios(scenarios_to_run, sleep_time)

    write_json_output(records)

    end_time = time.time(); total_duration = end_time - start_time
    print("\n" + "="*80); print(f"🏁 Kusmus Modular Data Factory finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total execution time: {total_duration:.2f} seconds.")
    if records: avg_time = total_duration / len(records); print(f"Average time per transcript: {avg_time:.2f} seconds.")
    print("="*80)

if __name__ == "__main__":
    main()def main():
    start_time = time.time()
    print(f"🚀 Initializing Kusmus Modular Data Factory (Model: {GEMINI_MODEL_NAME}) at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    print("="*80)

    # Use imported get_gemini_client
    client = get_gemini_client()
    if not client:
        print("❌ Exiting due to client initialization failure.")
        return # Exit if client fails during init

    # Generate data
    records = generate_scenarios(client)

    # Use imported write_json_output
    write_json_output(records)

    end_time = time.time(); total_duration = end_time - start_time
    print("\n" + "="*80); print(f"🏁 Kusmus Modular Data Factory finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total execution time: {total_duration:.2f} seconds.")
    if records: avg_time = total_duration / len(records) if len(records) > 0 else 0; print(f"Average time per transcript: {avg_time:.2f} seconds.")
    print("="*80)

if __name__ == "__main__":
    main()

# END OF SCRIPT
