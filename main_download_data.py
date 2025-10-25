# main_download_data.py
# This script programmatically downloads our source dataset from Hugging Face.

from datasets import load_dataset
import os

# --- CONFIGURATION ---
DATASET_NAME = "benjaminogbonna/nigerian_common_voice_dataset"
LOCAL_CACHE_DIR = "./hf_dataset_cache/" # We'll save it locally to a cache
CONFIG_NAME = "all" # This dataset has multiple 'configs' (languages). Let's get all of them.

# --- 1. SET UP ENVIRONMENT ---
# This ensures our script has a place to save the files.
os.makedirs(LOCAL_CACHE_DIR, exist_ok=True)
print(f"--- Preparing to download dataset: {DATASET_NAME} ---")

# --- 2. LOAD (AND DOWNLOAD) THE DATASET ---
# This one command does everything.
# It will authenticate (you may need to log in via terminal),
# download all the language files, and load them into a dataset object.
# This will take some time, as it is a very large dataset.
try:
    dataset = load_dataset(
        DATASET_NAME,
        name=CONFIG_NAME,
        cache_dir=LOCAL_CACHE_DIR
    )

    print("\n--- Download and Load Successful ---")
    print("The following languages (configs) are available:")
    print(dataset.keys())

    # Example: You can now access the 'hausa' split
    # hausa_train = dataset['hausa']['train']
    # print(f"\nExample: Loaded {len(hausa_train)} training samples for Hausa.")

except Exception as e:
    print(f"\n--- An Error Occurred ---")
    print(f"Error: {e}")
    print("Please ensure you are logged into Hugging Face (use 'huggingface-cli login')")
    print("and that you have an internet connection.")

