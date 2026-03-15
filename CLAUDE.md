# Recipe Book

Personal recipe card app — a static site hosted on GitHub Pages.

## What This Is

A searchable collection of ~115 recipes rendered as cards with filters (protein, meal type, cooking method) and a pinning system for weekly meal planning.

**Live site:** Deployed via GitHub Pages from `main` branch (see `.github/workflows/static.yml`).

## Project Structure

- `*.md` — Individual recipe files (one per recipe, markdown format)
- `build.py` — Parses all `.md` files into `recipes.json` for the site
- `recipes.json` — Generated file, do not edit by hand
- `index.html` — Single-page app (vanilla JS, no framework)
- `style.css` — Styles
- `pinned.json` — Pinned/starred recipes, synced to repo via GitHub API from the browser
- `_recipe_urls.json` — Maps recipe filenames to their source URLs
- `pinned.json` — Weekly pinned recipes (auto-synced from browser via GitHub API)

## Adding a Recipe

1. Create `recipe-name.md` in this directory following the format below
2. Add an entry to `_recipe_urls.json` with the source URL
3. Run `python3 build.py` to regenerate `recipes.json`
4. Commit all three changes and push

### Recipe Markdown Format

```markdown
# Recipe Title

## Ingredients
- 1 cup ingredient one
- 2 tablespoons ingredient two

### Optional Subgroup
- 1/2 cup grouped ingredient

## Instructions
1. First step.
2. Second step.

## Notes (optional)
Any extra section becomes notes.
```

- Title: `# heading` (required)
- `## Ingredients` and `## Instructions` are required sections
- Ingredients use `- ` bullet lists; subgroups use `### ` headings
- Instructions use numbered lists (`1.`, `2.`, etc.); subgroups use `### ` headings
- Any other `##` section is captured as notes

## Categorization

`build.py` auto-categorizes recipes by scanning the title and ingredients for keywords:
- **Protein:** chicken, beef, pork, shrimp, salmon, fish, turkey, lamb, or vegetarian (default)
- **Meal type:** dessert, soup, salad, pasta, breakfast, appetizer, side, snack, drink, or main (default)
- **Method:** slow-cooker, grill, air-fryer, no-cook, oven, stovetop (or null)

## Pin Syncing

Pins auto-save to `pinned.json` in the repo via the GitHub API when toggled in the browser. Requires a GitHub PAT with `repo` scope saved in the settings modal. Pins load from `pinned.json` on page load so they sync across browsers.
