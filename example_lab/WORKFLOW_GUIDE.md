# Workflow Development Guide

> For interactive workflow tutorials with live examples, see **[experiment_notebook.ipynb](notebooks/experiment_notebook.ipynb)**

This guide provides workflow schema reference and advanced patterns not covered in the interactive tutorial.

## Available Example Workflows

The example lab includes several workflows demonstrating different complexity levels:

| Workflow | Complexity | Purpose |
|----------|------------|---------|
| `minimal_test.workflow.yaml` | Beginner | Basic connectivity testing |
| `simple_transfer.workflow.yaml` | Intermediate | Resource movement between nodes |
| `multistep_transfer.workflow.yaml` | Advanced | Sequential multi-node operations |
| `transfer_resource.workflow.yaml` | Expert | Advanced resource management |
| `test_feedforward_data.workflow.yaml` | Research | Data-driven adaptive experiments |

## Workflow Schema Reference

### Basic Structure
```yaml
name: My Custom Workflow
metadata:
  author: Your Name
  info: Description of workflow purpose
  version: 1.0

steps:
  - name: Human-readable step name
    key: unique_step_identifier
    node: target_node_name
    action: method_to_execute
    args:
      parameter1: value1
    description: "Step description"
```

### Step Parameters

| Parameter Type | Syntax | Usage |
|----------------|--------|-------|
| **Static Values** | `volume: 100.0` | Fixed parameters |
| **Location References** | `source: "node.location"` | Resource locations |
| **File Inputs** | `protocol: "/path/file.json"` | Protocol files |
| **Dynamic Values** | `volume: "{{previous_step.result}}"` | Inter-step data |

### Available Actions by Node

| Node Type | Actions | Purpose |
|-----------|---------|---------|
| **liquidhandler** | `run_command`, `run_protocol`, `deck_transfer` | Liquid handling operations |
| **robotarm** | `pick_and_place`, `move_to_position` | Material transfer |
| **platereader** | `read_plate`, `read_well`, `calibrate` | Optical measurements |
| **advanced_example** | Various complex actions | Multi-function operations |

### Workflow Dependencies

#### Sequential Execution (Default)
Steps execute in order automatically.

#### Conditional Execution
```yaml
steps:
  - name: Check Status
    key: status_check
    action: get_status

  - name: Conditional Step
    key: conditional_action
    action: run_protocol
    condition: "status_check.result == 'ready'"
```

#### Parallel Execution
```yaml
steps:
  - name: Parallel Step 1
    key: parallel_1
    action: prepare_reagents
    parallel_group: "prep"

  - name: Parallel Step 2
    key: parallel_2
    action: prepare_plates
    parallel_group: "prep"

  - name: Wait for Prep
    key: wait_prep
    depends_on: ["parallel_1", "parallel_2"]
    action: begin_experiment
```

## Best Practices

### Workflow Design
1. **Start Simple**: Begin with single-step workflows and add complexity gradually
2. **Test Incrementally**: Validate each step before adding the next
3. **Use Descriptive Names**: Make step names and keys human-readable
4. **Document Purpose**: Always include metadata explaining the workflow's goal

### Error Handling
1. **Validate Resources**: Check resource availability before starting
2. **Handle Failures**: Design workflows to handle partial failures gracefully
3. **Monitor Progress**: Use the dashboard to track workflow execution
4. **Log Everything**: Ensure adequate logging for troubleshooting

### Performance Optimization
1. **Parallel Execution**: Run independent steps in parallel when possible
2. **Resource Scheduling**: Consider resource conflicts in step ordering
3. **Minimize Transfers**: Optimize resource movement to reduce cycle time
4. **Cache Results**: Reuse computational results where appropriate

## Workflow Debugging

### Common Issues

#### Resource Not Found
```
Error: Resource 'liquidhandler_1_deck1' not found
```
**Solution**: Verify resource IDs in node definitions and ensure nodes are running

#### Action Not Available
```
Error: Action 'invalid_action' not found on node 'liquidhandler_1'
```
**Solution**: Check node API documentation and verify action names

#### Location Conflicts
```
Error: Target location already occupied
```
**Solution**: Check resource states and add resource management steps

### Debugging Tools

#### Workflow Status
```bash
# Check workflow execution status
curl http://localhost:8005/workflows/status

# Get detailed workflow logs
curl http://localhost:8005/workflows/{workflow_id}/logs
```

#### Node Status
```bash
# Check individual node health
curl http://localhost:2000/health
curl http://localhost:2000/status

# List available actions
curl http://localhost:2000/definition
```

#### Resource Status
```bash
# Check resource inventory
curl http://localhost:8003/resources

# Get resource location tracking
curl http://localhost:8006/locations
```

## Advanced Features

### Dynamic Parameters

Use runtime parameters to make workflows flexible:

```yaml
name: Parameterized Workflow

parameters:
  - name: source_node
    type: string
    default: "liquidhandler_1"
  - name: volume
    type: float
    default: 100.0

steps:
  - name: Transfer
    key: transfer
    action: liquid_transfer
    args:
      source: "{{source_node}}.deck_1"
      volume: "{{volume}}"
```

### Data Integration

Capture and use experimental data in workflows:

```yaml
steps:
  - name: Measure Sample
    key: measurement
    action: read_plate

  - name: Analyze Results
    key: analysis
    action: run_analysis
    args:
      data: "{{measurement.result}}"

  - name: Adaptive Step
    key: adaptive
    action: adjust_parameters
    args:
      optimization_target: "{{analysis.recommendation}}"
```

### Workflow Composition

Combine smaller workflows into larger experimental campaigns:

```yaml
name: Multi-Day Experiment

metadata:
  author: Lab Manager
  info: Three-day experimental campaign
  version: 1.0

sub_workflows:
  - name: Day 1 Setup
    workflow: workflows/day1_prep.workflow.yaml
  - name: Day 2 Execution
    workflow: workflows/day2_experiment.workflow.yaml
  - name: Day 3 Analysis
    workflow: workflows/day3_analysis.workflow.yaml
```

## Next Steps

1. **Study the Examples**: Run through each workflow level in order
2. **Modify Parameters**: Change values in existing workflows to see effects
3. **Create Simple Workflows**: Start with single-step workflows for your use case
4. **Build Complexity**: Gradually add more steps and nodes
5. **Integrate Data**: Add data capture and analysis to your workflows

For more information:
- [MADSci Workcell Manager Documentation](../src/madsci_workcell_manager/README.md)
- [Workflow Schema Reference](../src/madsci_common/types/workflow_types.py)
- [Node Action Documentation](../src/madsci_node_module/README.md)
