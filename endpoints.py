# endpoints.py

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Dict
import logging
import json

# Import our previously defined functions and model
# Make sure these files (apitofunc.py and label_prediction_model.py) are in the same directory or properly installed.
from ApitoFunc import (
    generate_initial_scene,
    generate_scene,
    generate_dialogue,
    generate_ending_scene
)
from label_prediction_model import LabelPredictionModel

# -------------------------------------------------------------
# 1. Setup Logging
# -------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------
# 2. Define Pydantic Schemas
# -------------------------------------------------------------
class CharacterSchema(BaseModel):
    name: str = Field(..., description="The name of the character.")
    trait: str = Field(..., description="A short trait or description of the character.")

class StoryInputSchema(BaseModel):
    setting: str = Field(..., description="The setting for the story (e.g., 'a futuristic city').")
    character1: CharacterSchema
    character2: CharacterSchema

class StoryPartSchema(BaseModel):
    label: str = Field(..., description="Label for this part of the story (e.g., 'Scene' or 'Character').")
    text: str = Field(..., description="The generated text for this story part.")

class StoryOutputSchema(BaseModel):
    initial_scene: str = Field(..., description="The initial scene text.")
    main_body: List[StoryPartSchema] = Field(..., description="List of story segments generated in the main body.")
    ending_scene: str = Field(..., description="The ending scene text.")

# -------------------------------------------------------------
# 3. Initialize FastAPI
# -------------------------------------------------------------
app = FastAPI(
    title="Movie Script Generation API",
    description="""
    This API endpoint `generate_complete_story` generates a complete story (initial scene, main body, and ending scene) 
    based on a given setting and two characters (with names and traits). 
    It uses a label prediction model to decide whether to generate dialogue or a scene in each iteration. 
    """,
    version="1.0.0",
)

# -------------------------------------------------------------
# 4. Load the Label Prediction Model
# -------------------------------------------------------------
# Update 'model_path' to the actual path or huggingface checkpoint for your trained model.
model_path = "trained_roberta_dialogue_model"
label_model = LabelPredictionModel(model_path)

# We'll unify the label map:
# 0: 'Scene'
# 1: 'Scene description' -> treat as 'Scene'
# 2: 'Character'
# 3: 'Dialogue'          -> treat as 'Character' (since we want to generate dialogue if we see 'Character' or 'Dialogue')
# 4: 'Dialogue metadata' -> treat as 'Scene'
# 5: 'Metadata'          -> treat as 'Scene'
# 6: 'Transition'        -> treat as 'Scene'
# 
# So effectively:
#   if label in ['Scene', 'Scene description', 'Dialogue metadata', 'Metadata', 'Transition'] => "Scene"
#   if label in ['Character', 'Dialogue'] => "Character"

def unify_label(predicted_label: str) -> str:
    """
    Convert the raw label from the prediction to one of:
      - "Scene" for scene-related labels,
      - "Character" for character labels,
      - "Dialogue" for dialogue labels.
    """
    if predicted_label in ["Scene", "Scene description", "Dialogue metadata", "Metadata", "Transition"]:
        return "Scene"
    elif predicted_label == "Character":
        return "Character"
    elif predicted_label == "Dialogue":
        return "Dialogue"
    # Fallback to "Scene" if not recognized.
    return "Scene"


