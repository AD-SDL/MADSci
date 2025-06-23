"""
FIXED Example template definition files.

All custom_attributes now use proper CustomResourceAttributeDefinition format.
"""

from typing import Any

from madsci.common.types.resource_types.definitions import (
    CustomResourceAttributeDefinition,
)
from madsci.common.types.resource_types.resource_enums import (
    ConsumableTypeEnum,
    ContainerTypeEnum,
    ResourceTypeEnum,
)
from madsci.common.types.resource_types.templates import (
    ResourceTemplate,
    TemplateSource,
    _auto_register_template,
)

# =============================================================================
# LAB EQUIPMENT TEMPLATES - FIXED
# =============================================================================

# PCR Machine Templates
PCR_BIORAD_CFX96 = ResourceTemplate(
    template_name="pcr_biorad_cfx96",
    display_name="Bio-Rad CFX96 PCR Machine",
    description="Standard Bio-Rad CFX96 real-time PCR system setup",
    base_type=ResourceTypeEnum.asset,
    resource_class="biorad_cfx96_pcr",
    default_values={
        "custom_attributes": [
            CustomResourceAttributeDefinition(
                attribute_name="manufacturer", default_value="Bio-Rad"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="model", default_value="CFX96"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="max_temperature", default_value=100.0
            ),
            CustomResourceAttributeDefinition(
                attribute_name="min_temperature", default_value=4.0
            ),
            CustomResourceAttributeDefinition(
                attribute_name="heating_rate", default_value=5.0
            ),
            CustomResourceAttributeDefinition(
                attribute_name="cooling_rate", default_value=2.5
            ),
            CustomResourceAttributeDefinition(
                attribute_name="block_format", default_value="96-well"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="status", default_value="ready"
            ),
        ],
        "location": "Lab A",
    },
    required_overrides=["custom_attributes"],
    source=TemplateSource.SYSTEM,
    tags=["pcr", "biorad", "lab_equipment", "thermal_cycler"],
)

PCR_APPLIED_BIOSYSTEMS = ResourceTemplate(
    template_name="pcr_applied_biosystems_7500",
    display_name="Applied Biosystems 7500 PCR",
    description="Applied Biosystems 7500 Real-Time PCR System",
    base_type=ResourceTypeEnum.asset,
    resource_class="applied_biosystems_pcr",
    default_values={
        "custom_attributes": [  # ← FIXED: List of CustomResourceAttributeDefinition
            CustomResourceAttributeDefinition(
                attribute_name="manufacturer", default_value="Applied Biosystems"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="model", default_value="7500"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="max_temperature", default_value=99.9
            ),
            CustomResourceAttributeDefinition(
                attribute_name="min_temperature", default_value=4.0
            ),
            CustomResourceAttributeDefinition(
                attribute_name="block_format", default_value="96-well"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="software_version", default_value="v2.3"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="status", default_value="ready"
            ),
        ]
    },
    required_overrides=["custom_attributes"],
    source=TemplateSource.SYSTEM,
    tags=["pcr", "applied_biosystems", "lab_equipment"],
)

PLATE_READER_BIOTEK = ResourceTemplate(
    template_name="plate_reader_biotek_synergy",
    display_name="BioTek Synergy Plate Reader",
    description="BioTek Synergy multi-mode microplate reader",
    base_type=ResourceTypeEnum.asset,
    resource_class="biotek_plate_reader",
    default_values={
        "custom_attributes": [  # ← FIXED: List of CustomResourceAttributeDefinition
            CustomResourceAttributeDefinition(
                attribute_name="manufacturer", default_value="BioTek"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="model", default_value="Synergy H1"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="detection_modes",
                default_value=["absorbance", "fluorescence", "luminescence"],
            ),
            CustomResourceAttributeDefinition(
                attribute_name="wavelength_range", default_value="200-1000nm"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="status", default_value="ready"
            ),
        ]
    },
    required_overrides=["custom_attributes"],
    source=TemplateSource.SYSTEM,
    tags=["plate_reader", "biotek", "detection", "lab_equipment"],
)

