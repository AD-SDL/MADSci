"""MADSci module interface implementations."""

from madsci.module.interface.abstract_module_interface import AbstractModuleInterface
from madsci.module.interface.rest_module_interface import RestModuleInterface

MODULE_INTERFACE_MAP = {
    "rest_module_interface": RestModuleInterface,
}

__all__ = [
    AbstractModuleInterface.__name__,
    RestModuleInterface.__name__,
    "MODULE_INTERFACE_MAP",
]
