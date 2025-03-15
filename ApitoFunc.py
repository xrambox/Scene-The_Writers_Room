import requests
import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

default_model = "default:latest"

def generate_initial_scene(data: dict):
    """
    Generates an initial scene. 
    Accepts a dictionary similar to the JSON body you were previously receiving via POST.

    Example 'data' structure:
    {
        "setting": "a futuristic city",
        "characters": [
            {"name": "Alex", "trait": "a brave protagonist."},
            {"name": "Jordan", "trait": "a mysterious figure."}
        ]
    }

    Yields SSE-style lines as a Python generator.
    """

    # Use default values if some inputs are missing.
    setting = data.get("setting", "a quiet town")
    characters = data.get("characters", [
        {"name": "Alex", "trait": "a brave protagonist."},
        {"name": "Jordan", "trait": "a mysterious figure."}
    ])

    # Create a comma-separated list of character names.
    char_names = ", ".join([char.get("name", "Unknown") for char in characters])

    # Construct a prompt that introduces the setting and characters.
    prompt = (
        f"Write a cinematic movie scene set in {setting} featuring the characters: {char_names}. "
        "Introduce the setting and the characters with vivid, engaging details and establish a tone "
        "that promises a dramatic, intriguing movie ahead."
    )

    payload = {"model": default_model, "prompt": prompt, "stream": True}
    headers = {'Content-Type': 'application/json'}

    logger.debug(f"Initial scene prompt: {prompt}")

    try:
        response = requests.post(
            "https://llm.srv.webis.de/api/generate",
            data=json.dumps(payload),
            headers=headers,
            stream=True
        )
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    try:
                        part = json.loads(line.decode('utf-8')).get('response', '')
                        yield f"data: {json.dumps({'type': 'initial_scene_chunk', 'data': part})}\n\n"
                    except Exception as e:
                        logger.error(f"Error parsing initial scene line: {e}")
                        continue
        else:
            fallback = (
                "Fallback initial scene: In a quiet town, as the sun rises, "
                "two intriguing figures meet, marking the beginning of an epic tale."
            )
            logger.debug(f"Initial scene API returned {response.status_code}. Using fallback.")
            yield f"data: {json.dumps({'type': 'initial_scene_chunk', 'data': fallback})}\n\n"
    except Exception as e:
        logger.error(f"Error in generate_initial_scene function: {e}")
        yield f"data: {json.dumps({'type': 'error', 'data': 'An error occurred while generating the initial scene.'})}\n\n"


def generate_scene(data: dict):
    """
    Generates a new scene continuing from the current script. 

    Example 'data' structure:
    {
        "current_script": "Previously, the heroes overcame a big challenge...",
        "scene_description": "Now they face an unexpected twist in a dimly lit warehouse."
    }

    Yields SSE-style lines as a Python generator.
    """

    current_script = data.get("current_script", "")
    scene_description = data.get("scene_description", "Continue the story in a cinematic way.")

    if not current_script:
        error_msg = "Missing required field: current_script"
        logger.error(error_msg)
        # Return as SSE-like error message
        yield f"data: {json.dumps({'type': 'error', 'data': error_msg})}\n\n"
        return

    prompt = (
        f"Based on the following movie script:\n\n{current_script}\n\n"
        f"Generate a new scene. {scene_description}\n\n"
        "Write a cinematic scene that advances the story."
    )

    payload = {"model": default_model, "prompt": prompt, "stream": True}
    headers = {'Content-Type': 'application/json'}

    logger.debug(f"Scene prompt: {prompt}")

    try:
        response = requests.post(
            "https://llm.srv.webis.de/api/generate",
            data=json.dumps(payload),
            headers=headers,
            stream=True
        )
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    try:
                        part = json.loads(line.decode('utf-8')).get('response', '')
                        yield f"data: {json.dumps({'type': 'scene_chunk', 'data': part})}\n\n"
                    except Exception as e:
                        logger.error(f"Error parsing scene line: {e}")
                        continue
        else:
            fallback = (
                "Fallback scene: The narrative takes an unexpected turn, setting "
                "the stage for a dramatic sequence."
            )
            logger.debug(f"Scene generation API returned {response.status_code}. Using fallback.")
            yield f"data: {json.dumps({'type': 'scene_chunk', 'data': fallback})}\n\n"
    except Exception as e:
        logger.error(f"Error in generate_scene function: {e}")
        yield f"data: {json.dumps({'type': 'error', 'data': 'An error occurred while generating the scene.'})}\n\n"