# =============================================================================
# CONTAINER TEMPLATES - FIXED
# =============================================================================

MICROPLATE_96_WELL = ResourceTemplate(
    template_name="microplate_96_well_standard",
    display_name="Standard 96-Well Microplate",
    base_type=ResourceTypeEnum.container,
    description="Standard polystyrene 96-well microplate",
    resource_class="microplate_96_well",
    default_values={
        "capacity": 96,
        "container_type": ContainerTypeEnum.container,
        "custom_attributes": [  # ← FIXED: Proper CustomResourceAttributeDefinition objects
            CustomResourceAttributeDefinition(
                attribute_name="well_volume", default_value=200.0
            ),
            CustomResourceAttributeDefinition(
                attribute_name="material", default_value="polystyrene"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="color", default_value="clear"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="sterile", default_value=True
            ),
            CustomResourceAttributeDefinition(
                attribute_name="plate_type", default_value="flat_bottom"
            ),
        ],
    },
    source=TemplateSource.SYSTEM,
    tags=["microplate", "96_well", "container", "standard"],
)

MICROPLATE_384_WELL = ResourceTemplate(
    template_name="microplate_384_well_standard",
    display_name="Standard 384-Well Microplate",
    base_type=ResourceTypeEnum.container,
    description="Standard polystyrene 384-well microplate",
    resource_class="microplate_384_well",
    default_values={
        "capacity": 384,
        "container_type": ContainerTypeEnum.container,
        "custom_attributes": [  # ← FIXED: List of CustomResourceAttributeDefinition
            CustomResourceAttributeDefinition(
                attribute_name="well_volume", default_value=80.0
            ),
            CustomResourceAttributeDefinition(
                attribute_name="material", default_value="polystyrene"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="color", default_value="clear"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="sterile", default_value=True
            ),
            CustomResourceAttributeDefinition(
                attribute_name="plate_type", default_value="flat_bottom"
            ),
        ],
    },
    source=TemplateSource.SYSTEM,
    tags=["microplate", "384_well", "container", "high_throughput"],
)

TUBE_RACK_15ML = ResourceTemplate(
    template_name="tube_rack_15ml_standard",
    display_name="15mL Tube Rack",
    base_type=ResourceTypeEnum.container,
    description="Standard rack for 15mL conical tubes",
    resource_class="tube_rack",
    default_values={
        "capacity": 50,
        "container_type": ContainerTypeEnum.container,
        "custom_attributes": [  # ← FIXED: List of CustomResourceAttributeDefinition
            CustomResourceAttributeDefinition(
                attribute_name="tube_size", default_value="15ml"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="material", default_value="polypropylene"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="autoclavable", default_value=True
            ),
        ],
    },
    source=TemplateSource.SYSTEM,
    tags=["tube_rack", "15ml", "container", "rack"],
)

# =============================================================================
# REAGENT TEMPLATES - FIXED
# =============================================================================

TAQ_POLYMERASE = ResourceTemplate(
    template_name="taq_polymerase_standard",
    display_name="Taq DNA Polymerase",
    description="Standard Taq DNA Polymerase for PCR",
    base_type=ResourceTypeEnum.consumable,
    resource_class="pcr_enzyme",
    default_values={
        "consumable_type": ConsumableTypeEnum.consumable,
        "custom_attributes": [  # ← FIXED: List of CustomResourceAttributeDefinition
            CustomResourceAttributeDefinition(
                attribute_name="enzyme_name", default_value="Taq DNA Polymerase"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="concentration", default_value=5.0
            ),  # U/μL
            CustomResourceAttributeDefinition(
                attribute_name="buffer_included", default_value=True
            ),
            CustomResourceAttributeDefinition(
                attribute_name="storage_temperature", default_value=-20.0
            ),
            CustomResourceAttributeDefinition(
                attribute_name="activity", default_value="5000 U/mL"
            ),
        ],
    },
    required_overrides=["custom_attributes"],
    source=TemplateSource.SYSTEM,
    tags=["taq_polymerase", "pcr", "enzyme", "consumable"],
)

