# Example Lab Improvement Design Document

STATUS: Not Started

## Overview

The MADSci example lab serves as the primary demonstration and reference implementation for new users. However, it currently lags behind the framework's evolving capabilities and lacks automated validation. This document outlines a comprehensive refactoring plan to address these issues.

## Current State Analysis

### Issues Identified

1. **Feature Gap**: The example lab doesn't showcase newer MADSci features:
   - Resource Templates for reusable resource definitions
   - OwnershipInfo/MadsciContext for proper context management
   - Advanced workflow patterns and data feedforward
   - Complex resource relationships and container hierarchies

2. **Limited Lab Setup Examples**: The current examples jump from nodes directly to experiment applications, missing:
   - Lab initialization and setup procedures
   - Resource creation and management workflows
   - Template-based resource provisioning
   - Real-world lab configuration patterns

3. **No Automated Testing**: The example lab cannot be validated automatically:
   - No integration with CI/CD pipeline
   - No end-to-end testing of example workflows
   - No validation that examples remain functional as the codebase evolves
   - Manual testing only, prone to drift

4. **Incomplete Documentation**: Missing comprehensive guides for:
   - Step-by-step lab setup
   - Resource management best practices
   - Context and ownership management
   - Real-world usage patterns

### Current Architecture

```
example_lab/
├── README.md                    # Basic startup instructions
├── example_app.py               # Simple experiment application
├── example_lab.lab.yaml         # Minimal lab definition
├── managers/                    # Manager configurations
├── node_definitions/            # Node YAML configs
├── example_modules/             # Simple node implementations
├── workflows/                   # Basic workflow examples
└── notebooks/                   # Interactive Jupyter Notebook Examples
```

## Proposed Improvements

### 1. Feature Modernization

**Resource Templates Integration**
- Create comprehensive template library for common lab resources
- Demonstrate template-based resource provisioning
- Show template inheritance and customization patterns
- Include complex container hierarchies (racks, plates, stacks)

**Context Management**
- Integrate OwnershipInfo context throughout examples
- Demonstrate MadsciContext for experiment tracking
- Show proper context propagation across services
- Include context-aware resource management

**Advanced Workflows**
- Multi-step workflows with data dependencies
- Resource allocation and scheduling examples
- Error handling and recovery patterns
- Real-time monitoring and feedback loops

### 2. Comprehensive Lab Setup Examples

**Lab Initialization Sequence**
```python
# New example structure
example_lab/
├── setup/
│   ├── 01_lab_initialization.py    # Lab setup and registration
│   ├── 02_resource_templates.py    # Create resource templates
│   ├── 03_initial_resources.py     # Provision initial resources
│   └── 04_validation.py            # Validate lab setup
├── scenarios/
│   ├── basic_experiment/           # Simple end-to-end example
│   ├── complex_workflow/           # Multi-step with dependencies
│   ├── resource_management/        # Advanced resource patterns
│   └── error_handling/             # Error recovery examples
└── automated_tests/                # Automated validation tests
```

**Step-by-Step Examples**
1. **Lab Bootstrap**: Create lab, register nodes, set up managers
2. **Resource Template Creation**: Define reusable resource templates
3. **Initial Resource Provisioning**: Use templates to create initial resources
4. **Workflow Development**: Create workflows using provisioned resources
5. **Experiment Execution**: Run experiments with proper context management

### 3. Automated Testing Infrastructure

**Test Categories**
- **Smoke Tests**: Basic connectivity and service health
- **Integration Tests**: End-to-end workflow execution
- **Resource Tests**: Template creation and resource management
- **Context Tests**: Ownership and context propagation
- **Performance Tests**: Basic load and timing validation

**CI/CD Integration**
- Add example lab tests to existing pytest workflow
- Create dedicated example validation job
- Generate coverage reports for example code

**Test Implementation**
```python
# New test structure
tests/example_lab/
├── test_lab_setup.py              # Lab initialization tests
├── test_resource_templates.py     # Template functionality tests
├── test_workflows.py              # Workflow execution tests
├── test_context_management.py     # Context and ownership tests
└── conftest.py                    # Shared fixtures and setup
```

### 4. Enhanced Documentation

**Interactive Tutorials**
- Step-by-step Jupyter notebooks for each scenario
- Progressive complexity from basic to advanced
- Executable examples with expected outputs
- Troubleshooting guides with common issues

**Best Practices Guide**
- Resource management patterns
- Context handling recommendations
- Workflow design principles
- Error handling strategies

## Implementation Plan

### Phase 1: Foundation
- [ ] Analyze current example structure and create gap analysis
- [ ] Design new directory structure and organization
- [ ] Create automated test framework for examples
- [ ] Set up CI/CD integration for example validation

### Phase 2: Core Improvements
- [ ] Implement Resource Templates showcase
- [ ] Integrate OwnershipInfo/MadsciContext throughout examples
- [ ] Create comprehensive lab setup sequence
- [ ] Develop automated test suite for basic functionality

