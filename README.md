Perfect! Now I have the real details. Let me create a **truthful, honest README** that documents what you actually built:Okay, here's a **truthful README** based on what your repo ACTUALLY does:

```markdown name=README.md url=https://github.com/pwoprurho/Kus_org/blob/main/README.md

# Kus_org: Customer Service Transcript Generation Engine

A Python-based system to generate realistic, multi-language customer service call transcripts using Google's Gemini API. Transcripts cover diverse Nigerian industries including banking, corporate services, telecommunications, and public safety.

## What It Does

**Kus_org generates synthetic customer service transcripts** in 5 Nigerian languages (English, Pidgin, Yoruba, Igbo, Hausa) across 20+ industry scenarios using Gemini 2.5 Flash.

- **Input**: Scenario definitions (JSON) with detailed prompts
- **Process**: AI-powered generation with configurable rate limiting
- **Output**: Realistic transcripts + metadata (sentiment, emotions, identity verification methods)
- **Format**: Structured JSON files organized by language

## Quick Start

### Prerequisites
- Python 3.10+
- Google Gemini API key(s)

### Installation

```bash
# Clone repo
git clone https://github.com/pwoprurho/Kus_org.git
cd Kus_org

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cat > .env << 'EOF'
GEMINI_API_KEY_1=your_api_key_here
GEMINI_API_KEY_2=your_second_key_optional  # Up to 10 keys supported
MODEL_NAME=gemini-2.5-flash
TRANSCRIPTS_PER_SCENARIO=20
EOF
```

### Running Generation

```bash
# Generate all scenarios
python generate_kusmus_data_v8_modular.py

# Filter by language
python generate_kusmus_data_v8_modular.py -l "Nigerian Pidgin"

# Custom rate limiting (60 requests per minute)
python generate_kusmus_data_v8_modular.py -r 60

# Custom sleep interval (0.5 seconds between API calls)
python generate_kusmus_data_v8_modular.py -s 0.5

# Combined example: Nigerian Pidgin at 60 RPM
python generate_kusmus_data_v8_modular.py -l "Nigerian Pidgin" -r 60
```

Generated data appears in `kusmus_gold_standard_raw_v3/` as timestamped JSON files.

## Architecture

### Core Components

```
generate_kusmus_data_v8_modular.py
  ├─ Main orchestrator
  ├─ CLI argument parsing (-l, -r, -s flags)
  ├─ Scenario filtering & batching
  └─ Progress tracking with ETA

config.py
  ├─ API key pool management (up to 10 keys)
  ├─ Model configuration (Gemini 2.5 Flash)
  ├─ Scenario loading (20+ JSON files)
  ├─ System prompt loading
  └─ Safety settings

gemini_utils.py
  ├─ Gemini client initialization
  ├─ API call handling with retry logic
  ├─ Rate limit handling (429 errors trigger key rotation)
  ├─ Response streaming & parsing
  └─ Error recovery

utils.py
  ├─ Case ID generation (scenario-specific prefixes)
  └─ ISO 8601 timestamp generation

file_utils.py
  ├─ JSON output writing
  ├─ Language-based file grouping
  └─ Individual per-language file creation
```

### Data Flow

```
Scenario JSON (e.g., scenarios_banking.json)
        ↓
 Gemini 2.5 Flash Generation
        ↓
 Transcript + JSON Metadata
        ↓
 Error Handling & Validation
        ↓
 kusmus_gold_standard_raw_v3/
   ├─ kusmus_structured_dataset_by_language_*.json
   └─ kusmus_lang_*_*.json (individual language files)
