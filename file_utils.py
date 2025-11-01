# file_utils.py
"""Functions for saving the generated dataset."""

import json
import re  # --- NEW: Import regex for cleaning filenames ---
from pathlib import Path
from datetime import datetime
import sys
from collections import defaultdict

# Import OUTPUT_DIR from config
try:
    # Ensure config.py is in the same directory or Python path
    from config import OUTPUT_DIR
except ImportError:
    print("❌ FATAL: Cannot import OUTPUT_DIR from config.py.")
    print("   Please ensure config.py is present.")
    sys.exit(1)


def write_json_output(records: list):
    """
    Saves the generated records to a main structured JSON file (grouped by
    language) AND saves a separate JSON file for each individual language.
    """
    if not records:
        print("\n⚠️ No records were successfully generated. Skipping JSON output file creation.")
        return

    # --- 1. Restructure the flat list into a dictionary by language ---
    print(f"\n🔄 Restructuring {len(records)} records by language...")
    structured_data = defaultdict(list)
    
    for record in records:
        language = record.get("language", "Unspecified")
        structured_data[language].append(record)

    # Convert defaultdict to a regular dict
    final_data_structure = dict(structured_data)
    
    # --- 2. Save the Main Merged File (Grouped by Language) ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"kusmus_structured_dataset_by_language_{timestamp}"
    json_path = OUTPUT_DIR / f"{base_filename}.json"
    
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(final_data_structure, f, indent=2, ensure_ascii=False)
            
        print(f"\n💾 Saved Main Merged JSON (Structured by Language): {json_path}")
        print(f"✅ {len(records)} total transcripts processed and saved.")
    except Exception as e:
        print(f"❌ Error saving Main Merged JSON to '{json_path}': {e}")
        # We can choose to stop here or continue to save individual files
        # For robustness, let's continue if possible.
        
    # --- 3. Save Individual Language Files (NEW) ---
    print(f"\n💾 Saving individual language JSON files...")
    
    for language, language_records in final_data_structure.items():
        try:
            # Create a "slug" from the language name for a safe filename
            # "Yoruba (with all native diacritics)" -> "yoruba_with_all_native_diacritics"
            slug = language.lower()
            slug = re.sub(r'[\s\(\)]+', '_', slug)  # Replace spaces and parens with _
            slug = re.sub(r'_+', '_', slug)          # Collapse multiple underscores
            slug = re.sub(r'[^a-z0-9_]', '', slug)   # Remove any remaining invalid chars
            slug = slug.strip('_')                  # Clean up ends
            
            if not slug:
                slug = "unspecified"
            
            # Use the same timestamp as the main file for easy batching
            lang_filename = f"kusmus_lang_{slug}_{timestamp}.json"
            lang_path = OUTPUT_DIR / lang_filename
            
            with open(lang_path, "w", encoding="utf-8") as f:
                # Save the list of records directly, not the whole dict
                json.dump(language_records, f, indent=2, ensure_ascii=False)
                
            print(f"   > Saved ({len(language_records)} records): {lang_path}")
            
        except Exception as e:
            print(f"❌ Error saving individual file for '{language}': {e}")
