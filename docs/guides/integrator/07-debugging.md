# Debugging

**Audience**: Equipment Integrator
**Prerequisites**: [Wiring the Node](./05-wiring-the-node.md), [Testing Strategies](./06-testing-strategies.md)
**Time**: ~20 minutes

## Overview

Debugging instrument modules involves isolating issues across multiple layers: hardware communication, interface logic, node framework, and workcell orchestration. This guide covers systematic approaches to identifying and resolving problems at each layer.

## Debugging Layers

```
Layer 4: Workcell / Workflow
Layer 3: Node REST API
Layer 2: Interface Logic
Layer 1: Hardware / Driver
```

**Rule of thumb**: Always start debugging at the lowest layer and work upward. If the interface doesn't work standalone, the node won't work either.

## Layer 1: Hardware and Driver Issues

### Symptoms
- Connection timeouts
- No response from device
- Garbled data
- Permission errors

### Diagnosis

**Check physical connection:**

```bash
# Linux: List serial devices
ls -la /dev/ttyUSB* /dev/ttyACM*

# macOS: List serial devices
ls -la /dev/tty.usb* /dev/cu.usb*

# Check USB devices
lsusb  # Linux
system_profiler SPUSBDataType  # macOS
```

**Check permissions:**

```bash
# Linux: Add user to dialout group for serial access
sudo usermod -aG dialout $USER
# Log out and back in for group change to take effect

# Check device permissions
ls -la /dev/ttyUSB0
# Should show: crw-rw---- 1 root dialout ...
```

**Test raw communication:**

```python
# Quick serial test (independent of MADSci)
import serial

port = serial.Serial("/dev/ttyUSB0", baudrate=9600, timeout=5)
port.write(b"*IDN?\n")
response = port.readline()
print(f"Response: {response}")
port.close()
```

**Test network communication:**

```bash
# Check if device is reachable
ping 192.168.1.100

# Check if port is open
nc -zv 192.168.1.100 5000

# Test HTTP endpoint
curl http://192.168.1.100:5000/api/status
```

### Common Fixes

| Problem | Solution |
|---------|----------|
| `Permission denied: /dev/ttyUSB0` | Add user to `dialout` group (Linux) or check System Preferences > Security (macOS) |
| Device not found | Check cable, try different USB port, verify driver installed |
| Garbled data | Check baud rate, parity, stop bits match device settings |
| Timeout on read | Increase timeout, check device is powered on, verify command format |
| `Address already in use` | Another process has the port open. Use `lsof /dev/ttyUSB0` to find it |

## Layer 2: Interface Issues

### Symptoms
- Interface methods raise unexpected exceptions
- Incorrect data returned
- State inconsistencies

### Diagnosis

**Test the interface directly in Python:**

```python
# Interactive debugging (works in Jupyter too)
from my_sensor_interface import MySensorInterface

iface = MySensorInterface(port="/dev/ttyUSB0", baud_rate=9600)
iface.connect()

# Test individual operations
print(f"Connected: {iface.is_connected()}")
print(f"Reading: {iface.read_sensor()}")
print(f"State: {iface.get_state()}")

iface.disconnect()
```

**Compare real vs. fake interface behavior:**

```python
from my_sensor_interface import MySensorInterface
from my_sensor_fake_interface import MySensorFakeInterface

# Run the same operations on both
for iface in [MySensorFakeInterface(), MySensorInterface(port="/dev/ttyUSB0")]:
    iface.connect()
    try:
        reading = iface.read_sensor()
        print(f"{iface.__class__.__name__}: {reading}")
    except Exception as e:
        print(f"{iface.__class__.__name__}: ERROR - {e}")
    finally:
        iface.disconnect()
```

**Add debug logging to your interface:**

```python
import logging

logger = logging.getLogger(__name__)


class MySensorInterface:
    def read_sensor(self, samples=1):
        logger.debug(f"Reading sensor with {samples} samples")
        raw = self._send_command(f"READ {samples}")
        logger.debug(f"Raw response: {raw!r}")
        parsed = self._parse_response(raw)
        logger.debug(f"Parsed response: {parsed}")
        return parsed
```

Run with debug logging:

```bash
PYTHONPATH=src python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from my_sensor_interface import MySensorInterface
iface = MySensorInterface(port='/dev/ttyUSB0')
iface.connect()
print(iface.read_sensor())
iface.disconnect()
"
```

## Layer 3: Node Issues

### Symptoms
- Node starts but actions fail
- Incorrect action parameters
- Status endpoint returns errors
- Actions hang or timeout

### Diagnosis

