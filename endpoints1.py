# endpoints.py

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Dict
import logging
import json
import random

# Import our previously defined functions and model
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
    characters: List[CharacterSchema] = Field(..., min_items=2, description="List of characters in the story.")

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
    This API endpoint generates a complete story (initial scene, main body, and ending scene) 
    based on a given setting and multiple characters. It dynamically selects and swaps characters 
    during story generation.
    """,
    version="1.1.0",
)

# -------------------------------------------------------------
# 4. Load the Label Prediction Model
# -------------------------------------------------------------
model_path = "trained_roberta_dialogue_model"
label_model = LabelPredictionModel(model_path)

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
    Generates a complete movie script story with dynamic character interactions.
    """
    # Ensure at least 2 characters
    if len(story_input.characters) < 2:
        raise ValueError("At least 2 characters are required.")
    
    # Randomly select initial two characters
    active_characters = random.sample(story_input.characters, 2)
    
    # ---------------------------------------------------------
    # 5.1 Generate the Initial Scene
    # ---------------------------------------------------------
    init_data = {
        "setting": story_input.setting,
        "characters": [
            {"name": char.name, "trait": char.trait} for char in active_characters
        ]
    }
    
    initial_scene_text = ""
    for chunk in generate_initial_scene(init_data):
        if chunk.startswith("data:"):
            json_str = chunk[len("data:"):].strip()
            try:
                msg_data = json.loads(json_str)
                if msg_data.get("type") == "initial_scene_chunk":
                    initial_scene_text += msg_data["data"]
                elif msg_data.get("type") == "error":
                    initial_scene_text += f"[ERROR] {msg_data['data']}"
            except Exception as e:
                logger.error(f"Error parsing initial scene chunk: {e}")

    # This will hold our entire script so far
    current_script = initial_scene_text

    # ---------------------------------------------------------
    # 5.2 Generate the Main Body
    # ---------------------------------------------------------
    main_body = []
    
    # Track dialogue count and character interactions
    dialogue_count = 0
    max_dialogues_before_swap = 4  # Swap after 4-5 dialogues

    for _ in range(20):
        # Predict the label based on the last generated text
        if main_body:
            last_part = main_body[-1]
            input_text = f"{last_part['label']}: {last_part['text']}"
        else:
            input_text = initial_scene_text

        predicted_label_raw = label_model.predict_label(input_text)
        lower_pred = predicted_label_raw.lower()

        print(f"[DEBUG] Predicted Label: '{predicted_label_raw}' | lower Label: '{lower_pred}'")

        if lower_pred.startswith("character"):
            # If a "Character:" label is predicted, add only the character name
            char_text = active_characters[dialogue_count % 2].name
            main_body.append({"label": "Character", "text": char_text})
            current_script += "\n" + char_text

        elif lower_pred.startswith("dialogue"):
            dialogue_count += 1
            
            # Alternate between the two active characters
            speaker_index = (dialogue_count - 1) % 2
            speaker = active_characters[speaker_index]
            
            # Generate dialogue for the current speaker
            dialogue_input = {
                "speaker": speaker.name,
                "trait": speaker.trait,
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
            
            # Check if it's time to swap a character
            if dialogue_count >= max_dialogues_before_swap:
                # Reset dialogue count
                dialogue_count = 0
                
                # If more than 2 characters exist, try to swap
                if len(story_input.characters) > 2:
                    # Remove current active characters from potential swap candidates
                    swap_candidates = [
                        char for char in story_input.characters 
                        if char not in active_characters
                    ]
                    
                    if swap_candidates:
                        # Randomly select a new character to replace one of the current characters
                        new_character = random.choice(swap_candidates)
                        
                        # Randomly decide which active character to replace
                        replace_index = random.randint(0, 1)
                        active_characters[replace_index] = new_character

        else:
            # Generate a scene
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

# -------------------------------------------------------------
# 6. Instructions to Run
# -------------------------------------------------------------
"""
1. Install dependencies:
   pip install fastapi uvicorn pydantic requests torch transformers

2. Ensure you have the files:
   - apitofunc.py (contains generate_initial_scene, generate_scene, generate_dialogue, generate_ending_scene)
   - label_prediction_model.py (contains LabelPredictionModel class)
   - endpoints.py (this file)

3. Update the 'model_path' in this file to point to your actual RobertaForSequenceClassification model.

4. Launch the server:
   uvicorn endpoints:app --reload

5. Send a POST request to http://127.0.0.1:8000/generate_complete_story with JSON body:

   {
     "setting": "a mysterious island",
     "characters": [
       {"name": "Alice", "trait": "a curious explorer"},
       {"name": "Marcus", "trait": "a stoic guardian"},
       {"name": "Elena", "trait": "a tech-savvy scientist"},
       {"name": "Jack", "trait": "a resourceful adventurer"}
     ]
   }

6. You should receive a JSON response containing:
   {
     "initial_scene": "...",
     "main_body": [
       {"label": "Scene", "text": "..."},
       {"label": "Character", "text": "..."},
       ...
     ],
     "ending_scene": "..."
   }
"""

# This allows the script to be run directly if needed
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)