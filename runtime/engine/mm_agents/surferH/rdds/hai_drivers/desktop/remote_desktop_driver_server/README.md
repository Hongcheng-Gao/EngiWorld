[English](README.md) | [简体中文](README_CN.md)

# Remote Desktop Server

This server is deployed and runs in an AMI (Amazon Machine Image).

The FastAPI server exposes desktop control functionality via pyautogui for remote access.

## Get started

To start the server on the remote desktop, please follow these steps:
- Copy `hai_drivers/interfaces` directory into a dedicated folder on the machine.
- Copy `hai_drivers/desktop/remote_desktop_driver_server` into a dedicated folder as well.
  Important: Maintain the same folder structure between server and interfaces.
- Install uv on the machine.
- Navigate to the server directory and install the dependencies:
```bash
$ cd desktop/remote_desktop_driver_server
$ uv sync
```
- Activate your environment and start the server:
```bash
$ python src/server.py --host 0.0.0.0 --port 8000
```
