"""Generate standalone Redoc HTML pages from OpenAPI JSON specs.

Reads JSON specs from docs/api-specs/ and writes self-contained HTML pages
to docs/rest-api/ that can be opened directly in a browser.

Usage:
    python scripts/generate_redoc.py
"""

import copy
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


def break_circular_refs(spec: dict) -> int:
    """Break circular $ref chains that crash Redoc's schema renderer.

    Redoc processes the full schema tree on initialization.  When a
    discriminated-union schema (``oneOf`` + ``discriminator``) has variants
    whose properties reference the union itself (e.g. Container.children →
    AnyResourceModel → Container), Redoc enters infinite recursion.

    This function finds such back-references and replaces them with a simple
    ``{"type": "object"}`` stub so Redoc can render the page.  The canonical
    JSON spec in ``docs/api-specs/`` is **not** affected — only the in-memory
    copy used for HTML generation.

    Returns the number of back-references replaced.
    """
    schemas = spec.get("components", {}).get("schemas", {})

    # Step 1: identify union schemas (oneOf + discriminator) and their variants.
    union_variants: dict[str, set[str]] = {}
    for name, schema in schemas.items():
        if "oneOf" not in schema or "discriminator" not in schema:
            continue
        variants: set[str] = set()
        for item in schema["oneOf"]:
            ref = item.get("$ref", "")
            if ref:
                variants.add(ref.rsplit("/", 1)[-1])
        if variants:
            union_variants[name] = variants

    if not union_variants:
        return 0

    # Step 2: for each variant schema, replace $ref back-references to
    # the parent union with a non-recursive placeholder.
    replacements = 0

    def _replace_backrefs(obj: object, union_name: str) -> None:
        nonlocal replacements
        if isinstance(obj, dict):
            if "$ref" in obj and obj["$ref"].rsplit("/", 1)[-1] == union_name:
                obj.clear()
                obj.update(
                    {
                        "type": "object",
                        "title": union_name,
                        "description": f"Any {union_name} variant (recursive).",
                    }
                )
                replacements += 1
                return
            for value in obj.values():
                _replace_backrefs(value, union_name)
        elif isinstance(obj, list):
            for value in obj:
                _replace_backrefs(value, union_name)

    for union_name, variants in union_variants.items():
        for variant_name in variants:
            if variant_name in schemas:
                _replace_backrefs(schemas[variant_name], union_name)

    return replacements


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

        # Work on a deep copy so the canonical spec files are unmodified.
        render_spec = copy.deepcopy(spec)
        replaced = break_circular_refs(render_spec)
        if replaced:
            print(
                f"    Broke {replaced} circular $ref(s) for Redoc in {spec_path.name}"
            )

        # Generate a self-contained HTML page with the spec embedded inline
        html_filename = spec_path.stem + ".html"
        html_path = OUTPUT_DIR / html_filename
        html_content = REDOC_TEMPLATE.format(
            title=title,
            spec_json=json.dumps(render_spec),
        )
        html_path.write_text(html_content)
        print(f"  Generated {html_path}")

    print(f"\nGenerated {len(spec_files)} Redoc pages in {OUTPUT_DIR}")


if __name__ == "__main__":
    generate_redoc_pages()
