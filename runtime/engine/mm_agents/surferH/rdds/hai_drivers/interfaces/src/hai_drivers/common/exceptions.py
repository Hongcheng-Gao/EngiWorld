from uuid import UUID


class DriverException(Exception):
    pass


class SessionNotFoundError(Exception):
    """Raised when a session is not found."""

    def __init__(self, session_id: UUID) -> None:
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class InvalidRunnerTypeError(Exception):
    """Raised when an invalid runner type is specified."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class BrowserProfileNotFoundError(Exception):
    """Raised when a browser profile is not found."""

    def __init__(self, profile_id: UUID) -> None:
        self.profile_id = profile_id
        super().__init__(f"Browser profile not found: {profile_id}")


class RemoteDriverServiceError(Exception):
    """Base exception for remote driver service errors."""

    pass