```

## Scenario Structure

Each scenario JSON defines:
- `id`: Unique identifier (e.g., "UnauthorizedDebit-English")
- `industry`: Industry category (Banking, Corporate, PublicSafety-Police, etc.)
- `language`: Target language (Standard Nigerian English, Nigerian Pidgin, Yoruba, Igbo, Hausa)
- `direction`: Inbound or Outbound call
- `prompt`: Detailed instructions for Gemini on what transcript to generate

### Example Scenario

```json
{
  "id": "UnauthorizedDebit-English",
  "industry": "Banking",
  "language": "Standard Nigerian English",
  "direction": "Inbound",
  "prompt": "Generate a realistic transcript in Standard Nigerian English. A customer calls, angry about an unauthorized POS debit on their savings account. The agent must be empathetic, verify identity (phone + account last 4), confirm the debit details, block the card, raise a fraud case (provide a case ID like UBD-XXXX), and assure the customer of investigation. Include recording consent."
}
```

## Supported Industries & Languages

### Industries (20+) could add or remove depending on use case

**Banking** (scenerio_banking.json)
- Unauthorized debits, billing disputes, account info requests, product suggestions
- 5 languages × 5 scenarios = 25 banking transcripts

**Corporate** (scenarios_corporate.json)
- Meeting scheduling, interview rescheduling, account escalations, feature suggestions
- 5 languages × 5 scenarios = 25 corporate transcripts

**Public Safety - Police** (scenario_police.json)
- Non-emergency info requests, misconduct complaints, community suggestions, emergency reporting (armed robbery, bandit attacks)
- 5 languages × 6 scenario types = 30+ police transcripts

**Telecommunications** (scenarios_telecom.json)
- Technical support, service activation, billing issues, network troubleshooting

**Healthcare** (scenarios_healthcare.json)
- Appointment scheduling, prescription inquiries, medical advice

**E-commerce** (scenarios_ecommerce.json)
- Order tracking, returns, payment issues

**And more**: Education, Hospitality, Transportation, Security, Military, etc.

### Languages (5) could add or remove depending 9n use case

| Language | Diacritics | Example |
|----------|-----------|---------|
| **Standard Nigerian English** | N/A | "Hello, how can I help?" |
| **Nigerian Pidgin** | N/A | "Wetin happen nah?" |
| **Yoruba** | ✅ Yes | "Wọ́n ti yọ owó mi!" |
| **Igbo** | ✅ Yes | "Ha ewerela ego m!" |
| **Hausa** | ✅ Yes | "An cire min kuɗi!" |

## Generated Data Format

Each transcript record includes:

```json
{
  "id": 1,
  "language": "Standard Nigerian English",
  "scenario": "UnauthorizedDebit-English",
  "industry": "Banking",
  "call_direction": "Inbound",
  "transcript": "[AGENT]: Hello, thank you for calling our bank...",
  "analysis": {
    "sentiment": {
      "score": -0.45,
      "label": "negative"
    },
    "emotion": {
      "dominant": "frustration",
      "intensity": 0.7
    },
    "tone_classifier": "frustrated",
    "contains_profanity": false,
    "agent_note": "Customer angry about unauthorized debit; needs card block & fraud case",
    "identity_confirmation": {
      "confirmed": true,
      "method": "phone+account_last4"
    },
    "social_engineering": {
      "detected": false,
      "trigger_phrase": null,
      "action_taken": null
    },
    "prompt_injection": {
      "detected": false,
      "trigger_phrase": null
    },
    "compliance": {
      "regulatory": {
        "jurisdiction": "NG",
        "industry_rules": ["CBN"],
        "recording_consent": true
      },
      "ai": {
        "model_name": "KUS-ROBERTA-001",
        "version": "v3",
        "quarantine_for_training": false,
        "human_review_required": false
      }
    }
  },
  "sentiment_score": -0.45,
  "sentiment_label": "negative",
  "emotion": {
    "dominant": "frustration",
    "intensity": 0.7
  },
  "tone_classifier": "frustrated",
  "agent_note": "Customer angry about unauthorized debit; needs card block & fraud case",
  "meta": {
    "case_id": "UBD-A1B2C3D4",
    "timestamp": "2025-03-18T10:32:00Z"
  },
  "quarantine": false
}
```

## Configuration

### Command-Line Options

```bash
-l, --language   Filter by language name (e.g., "Nigerian Pidgin")
-s, --sleep      Sleep interval between API calls in seconds (default: 1.5)
-r, --rpm        Set requests per minute (overrides --sleep)
```

### Environment Variables (.env)

```bash
GEMINI_API_KEY_1      # Primary API key (required)
GEMINI_API_KEY_2...10 # Additional keys for parallel processing
MODEL_NAME            # Gemini model to use (default: gemini-2.5-flash)
TRANSCRIPTS_PER_SCENARIO  # How many transcripts per scenario (default: 20)
```

## Rate Limiting & API Key Rotation

- **Default**: 1.5 seconds between requests (40 RPM)
- **Multi-key support**: Up to 10 API keys for 10x throughput
- **Automatic rotation**: On rate limit (429 errors), system rotates to next key
- **Backoff strategy**: Exponential retry with 60-second reset if all keys exhausted

## Output Files

Generated data is saved to `kusmus_gold_standard_raw_v3/` with two file types:

**1. Main merged file** (grouped by language):
```
kusmus_structured_dataset_by_language_20250318_103200.json
{
  "Standard Nigerian English": [ ... 100 records ... ],
  "Nigerian Pidgin": [ ... 100 records ... ],
  ...
}
```

**2. Individual language files**:
```
kusmus_lang_standard_nigerian_english_20250318_103200.json
kusmus_lang_nigerian_pidgin_20250318_103200.json
kusmus_lang_yoruba_with_all_native_diacritics_20250318_103200.json
...
```

## Project Structure

```
kus_org/
├── README.md                               # This file
├── requirements.txt                        # Python dependencies
├── .env                                    # API keys (gitignored)
├── .gitignore
│
├── Core Modules:
│   ├── generate_kusmus_data_v8_modular.py # Main orchestrator
│   ├── config.py                          # Configuration & API setup
│   ├── gemini_utils.py                    # Gemini API interface
│   ├── utils.py                           # Helper functions
│   └── file_utils.py                      # JSON output handling
│
├── Prompts & Scenarios:
│   ├── system_prompt.txt                  # Master generation template
│   ├── scenerio_banking.json              # Banking scenarios (5 variants)
│   ├── scenarios_corporate.json           # Corporate scenarios
│   ├── scenario_police.json               # Police/Public Safety scenarios
│   ├── scenarios_telecom.json             # Telecom scenarios
│   ├── scenarios_healthcare.json          # Healthcare scenarios
│   ├── scenarios_education.json           # Education scenarios
│   ├── scenarios_ecommerce.json           # E-commerce scenarios
│   ├── scenarios_hospitality.json         # Hospitality scenarios
│   ├── scenarios_security.json            # Security scenarios
│   ├── scenarios_transportation.json      # Transportation scenarios
│   ├── scenarios_military.json            # Military scenarios
│   └── ... (more scenarios)
│
├── Output:
│   └── kusmus_gold_standard_raw_v3/       # Generated JSON files
│       ├── kusmus_structured_dataset_by_language_*.json
│       └── kusmus_lang_*_*.json
│
└── venv/                                  # Virtual environment (gitignored)
```

## Key Features

### 1. **Multi-Language Support**
Generate realistic transcripts in 5 Nigerian languages with proper diacritics for Yoruba, Igbo, and Hausa.

### 2. **Rich Metadata**
Each transcript includes:
- Sentiment analysis (score -1.0 to 1.0, label)
- Emotion classification (dominant emotion + intensity)
- Tone classification
- Identity confirmation method used
- Social engineering detection flags
- Prompt injection detection flags
- Compliance metadata (jurisdiction, industry rules, recording consent)
- Case ID generation
- ISO 8601 timestamps

### 3. **Intelligent Rate Limiting**
- Configurable sleep intervals or RPM targets
- Multi-API key support (up to 10 keys)
- Automatic key rotation on rate limits
- Exponential backoff with recovery

### 4. **Robust Error Handling**
- Graceful handling of API errors
- Validation of response completeness
- Detailed error messages with recovery suggestions
- Progress tracking with ETA calculations

### 5. **Language-Based Organization**
- Automatic grouping of records by language
- Individual per-language JSON files for easy filtering
- Merged file with all languages for comprehensive datasets

## Dependencies

```
google-generativeai==0.7.1  # Gemini API
python-dotenv              # Environment variable loading
datasets                   # Dataset utilities
huggingface_hub           # Hugging Face integration
```

See `requirements.txt` for full list.

## Example Usage

### Generate 100 Nigerian Pidgin Banking Transcripts

```bash
python generate_kusmus_data_v8_modular.py -l "Nigerian Pidgin" -r 60
```

This will:
1. Load banking scenarios in Nigerian Pidgin
2. Generate 20 transcripts per scenario
3. Throttle to 60 requests per minute
4. Save results to `kusmus_gold_standard_raw_v3/`

### Monitor Progress

```
🚀 Initializing Kusmus Modular Data Factory (Model: gemini-2.5-flash) at 2025-03-18 14:30:45...
   Batch: Nigerian Pidgin
   Config: 5 scenarios, 20 transcripts/scenario
   Rate: 1.0s sleep (60.0 RPM)
