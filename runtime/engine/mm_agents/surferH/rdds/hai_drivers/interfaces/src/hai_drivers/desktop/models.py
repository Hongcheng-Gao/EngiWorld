"""Pydantic models shared between the remote desktop client and server."""

from typing import Sequence

from hai_drivers.common.types import MouseButton, ScrollDirection
from pydantic import BaseModel


class PlatformResponse(BaseModel):
    """Response containing the platform."""

    platform: str


class ScreenshotResponse(BaseModel):
    """Response containing a screenshot as base64-encoded PNG bytes."""

    image_base64: str


class ScreenSizeResponse(BaseModel):
    """Response containing screen dimensions."""

    width: int
    height: int


class MousePositionResponse(BaseModel):
    """Response containing mouse cursor position."""

    x: int
    y: int


class MouseMoveRequest(BaseModel):
    """Request to move mouse to a specific position."""

    x: int
    y: int


class MousePressRequest(BaseModel):
    """Request to press a mouse button."""

    button: MouseButton


class MouseReleaseRequest(BaseModel):
    """Request to release a mouse button."""

    button: MouseButton


class ClickRequest(BaseModel):
    """Request to click at a specific position."""

    x: int
    y: int
    button: MouseButton = "left"


class DoubleClickRequest(BaseModel):
    """Request to double click at a specific position."""

    x: int
    y: int
    button: MouseButton = "left"
    delay_between_clicks: float = 0.05


class HotkeyRequest(BaseModel):
    """Request to press a hotkey."""

    keys: Sequence[str]


class WriteRequest(BaseModel):
    """Request to write text on the keyboard."""

    text: str
    delay_between_keys: float = 0.05


class TapKeyRequest(BaseModel):
    """Request to tap a specific key."""

    key: str


class PressKeyRequest(BaseModel):
    """Request to press a specific key without releasing it."""

    key: str


class ReleaseKeyRequest(BaseModel):
    """Request to release a specific key."""

    key: str


class ScrollRequest(BaseModel):
    """Request to scroll in a direction."""

    direction: ScrollDirection
    clicks: int


class AccessibilityTreeResponse(BaseModel):
    """Response containing the accessibility tree as a string."""

    tree: str


class RunCommandRequest(BaseModel):
    """Request to run a shell command."""

    command: list[str]
    env: dict[str, str] | None = None
    cwd: str | None = None
    detach: bool = False
    timeout: int | None = 60


class RunCommandResponse(BaseModel):
    """Response from running a shell command."""

    returncode: int
    stdout: str
    stderr: str
    exception: str | None = None


class ReadFileRequest(BaseModel):
    """Request to read a file from the desktop filesystem."""

    path: str


class ReadFileResponse(BaseModel):
    """Response containing file contents as base64-encoded bytes."""

    content_base64: str


class WriteFileRequest(BaseModel):
    """Request to write a file to the desktop filesystem."""

    path: str
    content_base64: str
