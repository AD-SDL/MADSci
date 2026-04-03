---
name: madsci-release-audit
description: Audit MADSci release artifacts for completeness and correctness. Use when preparing a PR, finishing a plan, completing a feature branch, or before any merge to main/unstable. Checks CHANGELOG, docs, guides, example lab, notebooks, templates, and skills for staleness, broken imports, and deprecated patterns.
---

# MADSci Release Artifact Audit

Code changes are only half the story. Documentation, examples, templates, and the CHANGELOG frequently fall out of sync with the code they describe. This skill provides a structured audit checklist to catch these gaps before they reach users.

## When to Use

- Before opening or updating a PR
- As the final phase of an implementation plan
- After completing a feature branch
- Before any merge to `main` or `unstable`
- When the user asks to "audit", "review artifacts", or "check docs"

## Audit Checklist

Work through each section. For each item, either confirm it's correct or fix it. Report findings to the user as you go.

### 1. CHANGELOG (`docs/CHANGELOG.md`)

**Goal**: Every user-facing change has a corresponding CHANGELOG entry.

1. Identify the version being prepared (check `pyproject.toml` at repo root for the current version)
2. Get the git log since the last release tag: `git log --oneline <last-tag>..HEAD`
3. For each merged PR, verify it has coverage in the CHANGELOG under the correct category:
   - **Added**: New features, new endpoints, new CLI commands, new templates
   - **Changed**: Behavior changes, renames, breaking changes (mark with `**BREAKING**`)
   - **Fixed**: Bug fixes
   - **Removed**: Deleted features or files
   - **Deprecated**: Newly deprecated APIs
4. Ensure the header uses the correct version and date format: `## [X.Y.Z] - YYYY-MM-DD`
5. Do NOT include interstitial development details (merge commits, pre-commit fixes, "merging with unstable", etc.)

### 2. Documentation and Guides (`docs/`)

**Goal**: Code examples in docs match the current API surface.

1. Search docs for import statements and verify they resolve:
   ```
   grep -r "from madsci\." docs/ --include="*.md"
   ```
2. Check for references to deprecated/removed names. Current known deprecated patterns:
   - `ActionHandler` (use `@action` decorator)
   - `self.node_definition` (use `self.node_info`)
   - `NodeDefinition` (use `NodeConfig`)
   - `SquidServer` / `SquidSettings` (use `LabManager` / `LabManagerSettings`)
   - `load_definition()` / `load_or_create_definition()` (removed)
   - `create_minio_client` (use `create_object_storage_client`)
   - `mongo_db_url` without backward-compat context (use `document_db_url`)
   - `PyMongoHandler` / `InMemoryMongoHandler` (use `PyDocumentStorageHandler` / `InMemoryDocumentStorageHandler`)
3. Check infrastructure references are current:
   - MongoDB references should say FerretDB (unless discussing migration)
   - Redis references should say Valkey (unless discussing migration)
   - MinIO references should say SeaweedFS (unless discussing migration)
   - Ports: FerretDB=27017, PostgreSQL=5432+5434, Valkey=6379, SeaweedFS=8333/9333
4. Verify cross-references between docs (links to other guides, README paths) still resolve

### 3. Example Lab (`examples/example_lab/`)

**Goal**: The example lab README and configuration match the actual compose/settings files.

1. Compare `README.md` infrastructure section against `compose.infra.yaml`:
   - Service names match
   - Ports match
   - Descriptions are accurate
2. Verify `settings.yaml` and `.env` use current field names and terminology
3. Check that example modules use current patterns (`@action`, `self.node_info`, `self.event_client`)
4. Verify workflow YAML files reference valid node names and actions
5. Check troubleshooting commands reference correct service names

### 4. Example Notebooks (`examples/notebooks/`)

**Goal**: Notebooks demonstrate current APIs and patterns.

1. Check import statements use current module paths
2. Verify class names and method signatures match current code:
   - `ExperimentNotebook`, `ExperimentScript`, `ExperimentTUI`, `ExperimentNode`
   - `RestNode`, `RestNodeConfig`, `@action`
   - `MadsciClientMixin` client properties (`event_client`, `workcell_client`, etc.)
3. Check that database/infrastructure references use FOSS terminology
4. Verify backup/migration notebook uses current tool names (`DocumentDBBackupTool`, etc.)

### 5. Bundled Templates (`src/madsci_common/madsci/common/bundled_templates/`)

**Goal**: Generated code from templates is correct and uses current APIs.

1. **Run the template validation tests** (these catch most issues automatically):
   ```bash
   pytest src/madsci_common/tests/test_templates/test_template_engine.py -x -q
   ```
   The `TestGeneratedCodeQuality` tests verify:
   - All `from madsci.*` imports resolve to real names
   - Generated YAML/TOML/JSON files parse correctly
   - No deprecated patterns appear in generated Python code

2. If tests pass, templates are likely correct. If adding new deprecations, update the `DEPRECATED_PYTHON_PATTERNS` list in the test file.

3. For manual review, spot-check:
   - Module templates use `@action` (not `ActionHandler`)
   - Module templates reference `self.node_info` (not `self.node_definition`)
   - Module templates use `self.event_client.info()` (not `self.logger.log()`)
   - Lab templates use `LabManager` / `LabManagerSettings` (not `SquidServer` / `SquidSettings`)
   - Types templates import `RestNodeConfig` from `madsci.common.types.node_types`

### 6. Agent Skills (`.agents/skills/`, `bundled_templates/_skills/`)

**Goal**: Skills reference current APIs and patterns.

1. Check that code examples in skill files use current import paths and class names
2. Verify architecture descriptions match current codebase structure
3. Ensure any file paths mentioned in skills still exist

### 7. Main README (`README.md`)

**Goal**: Top-level README is accurate for the release.

1. Verify version badge and CI status links
2. Check installation instructions are current
3. Verify quick start commands work
4. Ensure component documentation links resolve
5. Check the CLI command table matches the current command set

## What NOT to Audit

- **Auto-generated files**: `docs/Configuration.md`, `docs/api-specs/`, REST API docs (these are regenerated)
- **Git history**: Don't audit commit messages or branch structure
- **Test code**: Tests are validated by running them, not by reading them
- **Code internals**: This audit covers artifacts users interact with, not implementation details

## Adding New Deprecations

When you deprecate or remove an API, add the old name to two places:

1. `DEPRECATED_PYTHON_PATTERNS` in `src/madsci_common/tests/test_templates/test_template_engine.py` — catches it in templates automatically
2. The list in section 2 of this skill — reminds auditors to check docs/guides

## Reporting

After completing the audit, provide a summary:
- Items checked and confirmed correct
- Issues found and fixed
- Issues found that need user input
- Any items that could not be verified (e.g., Docker-dependent checks)
