import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "http://127.0.0.1:8000/generate_complete_story"

# Define the test input data with more than two characters
test_input = {
    "setting": "a haunted castle on a romantic night. There were 2 lovers. Alice and Alex.",
    "characters": [
        {"name": "Alice", "trait": "a curious traveler"},
        {"name": "Marcus", "trait": "a stoic guardian"},
        {"name": "Eleanor", "trait": "a ghostly noblewoman"},
        {"name": "Victor", "trait": "a mad scientist"},
        {"name": "Finn", "trait": "a lost child seeking answers"}
    ]
}

# Input without characters
# test_input = {"setting": "a haunted castle on a romantic night. There were 2 lovers. Alice and Alex and Sohaib."}

def validate_response(response_json):
    """
    Validate the structure of the response
    """
    try:
        # Check if all required keys exist
        assert "initial_scene_heading" in response_json, "Missing initial_scene_heading"
        assert "initial_scene_description" in response_json, "Missing initial_scene_description"
        assert "main_body" in response_json, "Missing main_body"
        assert "ending_scene" in response_json, "Missing ending_scene"
        
        # Check main_body structure
        assert isinstance(response_json["main_body"], list), "Main body should be a list"
        
        # Validate each story part
        valid_labels = ["Scene_Heading", "Narrative", "Character_Name", "Dialogue"]
        for part in response_json["main_body"]:
            assert "label" in part, "Missing label in story part"
            assert "text" in part, "Missing text in story part"
            assert part["label"] in valid_labels, f"Invalid label: {part['label']}"
        
        # Check text lengths
        assert len(response_json["initial_scene_heading"]) > 0, "Initial scene heading is empty"
        assert len(response_json["initial_scene_description"]) > 0, "Initial scene description is empty"
        assert len(response_json["ending_scene"]) > 0, "Ending scene is empty"
        
        return True
    except AssertionError as e:
        logger.error(f"Validation Error: {e}")
        return False

def test_generate_complete_story():
    """
    Sends a POST request to the FastAPI server and validates the response.
    """
    logger.info("\n=== Sending Test Request ===")
    headers = {"Content-Type": "application/json"}
    
    try:
        # Send request
        response = requests.post(API_URL, json=test_input, headers=headers)
        
        # Check response status
        if response.status_code != 200:
            logger.error(f"Request failed with status code {response.status_code}")
            logger.error(f"Response text: {response.text}")
            return
        
        # Parse response
        response_json = response.json()
        
        # Validate response structure
        if validate_response(response_json):
            logger.info("\n=== Test Passed: Response Validated Successfully ===\n")
            
            # Pretty print the response
            print(json.dumps(response_json, indent=4))
            
            # Additional detailed logging
            logger.info(f"Initial Scene Heading Length: {len(response_json['initial_scene_heading'])} characters")
            logger.info(f"Initial Scene Description Length: {len(response_json['initial_scene_description'])} characters")
            logger.info(f"Main Body Segments: {len(response_json['main_body'])}")
            logger.info(f"Ending Scene Length: {len(response_json['ending_scene'])} characters")
            
            # Log first few story parts
            logger.info("\n=== Story Parts Preview ===")
            for i, part in enumerate(response_json['main_body'][:5], 1):
                logger.info(f"Part {i} - Label: {part['label']}")
                logger.info(f"Text (first 100 chars): {part['text'][:100]}...\n")
        else:
            logger.error("=== Test Failed: Response Validation ===")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"\n=== Test Failed: Request Exception ===\n{e}")
    except json.JSONDecodeError as e:
        logger.error(f"\n=== Test Failed: JSON Decode Error ===\n{e}")
    except Exception as e:
        logger.error(f"\n=== Unexpected Error ===\n{e}")

def run_multiple_tests(num_tests=3):
    """
    Run multiple tests to ensure consistency
    """
    logger.info(f"\n=== Running {num_tests} Consecutive Tests ===")
    for i in range(num_tests):
        logger.info(f"\n--- Test {i+1} ---")
        test_generate_complete_story()

if __name__ == "__main__":
    # Run a single test
    test_generate_complete_story()
    
    # Uncomment the line below to run multiple tests
    # run_multiple_tests()