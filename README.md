# Scene-The_Writers_Room

# Story Generation API

## Setup Instructions

### 1. Create a Virtual Environment

#### On macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

#### On Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### 2. Install Dependencies
Once the virtual environment is activated, install the required packages:
```bash
pip install fastapi uvicorn pydantic requests torch transformers
```

## Running the API

### 3. Ensure Required Files Are Present
Make sure the following files exist in the project directory:
- **apitofunc.py** (Contains `generate_initial_scene`, `generate_scene`, `generate_dialogue`, `generate_ending_scene`)
- **label_prediction_model.py** (Contains `LabelPredictionModel` class)
- **endpoints.py** (This file)

### 4. Update Model Path
Modify the `model_path` variable in `endpoints.py` to point to your actual `RobertaForSequenceClassification` model.

### 5. Start the Server
Run the following command to launch the FastAPI server:
```bash
uvicorn endpoints:app --reload
```

### 6. Test the API
Send a POST request to `http://127.0.0.1:8000/generate_complete_story` with the following JSON body:
```json
{
  "setting": "a haunted castle on a stormy night",
  "character1": { "name": "Alice", "trait": "a curious traveler" },
  "character2": { "name": "Marcus", "trait": "a stoic guardian" }
}
```

### 7. Expected JSON Response
The API will return a structured JSON response:
```json
{
  "initial_scene": "...",
  "main_body": [
    {"label": "Scene", "text": "..."},
    {"label": "Character", "text": "..."},
    ...
  ],
  "ending_scene": "..."
}
```

## Notes
- Ensure your Python version is 3.8 or higher.
- If you encounter issues with dependencies, try upgrading pip:
  ```bash
  pip install --upgrade pip
  ```
- To deactivate the virtual environment, use:
  ```bash
  deactivate  # macOS/Linux
  venv\Scripts\deactivate  # Windows
  ```