**Check node health:**

```bash
# Health check
curl http://localhost:2000/health

# Node info (shows registered actions)
curl http://localhost:2000/info | python -m json.tool

# Current state
curl http://localhost:2000/state | python -m json.tool

# Node log
curl http://localhost:2000/log
```

**Test actions directly:**

```bash
# List available actions (from /info endpoint)
curl http://localhost:2000/info | python -c "
import sys, json
info = json.load(sys.stdin)
for action in info.get('actions', info.get('capabilities', {}).get('actions', [])):
    print(f'  {action}')
"

# Execute an action
curl -X POST http://localhost:2000/actions/measure \
  -H "Content-Type: application/json" \
  -d '{"samples": 1}' | python -m json.tool
```

**Run node with verbose logging:**

```bash
# Set log level via environment
LOG_LEVEL=DEBUG python my_sensor_rest_node.py
```

**Check for port conflicts:**

```bash
# Check if port 2000 is already in use
lsof -i :2000  # macOS/Linux
netstat -tlnp | grep 2000  # Linux
```

### Common Node Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| `Address already in use` | Another node or process on same port | Change port in config or stop the other process |
| Action not found | Method missing `@action` decorator | Add `@action` decorator to the method |
| Parameter validation error | Type mismatch in action parameters | Check type hints match the JSON being sent |
| Action hangs | Interface method blocks indefinitely | Add timeouts to interface operations |
| `startup_handler` fails | Interface can't connect | Check hardware connection, or switch to fake interface |
| `AttributeError: 'NoneType'` | Interface not initialized | Ensure `startup_handler` runs before actions |

## Layer 4: Workcell and Workflow Issues

### Symptoms
- Workflow steps fail
- Node not found by workcell
- Location resolution errors
- Workflow hangs on a step

### Diagnosis

**Check workcell status:**

```bash
madsci status
```

**Check node registration:**

```python
from madsci.client import WorkcellClient

wc = WorkcellClient(workcell_server_url="http://localhost:8005/")
nodes = wc.get_nodes()
for name, node in nodes.items():
    print(f"  {name}: {node.status} at {node.url}")
```

**Check workflow execution:**

```python
from madsci.client import WorkcellClient

wc = WorkcellClient(workcell_server_url="http://localhost:8005/")

# Get active workflows
active = wc.get_active_workflows()
for wf_id, wf in active.items():
    print(f"Workflow {wf_id}: step {wf.status.current_step_index}")
    for step in wf.steps:
        print(f"  {step.name}: {step.status}")

# Get archived (completed) workflows
archived = wc.get_archived_workflows(number=5)
for wf_id, wf in archived.items():
    print(f"Workflow {wf_id}: {wf.status}")
```

**Check event logs:**

```bash
# View recent events
madsci logs --tail 50

# Filter by level
madsci logs --level ERROR --tail 20

# Filter by pattern
madsci logs --grep "my_sensor"

# Follow logs in real time
madsci logs --follow
```

### Common Workcell Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Node not found | Node not registered with workcell | Check workcell config includes node URL |
| Step fails with connection error | Node URL incorrect or node not running | Verify node is running and URL is reachable from workcell |
| Location not resolved | Location not configured in Location Manager | Add location with `LocationClient.add_location()` |
| Workflow hangs | Step waiting for locked node | Check node status, unlock if stuck |
| Wrong parameters passed | Workflow YAML parameter names don't match action | Compare workflow step args with action method signature |

## Using the MADSci TUI for Debugging

The TUI provides a live view of system status:

```bash
madsci tui
```

Key screens:
- **Dashboard** (`d`): Overview of all service health
- **Status** (`s`): Detailed service status table
- **Logs** (`l`): Live log viewer with filtering

## Debugging Checklist

When something isn't working, follow this systematic checklist:

1. **Can you talk to the hardware directly?** (Python REPL, no MADSci)
2. **Does the interface work standalone?** (Import and call methods)
3. **Does the fake interface pass all tests?** (`pytest tests/test_interface.py`)
4. **Does the node start without errors?** (`python my_sensor_rest_node.py`)
5. **Can you call actions via curl?** (`curl -X POST http://localhost:2000/actions/measure`)
6. **Is the node registered with the workcell?** (`madsci status`)
7. **Do workflow steps reference the correct action names and parameters?**
8. **Are the event logs showing errors?** (`madsci logs --level ERROR`)

## What's Next?

- [Packaging & Deployment](./08-packaging-deployment.md) - Docker, dependencies, CI/CD
- [Publishing](./09-publishing.md) - Sharing modules with others
