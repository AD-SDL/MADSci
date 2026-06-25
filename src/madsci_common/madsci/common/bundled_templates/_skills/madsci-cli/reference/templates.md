# MADSci Template System

Reference for the bundled template system used by `madsci new`. SKILL.md links here when creating or modifying templates; everyday CLI work doesn't need this file.

## Contents

- [Manifest format](#manifest-format)
- [Template categories](#template-categories)
- [Jinja2 filters](#jinja2-filters)
- [Template-model alignment](#template-model-alignment)

## Manifest format

Templates live in `src/madsci_common/madsci/common/bundled_templates/`. Each has a `template.yaml` manifest:

```yaml
name: "Module Name"
version: "1.0.0"
description: "What this template creates"
category: "lab|module|node|interface|experiment|workflow"
tags: ["device", "robot"]

parameters:
  - name: module_name
    type: string
    description: "Name of the module"
    required: true
    pattern: "^[a-z][a-z0-9_]*$"
  - name: port
    type: integer
    description: "Server port"
    default: 2000
    min: 1024
    max: 65535
  - name: include_tests
    type: boolean
    description: "Include test files"
    default: true

files:
  - source: "template/{{module_name}}_node.py.j2"
    destination: "{{module_name}}/{{module_name}}_node.py"
  - source: "template/test_node.py.j2"
    destination: "{{module_name}}/tests/test_node.py"
    condition: "{{ include_tests }}"

hooks:
  post_generate:
    - command: "ruff format {{module_name}}/"
      continue_on_error: true
```

## Template categories

33 templates across these categories:

- `lab/`: minimal lab scaffold
- `module/`: device, compute modules (full packages with tests, Dockerfile)
- `node/`: basic node, rest node
- `interface/`: node interface
- `experiment/`: script, notebook, tui, node modalities
- `workflow/`: basic workflow
- `addon/`: docs, drivers, notebooks, gitignore, compose, dev_tools, agent_config, all

## Jinja2 filters

- `pascal_case` — converts `my_module` → `MyModule`

## Template-Model Alignment

Every template that generates YAML/JSON configuration must produce output that validates against a specific Pydantic model. Templates declare their target model via the `target_model` field in `template.yaml`:

```yaml
# In template.yaml
target_model: "madsci.common.types.workflow_types.WorkflowDefinition"
```

| Template Category | Output Type | Target Pydantic Model |
|---|---|---|
| lab/* | settings.yaml | MadsciContext / ManagerSettings subclasses (no single target_model — shared file) |
| workflow/* | *.workflow.yaml | `WorkflowDefinition` |
| node/* | Python code | Uses `RestNodeConfig` in generated code |
| module/* | Python package | Uses `RestNodeConfig`, domain-specific models |
| experiment/* | Python code | Uses `ExperimentDesign` in generated code |

When creating new templates for config files:

1. Identify the Pydantic model first
2. Build the template to match its schema
3. Set `target_model` in `template.yaml` so tests validate output automatically
