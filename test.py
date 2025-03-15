# test.py

import requests
import json

API_URL = "http://127.0.0.1:8000/generate_complete_story"

# Define the test input data
test_input = {
    "setting": "a haunted castle on a stormy night",
    "character1": {"name": "Alice", "trait": "a curious traveler"},
    "character2": {"name": "Marcus", "trait": "a stoic guardian"}
}

def test_generate_complete_story():
    """
    Sends a POST request to the FastAPI server and prints the response.
    """
    print("\n=== Sending Test Request ===")
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(API_URL, data=json.dumps(test_input), headers=headers)
        
        if response.status_code == 200:
            print("\n=== Test Passed: Response Received Successfully ===\n")
            response_json = response.json()
            print(json.dumps(response_json, indent=4))  # Pretty print the response
        else:
            print(f"\n=== Test Failed: Received Status Code {response.status_code} ===\n")
            print(response.text)  # Print error message if request fails

    except requests.exceptions.RequestException as e:
        print(f"\n=== Test Failed: Request Exception ===\n{e}")

if __name__ == "__main__":
    test_generate_complete_story()
