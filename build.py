#!/usr/bin/env python3
"""Parse markdown recipe cards into recipes.json for the static site."""

import json
import os
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
KNOWN_SECTIONS = {"ingredients", "instructions"}


def parse_markdown(text):
    """Parse a recipe markdown file into structured data."""
    lines = text.strip().split("\n")
    if not lines:
        return None

    # Title from first # heading
    title = None
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
            break
    if not title:
        return None

    # Split into ## sections
    sections = {}
    current_section = None
    current_lines = []
    for line in lines:
        if line.startswith("## "):
            if current_section is not None:
                sections[current_section] = current_lines
            current_section = line[3:].strip().lower()
            current_lines = []
        elif current_section is not None:
            current_lines.append(line)

    if current_section is not None:
        sections[current_section] = current_lines

    # Must have both ingredients and instructions
    if "ingredients" not in sections or "instructions" not in sections:
        return None

    ingredients = parse_ingredients(sections["ingredients"])
    instructions = parse_instructions(sections["instructions"])

    # Capture extra sections as notes
    notes = []
    for key, value in sections.items():
        if key not in KNOWN_SECTIONS:
            section_text = "\n".join(value).strip()
            if section_text:
                notes.append(f"## {key.title()}\n{section_text}")

    return {
        "title": title,
        "ingredients": ingredients,
        "instructions": instructions,
        "notes": "\n\n".join(notes) if notes else "",
    }


def parse_ingredients(lines):
    """Parse ingredient lines, preserving subsection headers."""
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("### "):
            result.append({"group": stripped[4:].strip(), "items": []})
        elif stripped.startswith("- "):
            item = stripped[2:].strip()
            if result and isinstance(result[-1], dict) and "items" in result[-1]:
                result[-1]["items"].append(item)
            else:
                result.append(item)
    return result


def parse_instructions(lines):
    """Parse instruction lines, preserving subsection headers."""
    result = []
    current_group = None
    current_steps = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("### "):
            if current_group is not None:
                result.append({"group": current_group, "steps": current_steps})
                current_steps = []
            current_group = stripped[4:].strip()
        elif re.match(r"^\d+\.", stripped):
            step = re.sub(r"^\d+\.\s*", "", stripped)
            current_steps.append(step)

    if current_group is not None:
        result.append({"group": current_group, "steps": current_steps})
    elif current_steps:
        result = current_steps

    return result


# --- Categorization ---

PROTEIN_KEYWORDS = {
    "chicken": "chicken",
    "beef": "beef",
    "steak": "beef",
    "meatloaf": "beef",
    "meatball": "beef",
    "hamburger": "beef",
    "cheeseburger": "beef",
    "pork": "pork",
    "ham": "pork",
    "bacon": "pork",
    "sausage": "pork",
    "shrimp": "shrimp",
    "prawn": "shrimp",
    "salmon": "salmon",
    "fish": "fish",
    "tilapia": "fish",
    "catfish": "fish",
    "cod": "fish",
    "tuna": "fish",
    "seafood": "fish",
    "turkey": "turkey",
    "lamb": "lamb",
}

# Title-only meal keywords: matched against the recipe title only, never the ingredient list.
# "carrots" in an ingredient list doesn't make a stew into a side dish.
TITLE_ONLY_MEAL_KEYWORDS = {
    "rice": "side",
    "carrots": "side",
    "broccoli": "side",
    "cauliflower": "side",
    "bean salad": "side",
}

# Soup-family titles always win — a "Chicken Noodle Soup" is a soup even though
# it also contains the pasta keyword "noodle".
SOUP_TITLE_KEYWORDS = ("soup", "stew", "chili", "chowder", "bisque")

# Everything else: title first, then full text fallback.
MEAL_KEYWORDS = {
    "breakfast": "breakfast",
    "brunch": "breakfast",
    "casserole": "main",
    "frittata": "breakfast",
    "quiche": "breakfast",
    "french toast": "breakfast",
    "pancake": "breakfast",
    "smoothie": "drink",
    "salad": "salad",
    "slaw": "salad",
    "pasta": "pasta",
    "spaghetti": "pasta",
    "linguine": "pasta",
    "macaroni": "pasta",
    "mac and cheese": "pasta",
    "orzo": "pasta",
    "tortellini": "pasta",
    "lasagna": "pasta",
    "appetizer": "appetizer",
    "deviled egg": "appetizer",
    "dip": "appetizer",
    "queso": "appetizer",
    "meatball": "appetizer",
    "flautas": "appetizer",
    "cookie": "dessert",
    "cake": "dessert",
    "frosting": "dessert",
    "crisp": "dessert",
    "muffin": "dessert",
    "pumpkin cookie": "dessert",
    "chocolate": "dessert",
    "brownie": "dessert",
    "energy bite": "snack",
}