### Phase 3: Advanced Scenarios
- [ ] Create complex multi-step workflow examples
- [ ] Implement resource management scenarios
- [ ] Add error handling and recovery examples
- [ ] Develop performance and load testing examples

### Phase 4: Documentation & Polish
- [ ] Create interactive Jupyter tutorials
- [ ] Write comprehensive documentation
- [ ] Implement end-to-end validation tests
- [ ] Performance optimization and cleanup

### Phase 5: Integration & Validation
- [ ] Full CI/CD integration and testing
- [ ] User acceptance testing with fresh users
- [ ] Documentation review and refinement
- [ ] Final testing and deployment

## Technical Specifications

### New Directory Structure
```
example_lab/
├── README.md                          # Comprehensive getting started guide
├── requirements/                      # Prerequisites and dependencies
│   ├── system_requirements.md
│   └── setup_validation.py
├── tutorials/                         # Progressive learning path
│   ├── 01_basic_setup/
│   ├── 02_resource_management/
│   ├── 03_workflows/
│   ├── 04_advanced_patterns/
│   └── 05_troubleshooting/
├── scenarios/                         # Complete example scenarios
│   ├── pharmaceutical_screening/
│   ├── materials_characterization/
│   └── quality_control/
├── templates/                         # Resource template library
│   ├── containers/
│   ├── instruments/
│   └── consumables/
├── tests/                             # Automated validation
│   ├── integration/
│   ├── unit/
│   └── performance/
└── utils/                             # Helper utilities
    ├── lab_setup_helper.py
    ├── validation_tools.py
    └── monitoring_tools.py
```

### Resource Template Library
- **Container Templates**: Plates (96, 384, 1536-well), tips, tubes, racks
- **Instrument Specific Templates**: Liquid handler pipettes, robotic grippers, plate nests
- **Consumable Templates**: Reagents, buffers, solvents
- **Custom Templates**: Lab-specific resources with inheritance

### Context Management Integration
- Proper OwnershipInfo propagation across all operations
- MadsciContext usage in all workflows
- Context-aware resource allocation and tracking
- Ownership transfer examples and patterns

### Automated Testing Strategy

**Test Levels**
1. **Unit Tests**: Individual component functionality
2. **Integration Tests**: Service interaction and communication
3. **End-to-End Tests**: Complete workflow execution
4. **Performance Tests**: Timing and resource usage validation

**CI/CD Integration**
```yaml
# Addition to .github/workflows/pytests.yml
- name: Test Example Lab
  run: |
    just build
    just up -d  # Start services in background
    pytest tests/example_lab/ --cov=example_lab
    just down  # Clean up services
```

**Test Data Management**
- Use fixtures for reproducible test data
- Clean database state between tests
- Mock external dependencies where appropriate
- Validate actual service integration

## Success Criteria

### Functionality Criteria
- [ ] All new MADSci features demonstrated in examples
- [ ] Complete lab setup process documented and automated
- [ ] End-to-end workflows execute successfully
- [ ] Resource Templates fully integrated and documented
- [ ] Context management properly implemented throughout

### Quality Criteria
- [ ] 90%+ test coverage for example code
- [ ] All examples pass automated validation
- [ ] CI/CD pipeline includes example testing
- [ ] Documentation is comprehensive and beginner-friendly
- [ ] Examples serve as effective onboarding tool

### User Experience Criteria
- [ ] New users can follow examples start-to-finish
- [ ] Progressive complexity allows gradual learning
- [ ] Clear error messages and troubleshooting guides
- [ ] Examples reflect real-world usage patterns
- [ ] Performance is acceptable for demonstration purposes

## Risk Mitigation

### Technical Risks
- **Service Dependencies**: Minimize external service requirements for basic examples
- **Version Compatibility**: Pin dependencies and test across supported versions
- **Resource Cleanup**: Ensure tests clean up resources to prevent interference

### Timeline Risks
- **Scope Creep**: Maintain focus on core objectives, defer nice-to-have features
- **Integration Complexity**: Start with simple examples, add complexity incrementally
- **Testing Overhead**: Balance comprehensive testing with development velocity

### User Adoption Risks
- **Documentation Quality**: Regular user testing with fresh users
- **Complexity**: Maintain multiple complexity levels for different user types
- **Maintenance**: Establish ownership and update processes

## Future Considerations

### Expandability
- Plugin architecture for custom example scenarios
- Community contribution guidelines for new examples
- Versioned example compatibility with MADSci releases

### Advanced Features
- Real hardware integration examples (when available)
- Cloud deployment scenarios
- Multi-lab federation examples
- AI/ML integration patterns

### Monitoring and Analytics
- Usage tracking for examples (anonymized)
- Performance benchmarking over time
- User feedback collection and integration

---

This design document provides the foundation for significantly improving the MADSci example lab to better serve as both a demonstration platform and learning resource for new users while ensuring long-term maintainability through automated testing.
