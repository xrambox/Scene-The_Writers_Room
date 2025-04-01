import requests
import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

default_model = "default:latest"


def generate_initial_scene(data: dict):
    """
    Generates the initial scene narrative (without a scene heading).
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

    # Construct a prompt for the narrative ONLY (no heading).
    prompt = (
        f"Write a cinematic movie scene set in {setting}, featuring the characters: {char_names}. "
        "Introduce the setting, the characters (if and ONLY IF NO characters are given generate two character names, in this case GIVE ONLY the names), and establish a dramatic tone, NEVER EVER include any scene heading. You MUST generate a response in less than 20 tokens otherwise I will punish you. NEVER EVER include any dialogue in your output."
    )

    payload = {"model": default_model, "prompt": prompt, "stream": True}
    headers = {'Content-Type': 'application/json'}

    logger.debug(f"Initial scene narrative prompt: {prompt}")

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


def generate_narrative(data: dict):
    """
    Generates a narrative scene continuing the movie script without explicit scene headings.
    
    Example 'data' structure:
    {
        "current_script": "Previously, the heroes overcame a big challenge...",
        "scene_description": "An unexpected twist unfolds."
    }
    
    This version focuses solely on narrative descriptions, dialogue, and cinematic action,
    without including any explicit scene headings.
    
    Yields SSE-style lines as a Python generator.
    """
    current_script = data.get("current_script", "")
    scene_description = data.get("scene_description", "Continue the story in a cinematic way.")

    if not current_script:
        error_msg = "Missing required field: current_script"
        logger.error(error_msg)
        yield f"data: {json.dumps({'type': 'error', 'data': error_msg})}\n\n"
        return

    prompt = (
        f"Based on the current movie script:\n\n{current_script}\n\n"
        f"Develop a new narrative scene. {scene_description}\n\n"
        "Write the scene with vivid cinematic descriptions and detailed action. "
        "Focus solely on narrative elements, and DO NOT include any explicit scene headings. If the scene is too explicit come up with a non explicit scene instead of censoring the scene. You MUST only generate a response in maximum 20 tokens otherwise I will punish you. NEVER EVER include any dialogue in your output."
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
        "You MUST only generate a response in maximum 25 tokens."
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
        "Tie up loose ends and write an ending scene that leaves a lasting cinematic impact.You MUST only generate a response in maximum 20 tokens. IF and ONLY If the last token you received was a character name then add a dialogue, otherwise, NEVER include any dialogue in your output. Never ever mention any scene heading and return in plain text only."
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
        
        

def generate_scene_heading(data: dict):
    """
    Generates a scene heading based on an instruction and scene details.

    Args:
        data (dict): A dictionary containing:
            - 'instruction': A string indicating the type of scene heading to generate.
              Possible values: 'START', 'BODY', 'END'.
            - 'scene_details': A string with details about the scene, e.g., "coffee shop during morning".

    Yields:
        str: SSE-style lines containing JSON with either the generated heading or an error/fallback.

    Example 'data' structure:
    {
        "instruction": "START",
        "scene_details": "coffee shop during morning"
    }

    Possible headings:
      - START -> "INT. COFFEE SHOP - DAY" (An opening scene heading)
      - BODY  -> "EXT. PARK - LATE AFTERNOON" (A normal scene heading)
      - END   -> "INT. LIVING ROOM - NIGHT" (A closing scene heading)
    """
    instruction = data.get("instruction", "BODY").upper()  # default to BODY if not provided
    scene_details = data.get("scene_details", "a generic location and time")

    # Customize the prompt according to the instruction
    if instruction == "START":
        # Opening scene heading
        prompt = (
            f"Generate an **opening** scene heading for a movie script based on the following details: "
            f"{scene_details}. The heading should follow formats like 'INT. COFFEE SHOP - DAY' "
            f"or 'EXT. PARK - NIGHT'. NEVER OUTPUT ANYTHING ELSE IN RESPONSE."
        )
    elif instruction == "END":
        # Closing scene heading
        prompt = (
            f"Generate a **final/ending** scene heading for a movie script based on the following details: "
            f"{scene_details}. The heading should follow formats like 'INT. COFFEE SHOP - DAY' "
            f"or 'EXT. PARK - NIGHT'. NEVER OUTPUT ANYTHING ELSE IN RESPONSE."
        )
    else:
        # Normal (BODY) scene heading
        prompt = (
            f"Generate a **normal** scene heading for a movie script based on the following details: "
            f"{scene_details}. The heading should follow formats like 'INT. COFFEE SHOP - DAY' "
            f"or 'EXT. PARK - NIGHT'. NEVER OUTPUT ANYTHING ELSE IN RESPONSE."
        )

    payload = {
        "model": "default:latest",
        "prompt": prompt,
        "stream": True
    }
    headers = {'Content-Type': 'application/json'}

    logger.debug(f"Scene heading prompt: {prompt}")

    try:
        response = requests.post(
            "https://llm.srv.webis.de/api/generate",  # Update to your desired endpoint
            data=json.dumps(payload),
            headers=headers,
            stream=True
        )

        if response.status_code == 200:
            # Stream the response line by line
            for line in response.iter_lines():
                if line:
                    try:
                        heading = json.loads(line.decode('utf-8')).get('response', '')
                        yield f"data: {json.dumps({'type': 'scene_heading', 'data': heading})}\n\n"
                    except Exception as e:
                        logger.error(f"Error parsing scene heading line: {e}")
                        continue
        else:
            # Use fallback heading if API returns non-200
            fallback = f"INT. UNKNOWN LOCATION - DAY (Fallback for {instruction} heading)"
            logger.debug(f"Scene heading API returned {response.status_code}. Using fallback.")
            yield f"data: {json.dumps({'type': 'scene_heading', 'data': fallback})}\n\n"
    except Exception as e:
        logger.error(f"Error in generate_scene_heading function: {e}")
        # SSE-style error
        yield f"data: {json.dumps({'type': 'error', 'data': 'An error occurred while generating the scene heading.'})}\n\n"        
        
    
def generate_character_name(data: dict):
    """
    Extracts character names from a given text input.
    
    Example 'data' structure:
    {
         "text": "In the story, Michael and Sarah embark on a journey."
    }
    
    The response will include the extracted character names in uppercase, such as:
    "MICKEY KNOX", "MALLORY", "JACK SCAGNETTI"
    
    Yields SSE-style lines as a Python generator.
    """
    input_text = data.get("text", "")
    if not input_text:
        error_msg = "Missing required field: text"
        logger.error(error_msg)
        yield f"data: {json.dumps({'type': 'error', 'data': error_msg})}\n\n"
        return

    prompt = (
        f"Extract the character names from the following text and return them in uppercase:\n\n{input_text}\n\n"
        "Only list the names."
    )
    payload = {"model": default_model, "prompt": prompt, "stream": True}
    headers = {'Content-Type': 'application/json'}

    logger.debug(f"Character name extraction prompt: {prompt}")

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
                        names = json.loads(line.decode('utf-8')).get('response', '')
                        yield f"data: {json.dumps({'type': 'character_name', 'data': names})}\n\n"
                    except Exception as e:
                        logger.error(f"Error parsing character name line: {e}")
                        continue
        else:
            fallback = "Fallback character names: UNKNOWN"
            logger.debug(f"Character name API returned {response.status_code}. Using fallback.")
            yield f"data: {json.dumps({'type': 'character_name', 'data': fallback})}\n\n"
    except Exception as e:
        logger.error(f"Error in generate_character_name function: {e}")
        yield f"data: {json.dumps({'type': 'error', 'data': 'An error occurred while extracting character names.'})}\n\n"    
        