METHOD_KEYWORDS = {
    "slow cooker": "slow-cooker",
    "crockpot": "slow-cooker",
    "crock pot": "slow-cooker",
    "crock-pot": "slow-cooker",
    "grill": "grill",
    "grilled": "grill",
    "smoker": "grill",
    "smoked": "grill",
    "air fryer": "air-fryer",
    "air-fryer": "air-fryer",
    "no bake": "no-cook",
    "no-bake": "no-cook",
    "no cook": "no-cook",
}


def _classify_meal(title_lower, full_text):
    # 1. Soup-family titles trump everything else.
    for kw in SOUP_TITLE_KEYWORDS:
        if _has_word(title_lower, kw):
            return "soup"
    # 2. Title-only side keywords (so "carrots" in an ingredient list can't fire).
    for kw in sorted(TITLE_ONLY_MEAL_KEYWORDS.keys(), key=len, reverse=True):
        if _has_word(title_lower, kw):
            return TITLE_ONLY_MEAL_KEYWORDS[kw]
    # 3. Remaining keywords: prefer a title hit, then fall back to ingredients.
    sorted_meal = sorted(MEAL_KEYWORDS.keys(), key=len, reverse=True)
    for kw in sorted_meal:
        if _has_word(title_lower, kw):
            return MEAL_KEYWORDS[kw]
    for kw in sorted_meal:
        if _has_word(full_text, kw):
            return MEAL_KEYWORDS[kw]
    return "main"


def _has_word(text, kw):
    # Word-boundary match with optional trailing 's' so "meatball" matches "meatballs"
    # and "cake" doesn't match "cheesecake".
    return re.search(r"\b" + re.escape(kw) + r"s?\b", text) is not None


def categorize(title, ingredients_text):
    """Auto-categorize a recipe by protein, meal type, and method."""
    title_lower = title.lower()
    text = (title + " " + ingredients_text).lower()

    protein = "vegetarian"
    for kw, cat in PROTEIN_KEYWORDS.items():
        if kw in text:
            protein = cat
            break

    meal = _classify_meal(title_lower, text)

    method = None
    for kw, cat in METHOD_KEYWORDS.items():
        if kw in text:
            method = cat
            break
    # Fallback: check for oven/bake/broil/stovetop clues
    if method is None:
        if any(w in text for w in ["bake", "baked", "oven", "broil", "roast"]):
            method = "oven"
        elif any(w in text for w in ["skillet", "pan", "stir fry", "stir-fry", "saute", "sautee", "stovetop"]):
            method = "stovetop"

    return protein, meal, method


def flatten_ingredients_text(ingredients):
    """Flatten structured ingredients to plain text for search/categorization."""
    parts = []
    for item in ingredients:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and "items" in item:
            parts.extend(item["items"])
    return " ".join(parts)


def flatten_instructions_text(instructions):
    """Flatten structured instructions to plain text for search."""
    parts = []
    for item in instructions:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and "steps" in item:
            parts.extend(item["steps"])
    return " ".join(parts)


def main():
    # Load source URLs
    urls_file = SCRIPT_DIR / "_recipe_urls.json"
    url_map = {}
    if urls_file.exists():
        with open(urls_file) as f:
            for entry in json.load(f):
                url_map[entry["file"]] = entry["url"]

    recipes = []
    all_proteins = set()
    all_meals = set()
    all_methods = set()

    md_files = sorted(SCRIPT_DIR.glob("*.md"))
    for md_file in md_files:
        if md_file.name.startswith("_"):
            continue

        text = md_file.read_text(encoding="utf-8")
        parsed = parse_markdown(text)
        if parsed is None:
            print(f"  Skipped: {md_file.name}")
            continue

        ingredients_text = flatten_ingredients_text(parsed["ingredients"])
        instructions_text = flatten_instructions_text(parsed["instructions"])

        protein, meal, method = categorize(parsed["title"], ingredients_text)
        all_proteins.add(protein)
        all_meals.add(meal)
        if method:
            all_methods.add(method)

        search_text = " ".join([
            parsed["title"].lower(),
            ingredients_text.lower(),
            instructions_text.lower(),
        ])

        recipe = {
            "id": md_file.stem,
            "title": parsed["title"],
            "ingredients": parsed["ingredients"],
            "instructions": parsed["instructions"],
            "notes": parsed["notes"],
            "protein": protein,
            "meal": meal,
            "method": method,
            "sourceUrl": url_map.get(md_file.name, ""),
            "searchText": search_text,
        }
        recipes.append(recipe)

    output = {
        "recipes": recipes,
        "filters": {
            "protein": sorted(all_proteins),
            "meal": sorted(all_meals),
            "method": sorted(all_methods),
        },
    }

    out_path = SCRIPT_DIR / "recipes.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nBuilt {len(recipes)} recipes → {out_path}")
    print(f"Proteins: {sorted(all_proteins)}")
    print(f"Meals: {sorted(all_meals)}")
    print(f"Methods: {sorted(all_methods)}")


if __name__ == "__main__":
    main()
