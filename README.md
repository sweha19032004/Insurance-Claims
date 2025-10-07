## AI-Powered Insurance Claims Processing System

### Overview
This project ingests claim document bundles (PDFs, images, DOCX, TXT), extracts text via OCR, parses key fields, scores fraud risk, and generates an adjuster summary using an Ollama-hosted LLM.

### Requirements
- Python 3.10+
- MySQL 8+
- Tesseract OCR installed and in PATH (or set `TESSERACT_CMD`)
- Poppler (for `pdf2image`) installed and in PATH on Windows
- Ollama installed and running a compatible model

### Setup
1) Create and activate a virtual environment, then install deps:
```
pip install -r requirements.txt
```

2) Configure environment variables (copy `ENV.example` to `.env` or set in shell):
```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DATABASE=insurance
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
```

3) Prepare MySQL schema:
```
mysql -h %MYSQL_HOST% -P %MYSQL_PORT% -u %MYSQL_USER% -p%MYSQL_PASSWORD% -e "CREATE DATABASE IF NOT EXISTS %MYSQL_DATABASE%"
mysql -h %MYSQL_HOST% -P %MYSQL_PORT% -u %MYSQL_USER% -p%MYSQL_PASSWORD% %MYSQL_DATABASE% < schema.sql
```

4) Start Ollama and create the model (optional, uses default if present):
```
ollama create claims-adjuster -f Modelfile
set OLLAMA_MODEL=claims-adjuster
```

### Running the Pipeline
Put your claim documents into a folder, e.g. `D:\claims\CLM-0001`.

```
python -m app.cli --claim-number CLM-0001 --policy-holder "Jane Doe" --claim-type "Auto" --input-folder D:\claims\CLM-0001 --incident-description "Rear-end collision on 2025-09-01"
```

The script will:
- Register and OCR documents
- Extract fields like policy number, claim number, ICD-10 codes
- Score fraud risk and store it
- Generate an LLM summary and print it

### Notes
- On Windows install Poppler: download binaries and add `bin` to PATH.
- If Tesseract is not auto-detected, set `pytesseract.pytesseract.tesseract_cmd` to `TESSERACT_CMD`.

### Student Tasks
### Optional Streamlit UI
Run a minimal UI for uploads and summary display:

```
streamlit run ui/app.py
```

Enter claim details, upload files, and click Process Claim. The UI writes files to a temp directory and invokes the same pipeline used by the CLI.

- Data Annotation: Label fields such as `policy_number`, `claim_number`, `icd10_code`, document type classes (e.g., `claim_form`, `medical_report`, `policy_doc`), and page-level regions for OCR quality checks. Include entity spans with confidence.
- Fraud Scorecard: Use data points like mismatched policy numbers, excessive ICD codes, missing claim number, inconsistent dates, and repeated providers. Assign integer weights and calibrate thresholds for LOW/MEDIUM/HIGH.
- LLM Prompt: See `app/prompt_template.txt`. Provide structured JSON and snippets; ensure the model sticks to provided facts and outputs a fixed format for easy downstream parsing.

### Additional Docs
- Annotation guidelines and schema: `docs/annotation_guidelines.md`
- Fraud scorecard details: `docs/fraud_scorecard.md`

### Optional FastAPI Service
Run an API to process and fetch summaries:

```
uvicorn api.main:app --reload
```

Endpoints:
- POST /process {claim_number, policy_holder, claim_type, input_folder, incident_description?}
- GET /summary/{claim_number}

### Tests
Run basic tests:
```
pytest -q
```


