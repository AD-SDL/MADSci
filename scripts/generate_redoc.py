"""Generate standalone Redoc HTML pages from OpenAPI JSON specs.

Reads JSON specs from docs/api-specs/ and writes self-contained HTML pages
to docs/rest-api/ that can be opened directly in a browser.

Usage:
    python scripts/generate_redoc.py
"""

import json
from pathlib import Path

SPECS_DIR = Path(__file__).resolve().parent.parent / "docs" / "api-specs"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "rest-api"

REDOC_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <title>{title} - REST API</title>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
  <style>body {{ margin: 0; padding: 0; }}</style>
</head>
<body>
  <div id="redoc-container"></div>
  <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
  <script>
    var spec = {spec_json};
    Redoc.init(spec, {{}}, document.getElementById('redoc-container'));
  </script>
</body>
</html>
"""


def generate_redoc_pages() -> None:
    """Generate Redoc HTML pages for each OpenAPI spec."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    spec_files = sorted(SPECS_DIR.glob("*.json"))
    if not spec_files:
        print(f"No JSON specs found in {SPECS_DIR}")
        return

    for spec_path in spec_files:
        spec = json.loads(spec_path.read_text())
        title = spec.get("info", {}).get("title", spec_path.stem)

        # Generate a self-contained HTML page with the spec embedded inline
        html_filename = spec_path.stem + ".html"
        html_path = OUTPUT_DIR / html_filename
        html_content = REDOC_TEMPLATE.format(
            title=title,
            spec_json=json.dumps(spec),
        )
        html_path.write_text(html_content)
        print(f"  Generated {html_path}")

    print(f"\nGenerated {len(spec_files)} Redoc pages in {OUTPUT_DIR}")


if __name__ == "__main__":
    generate_redoc_pages()
