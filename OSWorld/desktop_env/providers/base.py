from abc import ABC, abstractmethod


class Provider(ABC):
    """Lifecycle of a virtualized desktop instance keyed to a per-task image.

    Call order from DesktopEnv:
        start_emulator(image, headless, os_type)  -- once per (process, image)
        get_ip_address()                          -- after every start / reset_to_clean
        reset_to_clean()                          -- between tasks that share the same image
        stop_emulator()                           -- before re-starting with a different image, or on close
    """

    def __init__(self, region: str = None):
        self.region = region

    @abstractmethod
    def start_emulator(self, image: str, headless: bool, os_type: str) -> None:
        """Start a fresh instance bound to the resolved `image`. Must block until osworld_server is reachable."""

    @abstractmethod
    def get_ip_address(self) -> str:
        """Return the access endpoint as five colon-segments:
            host:server_port:chromium_port:vnc_port:vlc_port
        """

    @abstractmethod
    def reset_to_clean(self) -> None:
        """Roll the current instance back to a clean state on the same image.

        For sandboxes without snapshot support this is stop + start of the same image.
        Endpoints may change after this call; callers must re-read get_ip_address().
        """

    @abstractmethod
    def stop_emulator(self) -> None:
        """Tear down the current instance. Must be idempotent."""


class VMManager(ABC):
    """Translates the logical snapshot name from task_config['snapshot'] into the provider-specific image id."""

    @abstractmethod
    def resolve_image(self, snapshot: str, os_type: str, **kwargs) -> str:
        """Map task_config['snapshot'] (a bare name, no path / no extension) to the value
        passed to provider.start_emulator(image, ...).

        File-based providers append the project-conventional directory and extension:
            docker:      f"vm_images/{snapshot}.qcow2"  (download on first use)
            vmware:      f"vm_images/{snapshot}.vmx"
            virtualbox:  f"vm_images/{snapshot}.vbox"
        Sandbox / cloud providers translate to whatever id their backend expects:
            msh-sandbox: f"osworld:{snapshot}"
            aws:         AMI id, looked up from a name -> ami mapping table.
        """
