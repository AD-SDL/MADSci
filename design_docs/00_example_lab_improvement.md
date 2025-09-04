# Example Lab Improvement Design Document

STATUS: Phase 1 Complete, Phase 2 Complete ✅

## Overview

The MADSci example lab serves as the primary demonstration and reference implementation for new users. However, it currently lags behind the framework's evolving capabilities and lacks automated validation. This document outlines a comprehensive refactoring plan to address these issues.

## Current State Analysis

### Issues Identified

1. **Feature Gap**: The example lab doesn't showcase newer MADSci features:
   - Resource Templates for reusable resource definitions
   - OwnershipInfo/MadsciContext for proper context management
   - Advanced workflow patterns and data feedforward
   - New workflow parameter system (input vs feed forward parameters)
   - File-based workflow parameters and automated parameter promotion
   - Internal workcell actions and improved error handling
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
- Multi-step workflows with data dependencies and improved parameter handling
- Demonstration of new workflow parameter separation (input vs feed forward)
- File-based workflow parameters and automatic parameter promotion
- Internal workcell actions for improved workflow control
- Enhanced error handling with capped error message lengths
- Resource allocation and scheduling examples
- Real-time monitoring and feedback loops with reduced redundant logging

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
4. **Workflow Development**: Create workflows using provisioned resources with new parameter system
5. **Experiment Execution**: Run experiments with proper context management and improved error handling

### 3. Automated Testing Infrastructure

**Test Categories**
- **Smoke Tests**: Basic connectivity and service health
- **Integration Tests**: End-to-end workflow execution with new parameter system
- **Workflow Tests**: Validation of input/feed forward parameter separation and file handling
- **Resource Tests**: Template creation and resource management
- **Context Tests**: Ownership and context propagation
- **Error Handling Tests**: Validation of capped error messages and retry mechanisms
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
├── test_workflows.py              # Workflow execution tests with new parameter system
├── test_workflow_parameters.py    # Input/feed forward parameter validation
├── test_error_handling.py         # Capped error messages and retry logic
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
- Workflow design principles with new parameter system
- File-based workflow parameter patterns
- Error handling strategies including retry mechanisms
- Internal workcell action usage patterns

## Implementation Plan

### Phase 1: Foundation ✅ COMPLETED
- [x] Analyze current example structure and create gap analysis
- [x] Design new directory structure and organization
- [x] Refactor setup documentation from markdown to interactive Jupyter notebooks
- [x] Create automated test framework for examples
- [x] Set up CI/CD integration for example validation

#### Phase 1 Final Update ✅ COMPLETED

**Automated Test Framework Implementation Complete:**

4. **Automated Test Framework** - Comprehensive test infrastructure created:
   ```
   tests/example_lab/
   ├── conftest.py                     # Shared fixtures and test configuration
   ├── pytest.ini                     # Test-specific configuration and markers
   ├── run_tests.py                    # Convenient test runner script
   ├── README.md                       # Test documentation and usage guide
   ├── test_lab_setup.py              # Service health and lab configuration tests
   ├── test_resource_templates.py     # Resource template validation tests
   ├── test_workflows.py              # Workflow execution and monitoring tests
   ├── test_workflow_parameters.py    # New parameter system tests (PR #104)
   ├── test_error_handling.py         # Error capping and retry tests (PR #104)
   └── test_context_management.py     # OwnershipInfo and context tests
   ```

5. **CI/CD Integration Complete** - Updated `.github/workflows/pytests.yml`:
   - Added "Test Example Lab (Integration)" job
   - Service orchestration with `just build && just up -d`
   - Automated test execution with coverage reporting
   - Proper cleanup with `just down`

**Test Framework Features:**
- **60+ Unit Tests**: Comprehensive validation of core functionality
- **Service Isolation**: Tests skip gracefully when services unavailable
- **Test Markers**: `@pytest.mark.requires_services` for integration tests
- **Coverage Integration**: Compatible with existing coverage reporting
- **Test Categories**: Lab setup, resource templates, workflows, parameters, error handling, context management

#### Phase 1 Previous Updates

**NOTE**: PR #104 "Workflow improvements" merged significant updates to workflow system that must be integrated into examples.

**Earlier Completed Tasks:**

1. **Gap Analysis Complete** - Identified key issues:
   - Missing modern MADSci features (Resource Templates, Context Management)
   - No automated testing or CI/CD integration
   - Limited documentation and progression
   - Architectural misalignment with microservices approach

2. **New Directory Structure** - Created comprehensive organization:
   ```
   example_lab/
   ├── setup/                    # Interactive setup notebooks
   ├── tutorials/                # Progressive learning path
   ├── scenarios/                # Complete example scenarios
   ├── templates/                # Resource template library
   ├── tests/                    # Automated validation
   └── utils/                    # Helper utilities
   ```

