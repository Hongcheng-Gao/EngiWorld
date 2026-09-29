from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Sequence

from hai_drivers.common.types import Key, MouseButton, ScrollDirection
from hai_drivers.desktop.models import RunCommandResponse


class DesktopDriverInterface(ABC):
    @cached_property
    @abstractmethod
    def platform(self) -> str:
        """Get the platform of the desktop."""

    @abstractmethod
    def screenshot_png_bytes(self) -> bytes:
        """Take a png screenshot and return it as bytes."""

    @abstractmethod
    def get_screen_size(self) -> tuple[int, int]:
        """Get the screen dimensions as (width, height)."""

    @abstractmethod
    def get_mouse_position(self) -> tuple[int, int]:
        """Get the current mouse position as (x, y)."""

    @abstractmethod
    def get_accessibility_tree(self) -> str:
        """Get the accessibility tree of the visible screen as an xml string."""

    @abstractmethod
    def get_number_of_pixels_scrolled_per_click(self) -> int:
        """Return the number of px scrolled by a scrolling click.

        This value should either be a constant or cached by the implementation.
        """

    @abstractmethod
    def mouse_move_to(self, x: int, y: int):
        """Move the mouse to the coordinates."""

    @abstractmethod
    def mouse_press(self, button: MouseButton):
        """Press a mouse button down without releasing it."""

    @abstractmethod
    def mouse_release(self, button: MouseButton):
        """Release a previously pressed mouse button."""

    @abstractmethod
    def click(self, x: int, y: int, button: MouseButton = "left"):
        """Click at the specified screen coordinates."""

    @abstractmethod
    def double_click(self, x: int, y: int, button: MouseButton = "left", delay_between_clicks: float = 0.05):
        """Double click at the specified screen coordinates."""

    @abstractmethod
    def write(self, text: str, delay_between_keys: float = 0.05) -> None:
        """Type a string of text.
        Capital letters and other special characters will be translated into the correct keycode sequence.

        delay_between_keys: secs between each key press.
        """

    @abstractmethod
    def hotkey(self, keys: list[Key]):
        """Performs key down presses on the arguments passed in order, then performs key releases in reverse order."""

    @abstractmethod
    def tap_key(self, key: Key):
        """Tap a keyboard key. Performs both press and release of the key."""

    @abstractmethod
    def press_key(self, key: Key):
        """Press a keyboard key down without releasing it.

        Behaviour of pressing a Key might be OS specific. e.g Ctrl vs Command
        """

    @abstractmethod
    def release_key(self, key: Key):
        """Release a previously pressed keyboard key."""

    @abstractmethod
    def scroll_by_n_clicks(self, direction: ScrollDirection, clicks: int):
        """Scroll in a direction by a number of atomic scrolling click.

        The size of a click differs per platform, you can get it with get_number_of_pixels_scrolled_per_click().
        """

    def scroll_by_n_pxs(self, direction: ScrollDirection, pixels: int):
        """Scroll in a direction by at least `pixels`, 1 px ~= 0.26 mm.

        If pixels is not a multiple of get_number_of_pixels_scrolled_per_click(), the n pixels scrolled will be higher than pixels.
        """
        npixels_per_click = self.get_number_of_pixels_scrolled_per_click()
        self.scroll_by_n_clicks(
            direction=direction,
            clicks=(pixels // npixels_per_click) + (1 if pixels % npixels_per_click > 0 else 0),
        )

    @abstractmethod
    def run_command(
        self,
        command: Sequence[str],
        timeout: int | None = 60,
        env: dict[str, str] | None = None,
        cwd: Path | None = None,
        detach: bool = False,
        ignore_errors: bool = False,
    ) -> RunCommandResponse:
        """Run a shell command on the desktop."""

    @abstractmethod
    def read_file(self, path: str) -> bytes:
        """Read a file from the desktop filesystem. Returns raw bytes."""

    @abstractmethod
    def write_file(self, path: str, content: bytes) -> None:
        """Write raw bytes to a file on the desktop filesystem."""