def generate_dialogue(data: dict):
    """
    Generates a dialogue line for a given character based on context.

    Example 'data' structure:
    {
        "speaker": "Alex",
        "trait": "Alex is a cautious but hopeful survivor.",
        "current_scene": "They are hiding in the old library...",
        "dialogue_context": [
            {"role": "system", "content": "Something about previous context..."},
            {"role": "user", "content": "A past dialogue or query..."}
        ]
    }

    Yields SSE-style lines as a Python generator.
    """

    speaker = data.get("speaker", "Unknown")
    trait = data.get("trait", f"{speaker} is an interesting character.")
    current_scene = data.get("current_scene", "")
    dialogue_context = data.get("dialogue_context", [])

    # Construct the system message for the character.
    system_message = f"Your name is {speaker}. {trait} "
    if current_scene:
        system_message += f"The current scene is: {current_scene}. "
    system_message += (
        "Respond with a short, cinematic dialogue line appropriate to the scene; "
        "keep it below 50 characters."
    )

    # Build the messages list for the chat API.
    messages = [{"role": "system", "content": system_message}]
    # If a dialogue context is provided, include it.
    if dialogue_context:
        # Expecting dialogue_context to be a list of previous messages, 
        # e.g., [{"role": "user", "content": "Hi there!"}, ...]
        messages.extend(dialogue_context)

    # Finally, user's turn prompt
    messages.append({"role": "user", "content": "Your turn to speak."})

    payload = {"model": default_model, "messages": messages, "stream": True}
    headers = {'Content-Type': 'application/json'}

    logger.debug(f"Dialogue messages for {speaker}: {messages}")

    try:
        response = requests.post(
            "https://llm.srv.webis.de/api/chat",
            data=json.dumps(payload),
            headers=headers,
            stream=True
        )
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    try:
                        token = json.loads(line.decode('utf-8')).get('message', {}).get('content', '')
                        yield f"data: {json.dumps({'type': 'dialogue_chunk', 'speaker': speaker, 'data': token})}\n\n"
                    except Exception as e:
                        logger.error(f"Error parsing dialogue line: {e}")
                        continue
        else:
            fallback = f"Fallback dialogue: {speaker} remains silent for a moment."
            logger.debug(f"Dialogue API returned {response.status_code}. Using fallback.")
            yield f"data: {json.dumps({'type': 'dialogue_chunk', 'speaker': speaker, 'data': fallback})}\n\n"
    except Exception as e:
        logger.error(f"Error in generate_dialogue function: {e}")
        yield f"data: {json.dumps({'type': 'error', 'data': 'An error occurred while generating dialogue.'})}\n\n"


