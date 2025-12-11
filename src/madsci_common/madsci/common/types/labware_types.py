"""Uniform types for labware definitions and configurations, primarily useful for ANSI/SLAS aka SBS compatible labware. https://www.slas.org/education/ansi-slas-microplate-standards/"""

from typing import Optional

from madsci.common.types.base_types import MadsciBaseModel
from pydantic import Field, field_validator, model_validator


class GripperDimensions(MadsciBaseModel):
    """Dimensions for grippers designed to grab a plate in the center of mass, typically from "above"."""

    height: Optional[float] = Field(
        default=None,
        description="The distance between the bottom of the gripper fingers and the limiting surface above the plate, in millimeters. If not specified, it is assumed that the gripper can grip the plate at any height.",
        ge=0,
    )
    finger_height: Optional[float] = Field(
        default=None,
        description="Distance from the bottom of the gripper fingers to the top of the gripper fingers, in millimeters. This is used to prevent using grip points that overhang the top of the labware or any lips. If unset, the gripper fingers are modeled as dimensionless for the purpose of grab height.",
        ge=0,
    )
    safe_clearance: Optional[float] = Field(
        default=None,
        description="The height, measured from the bottom of the gripper fingers in millimeters, that the gripper requires as safe overhead clearance to avoid collisions when moving labware. This is used to ensure that the gripper does not collide with overhangs. If unset, no overhead clearance is enforced.",
        ge=0,
    )


class LabwareDimensions(MadsciBaseModel):
    """Dimensions used for calculating how a gripper can grip a piece of labware."""

    height: float = Field(
        description="The height of the labware measured from the bottom to the top, in millimeters.",
        gt=0.0,
    )
    lid_lip: Optional[float] = Field(
        default=0.0,
        description="The height of the lip or overhang a lid rests on when on the labware, in millimeters, measured from the base of the labware. This is used to calculate the height when a lid is present, and to prevent grips that overhang.",
        ge=0.0,
    )
    lid_height: Optional[float] = Field(
        default=None,
        description="The height of the lid, measured from it's base to it's top, in millimeters. This is used to calculate the total height of the labware when a lid is present, as well as for lid-related operations like removal and replacement.",
        ge=0.0,
    )
    lidded: bool = Field(
        default=False,
        description="Whether the labware currently has a lid on it. If true, the lid_height and lid_lip will be used to compute the total height of the labware for gripper calculations. If false, the lid dimensions will be ignored.",
    )
    grip_exclusion_ranges: Optional[list[float]] = Field(
        default=None,
        description="A list of height ranges, as measured from the bottom of the labware (in millimeters), that the gripper should avoid when gripping the labware. Each pair of values represents a start and end height (e.g., [10, 20, 30, 40] means avoid 10-20mm and 30-40mm). This is useful for avoiding fragile areas, lips, or other features on the labware. If unset, no exclusion ranges are applied.",
        min_length=2,
    )

    @field_validator("grip_exclusion_ranges", mode="after")
    def exclusion_ranges_are_pairs(
        self, v: Optional[list[float]]
    ) -> Optional[list[float]]:
        """Validate that exclusion ranges are in pairs."""
        if v is not None and len(v) % 2 != 0:
            raise ValueError(
                "grip_exclusion_ranges must be in pairs of start and end heights."
            )
        return v

    @model_validator(mode="after")
    def validate_lid_properties(self) -> "LabwareDimensions":
        """Ensures that:
        If lidded is true, lid_height must be set.
        If lidded is true, lid_lip + lid_height > height.
        """
        if self.lidded and self.lid_height is None:
            raise ValueError("If lidded is true, lid_height must be set.")
        if self.lidded and self.lid_lip + self.lid_height < self.height:
            raise ValueError(
                "If lidded is true, lid_lip + lid_height must be greater than or equal to height."
            )
        return self


class NestDimensions(MadsciBaseModel):
    """Dimensions of a labware nest location in the lab, used for gripper calculations."""

    max_height: Optional[float] = Field(
        default=None,
        description="The maximum height to safely approach the location, in millimeters. This is used in conjuction with the gripper's safe_clearance to prevent collisions with overhead structures or equipment. If unset, no maximum height is enforced.",
        ge=0.0,
    )
    min_approach_height: float = Field(
        default=0.0,
        description="The minimum height to approach the location, in millimeters. This is used to prevent collisions with structures around the location, including nest walls or holders. If unset, no minimum approach height is enforced.",
        ge=0.0,
    )
    min_grip_height: float = Field(
        default=0.0,
        description="The minimum height to grip labware at the location, in millimeters. This is used to prevent collisions with structures around the location, including nest walls or holders. If unset, no minimum height is enforced.",
        ge=0.0,
    )
    training_height: float = Field(
        default=0.0,
        description="The grip height at which the location was trained to pick/place labware at this location, in millimeters, measured from the base of the location. This is used to compute the 'true' location position. If unset, no training height is recorded and the stored joint angles are assumed to be the accurate position of the location.",
        ge=0.0,
    )
    press_fit_depth: float = Field(
        default=0.0,
        description="The depth to which labware should be pressed into the location for a secure fit, in millimeters. This is used to ensure that labware is properly seated in locations that require pressure to properly seat. If unset, no press-fit depth is applied.",
        ge=0.0,
    )