3. **Interactive Setup Notebooks** - Replaced static markdown with executable Jupyter notebooks:
   - **01_service_orchestration.ipynb**: Docker-based service startup with live health checks
   - **02_resource_templates.ipynb**: Hands-on template creation and resource provisioning
   - **03_initial_resources.ipynb**: Complete lab resource setup with spatial organization
   - **04_validation.ipynb**: Comprehensive testing framework with automated reporting

**Key Innovations:**
- **Interactive Documentation**: Users can execute setup commands directly in notebooks
- **Live Validation**: Real-time feedback and error handling during setup
- **Microservices-First Approach**: Aligned with MADSci's distributed architecture
- **Context Management Integration**: Proper OwnershipInfo and MadsciContext usage throughout
- **Modern Features**: Resource Templates, spatial organization, automated testing

### Phase 2: Core Improvements ✅ COMPLETED
- [x] Implement Resource Templates showcase
- [x] Integrate OwnershipInfo/MadsciContext throughout examples
- [x] Create comprehensive lab setup sequence
- [x] Update workflows to use new parameter system (input/feed forward separation)
- [x] Demonstrate file-based workflow parameters and automatic promotion
- [x] Implement internal workcell actions in example workflows
- [x] Develop automated test suite for basic functionality

#### Phase 2 Final Update ✅ COMPLETED

**Core Improvements Implementation Complete:**

1. **Resource Templates Showcase** - Enhanced integration throughout examples:
   - Resource Templates already well-implemented in `02_resource_templates.ipynb`
   - Comprehensive template library with plates, tips, and reagents
   - Template-based resource creation with context management
   - Template validation and error handling demonstrations

2. **OwnershipInfo/MadsciContext Integration** - Full context management:
   ```
   example_lab/
   ├── enhanced_example_app.py           # Enhanced app with full context management
   ├── setup/05_comprehensive_lab_setup.ipynb  # Complete context integration demo
   └── workflows/enhanced_context_workflow.workflow.yaml  # Context-aware workflows
   ```

3. **Modern Workflow Parameter System** - Complete implementation:
   ```
   workflows/
   ├── enhanced_context_workflow.workflow.yaml    # Input/feedforward separation demo
   ├── file_parameters_demo.workflow.yaml        # File-based parameters with auto-promotion
   └── internal_actions_demo.workflow.yaml       # Internal workcell actions showcase
   ```

4. **File-Based Parameter Handling** - Comprehensive demonstration:
   ```
   data_files/
   ├── sample_manifest.csv           # Example CSV input file
   ├── protocol_template.py          # Customizable protocol template
   └── processing_config.json        # Configuration parameter file
   ```

5. **Internal Workcell Actions** - Advanced workflow control:
   - Validation actions (`validate_file`, `validate_step_output`)
   - Report generation (`generate_comprehensive_report`)
   - Session management (`finalize_workflow`, `archive_workflow_files`)
   - Error handling and recovery actions

6. **Enhanced Test Coverage** - Updated test suite:
   ```
   tests/example_lab/test_enhanced_features.py   # Comprehensive Phase 2 feature tests
   ```

**Key Innovations Delivered:**
- **Complete Context Integration**: OwnershipInfo and MadsciContext throughout all examples
- **Modern Parameter Architecture**: Clear separation of input, file, and feed-forward parameters
- **File Parameter Automation**: Automatic promotion and validation of file-based parameters
- **Advanced Workflow Control**: Internal actions for validation, reporting, and session management
- **Enhanced Error Handling**: Comprehensive retry mechanisms and failure recovery
- **Template-Driven Development**: Consistent use of Resource Templates with context tracking

### Phase 3: Advanced Scenarios
- [ ] Create complex multi-step workflow examples with new parameter patterns
- [ ] Implement resource management scenarios
- [ ] Add error handling and recovery examples using retry mechanisms
- [ ] Demonstrate workflow run separation from definition submission
- [ ] Show advanced file parameter handling in workflows
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
- [ ] New workflow parameter system (input/feed forward) showcased in examples
- [ ] File-based workflow parameters and automatic promotion demonstrated
- [ ] Internal workcell actions integrated into example workflows
- [ ] Complete lab setup process documented and automated
- [ ] End-to-end workflows execute successfully with improved error handling
- [ ] Resource Templates fully integrated and documented
- [ ] Context management properly implemented throughout

### Quality Criteria
- [x] CI/CD pipeline includes example testing
- [ ] 90%+ test coverage for example code
- [ ] All examples pass automated validation
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
