#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_kusmus_data_v8_modular.py
Main orchestrator for Kusmus Data Sprint using modular functions.
Reads config, generates data via Gemini, and saves JSON output.
"""

import sys
import time
from datetime import datetime

# Import configurations and utility functions
try:
    # Ensure Python can find the modules in the current directory
    # If running as a script, '.' should be implicitly in sys.path
    # If importing from elsewhere, adjust sys.path if needed
    from config import SCENARIOS, NUM_PER_SCENARIO, GEMINI_MODEL_NAME
    from utils import generate_case_id, now_iso
    from gemini_utils import get_gemini_client, analyze_transcript
    from file_utils import write_json_output
    print("✅ All modules imported successfully.")
except ImportError as e:
    print(f"❌ FATAL: Could not import necessary modules: {e}")
    print("   Ensure config.py, utils.py, gemini_utils.py, and file_utils.py are in the same directory as this script.")
    sys.exit(1)


def generate_scenarios(client) -> list:
    """
    Main loop using scenarios loaded from config.
    Calls analyze_transcript from gemini_utils.
    """
    all_records = []
    # Use SCENARIOS loaded from config.py
    total_expected = len(SCENARIOS) * NUM_PER_SCENARIO
    print(f"\n--- Starting generation ({total_expected} total transcripts)... ---")
    global_id_counter = 1; start_time_total = time.time()

    for scenario_index, scenario in enumerate(SCENARIOS):
        # Safely get scenario details with defaults from loaded config
        scenario_id=scenario.get('id',f'UnknownScenario_{scenario_index+1}')
        scenario_lang=scenario.get('language','Unknown')
        scenario_industry=scenario.get('industry','Unknown')
        scenario_direction=scenario.get('direction','Unknown')
        scenario_prompt=scenario.get('prompt','') # The actual prompt for Gemini

        if not scenario_prompt:
            print(f"⚠️ Skipping scenario '{scenario_id}': missing 'prompt' in config.")
            continue

        print(f"\n🎬 [{scenario_index+1}/{len(SCENARIOS)}] Generating {NUM_PER_SCENARIO} for: {scenario_id} ({scenario_lang})...");
        success_count=0; scenario_start_time=time.time()
        for i in range(NUM_PER_SCENARIO):
            # Use the imported analyze_transcript function
            parsed = analyze_transcript(client, scenario_prompt)

            if parsed and parsed.get("transcript") and parsed.get("parsed_json"):
                full_json=parsed["parsed_json"];
                # Assemble record using data from config and parsed JSON
                record={"id":global_id_counter,"language":scenario_lang,"scenario":scenario_id,"industry":scenario_industry,"call_direction":scenario_direction,"transcript":parsed["transcript"],**full_json}

                # Use imported utility functions for meta fields
                meta=record.get("meta",{}); analysis=record.get("analysis",{})
                is_sec_threat=analysis.get("prompt_injection",{}).get("detected",False) or analysis.get("social_engineering",{}).get("detected",False)

                # Add Case ID only if relevant scenario and not a security threat
                if "case_id" not in meta and scenario_id not in ["AccountInfoRequest","PromptInjectionAttack"] and not is_sec_threat:
                    meta.setdefault("case_id",generate_case_id(prefix=scenario_id[:4].upper()))
                # Add Timestamp if not provided
                if "timestamp" not in meta:
                    meta.setdefault("timestamp",now_iso())
                record["meta"]=meta;

                all_records.append(record); success_count+=1; global_id_counter+=1
            else:
                print(f"   > Skipping gen {i+1}/{NUM_PER_SCENARIO} due to error.", end="\r")

            # Progress update
            elapsed=time.time()-scenario_start_time; avg_t=elapsed/(i+1) if (i+1)>0 else 0; eta=avg_t*(NUM_PER_SCENARIO-(i+1)) if avg_t>0 else 0
            print(f"   > Progress: {success_count}/{i+1} attempted ({i+1}/{NUM_PER_SCENARIO}) | Avg: {avg_t:.2f}s | ETA: {eta:.0f}s", end="\r")
            # Rate limiting - adjust sleep time based on API limits (e.g., 60 RPM for flash)
            time.sleep(1.5) # ~40 RPM - Increase if hitting limits

        scen_dur=time.time()-scenario_start_time;
        # Clear progress line before printing final status
        print(" " * 80, end="\r") # Clear the line
        print(f"   > Done: {scenario_id}. Generated {success_count}/{NUM_PER_SCENARIO} successfully in {scen_dur:.2f}s.")

    total_dur=time.time()-start_time_total; print(f"\n--- Generation Complete ---"); print(f"Success: {len(all_records)}/{total_expected} transcripts in {total_dur:.2f}s.")
    if len(all_records)<total_expected: print(f"⚠️ Missed {total_expected-len(all_records)} transcripts due to errors or skips.")
    return all_records

# --- Main Execution ---
def main():
    start_time = time.time()
    print(f"🚀 Initializing Kusmus Modular Data Factory (Model: {GEMINI_MODEL_NAME}) at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    print("="*80)

    # Use imported get_gemini_client
    client = get_gemini_client()
    if not client: return # Exit if client fails during init

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