MASTER_MIX_PCR = ResourceTemplate(
    template_name="pcr_master_mix_standard",
    display_name="PCR Master Mix",
    description="Ready-to-use PCR master mix",
    base_type=ResourceTypeEnum.consumable,
    resource_class="pcr_master_mix",
    default_values={
        "consumable_type": ConsumableTypeEnum.consumable,
        "custom_attributes": [  # ← FIXED: List of CustomResourceAttributeDefinition
            CustomResourceAttributeDefinition(
                attribute_name="components",
                default_value=["Taq polymerase", "dNTPs", "MgCl2", "buffer"],
            ),
            CustomResourceAttributeDefinition(
                attribute_name="concentration", default_value="2x"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="storage_temperature", default_value=-20.0
            ),
            CustomResourceAttributeDefinition(
                attribute_name="reaction_volume", default_value="25μL recommended"
            ),
        ],
    },
    required_overrides=["custom_attributes"],
    source=TemplateSource.SYSTEM,
    tags=["master_mix", "pcr", "consumable", "ready_to_use"],
)

# =============================================================================
# POOL RESOURCE TEMPLATES - ALREADY CORRECT FORMAT
# =============================================================================

WATER_NUCLEASE_FREE_POOL = ResourceTemplate(
    template_name="water_nuclease_free_pool",
    display_name="Nuclease-Free Water Pool",
    base_type=ResourceTypeEnum.pool,
    description="Pool of nuclease-free water for molecular biology",
    resource_class="liquid_pool",
    default_values={
        "custom_attributes": [  # ← ALREADY CORRECT: List of CustomResourceAttributeDefinition
            CustomResourceAttributeDefinition(
                attribute_name="liquid_type", default_value="nuclease_free_water"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="sterility", default_value="nuclease_free"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="volume_per_aliquot", default_value=1.0
            ),
            CustomResourceAttributeDefinition(
                attribute_name="storage_temperature", default_value=4.0
            ),
            CustomResourceAttributeDefinition(attribute_name="pH", default_value=7.0),
            CustomResourceAttributeDefinition(
                attribute_name="quality_grade", default_value="molecular_biology"
            ),
        ]
    },
    required_overrides=["total_quantity"],
    source=TemplateSource.SYSTEM,
    tags=["water", "nuclease_free", "liquid", "pool", "molecular_biology"],
)

PIPETTE_TIPS_P200_POOL = ResourceTemplate(
    template_name="pipette_tips_p200_pool",
    display_name="P200 Pipette Tips Pool",
    base_type=ResourceTypeEnum.pool,
    description="Pool of 200μL pipette tips",
    resource_class="pipette_tip_pool",
    default_values={
        "custom_attributes": [  # ← ALREADY CORRECT: List of CustomResourceAttributeDefinition
            CustomResourceAttributeDefinition(
                attribute_name="tip_volume", default_value=200.0
            ),
            CustomResourceAttributeDefinition(
                attribute_name="material", default_value="polypropylene"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="sterile", default_value=True
            ),
            CustomResourceAttributeDefinition(
                attribute_name="filtered", default_value=False
            ),
            CustomResourceAttributeDefinition(
                attribute_name="color", default_value="clear"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="tip_type", default_value="standard"
            ),
        ]
    },
    required_overrides=["total_quantity"],
    source=TemplateSource.SYSTEM,
    tags=["pipette_tips", "p200", "consumable", "pool", "pipetting"],
)

