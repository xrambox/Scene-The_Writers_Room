import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "http://127.0.0.1:8000/generate_complete_story"

# Define the input data based on the new story
test_input = {
    "setting": "An abandoned prison in Germany being renovated by a young Iranian couple's building repair company.",
    "characters": [
        {"name": "Aida", "trait": "hardworking, determined, emotional"},
        {"name": "Saman", "trait": "kind, humorous, hardworking, rational"},
        {"name": "Ahmad", "trait": "calm, introverted, compassionate, 60 years old"},
        {"name": "Producer", "trait": "strong communication skills, logical, composed, 66 years old"}
    ]
}

def validate_response(response_json):
    """
    Validate the structure of the response
    """
    try:
        assert "initial_scene_heading" in response_json, "Missing initial_scene_heading"
        assert "initial_scene_description" in response_json, "Missing initial_scene_description"
        assert "main_body" in response_json, "Missing main_body"
        assert "ending_scene_heading" in response_json, "Missing ending_scene_heading"
        assert "ending_scene_description" in response_json, "Missing ending_scene_description"
        
        assert isinstance(response_json["main_body"], list), "Main body should be a list"
        
        valid_labels = ["Scene_Heading", "Narrative", "Character_Name", "Dialogue"]
        for part in response_json["main_body"]:
            assert "label" in part, "Missing label in story part"
            assert "text" in part, "Missing text in story part"
            assert part["label"] in valid_labels, f"Invalid label: {part['label']}"
        
        assert len(response_json["initial_scene_heading"]) > 0, "Initial scene heading is empty"
        assert len(response_json["initial_scene_description"]) > 0, "Initial scene description is empty"
        assert len(response_json["ending_scene_heading"]) > 0, "Ending scene heading is empty"
        assert len(response_json["ending_scene_description"]) > 0, "Ending scene description is empty"
        
        return True
    except AssertionError as e:
        logger.error(f"Validation Error: {e}")
        return False

def test_generate_complete_story():
    """
    Sends a POST request to the API and validates the response.
    """
    logger.info("\n=== Sending Test Request ===")
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(API_URL, json=test_input, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Request failed with status code {response.status_code}")
            logger.error(f"Response text: {response.text}")
            return
        
        response_json = response.json()
        
        if validate_response(response_json):
            logger.info("\n=== Test Passed: Response Validated Successfully ===\n")
            print(json.dumps(response_json, indent=4))
        else:
            logger.error("=== Test Failed: Response Validation ===")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"\n=== Test Failed: Request Exception ===\n{e}")
    except json.JSONDecodeError as e:
        logger.error(f"\n=== Test Failed: JSON Decode Error ===\n{e}")
    except Exception as e:
        logger.error(f"\n=== Unexpected Error ===\n{e}")

if __name__ == "__main__":
    test_generate_complete_story()