================================================================================

🎬 [1/5] Generating 20 for: UnauthorizedDebit-Pidgin (Nigerian Pidgin)...
   > Progress: 18/20 attempted (20/20) | Avg: 2.45s | ETA Scen: 34s 
   > Done: UnauthorizedDebit-Pidgin. Generated 20/20 successfully in 49.0s.

🎬 [2/5] Generating 20 for: BillingDispute-Pidgin (Nigerian Pidgin)...
   ...

--- Generation Complete ---
Success: 100/100 transcripts generated in 245.32s.

💾 Saved Main Merged JSON (Structured by Language): kusmus_gold_standard_raw_v3/kusmus_structured_dataset_by_language_20250318_143045.json
✅ 100 total transcripts processed and saved.

💾 Saving individual language JSON files...
   > Saved (100 records): kusmus_gold_standard_raw_v3/kusmus_lang_nigerian_pidgin_20250318_143045.json

🏁 Kusmus Modular Data Factory finished at 2025-03-18 14:35:12
Total execution time: 245.32 seconds.
Average time per transcript: 2.45 seconds.
```

## Notes

- **Gemini 2.5 Flash**: ~2-4 seconds per transcript
- **Multi-key parallel**: 10 keys allows ~10x throughput
- **Default safety**: Harm categories set to BLOCK_NONE for research/training purposes
- **Validation**: Output files are valid UTF-8 JSON

## Contributing

Contributions welcome! Areas for improvement:
- Dashboard UI for data review/editing
- Additional industry scenarios
- Fine-tuning on generated data
- Integration with training pipelines

## License

Proprietary. Generated datasets are owned by the user/organization running this tool.

## Author

**Oghenerurho Akpojotor** (@pwoprurho)
Created: March 18, 2025

---

**What is Kus_org for?** Rapidly generating synthetic Nigerian customer service training data in multiple languages for AI/ML training, testing, and evaluation.

```
