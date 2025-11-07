# MADSci Data Manager

## Overview
The Data Manager (Port 8004) handles data capture, storage, and querying for scientific experiments. It provides a centralized service for managing experimental data, analysis results, and associated metadata.

## Key Responsibilities
- **Data Storage**: Centralized storage of experimental data and results
- **Data Querying**: Efficient retrieval and filtering of stored data
- **Metadata Management**: Tracking data provenance, quality, and relationships
- **Data Validation**: Ensuring data integrity and format compliance
- **Analysis Integration**: Support for data analysis pipelines and results storage

## Server Architecture
- **data_server.py**: Main FastAPI server providing data management endpoints
- REST API endpoints for data operations (create, read, update, delete)
- Integration with object storage systems for file-based data
- Database integration for metadata and structured data storage

## Data Types Supported
- Experimental measurements and sensor data
- Analysis results and derived data
- File-based data (images, documents, raw instrument output)
- Structured data (CSV, JSON, database records)
- Metadata and annotations

## API Endpoints
- Data upload and storage operations
- Query and retrieval with filtering capabilities
- Data export in various formats
- Metadata management and search
- Data quality and validation reporting

## Configuration
Environment variables with `DATA_` prefix:
- Database connection settings
- Object storage configuration
- Data validation rules
- Export format options

## Integration Points
- **Event Manager**: Log data operations and access events
- **Experiment Manager**: Store experimental results and measurements
- **Resource Manager**: Track data associated with specific resources
- **Workcell Manager**: Store workflow execution data and outputs
