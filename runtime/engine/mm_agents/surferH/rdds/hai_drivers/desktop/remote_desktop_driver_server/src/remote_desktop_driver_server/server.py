"""FastAPI server that exposes desktop control functionality via pyautogui."""

import base64
import io
import sys
from contextlib import asynccontextmanager

import pyautogui
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from hai_drivers.desktop.models import (
    ClickRequest,
    DoubleClickRequest,
    HotkeyRequest,
    MouseMoveRequest,
    MousePositionResponse,
    MousePressRequest,
    MouseReleaseRequest,
    PlatformResponse,
    PressKeyRequest,
    ReadFileRequest,
    ReadFileResponse,
    ReleaseKeyRequest,
    RunCommandRequest,
    RunCommandResponse,
    ScreenshotResponse,
    ScreenSizeResponse,
    ScrollRequest,
    TapKeyRequest,
    WriteFileRequest,
    WriteRequest,
)
from hai_drivers.desktop.utils import run_command_impl


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    pyautogui.FAILSAFE = False
    yield


app = FastAPI(title="Remote Desktop Control Server", lifespan=lifespan)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(status_code=200, content={"status": "healthy"})


@app.get("/platform", response_model=PlatformResponse)
async def get_platform():
    """Get the platform."""
    return PlatformResponse(platform=sys.platform)


@app.get("/screenshot", response_model=ScreenshotResponse)
async def get_screenshot():
    """Capture a screenshot and return it as base64-encoded PNG bytes."""
    screenshot = pyautogui.screenshot()
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
    return ScreenshotResponse(image_base64=img_base64)


@app.get("/screen_size", response_model=ScreenSizeResponse)
async def get_screen_size():
    """Get the screen dimensions."""
    size = pyautogui.size()
    return ScreenSizeResponse(width=size.width, height=size.height)


@app.get("/mouse_position", response_model=MousePositionResponse)
async def get_mouse_position():
    """Get the current mouse cursor position."""
    position = pyautogui.position()
    return MousePositionResponse(x=position.x, y=position.y)


@app.post("/mouse_move")
async def mouse_move(request: MouseMoveRequest):
    """Move the mouse to a specific position."""
    pyautogui.moveTo(request.x, request.y)
    return JSONResponse(status_code=200, content={"status": "success"})


@app.post("/mouse_press")
async def mouse_press(request: MousePressRequest):
    """Press a mouse button."""
    pyautogui.mouseDown(button=request.button)
    return JSONResponse(status_code=200, content={"status": "success"})


@app.post("/mouse_release")
async def mouse_release(request: MouseReleaseRequest):
    """Release a mouse button."""
    pyautogui.mouseUp(button=request.button)
    return JSONResponse(status_code=200, content={"status": "success"})


@app.post("/click")
async def click(request: ClickRequest):
    """Click at a specific position."""
    pyautogui.click(x=request.x, y=request.y, button=request.button)
    return JSONResponse(status_code=200, content={"status": "success"})


@app.post("/double_click")
async def double_click(request: DoubleClickRequest):
    """Double click at a specific position."""
    pyautogui.doubleClick(
        x=request.x,
        y=request.y,
        button=request.button,
        interval=request.delay_between_clicks,
    )
    return JSONResponse(status_code=200, content={"status": "success"})


@app.post("/hotkey")
async def hotkey(request: HotkeyRequest):
    """Press a hotkey."""
    pyautogui.hotkey(*request.keys)
    return JSONResponse(status_code=200, content={"status": "success"})


@app.post("/tap_key")
async def tap_key(request: TapKeyRequest):
    """Tap a specific key. Performs both press and release of the key."""
    pyautogui.press(request.key)
    return JSONResponse(status_code=200, content={"status": "success"})


@app.post("/press_key")
async def press_key(request: PressKeyRequest):
    """Press a specific key without releasing it."""
    pyautogui.keyDown(request.key)
    return JSONResponse(status_code=200, content={"status": "success"})


@app.post("/release_key")
async def release_key(request: ReleaseKeyRequest):
    """Release a specific key."""
    pyautogui.keyUp(request.key)
    return JSONResponse(status_code=200, content={"status": "success"})


@app.post("/write")
async def write(request: WriteRequest):
    """Write text on the keyboard."""
    pyautogui.write(request.text, interval=request.delay_between_keys)
    return JSONResponse(status_code=200, content={"status": "success"})


@app.post("/scroll")
async def scroll(request: ScrollRequest):
    """Scroll in a direction by a number of clicks."""
    # pyautogui.scroll() takes positive values for up, negative for down
    # For horizontal scrolling, we use pyautogui.hscroll()
    if request.direction == "up":
        pyautogui.scroll(request.clicks)
    elif request.direction == "down":
        pyautogui.scroll(-request.clicks)
    elif request.direction == "right":
        pyautogui.hscroll(request.clicks)
    elif request.direction == "left":
        pyautogui.hscroll(-request.clicks)
    else:
        raise ValueError(f"Invalid scroll direction: {request.direction}")

    return JSONResponse(status_code=200, content={"status": "success"})


@app.post("/run_command", response_model=RunCommandResponse)
def run_command(request: RunCommandRequest):
    """Run a shell command and return the output."""
    return run_command_impl(
        command=request.command, timeout=request.timeout, env=request.env, cwd=request.cwd, detach=request.detach
    )


@app.post("/read_file", response_model=ReadFileResponse)
def read_file(request: ReadFileRequest):
    """Read a file and return its contents as base64."""
    from pathlib import Path

    path = Path(request.path).expanduser()
    if not path.exists():
        return JSONResponse(status_code=404, content={"detail": f"File not found: {request.path}"})
    if not path.is_file():
        return JSONResponse(status_code=400, content={"detail": f"Not a file: {request.path}"})
    content = path.read_bytes()
    return ReadFileResponse(content_base64=base64.b64encode(content).decode("ascii"))


@app.post("/write_file")
def write_file(request: WriteFileRequest):
    """Write base64-encoded content to a file."""
    from pathlib import Path

    path = Path(request.path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = base64.b64decode(request.content_base64)
    path.write_bytes(content)
    return JSONResponse(status_code=200, content={"status": "success", "path": str(path)})


if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Remote Desktop Driver Server")
    parser.add_argument("--host", default="::", help="server host")
    parser.add_argument("--port", type=int, default=5000, help="server port")
    parser.add_argument("--reload", action="store_true", help="reload server")
    args = parser.parse_args()

    uvicorn.run("server:app", host=args.host, port=args.port, reload=args.reload)
