# MADSci Data Manager

Handles capturing, storing, and querying data, in either JSON value or file form, created during the course of an experiment (either collected by instruments, or synthesized during anaylsis).

## Notable Features

- Collects and stores data generated in the course of an experiment as "datapoints"
- Current datapoint types supported: Values (as JSON-serializable data) and Files (stored as-is)
- Datapoints include metadata such as ownership info and datetimestamps
- Datapoints are queryable and searchable based on both value and metadata

## Usage

### Manager

To create and run a new MADSci Data Manager, do the following in your MADSci lab directory:

- If you're not using docker compose, provision and configure a MongoDB instance.
- If you're using docker compose, create or add the following to your Lab's `compose.yaml`, defining your docker compose services for the DataManager and a MongoDB database to store datapoints.


```yaml
name: madsci_example_lab
services:
  mongodb:
    container_name: mongodb
    image: mongodb/mongodb-community-server:latest
    ports:
      - 27017:27017
  data_manager:
    container_name: data_manager
    image: madsci:latest
    build:
      context: ..
      dockerfile: Dockerfile
    environment:
      - USER_ID=1000
      - GROUP_ID=1000
    network_mode: host
    volumes:
      - /path/to/your/lab/direcotry:/home/madsci/lab/
      - .madsci:/home/madsci/.madsci/
    command: python -m madsci.data_manager.data_server
    depends_on:
      - mongodb
```

```bash
# Create a Data Manager Definition
madsci manager add -t data_manager
# Start the database and Data Manager Server
docker compose up
# OR
python -m madsci.data_manager.data_server
```

You should see a REST server started on the configured host and port. Navigate in your browser to the URL you configured (default: `http://localhost:8004/`) to see if it's working.

You can see up-to-date documentation on the endpoints provided by your event manager, and try them out, via the swagger page served at `http://your-data-manager-url-here/docs`.

### Client

You can use MADSci's `DataClient` (`madsci.client.data_client.DataClient`) in your python code to save, get, or query datapoints.

Here are some examples of using the `DataClient` to interact with the Data Manager:

```python
from madsci.client.data_client import DataClient
from madsci.common.types.datapoint_types import ValueDataPoint, FileDataPoint
from datetime import datetime

# Initialize the DataClient
client = DataClient(url="http://localhost:8004")

# Create a ValueDataPoint
value_datapoint = ValueDataPoint(
    label="Temperature Reading",
    value={"temperature": 23.5, "unit": "Celsius"},
    data_timestamp=datetime.now()
)

# Submit the ValueDataPoint
submitted_value_datapoint = client.submit_datapoint(value_datapoint)
print(f"Submitted ValueDataPoint: {submitted_value_datapoint}")

# Retrieve the ValueDataPoint by ID
retrieved_value_datapoint = client.get_datapoint(submitted_value_datapoint.datapoint_id)
print(f"Retrieved ValueDataPoint: {retrieved_value_datapoint}")

# Create a FileDataPoint
file_datapoint = FileDataPoint(
    label="Experiment Log",
    path="/path/to/experiment_log.txt",
    data_timestamp=datetime.now()
)

# Submit the FileDataPoint
submitted_file_datapoint = client.submit_datapoint(file_datapoint)
print(f"Submitted FileDataPoint: {submitted_file_datapoint}")

# Retrieve the FileDataPoint by ID
retrieved_file_datapoint = client.get_datapoint(submitted_file_datapoint.datapoint_id)
print(f"Retrieved FileDataPoint: {retrieved_file_datapoint}")

# Save the file from the FileDataPoint to a local path
client.save_datapoint_value(submitted_file_datapoint.datapoint_id, "/local/path/to/save/experiment_log.txt")
print("File saved successfully.")
```