def generate_ending_scene(data: dict):
    """
    Generates the final ending scene based on the current script.

    Example 'data' structure:
    {
        "current_script": "The story so far... it all builds up to this moment.",
        "ending_description": "A dramatic conclusion that ties up loose ends."
    }

    Yields SSE-style lines as a Python generator.
    """

    current_script = data.get("current_script", "")
    ending_description = data.get("ending_description", 
                                 "The movie reaches a dramatic and satisfying conclusion.")

    if not current_script:
        error_msg = "Missing required field: current_script"
        logger.error(error_msg)
        yield f"data: {json.dumps({'type': 'error', 'data': error_msg})}\n\n"
        return

    prompt = (
        f"Based on the following movie script:\n\n{current_script}\n\n"
        f"Generate the final ending scene. {ending_description}\n\n"
        "Tie up loose ends and write an ending scene that leaves a lasting cinematic impact."
    )

    payload = {"model": default_model, "prompt": prompt, "stream": True}
    headers = {'Content-Type': 'application/json'}

    logger.debug(f"Ending scene prompt: {prompt}")

    try:
        response = requests.post(
            "https://llm.srv.webis.de/api/generate",
            data=json.dumps(payload),
            headers=headers,
            stream=True
        )
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    try:
                        part = json.loads(line.decode('utf-8')).get('response', '')
                        yield f"data: {json.dumps({'type': 'ending_scene_chunk', 'data': part})}\n\n"
                    except Exception as e:
                        logger.error(f"Error parsing ending scene line: {e}")
                        continue
        else:
            fallback = (
                "Fallback ending: The movie concludes with a powerful, unforgettable finale."
            )
            logger.debug(f"Ending scene API returned {response.status_code}. Using fallback.")
            yield f"data: {json.dumps({'type': 'ending_scene_chunk', 'data': fallback})}\n\n"
    except Exception as e:
        logger.error(f"Error in generate_ending_scene function: {e}")
        yield f"data: {json.dumps({'type': 'error', 'data': 'An error occurred while generating the ending scene.'})}\n\n"
        
        
        
        
        
        
        
        
        
        
        
################
 #   Below is the sample code on how to calll these functions
##############

# caller_script.py

# from movie_script_functions import (
#     generate_initial_scene,
#     generate_scene,
#     generate_dialogue,
#     generate_ending_scene
# )
# import json

# def main():
#     # ==========================================================
#     # 1. Prepare Your Input Data
#     # ==========================================================
#     # This replicates the JSON body you would have sent in the POST request.
#     initial_scene_data = {
#         "setting": "a futuristic city",
#         "characters": [
#             {"name": "Alex", "trait": "a brave protagonist."},
#             {"name": "Jordan", "trait": "a mysterious figure."}
#         ]
#     }

#     # ==========================================================
#     # 2. Call the Generator Function
#     # ==========================================================
#     # The function returns a generator that yields SSE-like lines.
#     scene_generator = generate_initial_scene(initial_scene_data)

#     # ==========================================================
#     # 3. Consume the Generator Output
#     # ==========================================================
#     # Each yielded item is a string, usually in SSE format:
#     # "data: {...}\n\n"
#     #
#     # You can iterate over it and parse the JSON part as needed.
#     for sse_line in scene_generator:
#         # Optionally, just print each line to see the SSE data:
#         print(f"Raw SSE line:\n{sse_line}")

#         # You can parse the SSE line if you want:
#         # Typically it looks like:
#         # data: {"type": "initial_scene_chunk", "data": "some text"}\n\n
#         #
#         # To parse:
#         if sse_line.startswith("data:"):
#             # Extract the JSON part
#             json_str = sse_line[len("data:"):].strip()
#             # Sometimes there's an extra newline, so strip again:
#             json_str = json_str.strip()
            
#             # Parse the JSON
#             try:
#                 msg_data = json.loads(json_str)
#                 # e.g. msg_data = {"type": "initial_scene_chunk", "data": "some text"}
#                 if msg_data.get("type") == "initial_scene_chunk":
#                     # You can handle the chunk as you like:
#                     print(f"Initial scene chunk: {msg_data['data']}")
#                 elif msg_data.get("type") == "error":
#                     # Handle errors
#                     print(f"Error: {msg_data['data']}")
#                 else:
#                     # Some other type of message
#                     print(f"Received other message type: {msg_data}")
#             except json.JSONDecodeError:
#                 print("Failed to parse SSE line as JSON.")

#     # ==========================================================
#     # 4. Calling Other Functions
#     # ==========================================================
#     # You can do the same for `generate_scene`, `generate_dialogue`, or
#     # `generate_ending_scene` with their respective parameters.
#     #
#     # For instance:
#     #
#     # scene_data = {
#     #     "current_script": "So far, the heroes overcame a great challenge...",
#     #     "scene_description": "They find themselves in a dark alley..."
#     # }
#     # 
#     # scene_gen = generate_scene(scene_data)
#     # for line in scene_gen:
#     #     print(line)  # Parse similarly if you want

# if __name__ == "__main__":
#     main()