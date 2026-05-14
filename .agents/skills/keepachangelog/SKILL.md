---
name: keepachangelog
description: Maintain `docs/CHANGELOG.md` in the Keep a Changelog 1.1.0 format. Use when adding a CHANGELOG entry for a new feature, bug fix, deprecation, or removal; preparing a release (cutting an `[Unreleased]` section into a versioned section); reviewing a PR for missing or malformed CHANGELOG entries; or whenever the user mentions "changelog", "release notes", "what's new", or "Unreleased" section.
---

# Keep a Changelog (MADSci)

The MADSci changelog lives at `docs/CHANGELOG.md` and follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) with [Semantic Versioning](https://semver.org/spec/v2.0.0.html). This skill captures the format rules and the MADSci-specific conventions layered on top.

## Core Principles

1. **Changelogs are for humans, not machines.** Describe user-visible impact, not commit history.
2. **Every released version gets a section.** Skipping versions destroys trust in the document.
3. **Group by change type, not by PR.** Readers want "what changed", not "what shipped together".
4. **Reverse chronological.** Newest version on top; `[Unreleased]` always above the latest release.
5. **Dates in ISO 8601** (`YYYY-MM-DD`). Never localized formats.

## Change Categories

Use only these six headings, in this order when present:

| Category | Use for |
|----------|---------|
| `### Added` | New features, endpoints, CLI commands, settings, templates, public APIs |
| `### Changed` | Behavior changes to existing features (non-breaking and breaking) |
| `### Deprecated` | APIs/features still working but scheduled for removal |
| `### Removed` | Deleted features, endpoints, settings, classes, files |
| `### Fixed` | Bug fixes |
| `### Security` | Vulnerability patches |

Omit empty categories. Do not invent new ones (`Refactored`, `Internal`, `Infrastructure`, etc.) — pick the closest of the six.

## Section Structure

```markdown
## [Unreleased]

### Added
- **`SilaNodeClient`**: New client for SiLA2 servers over gRPC. Supports observable/unobservable commands and binary responses.

### Changed
- **BREAKING**: `DocumentDBBackupSettings` env prefix changed from `MONGODB_` to `DOCUMENT_DB_`.

### Removed
- **`madsci new workcell` subcommand**: Generated an orphaned YAML format with no Pydantic model.

## [0.8.0] - 2026-03-31

### Added
...
```

### Conventions used in this repo

- **Lead with the symbol or feature in backticks/bold**: `` - **`SilaNodeClient`**: ... `` — readers scan the bold prefix to find what they care about.
- **Mark breaking changes inline** with `**BREAKING**:` at the start of the bullet, even inside `### Changed` or `### Removed`.
- **Optional sub-headings** (`####`) group large feature buckets within a category — see the `[0.8.0]` "Node Location Template System" pattern. Use sparingly: only when one release ships several distinct, named workstreams.
- **Cross-reference issues, PRs, and OpenSpec changes** with relative links: `[`openspec/changes/...`](../openspec/changes/...)`. CHANGELOG paths are relative to `docs/`, not repo root.
- **Explain the why for removals and deprecations.** A removal entry should answer "what should I use instead?".

## Workflow: Adding an Entry

When you ship a user-visible change on a feature branch:

1. Open `docs/CHANGELOG.md`.
2. Find the `## [Unreleased]` section at the top.
3. Add your bullet under the correct category, creating the `### Added`/`### Changed`/etc. subheading if it doesn't exist yet.
4. Order categories Added → Changed → Deprecated → Removed → Fixed → Security.
5. Write the bullet from the user's perspective — what they can now do, what changed for them, what they need to migrate.

**One PR ≠ one bullet.** Split a multi-feature PR into multiple bullets across categories. Combine trivially related bullets (e.g., five new CLI subcommands of one command group can be one bullet listing the subcommands).

## Workflow: Cutting a Release

When promoting `[Unreleased]` to a versioned release:

1. Decide the version per SemVer: breaking changes → major; new features → minor; fixes only → patch. (MADSci is pre-1.0, so minor bumps may include breaking changes — call them out explicitly.)
2. Replace `## [Unreleased]` with `## [X.Y.Z] - YYYY-MM-DD` using today's date.
3. Insert a fresh empty `## [Unreleased]` section above it.
4. Within the new release section, prune anything that turned out to be reverted, internal-only, or duplicated.
5. Verify `pyproject.toml` versions and the CHANGELOG version match.

## What NOT to Include

- Merge commits, "merging with unstable", pre-commit autofixes, lint-only churn
- Internal refactors with no observable behavior change (unless they unblock something users will notice)
- Test-only changes
- Dependency bumps, unless they change supported versions or fix a CVE (use `### Security`)
- Generated files (`docs/Configuration.md`, OpenAPI specs)
- Future plans, TODOs, "coming soon" notes — the changelog records what shipped

## Anti-Patterns

- **Commit-log dump**: pasting `git log --oneline` output. Translate commits into user impact.
- **Vague entries**: "Various fixes and improvements", "Refactored auth". Name the surface that changed.
- **Tense drift**: pick past tense ("Added X", "Removed Y") and stay consistent within a release.
- **Burying breaking changes** in `### Fixed` or unmarked under `### Changed`. Always prefix with `**BREAKING**:`.
- **Editing released sections** to add forgotten entries. Add them to `[Unreleased]` with a note (`Backport from 0.8.0:`) instead — released sections are immutable history.
- **Omitting the Unreleased section** after cutting a release. Always leave a fresh empty one.

## Quick Audit

Before merging a PR, ask:
- Did this PR change anything a user would notice (API, CLI, config, behavior, defaults)?
- If yes: is there a CHANGELOG entry under `[Unreleased]` in the right category?
- If breaking: is it marked `**BREAKING**:`?
- If a removal/deprecation: does the entry tell the user what to use instead?

For the broader release-time audit (docs, examples, templates, skills), see the `madsci-release-audit` skill — it invokes this skill for the CHANGELOG portion.
