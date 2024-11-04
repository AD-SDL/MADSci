"""REST-based module interface and helper classes."""

from madsci.module.base_module import BaseModule, ModuleController, ModuleInterface


class RestModule(BaseModule):
    """REST-based module interface and helper classes."""

    pass


class RestModuleInterface(ModuleInterface):
    """REST-based module interface."""

    pass


class RestControlInterface(ModuleController):
    """REST-based control interface."""

    pass
