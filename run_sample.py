# test_import.py
import sys
import google.generativeai # Import base first to check version easily

print(f"--- Running with Python: {sys.executable} ---")
print(f"--- google-generativeai version: {google.generativeai.__version__} ---") # Confirm version seen by script

try:
    print("Attempting base import...")
    from google import generativeai as genai
    print("✅ Base import OK.")

    print("Attempting types import...")
    # This is the line we're testing
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    print("✅ SUCCESS: All imports worked!")

except ImportError as e:
    print(f"❌ FAILED ImportError: {e}")
    print("\nPython sys.path:")
    for path_item in sys.path:
        print(f"- {path_item}")
except Exception as e:
    print(f"❌ FAILED with unexpected error: {e}")