MICROPLATE_96_WELL_POOL = ResourceTemplate(
    template_name="microplate_96_well_pool",
    display_name="96-Well Microplate Pool",
    base_type=ResourceTypeEnum.pool,
    description="Pool of standard 96-well microplates",
    resource_class="microplate_pool",
    default_values={
        "custom_attributes": [  # ← ALREADY CORRECT: List of CustomResourceAttributeDefinition
            CustomResourceAttributeDefinition(
                attribute_name="plate_type", default_value="96_well"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="material", default_value="polystyrene"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="well_volume", default_value=200.0
            ),
            CustomResourceAttributeDefinition(
                attribute_name="sterile", default_value=True
            ),
            CustomResourceAttributeDefinition(
                attribute_name="color", default_value="clear"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="bottom_type", default_value="flat"
            ),
        ]
    },
    required_overrides=["total_quantity"],
    source=TemplateSource.SYSTEM,
    tags=["microplate", "96_well", "container", "pool", "assay"],
)

# =============================================================================
# NODE-SPECIFIC TEMPLATES - FIXED
# =============================================================================

OT2_ROBOT_STANDARD = ResourceTemplate(
    template_name="ot2_robot_standard_setup",
    display_name="OT2 Robot - Standard Setup",
    description="Opentrons OT2 robot with standard pipette configuration",
    base_type=ResourceTypeEnum.asset,
    resource_class="ot2_robot",
    default_values={
        "custom_attributes": [  # ← FIXED: List of CustomResourceAttributeDefinition
            CustomResourceAttributeDefinition(
                attribute_name="manufacturer", default_value="Opentrons"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="model", default_value="OT-2"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="left_pipette", default_value="P300 Single"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="right_pipette", default_value="P20 Single"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="software_version", default_value="6.3.0"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="status", default_value="ready"
            ),
        ]
    },
    required_overrides=["custom_attributes"],
    source=TemplateSource.NODE,
    tags=["ot2", "robot", "automation", "pipetting"],
)

# =============================================================================
# GRIPPER TEMPLATES - FIXED (This was causing the validation error!)
# =============================================================================

PF400_GRIPPER = ResourceTemplate(
    template_name="pf400_gripper",
    display_name="PF400 Robotic Arm Gripper",
    base_type=ResourceTypeEnum.slot,
    description="Precise Automation PF400 robotic arm gripper slot",
    resource_class="pf400_gripper_slot",
    default_values={
        "custom_attributes": [  # ← FIXED: List of CustomResourceAttributeDefinition (this was the problem!)
            CustomResourceAttributeDefinition(
                attribute_name="robot_type", default_value="PF400"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="manufacturer", default_value="Precise Automation"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="gripper_type", default_value="parallel_jaw"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="max_payload", default_value="5kg"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="grip_force", default_value="adjustable"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="status", default_value="available"
            ),
        ]
    },
    required_overrides=["owner"],
    source=TemplateSource.NODE,
    tags=["pf400", "gripper", "slot", "robot", "automation"],
)

SCICLOPS_GRIPPER = ResourceTemplate(
    template_name="sciclops_gripper",
    display_name="Sciclops Plate Crane Gripper",
    base_type=ResourceTypeEnum.slot,
    description="Hudson Robotics Sciclops robotic plate crane gripper slot",
    resource_class="sciclops_gripper_slot",
    default_values={
        "custom_attributes": [  # ← FIXED: List of CustomResourceAttributeDefinition
            CustomResourceAttributeDefinition(
                attribute_name="robot_type", default_value="Sciclops"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="manufacturer", default_value="Hudson Robotics"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="gripper_type", default_value="plate_gripper"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="plate_compatibility",
                default_value=["96_well", "384_well", "deep_well"],
            ),
            CustomResourceAttributeDefinition(
                attribute_name="grip_method", default_value="side_grip"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="status", default_value="available"
            ),
        ]
    },
    required_overrides=["owner"],
    source=TemplateSource.NODE,
    tags=["sciclops", "gripper", "slot", "plate_crane", "automation"],
)

