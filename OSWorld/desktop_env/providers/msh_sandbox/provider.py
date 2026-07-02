import asyncio
import logging
import threading

from agentgym.sandbox.osworld import OSWorldSandbox

from desktop_env.providers.base import Provider

logger = logging.getLogger("desktopenv.providers.msh_sandbox.MshSandboxProvider")
logger.setLevel(logging.INFO)

DEFAULT_TTL_SECONDS = 30 * 60
HEARTBEAT_INTERVAL_SECONDS = 10 * 60
DEFAULT_SPEC = "g4il.2xlarge"


class MshSandboxProvider(Provider):
    """OSWorld provider backed by agentgym OSWorldSandbox.

    Each task gets its own sandbox session. reset_to_clean tears down the current
    session and allocates a new one on the same image, since sandboxes have no
    snapshot support. A daemon heartbeat thread refreshes the session TTL while
    the sandbox is alive so long-running tasks are not killed at the initial TTL.
    """

    def __init__(self, region: str = None, *, spec: str = DEFAULT_SPEC):
        super().__init__(region)
        self.spec = spec
        self.sandbox: OSWorldSandbox | None = None
        self._image: str | None = None
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_stop: threading.Event | None = None

    def start_emulator(self, image: str, headless: bool, os_type: str) -> None:
        logger.info(
            f"Allocating sandbox image={image} spec={self.spec} ttl={DEFAULT_TTL_SECONDS}s"
        )
        sb = OSWorldSandbox(ttl=DEFAULT_TTL_SECONDS, image=image, spec=self.spec)
        # Bind handle BEFORE start_sync. If wait_ready fails and api.delete also
        # fails inside agentgym's start(), sb.id stays set; binding early keeps
        # the handle reachable for the caller to retry stop_sync.
        self.sandbox = sb
        self._image = image
        sb.start_sync()
        logger.info(
            f"Sandbox ready id={sb.id} osworld={sb.endpoint_osworld} cdp={sb.endpoint_cdp}"
        )
        self._start_heartbeat(sb)

    def get_ip_address(self) -> str:
        sb = self.sandbox
        if sb is None:
            raise RuntimeError("get_ip_address called before start_emulator")
        return f"{sb.osworld_host}:{sb.osworld_port}:{sb.cdp_port}:{sb.vnc_port}:{sb.vlc_port}"

    def reset_to_clean(self) -> None:
        if self._image is None:
            raise RuntimeError("reset_to_clean called before start_emulator")
        image = self._image
        self.stop_emulator()
        self.start_emulator(image, headless=False, os_type="")

    def stop_emulator(self) -> None:
        # Heartbeat must be stopped first; if stop_sync fails and the caller retries,
        # 30min TTL still bounds the leak even without heartbeat refresh.
        self._stop_heartbeat()
        sb = self.sandbox
        if sb is None:
            return
        if not sb.id:
            # Bound but never allocated server-side (start_sync raised before
            # agentgym's update_from_session). Nothing to release.
            self.sandbox = None
            self._image = None
            return
        sandbox_id = sb.id  # SessionSandbox.stop_sync clears sb.id only on success
        # Let stop_sync raise on failure. agentgym already logs the error before
        # re-raising; SessionSandbox keeps sb.id intact on failure, and we keep
        # self.sandbox bound, so the agentgym handle stays actionable for retry.
        sb.stop_sync()
        logger.info(f"Released sandbox id={sandbox_id}")
        self.sandbox = None
        self._image = None

    def _start_heartbeat(self, sb: OSWorldSandbox) -> None:
        stop = threading.Event()
        thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(sb, stop),
            name=f"msh-sandbox-heartbeat-{sb.id}",
            daemon=True,
        )
        self._heartbeat_stop = stop
        self._heartbeat_thread = thread
        thread.start()

    def _stop_heartbeat(self) -> None:
        stop = self._heartbeat_stop
        thread = self._heartbeat_thread
        self._heartbeat_stop = None
        self._heartbeat_thread = None
        if stop is not None:
            stop.set()
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)

    def _heartbeat_loop(self, sb: OSWorldSandbox, stop: threading.Event) -> None:
        sandbox_id = sb.id
        while not stop.wait(HEARTBEAT_INTERVAL_SECONDS):
            try:
                # NOTE: agentgym's SessionAPI.refresh_sync drops `self.refresh`
                # and feeds the (id, ttl) tuple straight to asyncio.run, so the
                # SDK's sync path raises ValueError and never refreshes. Drive
                # the working async entrypoint ourselves until the SDK is fixed.
                ok = asyncio.run(sb.refresh(DEFAULT_TTL_SECONDS))
            except Exception as e:
                logger.error(
                    f"Error refreshing sandbox id={sandbox_id}: {e.__class__.__name__} {e}"
                )
                continue
            if ok:
                logger.info(
                    f"Refreshed sandbox id={sandbox_id} ttl={DEFAULT_TTL_SECONDS}s"
                )
            else:
                logger.warning(
                    f"Sandbox id={sandbox_id} not found on refresh, stopping heartbeat"
                )
                return
