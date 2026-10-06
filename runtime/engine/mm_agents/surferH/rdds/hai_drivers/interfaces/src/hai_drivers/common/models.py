from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SessionStatus(StrEnum):
    """Known session status values. The API may return other values."""

    RUNNING = "running"
    UNKNOWN = "unknown"
    FAILED = "failed"
    STOPPED = "stopped"
    PENDING = "pending"
    STARTING = "starting"


# ============================================================================
# Schemas
# ============================================================================


class SessionCreate(BaseModel):
    """Request model for creating a session."""

    type: Literal["browser", "desktop"]
    mode: Literal["headless", "headful"]
    region: Literal["default", "us-west-2"] = "default"
    labels: dict[str, str] = Field(default_factory=dict)
    browser_name: str | None = None
    platform_name: str | None = None
    resolution: str | None = None
    timezone: str = "Europe/Paris"
    image: str | None = None
    browser_profile_id: UUID | str | None = None


class ConnectUrlsResponse(BaseModel):
    """Connection URLs for a session."""

    novnc: str | None = None
    webrtc: str | None = None
    command: str | None = None
    devtools: str | None = None
    webdriver: str | None = None
    desktop: str | None = None
    evaluation: str | None = None


class SessionRead(BaseModel):
    """Response model for a session."""

    id: UUID
    status: str | None = None  # See SessionStatus for known values
    runner_endpoint: str | None = None
    region: str
    runner: str
    type: str
    mode: str
    browser_name: str | None = None
    platform_name: str | None = None
    resolution: str | None = None
    labels: dict[str, Any] | None = None
    timezone: str | None = None
    connect_urls: ConnectUrlsResponse | None = None
    created_at: datetime
    updated_at: datetime


class SessionList(BaseModel):
    """Response model for listing sessions."""

    total: int
    limit: int
    offset: int
    sessions: list[SessionRead]


# ============================================================================
# Browser Profile Schemas
# ============================================================================


class BrowserProfileCreate(BaseModel):
    """Request model for completing a browser profile upload."""

    name: str
    browser_name: str
    browser_version: str
    description: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)


class BrowserProfileRead(BaseModel):
    """Response model for a browser profile."""

    id: UUID
    name: str
    description: str | None = None
    browser_name: str
    browser_version: str
    s3_path: str | None = None
    file_size_bytes: int | None = None
    checksum: str | None = None
    usage_count: int = 0
    last_used_at: datetime | None = None
    labels: dict[str, str] | None = None
    created_at: datetime
    updated_at: datetime


class BrowserProfileList(BaseModel):
    """Response model for listing browser profiles."""

    total: int
    limit: int
    offset: int
    profiles: list[BrowserProfileRead]


class InitiateUploadResponse(BaseModel):
    """Response model for initiating a browser profile upload."""

    profile_id: UUID
    upload_url: str
    upload_fields: dict[str, str]
    upload_expires_in: int
