Module madsci.client.cli.tui.widgets.service_aware
==================================================
ServiceAwareContainer widget for MADSci TUI.

Container that gates children behind a service health check. Shows
children when the service is available, and an "unavailable" panel
with a retry button when it is not.

.. note:: Not yet used by any screen -- designed for future adoption.
   See https://github.com/AD-SDL/MADSci/issues/278

Classes
-------

`ServiceAwareContainer(service_url: str, service_name: str, *, check_interval: float = 5.0, **kwargs: Any)`
:   Container that gates children behind a service health check.
    
    Shows children when the service is available. Shows an "unavailable"
    panel with a retry button when the service is unreachable.
    Uses :func:`check_service_health_async` for health checking.
    
    Posts :class:`ServiceAvailable` and :class:`ServiceUnavailable`
    messages when the service state changes.
    
    Usage::
    
        yield ServiceAwareContainer(
            service_url="http://localhost:8001/",
            service_name="Event Manager",
        )
    
    Initialize the container.
    
    Args:
        service_url: Base URL of the service to check.
        service_name: Human-readable service name for display.
        check_interval: Interval in seconds between health checks.
        **kwargs: Additional keyword arguments forwarded to ``Widget``.

    ### Ancestors (in MRO)

    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `DEFAULT_CSS`
    :

    `ServiceAvailable`
    :   Posted when the service becomes available.

    `ServiceUnavailable`
    :   Posted when the service becomes unavailable.

    `can_focus`
    :

    `can_focus_children`
    :

    ### Instance variables

    `is_available: Reactive[ReactiveType] | ReactiveType`
    :   Create a reactive attribute.
        
        Args:
            default: A default value or callable that returns a default.
            layout: Perform a layout on change.
            repaint: Perform a repaint on change.
            init: Call watchers on initialize (post mount).
            always_update: Call watchers even when the new value equals the old value.
            recompose: Compose the widget again when the attribute changes.
            bindings: Refresh bindings when the reactive changes.
            toggle_class: An optional TCSS classname(s) to toggle based on the truthiness of the value.

    ### Methods

    `check_health(self) ‑> bool`
    :   Perform a health check against the service.
        
        Returns:
            ``True`` if the service is available, ``False`` otherwise.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the container layout.

    `on_button_pressed(self, event: Button.Pressed) ‑> None`
    :   Handle retry button press.

    `on_mount(self) ‑> None`
    :   Start periodic health checks on mount.

    `watch_is_available(self, value: bool) ‑> None`
    :   React to availability changes by toggling panels.