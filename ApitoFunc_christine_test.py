import requests
import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

default_model = "default:latest"

def generate_Initialscene_heading(data: dict):
    """
    Generates a scene heading, e.g. "INT. ABANDONED WAREHOUSE – NIGHT" 
    Accepts the same dictionary structure as generate_initial_scene.

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

    # Prompt specifically for a scene heading.
    # You can change the prompt style to fit your exact formatting needs.
    heading_prompt = (
        f"Write a short, cinematic scene heading for a movie set in {setting} "
        f"featuring the characters: {char_names}. Make it look like a screenplay heading. Max 10 words."
        "(e.g., INT. ABANDONED WAREHOUSE - NIGHT)."
    )

    payload = {"model": default_model, "prompt": heading_prompt, "stream": True}
    headers = {'Content-Type': 'application/json'}

    logger.debug(f"Scene heading prompt: {heading_prompt}")

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
                        yield f"data: {json.dumps({'type': 'scene_heading_chunk', 'data': part})}\n\n"
                    except Exception as e:
                        logger.error(f"Error parsing scene heading line: {e}")
                        continue
        else:
            fallback = "INT. QUIET TOWN – DAWN"
            logger.debug(f"Scene heading API returned {response.status_code}. Using fallback.")
            yield f"data: {json.dumps({'type': 'scene_heading_chunk', 'data': fallback})}\n\n"
    except Exception as e:
        logger.error(f"Error in generate_scene_heading function: {e}")
        yield f"data: {json.dumps({'type': 'error', 'data': 'An error occurred while generating the scene heading.'})}\n\n"


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
        "Introduce the setting, the characters, and establish a dramatic tone, but do not include any scene heading. Maximum 20 tokens please. "
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
        "Write the scene with vivid cinematic descriptions, detailed action, and dialogue where appropriate. "
        "Focus solely on narrative elements and dialogue, and do not include any explicit scene headings. Maximum 15 tokens in response please."
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
        "Tie up loose ends and write an ending scene that leaves a lasting cinematic impact. Maximum 20 tokens in response please."
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
       
        
        
def generate_scene_heading(data: dict):
    """
    Generates a scene heading based on input scene details.
    
    Example 'data' structure:
    {
        "scene_details": "coffee shop during morning"
    }
    
    The generated heading will follow typical movie script formats such as:
    "INT. COFFEE SHOP - DAY"
    
    Yields SSE-style lines as a Python generator.
    """
    scene_details = data.get("scene_details", "a generic location and time")
    prompt = (
        f"Generate a scene heading for a movie script based on the following details: {scene_details}. "
        "The heading should follow formats like 'INT. COFFEE SHOP - DAY' or 'EXT. PARK - NIGHT'. Maximum 10 tokens in response please."
    )
    payload = {"model": default_model, "prompt": prompt, "stream": True}
    headers = {'Content-Type': 'application/json'}

    logger.debug(f"Scene heading prompt: {prompt}")

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
                        heading = json.loads(line.decode('utf-8')).get('response', '')
                        yield f"data: {json.dumps({'type': 'scene_heading', 'data': heading})}\n\n"
                    except Exception as e:
                        logger.error(f"Error parsing scene heading line: {e}")
                        continue
        else:
            fallback = "Fallback scene heading: INT. UNKNOWN LOCATION - DAY"
            logger.debug(f"Scene heading API returned {response.status_code}. Using fallback.")
            yield f"data: {json.dumps({'type': 'scene_heading', 'data': fallback})}\n\n"
    except Exception as e:
        logger.error(f"Error in generate_scene_heading function: {e}")
        yield f"data: {json.dumps({'type': 'error', 'data': 'An error occurred while generating the scene heading.'})}\n\n"        
        
        
        
        
        
# {
#   "functions": [
#     {
#       "name": "generate_initial_scene",
#       "purpose": "Generates an initial cinematic scene based on the provided setting and characters.",
#       "sample_input": {
#         "setting": "a futuristic city",
#         "characters": [
#           { "name": "Alex", "trait": "a brave protagonist." },
#           { "name": "Jordan", "trait": "a mysterious figure." }
#         ]
#       },
#       "sample_output": "data: {\"type\": \"initial_scene_chunk\", \"data\": \"In a futuristic city illuminated by neon lights, Alex and Jordan meet under extraordinary circumstances, setting the stage for an epic adventure...\"}",
#       "explanation": "The function builds a prompt using the provided setting and characters, calls the generation API, and then streams back an SSE-formatted line. The output is a JSON string wrapped in an SSE data field with a 'type' of 'initial_scene_chunk'."
#     },
#     {
#       "name": "generate_narrative",
#       "purpose": "Generates a narrative scene continuing from the current script without explicit scene headings.",
#       "sample_input": {
#         "current_script": "The heroes have just discovered a secret passage beneath the ancient ruins.",
#         "scene_description": "A sudden confrontation erupts in the darkness."
#       },
#       "sample_output": "data: {\"type\": \"scene_chunk\", \"data\": \"Deep within the labyrinthine ruins, tension mounts as unexpected adversaries emerge from the shadows. Amid whispered warnings and clashing sounds, a fierce confrontation erupts, altering the course of their journey.\"}",
#       "explanation": "The function uses the provided current script and scene description to form a cinematic prompt. It instructs the model to produce vivid narrative and dialogue without including any explicit scene headings. The output is streamed as an SSE line with a 'type' of 'scene_chunk'."
#     },
#     {
#       "name": "generate_dialogue",
#       "purpose": "Generates a short, cinematic dialogue line for a given character based on context.",
#       "sample_input": {
#         "speaker": "Alex",
#         "trait": "Alex is a determined, quick-witted survivor.",
#         "current_scene": "Amid a chaotic battleground, Alex stands firm.",
#         "dialogue_context": [
#           { "role": "system", "content": "Keep dialogue concise and impactful." },
#           { "role": "user", "content": "What does Alex say next?" }
#         ]
#       },
#       "sample_output": "data: {\"type\": \"dialogue_chunk\", \"speaker\": \"Alex\", \"data\": \"Let's move, quickly!\"}",
#       "explanation": "The function constructs a system message for the character based on the provided context and instructs the model to generate a brief cinematic dialogue line. The response is streamed in SSE format with a 'type' of 'dialogue_chunk' and includes the 'speaker' field."
#     },
#     {
#       "name": "generate_ending_scene",
#       "purpose": "Generates the final scene that concludes the movie script, tying up loose narrative elements.",
#       "sample_input": {
#         "current_script": "After a series of thrilling encounters, the heroes' journey reaches its climax.",
#         "ending_description": "A dramatic, satisfying conclusion that ties up loose ends."
#       },
#       "sample_output": "data: {\"type\": \"ending_scene_chunk\", \"data\": \"In a final breathtaking sequence, the heroes confront their destiny. The culmination of their trials leads to an unforgettable climax that resolves their journey with dramatic intensity.\"}",
#       "explanation": "Using the current script and ending description, this function creates a prompt for the final cinematic scene. The generated text is designed to provide a conclusive ending, and it is streamed back as an SSE line with a 'type' of 'ending_scene_chunk'."
#     },
#     {
#       "name": "generate_scene_heading",
#       "purpose": "Generates a scene heading following standard screenplay formatting based on the provided scene details.",
#       "sample_input": {
#         "scene_details": "abandoned warehouse at night"
#       },
#       "sample_output": "data: {\"type\": \"scene_heading\", \"data\": \"INT. ABANDONED WAREHOUSE - NIGHT\"}",
#       "explanation": "The function creates a prompt that instructs the model to produce a standard screenplay scene heading (e.g., 'INT. ABANDONED WAREHOUSE - NIGHT') based on the input details. The output is an SSE-formatted line with a 'type' of 'scene_heading'."
#     },
#     {
#       "name": "generate_character_name",
#       "purpose": "Extracts character names from the given text and returns them in uppercase.",
#       "sample_input": {
#         "text": "In this adventure, Michael and Sarah embark on a daring mission."
#       },
#       "sample_output": "data: {\"type\": \"character_name\", \"data\": \"MICHAEL, SARAH\"}",
#       "explanation": "The function processes the input text, extracts the character names, converts them to uppercase, and then streams the results back as an SSE line with a 'type' of 'character_name'."
#     }
#   ]
# }