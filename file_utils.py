# file_utils.py
"""Functions for saving the generated dataset."""

import json
from pathlib import Path
from datetime import datetime
import sys

# Import OUTPUT_DIR from config
try:
    # Ensure config.py is in the same directory or Python path
    from config import OUTPUT_DIR
except ImportError:
    print("❌ FATAL: Cannot import OUTPUT_DIR from config.py.")
    # Fallback or exit - Using a fallback might save data unexpectedly
    print("   Please ensure config.py is present.")
    sys.exit(1)


def write_json_output(records: list):
    """Saves the generated records ONLY to a structured JSON file."""
    if not records:
        print("\n⚠️ No records were successfully generated. Skipping JSON output file creation.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Make filename more descriptive if needed
    base_filename = f"kusmus_structured_dataset_modular_{timestamp}"
    json_path = OUTPUT_DIR / f"{base_filename}.json"
    try:
        # Use ensure_ascii=False for proper handling of native scripts
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved Master JSON (Full Structure): {json_path}")
        print(f"✅ {len(records)} total transcripts processed and saved.")
    except Exception as e:
        print(f"❌ Error saving JSON to '{json_path}': {e}")