UR_ROBOT_GRIPPER = ResourceTemplate(
    template_name="ur_robot_gripper",
    display_name="UR Robot Gripper",
    base_type=ResourceTypeEnum.slot,
    description="Universal Robots (UR) collaborative robot gripper slot",
    resource_class="ur_gripper_slot",
    default_values={
        "custom_attributes": [  # ← FIXED: List of CustomResourceAttributeDefinition
            CustomResourceAttributeDefinition(
                attribute_name="robot_type", default_value="UR"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="manufacturer", default_value="Universal Robots"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="gripper_type", default_value="adaptive_gripper"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="ur_model", default_value="UR5e"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="payload_capacity", default_value="5kg"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="reach", default_value="850mm"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="status", default_value="available"
            ),
        ]
    },
    required_overrides=["owner", "custom_attributes"],
    source=TemplateSource.NODE,
    tags=["ur_robot", "gripper", "slot", "collaborative_robot", "automation"],
)

# =============================================================================
# EXPERIMENT-SPECIFIC TEMPLATES - FIXED
# =============================================================================

DNA_EXTRACTION_PLATE_SETUP = ResourceTemplate(
    template_name="dna_extraction_plate_setup",
    display_name="DNA Extraction Plate Setup",
    base_type=ResourceTypeEnum.container,
    description="96-well plate setup for DNA extraction experiments",
    resource_class="microplate_96_well",
    default_values={
        "capacity": 96,
        "container_type": ContainerTypeEnum.container,
        "custom_attributes": [  # ← FIXED: List of CustomResourceAttributeDefinition
            CustomResourceAttributeDefinition(
                attribute_name="experiment_type", default_value="dna_extraction"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="well_volume", default_value=200.0
            ),
            CustomResourceAttributeDefinition(
                attribute_name="material", default_value="polypropylene"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="sterile", default_value=True
            ),
            CustomResourceAttributeDefinition(
                attribute_name="protocol", default_value="standard_dna_extraction_v1.2"
            ),
        ],
    },
    source=TemplateSource.EXPERIMENT,
    tags=["dna_extraction", "experiment", "microplate", "protocol"],
)

# =============================================================================
# TEMPLATE REGISTRATION
# =============================================================================

_ALL_TEMPLATES = [
    # Lab Equipment
    PCR_BIORAD_CFX96,
    PCR_APPLIED_BIOSYSTEMS,
    PLATE_READER_BIOTEK,
    # Containers
    MICROPLATE_96_WELL,
    MICROPLATE_384_WELL,
    TUBE_RACK_15ML,
    # Reagents
    TAQ_POLYMERASE,
    MASTER_MIX_PCR,
    # Node-specific
    OT2_ROBOT_STANDARD,
    # Gripper Templates (Slot resources)
    PF400_GRIPPER,  # ← This was causing the validation error - now fixed!
    SCICLOPS_GRIPPER,
    UR_ROBOT_GRIPPER,
    # Pool Resources
    WATER_NUCLEASE_FREE_POOL,
    PIPETTE_TIPS_P200_POOL,
    MICROPLATE_96_WELL_POOL,
    # Experiment-specific
    DNA_EXTRACTION_PLATE_SETUP,
]

# Auto-register all templates when module is imported
for template in _ALL_TEMPLATES:
    _auto_register_template(template)

TEMPLATE_SUMMARY = {
    "total_count": len(_ALL_TEMPLATES),
    "categories": {
        "Lab Equipment": 3,
        "Containers": 3,
        "Reagents": 2,
        "Robotic Systems": 1,
        "Grippers": 3,
        "Pool Resources": 3,
        "Experiments": 1,
    },
}


def get_template_summary() -> dict[str, Any]:
    """Get a summary of all available templates."""
    return TEMPLATE_SUMMARY.copy()
