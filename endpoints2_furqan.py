# endpoints.py

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import logging
import json
import random
import re

import os
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

# Import our previously defined functions and model
from ApitoFunc_christine_test_1 import (
    generate_scene_heading,
    generate_initial_scene,
    generate_narrative,
    generate_dialogue,
    generate_ending_scene,
    generate_character_name
)
from label_prediction_model_new import LabelPredictionModel

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
    characters: Optional[List[CharacterSchema]] = Field(
        default=None, description="List of characters in the story."
    )

class StoryPartSchema(BaseModel):
    label: str = Field(..., description="Label for this part of the story (e.g., 'Scene_Heading' or 'Dialogue').")
    text: str = Field(..., description="The generated text for this story part.")

class StoryOutputSchema(BaseModel):
    initial_scene_heading: str = Field(..., description="The initial scene heading text.")
    initial_scene_description: str = Field(..., description="The initial scene narrative text.")
    main_body: List[StoryPartSchema] = Field(..., description="List of story segments generated in the main body.")
    ending_scene_heading: str = Field(..., description="The ending scene heading text.")
    ending_scene_description: str = Field(..., description="The ending scene narrative text.")

# -------------------------------------------------------------
# 3. Initialize FastAPI
# -------------------------------------------------------------
app = FastAPI(
    title="Movie Script Generation API",
    description="""
    This API endpoint generates a complete story (initial scene heading, initial scene description, main body, and ending scene) 
    based on a given setting and multiple characters. It dynamically selects and swaps characters during story generation.
    """,
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# 4. Load the Label Prediction Model
# -------------------------------------------------------------
model_path = "trained_roberta_dialogue_model_new_large"
label_model = LabelPredictionModel(model_path)

def unify_label(predicted_label: str) -> str:
    """
    Convert the raw label from the prediction to one of:
      - "Scene_Heading" for scene headings,
      - "Narrative" for narrative descriptions,
      - "Character_Name" for character names,
      - "Dialogue" for dialogue lines.
    """
    if predicted_label in ["Scene_Heading", "Narrative"]:
        return predicted_label
    elif predicted_label == "Character_Name":
        return "Character_Name"
    elif predicted_label == "Dialogue":
        return "Dialogue"
    # Fallback to "Narrative" if not recognized.
    return "Narrative"

# -------------------------------------------------------------
# 5. The Main Endpoint
# -------------------------------------------------------------
@app.post("/generate_complete_story", response_model=StoryOutputSchema)
def generate_complete_story(story_input: StoryInputSchema) -> StoryOutputSchema:
    """
    Generates a complete movie script story with dynamic character interactions.
    If no characters are provided, it generates character names based on the setting.
    """
    # Check if characters are missing or empty
    if not hasattr(story_input, "characters") or not story_input.characters:
        logger.info("No characters provided. Generating character names based on the setting.")
        
        # Generate character names using the setting as input
        character_names_chunks = []  # Store received chunks

        for chunk in generate_character_name({"text": story_input.setting}):
            if chunk.startswith("data:"):
                json_str = chunk[len("data:"):].strip()
                try:
                    msg_data = json.loads(json_str)
                    if msg_data.get("type") == "character_name":
                        character_names_chunks.append(msg_data["data"])  # Collect chunks
                    elif msg_data.get("type") == "error":
                        logger.error(f"Error generating character names: {msg_data['data']}")
                        raise ValueError("Failed to generate character names.")
                except Exception as e:
                    logger.error(f"Error parsing character name chunk: {e}")
                    raise ValueError("Failed to parse character names.")

        # Combine all name chunks into a single string
        character_names = "".join(character_names_chunks).strip()

        # Split names by both commas and newlines
        character_names_list = [name.strip() for name in re.split(r"[\n,]", character_names) if name.strip()]

        # Debugging output
        logger.info(f"Final character names: {character_names_list}")
                
        # Create CharacterSchema objects for each name
        story_input.characters = [
            CharacterSchema(name=name, trait=f"a mysterious character in {story_input.setting}")
            for name in character_names_list
        ]
    
    # Ensure at least 2 characters
    if len(story_input.characters) < 2:
        raise ValueError("At least 2 characters are required.")
    
    # Randomly select initial two characters
    active_characters = random.sample(story_input.characters, 2)
    
    # ---------------------------------------------------------
    # 5.1 Generate the Initial Scene Heading
    # ---------------------------------------------------------
    init_heading_data = {
        "instruction": "START",
        "scene_details": f"{story_input.setting} featuring {active_characters[0].name} and {active_characters[1].name}"
    }
    
    initial_scene_heading_text = ""
    for chunk in generate_scene_heading(init_heading_data):
        if chunk.startswith("data:"):
            json_str = chunk[len("data:"):].strip()
            try:
                msg_data = json.loads(json_str)
                if msg_data.get("type") == "scene_heading":
                    initial_scene_heading_text += msg_data["data"]
                elif msg_data.get("type") == "error":
                    initial_scene_heading_text += f"[ERROR] {msg_data['data']}"
            except Exception as e:
                logger.error(f"Error parsing initial scene heading chunk: {e}")

    # ---------------------------------------------------------
    # 5.2 Generate the Initial Scene Description
    # ---------------------------------------------------------
    init_scene_data = {
        "setting": story_input.setting,
        "characters": [
            {"name": char.name, "trait": char.trait} for char in active_characters
        ]
    }
    
    initial_scene_description_text = ""
    for chunk in generate_initial_scene(init_scene_data):
        if chunk.startswith("data:"):
            json_str = chunk[len("data:"):].strip()
            try:
                msg_data = json.loads(json_str)
                if msg_data.get("type") == "initial_scene_chunk":
                    initial_scene_description_text += msg_data["data"]
                elif msg_data.get("type") == "error":
                    initial_scene_description_text += f"[ERROR] {msg_data['data']}"
            except Exception as e:
                logger.error(f"Error parsing initial scene description chunk: {e}")

    # This will hold our entire script so far
    current_script = initial_scene_heading_text + "\n" + initial_scene_description_text

    # ---------------------------------------------------------
    # 5.3 Generate the Main Body
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
            input_text = current_script

        print("LABEL MODEL CALL")
        print(input_text)
        predicted_label_raw = label_model.predict_label(input_text)
        unified_label = unify_label(predicted_label_raw)

        print(f"[DEBUG] Predicted Label: '{predicted_label_raw}' | Unified Label: '{unified_label}'")

        if unified_label == "Character_Name":
            # If a "Character_Name" label is predicted, add only the character name
            char_text = active_characters[dialogue_count % 2].name
            main_body.append({"label": "Character_Name", "text": char_text})
            current_script += "\n" + char_text

        elif unified_label == "Dialogue":
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

        elif unified_label == "Scene_Heading":
            # Generate a scene heading
            scene_heading_input = {
                "instruction": "BODY",
                "scene_details": "a new scene location and time"
            }
            scene_heading_text = ""
            for chunk in generate_scene_heading(scene_heading_input):
                if chunk.startswith("data:"):
                    json_str = chunk[len("data:"):].strip()
                    try:
                        msg_data = json.loads(json_str)
                        if msg_data.get("type") == "scene_heading":
                            scene_heading_text += msg_data["data"]
                        elif msg_data.get("type") == "error":
                            scene_heading_text += f"[ERROR] {msg_data['data']}"
                    except Exception as e:
                        logger.error(f"Error parsing scene heading chunk: {e}")
            
            main_body.append({"label": "Scene_Heading", "text": scene_heading_text})
            current_script += "\n" + scene_heading_text

        else:  # Default to "Narrative"
            # Generate a narrative scene
            narrative_input = {
                "current_script": current_script,
                "scene_description": "Continue the cinematic story with more details."
            }
            narrative_text = ""
            for chunk in generate_narrative(narrative_input):
                if chunk.startswith("data:"):
                    json_str = chunk[len("data:"):].strip()
                    try:
                        msg_data = json.loads(json_str)
                        if msg_data.get("type") == "scene_chunk":
                            narrative_text += msg_data["data"]
                        elif msg_data.get("type") == "error":
                            narrative_text += f"[ERROR] {msg_data['data']}"
                    except Exception as e:
                        logger.error(f"Error parsing narrative chunk: {e}")
            
            main_body.append({"label": "Narrative", "text": narrative_text})
            current_script += "\n" + narrative_text

        # ---------------------------------------------------------
    # 5.4 Generate the Ending Scene Heading and Description
    # ---------------------------------------------------------
    # First generate the ending scene heading
    ending_heading_data = {
        "instruction": "END",
        "scene_details": "final scene location and time"
    }
    
    ending_scene_heading_text = ""
    for chunk in generate_scene_heading(ending_heading_data):
        if chunk.startswith("data:"):
            json_str = chunk[len("data:"):].strip()
            try:
                msg_data = json.loads(json_str)
                if msg_data.get("type") == "scene_heading":
                    ending_scene_heading_text += msg_data["data"]
                elif msg_data.get("type") == "error":
                    ending_scene_heading_text += f"[ERROR] {msg_data['data']}"
            except Exception as e:
                logger.error(f"Error parsing ending scene heading chunk: {e}")
    
    # Add the ending scene heading to the current script
    current_script += "\n" + ending_scene_heading_text
    
    # Then generate the ending scene description
    ending_data = {
        "current_script": current_script,
        "ending_description": "Craft a compelling final scene that ties everything together."
    }

    ending_scene_description_text = ""
    for chunk in generate_ending_scene(ending_data):
        if chunk.startswith("data:"):
            json_str = chunk[len("data:"):].strip()
            try:
                msg_data = json.loads(json_str)
                if msg_data.get("type") == "ending_scene_chunk":
                    ending_scene_description_text += msg_data["data"]
                elif msg_data.get("type") == "error":
                    ending_scene_description_text += f"[ERROR] {msg_data['data']}"
            except Exception as e:
                logger.error(f"Error parsing ending scene chunk: {e}")

    # ---------------------------------------------------------
    # 5.5 Build and Return the Response
    # ---------------------------------------------------------
    # Convert main_body to StoryPartSchema
    main_body_output = [StoryPartSchema(label=part["label"], text=part["text"]) for part in main_body]

    result = StoryOutputSchema(
        initial_scene_heading=initial_scene_heading_text,
        initial_scene_description=initial_scene_description_text,
        main_body=main_body_output,
        ending_scene_heading=ending_scene_heading_text,
        ending_scene_description=ending_scene_description_text
    )

    # Save the API call before returning
    save_api_call(
        input_data=story_input.dict(),
        output_data=result.dict()
    )
    
    return result

# -------------------------------------------------------------
# 6. Instructions to Run
# -------------------------------------------------------------
"""
1. Install dependencies:
   pip install fastapi uvicorn pydantic requests torch transformers

2. Ensure you have the files:
   - ApitoFunc_christine_test.py (contains generate_initial_scene, generate_scene, generate_dialogue, generate_ending_scene)
   - label_prediction_model_new.py (contains LabelPredictionModel class)
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
     "initial_scene_heading": "...",
     "initial_scene_description": "...",
     "main_body": [
       {"label": "Scene_Heading", "text": "..."},
       {"label": "Narrative", "text": "..."},
       {"label": "Character_Name", "text": "..."},
       {"label": "Dialogue", "text": "..."},
       ...
     ],
     "ending_scene_heading": "...",
     "ending_scene_description": "..."
   }
"""

# Add this right before the main endpoint function
def save_api_call(input_data: dict, output_data: dict):
    # Create runs directory if it doesn't exist
    os.makedirs("runs", exist_ok=True)
    
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"runs/api_call_{timestamp}.txt"
    
    # Write input and output to file
    with open(filename, "w") as f:
        f.write("=== INPUT ===\n")
        f.write(json.dumps(input_data, indent=2))
        f.write("\n\n=== OUTPUT ===\n")
        f.write(json.dumps(output_data, indent=2))
    
    logger.info(f"Saved API call to {filename}")

# This allows the script to be run directly if needed
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)