# -------------------------------------------------------------
# 5. The Main Endpoint
# -------------------------------------------------------------
@app.post("/generate_complete_story", response_model=StoryOutputSchema)
def generate_complete_story(story_input: StoryInputSchema) -> StoryOutputSchema:
    """
    Generates a complete movie script story given:
      - A setting
      - Two characters (name + trait)

    Workflow:
    1. Generate the initial scene via `generate_initial_scene`.
    2. For 10 iterations:
       a) Use the label prediction model on the last generation text.
       b) If label is "Character", call `generate_dialogue` with the next character in an alternating pattern.
       c) If label is "Scene", call `generate_scene`.
    3. Generate the ending scene via `generate_ending_scene`.
    4. Return all parts in a well-defined JSON format.
    """

    # ---------------------------------------------------------
    # 5.1 Generate the Initial Scene
    # ---------------------------------------------------------
    init_data = {
        "setting": story_input.setting,
        "characters": [
            {"name": story_input.character1.name, "trait": story_input.character1.trait},
            {"name": story_input.character2.name, "trait": story_input.character2.trait},
        ]
    }
    
    initial_scene_text = ""
    for chunk in generate_initial_scene(init_data):
        # chunk is in SSE format: data: {...}\n\n
        if chunk.startswith("data:"):
            # Parse out the JSON part
            json_str = chunk[len("data:"):].strip()
            try:
                msg_data = json.loads(json_str)
                if msg_data.get("type") == "initial_scene_chunk":
                    initial_scene_text += msg_data["data"]
                elif msg_data.get("type") == "error":
                    # If there's an error, we capture it
                    initial_scene_text += f"[ERROR] {msg_data['data']}"
            except Exception as e:
                logger.error(f"Error parsing initial scene chunk: {e}")

    # This will hold our entire script so far; we feed it into label prediction model.
    current_script = initial_scene_text

    # ---------------------------------------------------------
    # 5.2 Generate the Main Body
    # ---------------------------------------------------------
    main_body = []
    # We'll alternate speakers between character1 and character2 when needed
    characters = [story_input.character1, story_input.character2]
    speaker_index = 0

    for _ in range(10):
        # Predict the label based on the last generated text (current_script)
        # Use only the last generated text with its label
        if main_body:
            last_part = main_body[-1]
            input_text = f"{last_part['label']}: {last_part['text']}"
        else:
            input_text = initial_scene_text

        predicted_label_raw = label_model.predict_label(input_text)

        lower_pred = predicted_label_raw.lower()

        print(f"[DEBUG] Predicted Label: '{predicted_label_raw}' | lower Label: '{lower_pred}'")

        if lower_pred.startswith("character"):
            # If a "Character:" label is predicted, add only the character name (alternating)
            speaker_data = characters[speaker_index]
            speaker_index = (speaker_index + 1) % 2  # alternate between the two characters
            char_text = speaker_data.name
            main_body.append({"label": "Character", "text": char_text})
            current_script += "\n" + char_text

        elif lower_pred.startswith("dialogue"):
            # Use generate_dialogue function instead of directly extracting from predicted label
            dialogue_input = {
                "speaker": characters[speaker_index - 1].name,  # Use previous character since speaker_index already incremented
                "trait": characters[speaker_index - 1].trait,
                "current_scene": current_script,
                "dialogue_context": []
            }
            dialogue_text = ""
            for chunk in generate_dialogue(dialogue_input):
                if chunk.startswith("data:"):
                    json_str = chunk[len("data:"):].strip()
                    try:
                        msg_data = json.loads(json_str)
                        if msg_data.get("type") == "dialogue_chunk":
                            dialogue_text += msg_data["data"]
                        elif msg_data.get("type") == "error":
                            dialogue_text += f"[ERROR] {msg_data['data']}"
                    except Exception as e:
                        logger.error(f"Error parsing dialogue chunk: {e}")
            main_body.append({"label": "Dialogue", "text": dialogue_text})
            current_script += "\n" + dialogue_text


        else:
            # Otherwise, treat it as a request to generate a scene.
            scene_input = {
                "current_script": current_script,
                "scene_description": "Continue the cinematic story with more details."
            }
            scene_text = ""
            for chunk in generate_scene(scene_input):
                if chunk.startswith("data:"):
                    json_str = chunk[len("data:"):].strip()
                    try:
                        msg_data = json.loads(json_str)
                        if msg_data.get("type") == "scene_chunk":
                            scene_text += msg_data["data"]
                        elif msg_data.get("type") == "error":
                            scene_text += f"[ERROR] {msg_data['data']}"
                    except Exception as e:
                        logger.error(f"Error parsing scene chunk: {e}")
            main_body.append({"label": "Scene", "text": scene_text})
            current_script += "\n" + scene_text

    # ---------------------------------------------------------
    # 5.3 Generate the Ending Scene
    # ---------------------------------------------------------
    ending_data = {
        "current_script": current_script,
        "ending_description": "Craft a compelling final scene that ties everything together."
    }

    ending_scene_text = ""
    for chunk in generate_ending_scene(ending_data):
        if chunk.startswith("data:"):
            json_str = chunk[len("data:"):].strip()
            try:
                msg_data = json.loads(json_str)
                if msg_data.get("type") == "ending_scene_chunk":
                    ending_scene_text += msg_data["data"]
                elif msg_data.get("type") == "error":
                    ending_scene_text += f"[ERROR] {msg_data['data']}"
            except Exception as e:
                logger.error(f"Error parsing ending scene chunk: {e}")

    # ---------------------------------------------------------
    # 5.4 Build and Return the Response
    # ---------------------------------------------------------
    # Convert main_body to StoryPartSchema
    main_body_output = [StoryPartSchema(label=part["label"], text=part["text"]) for part in main_body]

    result = StoryOutputSchema(
        initial_scene=initial_scene_text,
        main_body=main_body_output,
        ending_scene=ending_scene_text
    )
    return result

