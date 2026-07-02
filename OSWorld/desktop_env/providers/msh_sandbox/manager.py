from desktop_env.providers.base import VMManager


class MshSandboxVMManager(VMManager):
    """Maps the task snapshot to a sandbox image id under the 'osworld:' namespace
    (e.g. snapshot='FreeCAD0.19' -> image='osworld:FreeCAD0.19')."""

    def resolve_image(self, snapshot: str, os_type: str, **kwargs) -> str:
        return f"osworld:{snapshot}"
