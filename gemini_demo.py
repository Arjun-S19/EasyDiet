from __future__ import annotations
import os
from pathlib import Path
import re
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> None:
        '''Dummy load_dotenv if python-dotenv is not installed'''
        return None

try:
    from google import genai
except ImportError as exc:
    genai = None
    GENAI_IMPORT_ERROR = exc
else:
    GENAI_IMPORT_ERROR = None

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PROMPT = Path("system_prompt.txt").read_text(encoding="utf-8")
MODEL_NAME = "gemini-2.5-flash"

ingredients = [
    "2 onions",
    "1 bell pepper",
    "3 cloves of garlic",
    "3 tomatoes",
    "4 eggs",
    "penne pasta",
    "olive oil",
    "salt",
    "whole chicken",
]

INSTRUCTION_PATTERN = re.compile(r"(\d+)\.\s+(.+)")


def create_client() -> object:
    '''Create and return a Gemini API client'''
    if genai is None:
        raise RuntimeError("google-genai is not installed") from GENAI_IMPORT_ERROR
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=GEMINI_API_KEY)


def format_ingredients_for_prompt(items: list[str]) -> str:
    '''Return the ingredient list formatted to match the system prompt contract'''
    quoted_items = ", ".join(f'"{item}"' for item in items)
    return f"INGREDIENTS = [{quoted_items}]"


def build_prompt_contents(prompt_text: str, items: list[str]) -> str:
    '''Compose the full prompt sent to the model'''
    formatted_ingredients = format_ingredients_for_prompt(items)
    return f"{prompt_text.strip()}\n\n{formatted_ingredients}"


def generate_recipe_text(items: list[str], client: object | None = None) -> str:
    '''Request recipe text from Gemini for the provided ingredients'''
    prompt_contents = build_prompt_contents(PROMPT, items)
    active_client = client or create_client()
    response = active_client.models.generate_content(model=MODEL_NAME, contents=prompt_contents)
    if not hasattr(response, "text") or not response.text:
        raise RuntimeError("Model response did not include printable recipe text.")
    return response.text


def validate_recipe_output(recipe_text: str) -> list[dict[str, object]]:
    '''Validate the model output and return structured recipe data if valid'''
    if not recipe_text or not recipe_text.strip():
        raise ValueError("Recipe output is empty.")

    blocks = [
        block.strip()
        for block in re.split(r"\n{2,}(?=[^\n]+\nServings:)", recipe_text.strip())
        if block.strip()
    ]

    if not blocks:
        raise ValueError("No recipe blocks were found in the output")

    if not 2 <= len(blocks) <= 4:
        raise ValueError(f"Expected between 2 and 4 recipes, found {len(blocks)}.")

    parsed_recipes: list[dict[str, object]] = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]

        if len(lines) < 6:
            raise ValueError("Recipe block is missing required lines")

        title = lines[0]

        servings_match = re.fullmatch(r"Servings:\s*(\d+)", lines[1])
        if not servings_match:
            raise ValueError("Servings line is malformed or missing")
        servings = int(servings_match.group(1))

        time_match = re.fullmatch(r"Time:\s*(\d+)\s+minutes", lines[2])
        if not time_match:
            raise ValueError("Time line is malformed or missing")
        time_minutes = int(time_match.group(1))

        if lines[3] != "Ingredients:":
            raise ValueError("Ingredients section heading is missing")

        idx = 4
        ingredients_list: list[str] = []
        while idx < len(lines) and lines[idx].startswith("- "):
            ingredients_list.append(lines[idx][2:].strip())
            idx += 1

        if not ingredients_list:
            raise ValueError("At least one ingredient line is required")

        if idx >= len(lines) or lines[idx] != "Instructions:":
            raise ValueError("Instructions section heading is missing")

        idx += 1
        instructions: list[str] = []
        while idx < len(lines) and (match := INSTRUCTION_PATTERN.match(lines[idx])):
            instructions.append(match.group(2).strip())
            idx += 1

        if not instructions:
            raise ValueError("At least one numbered instruction is required")

        if idx != len(lines):
            raise ValueError("Unexpected extra content found after instructions")

        parsed_recipes.append(
            {
                "title": title,
                "servings": servings,
                "time_minutes": time_minutes,
                "ingredients": ingredients_list,
                "instructions": instructions,
            }
        )

    return parsed_recipes


def main() -> None:
    '''Main function to generate and validate recipe text'''
    recipe_text = generate_recipe_text(ingredients)
    validate_recipe_output(recipe_text)
    print(recipe_text)


if __name__ == "__main__":
    main()
