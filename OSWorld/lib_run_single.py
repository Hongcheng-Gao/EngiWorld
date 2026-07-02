import datetime
import json
import logging
import os
import time
from io import BytesIO
from multiprocessing import current_process

from wrapt_timeout_decorator import *
from PIL import Image
from lib_results_logger import log_task_completion
from desktop_env.controllers.python import SandboxExecuteHardTimeoutError
from mm_agents.agent import encode_image
from mm_agents.cli_policy import CliPolicyViolation, validate_cli_action

logger = logging.getLogger("desktopenv.experiment")


# ---- step-level resume helpers ---------------------------------------------
# Wired in via `--resume` (default on). When a task is interrupted mid-run, on
# the next launch we replay the recorded action sequence from traj.jsonl
# against a fresh (deterministic) sandbox, then let the agent continue from
# step N+1. Each replayed action is followed by a 60s sleep — long enough for
# even the heaviest CAD UI to settle, since we no longer have LLM latency
# acting as a natural delay between actions.

_RESUME_SLEEP_SECONDS = 60


def _read_traj_for_resume(example_result_dir):
    """Read traj.jsonl and group rows by step_num.

    Returns a list of step-groups in ascending step_num order, where each
    group is::

        {
          "step_num":        int,
          "response":        str,         # raw model output for this step
          "actions":         [(kind, code), ...],   # excludes null-action rows
          "info":            dict,        # last row's info (may have hard_timeout)
          "parse_error":     str | None,
          "bash_runs":       list | None, # terminal-mode only
          "readimg":         list | None, # terminal-mode only
          "terminal_signal": str | None,  # terminal-mode only
          "terminal_signal_payload": str | None, # terminal-mode only
          "done":            bool,
        }

    Returns [] for missing / empty / fully-corrupt files. A partial trailing
    line (truncated JSON from a crash mid-append) is silently skipped — this
    matches lib_results_logger's reader behavior.
    """
    path = os.path.join(example_result_dir, "traj.jsonl")
    if not os.path.isfile(path):
        return []
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    # Partial trailing line from a crashed append. Skip.
                    continue
    except OSError:
        return []
    if not rows:
        return []

    groups_by_step = {}
    for r in rows:
        sn = r.get("step_num")
        if not isinstance(sn, int):
            continue
        groups_by_step.setdefault(sn, []).append(r)
    if not groups_by_step:
        return []

    out = []
    for sn in sorted(groups_by_step):
        rs = groups_by_step[sn]
        actions = []
        for r in rs:
            a = r.get("action")
            if isinstance(a, dict) and "kind" in a:
                actions.append((a["kind"], a.get("code", "") or ""))
        last = rs[-1]
        out.append({
            "step_num": sn,
            "response": rs[0].get("response", "") or "",
            "actions": actions,
            "info": last.get("info") or {},
            "parse_error": last.get("parse_error"),
            "bash_runs": last.get("bash_runs"),
            "readimg": last.get("readimg"),
            "terminal_signal": last.get("terminal_signal"),
            "terminal_signal_payload": last.get("terminal_signal_payload"),
            "done": bool(last.get("done", False)),
        })
    return out


def _purge_example_dir(example_result_dir):
    """Remove all files in example_result_dir (resume fallback / fresh-run reset)."""
    if not os.path.isdir(example_result_dir):
        return
    for f in os.listdir(example_result_dir):
        p = os.path.join(example_result_dir, f)
        try:
            if os.path.isfile(p) or os.path.islink(p):
                os.remove(p)
        except OSError:
            pass


def _restore_pending_feedback(agent, last_group):
    """Re-arm agent._pending_runtime_error / _pending_parse_error to mirror what
    the agent would have seen on the next-turn user message in the original run.

    Simplified vs the live path: we don't replicate the detach-hint text from
    lib_run_single's hard_timeout handler — by the time we resume, the system
    prompt has already taught the model about detach patterns, so a terse
    "sandbox killed your last action" is enough to align behavior.
    """
    if not last_group:
        return
    if last_group.get("info", {}).get("hard_timeout"):
        agent._pending_runtime_error = (
            "Your previous action was killed by the sandbox: it exceeded the "
            "120s per-action wall-clock budget. Only the immediate child was "
            "terminated; any grandchild processes may still be running on the VM."
        )
    pe = last_group.get("parse_error")
    if pe:
        agent._pending_parse_error = pe


def _gui_observation_for_agent(agent, obs):
    mode = getattr(agent, "eval_mode", "")
    if mode == "gui-a11y":
        formatter = getattr(agent, "_format_a11y_observation", None)
        accessibility_tree = ""
        if callable(formatter):
            accessibility_tree = formatter(obs)
        else:
            accessibility_tree = obs.get("accessibility_tree") or ""
        return {
            "screenshot": None,
            "accessibility_tree": accessibility_tree,
        }
    if mode == "gui-screenshot-a11y":
        formatter = getattr(agent, "_format_a11y_observation", None)
        accessibility_tree = ""
        if callable(formatter):
            accessibility_tree = formatter(obs)
        else:
            accessibility_tree = obs.get("accessibility_tree") or ""
        return {
            "screenshot": encode_image(obs["screenshot"]),
            "accessibility_tree": accessibility_tree,
        }
    return {
        "screenshot": encode_image(obs["screenshot"]),
        "accessibility_tree": None,
    }


def _replay_gui_steps(env, agent, groups, sleep_seconds, bash_timeout):
    """Replay a GUI-mode trajectory against the live env.

    Side effects on ``agent``:
      - Appends one entry per replayed step to ``thoughts/actions/observations``
        (PromptAgent expects all three lists equal-length; predict() only reads
        the last ``max_trajectory_length`` entries, so older entries are fine
        with placeholder shapes).
      - Re-arms ``_pending_runtime_error`` / ``_pending_parse_error`` from the
        final group's metadata so the next predict() sees the same feedback the
        original run would have shown.

    Returns ``(last_obs, done_flag, completed_step_count)``. The caller should
    set step_idx = completed_step_count and continue the normal loop.
    """
    obs = env._get_obs()
    done = False
    completed = 0
    for grp in groups:
        # Mirror predict()'s order: it appends to observations BEFORE writing
        # to thoughts/actions. We replicate the steady-state shape here.
        agent.observations.append(_gui_observation_for_agent(agent, obs))
        agent.thoughts.append(grp["response"])
        # Match parse_typed_actions' return: List[Tuple[str, str]]. predict()
        # never inspects this directly (agent.py only unpacks `previous_action`
        # in its history loop and ignores it), but matching shape keeps any
        # future readers honest. Empty list is fine for parse-error groups —
        # mirrors agent.py:985 which appends [] on parse failure to preserve
        # the len(observations)==len(actions)==len(thoughts) invariant.
        agent.actions.append([tuple(a) for a in grp["actions"]])

        for kind, code in grp["actions"]:
            try:
                obs, _reward, done, _info = env.step(
                    (kind, code), sleep_seconds, bash_timeout=bash_timeout
                )
            except SandboxExecuteHardTimeoutError as exc:
                logger.warning("[resume] env.step hit budget cap during replay: %s", exc)
                obs = env._get_obs()
                done = False
            if done:
                break
        completed += 1
        if done:
            break

    _restore_pending_feedback(agent, groups[-1] if groups else None)
    return obs, done, completed


def _replay_cli_steps(env, agent, groups, sleep_seconds, bash_timeout, task_config=None, text_only=False):
    """Replay a terminal-mode trajectory.

    Two obs shapes are in play here and they must not be confused:

      - **predict input**  ``{"bash_runs": [...], "images": [(path, bytes), ...]}``
        — what ``run_single_example_terminal`` builds and passes to
        ``agent.predict()``. The returned obs uses this shape.
      - **internal storage** ``{"bash_runs": [...], "images_paths": [paths]}``
        — what ``predict()`` actually appends to ``self.observations`` after
        stripping bytes. We must mirror this when populating agent history.

    bash actions go through ``env.controller.run_bash_script``; readimg goes
    through ``env.controller.get_file``. WAIT/DONE/FAIL are folded into the
    trailing ``terminal_signal`` for the group.
    """
    obs_input = {"bash_runs": [], "images": []}
    done = False
    completed = 0
    for grp in groups:
        # Mirror predict()'s internal-form append. observations[k] corresponds
        # to the obs that fed predict() at step k+1.
        agent.observations.append({
            "bash_runs": obs_input["bash_runs"],
            "images_paths": [p for (p, _data) in obs_input["images"]],
        })
        agent.thoughts.append(grp["response"])
        # Match parse_typed_actions' return: List[Tuple[str, str]]. predict()
        # never inspects this directly (agent.py only unpacks `previous_action`
        # in its history loop and ignores it), but matching shape keeps any
        # future readers honest. Empty list is fine for parse-error groups —
        # mirrors agent.py:985 which appends [] on parse failure to preserve
        # the len(observations)==len(actions)==len(thoughts) invariant.
        agent.actions.append([tuple(a) for a in grp["actions"]])

        bash_runs = []
        next_images = []  # [(path, bytes_or_empty), ...] — input shape
        for kind, code in grp["actions"]:
            if kind in ("bash", "python"):
                ts = datetime.datetime.now().strftime("%Y%m%d@%H%M%S%f")
                try:
                    validate_cli_action(kind, code, task_config, text_only=text_only)
                    if kind == "python":
                        result = env.controller.run_python_script(code, timeout=bash_timeout)
                    else:
                        result = env.controller.run_bash_script(code, timeout=bash_timeout)
                except SandboxExecuteHardTimeoutError as exc:
                    logger.warning("[resume] cli %s hit budget cap: %s", kind, exc)
                    result = {"output": "", "error": str(exc), "returncode": -1}
                except CliPolicyViolation as exc:
                    logger.warning("[resume] cli %s rejected by policy: %s", kind, exc)
                    result = {
                        "output": "",
                        "error": f"[{kind} action rejected by CLI integrity policy: {exc}]",
                        "returncode": -2,
                    }
                except Exception as exc:
                    logger.warning("[resume] cli %s failed: %s", kind, exc)
                    result = {"output": "", "error": f"[{kind} action raised: {exc}]",
                              "returncode": -1}
                bash_runs.append({
                    "command": code if kind == "bash" else f"[python]\n{code}",
                    "stdout": result.get("output") or "",
                    "stderr": result.get("error") or "",
                    "returncode": result.get("returncode", result.get("return_code", -1)),
                    "timestamp": ts,
                })
            elif kind == "readimg":
                if text_only:
                    next_images.append((f"{code} [error: readimg disabled in cli-text]", b""))
                    continue
                try:
                    data = env.controller.get_file(code)
                except Exception as exc:
                    next_images.append((f"{code} [error: {exc}]", b""))
                    continue
                if not data:
                    next_images.append((f"{code} [error: empty]", b""))
                else:
                    next_images.append((code, data))
            elif kind in ("WAIT", "DONE", "FAIL"):
                # Defer to the trailing terminal_signal handling below.
                pass
            # Other kinds (shouldn't appear in CLI mode) are ignored.
            time.sleep(sleep_seconds)

        sig = grp.get("terminal_signal")
        sig_payload = grp.get("terminal_signal_payload") or ""
        if not sig_payload:
            for kind, code in grp["actions"]:
                if kind == "WAIT":
                    sig_payload = code
                    break
        if sig in ("DONE", "FAIL"):
            done = True
        elif sig == "WAIT":
            time.sleep(_coerce_wait_seconds(sig_payload))

        obs_input = {"bash_runs": bash_runs, "images": next_images}
        completed += 1
        if done:
            break

    _restore_pending_feedback(agent, groups[-1] if groups else None)
    return obs_input, done, completed


def _flush_llm_attempts(agent, example_result_dir, step_num):
    """Flush PromptAgent.call_llm's per-attempt telemetry to llm_calls.jsonl.

    One row per LLM attempt (a step that retried 3 times produces 3 rows).
    Schema is intentionally kept independent of traj.jsonl: this file is for
    post-mortem analysis of finish_reason / usage / latency across providers,
    not for runtime evaluation. Other (non-PromptAgent) runners in this file
    don't populate ``_llm_attempts``; getattr-with-default keeps them silent.
    """
    attempts = getattr(agent, "_llm_attempts", None) or []
    if not attempts:
        return
    path = os.path.join(example_result_dir, "llm_calls.jsonl")
    n = len(attempts)
    with open(path, "a", encoding="utf-8") as f:
        for i, att in enumerate(attempts):
            row = {
                "step_num": step_num,
                "attempt_idx": i + 1,
                "is_final": (i == n - 1),
                **att,
            }
            f.write(json.dumps(row, ensure_ascii=False))
            f.write("\n")


def run_single_example(agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    runtime_logger = setup_logger(example, example_result_dir)

    # Reset environment first to get fresh VM IP
    env.reset(task_config=example)

    # Reset agent with fresh VM IP (for snapshot reverts)
    try:
        agent.reset(runtime_logger, vm_ip=env.vm_ip)
    except Exception as e:
        agent.reset(vm_ip=env.vm_ip)

    time.sleep(180) # Wait for the environment to be ready
    obs = env._get_obs() # Get the initial observation
    done = False
    step_idx = 0

    # Step-level resume: if traj.jsonl from a prior interrupted run exists and
    # --resume is on, replay the recorded actions against this fresh sandbox
    # so the agent picks up at step N+1. The sandbox state must be
    # deterministic across launches for replay to land on the same UI state.
    resume_attempted = (
        getattr(args, "resume", False)
        and os.path.isfile(os.path.join(example_result_dir, "traj.jsonl"))
    )
    record_video_active = False
    if resume_attempted:
        groups = _read_traj_for_resume(example_result_dir)
        if not groups:
            logger.warning(
                "[resume] traj.jsonl unparseable for %s; falling back to fresh run",
                example.get("id", "<unknown>"),
            )
            _purge_example_dir(example_result_dir)
            if getattr(args, "record_video", False):
                env.controller.start_recording()
                record_video_active = True
        else:
            if getattr(args, "record_video", False):
                logger.warning(
                    "[resume] record_video disabled in resume mode (cannot stitch "
                    "mp4 across sessions); existing recording.mp4 left in place."
                )
            if (
                "a11y" in (getattr(args, "observation_type", "") or "")
                or getattr(args, "eval_mode", "") in ("gui-a11y", "gui-screenshot-a11y")
            ):
                logger.warning(
                    "[resume] a11y observation mode: replayed history entries are regenerated "
                    "from the live accessibility tree after each replayed step. Use --no-resume "
                    "if you need a completely fresh a11y trajectory.",
                )
            try:
                obs, done, step_idx = _replay_gui_steps(
                    env, agent, groups,
                    sleep_seconds=_RESUME_SLEEP_SECONDS,
                    bash_timeout=getattr(args, "bash_timeout", _BASH_TIMEOUT_DEFAULT),
                )
                logger.info(
                    "[resume] replayed %d step(s) for %s; resuming from step %d "
                    "(done_from_replay=%s)",
                    step_idx, example.get("id", "<unknown>"), step_idx + 1, done,
                )
            except Exception as exc:
                logger.warning(
                    "[resume] replay raised %s: %s; falling back to fresh run",
                    type(exc).__name__, exc,
                )
                _purge_example_dir(example_result_dir)
                env.reset(task_config=example)
                try:
                    agent.reset(runtime_logger, vm_ip=env.vm_ip)
                except Exception:
                    agent.reset(vm_ip=env.vm_ip)
                time.sleep(180)
                obs = env._get_obs()
                done = False
                step_idx = 0
                if getattr(args, "record_video", False):
                    env.controller.start_recording()
                    record_video_active = True
    else:
        if getattr(args, "record_video", False):
            env.controller.start_recording()
            record_video_active = True

    while not done and step_idx < max_steps:
        response, actions = agent.predict(
            instruction,
            obs
        )
        # Per-step LLM telemetry: independent file from traj.jsonl so retry
        # storms (LLM_RETRIES=512) can't bloat single trajectory rows.
        _flush_llm_attempts(agent, example_result_dir, step_idx + 1)
        # Persist the first system / user prompt actually sent to the model,
        # plus the initial screenshot that backs the first user turn. Guarded
        # with hasattr so non-PromptAgent callers stay unaffected.
        if step_idx == 0:
            sys_text = getattr(agent, "_first_system_text", None)
            user_text = getattr(agent, "_first_user_text", None)
            if sys_text:
                with open(os.path.join(example_result_dir, "system_prompt.txt"), "w", encoding="utf-8") as f:
                    f.write(sys_text)
            if user_text:
                with open(os.path.join(example_result_dir, "first_user_prompt.txt"), "w", encoding="utf-8") as f:
                    f.write(user_text)
            initial_screenshot = obs.get("screenshot") if isinstance(obs, dict) else None
            if initial_screenshot:
                with open(os.path.join(example_result_dir, "initial_screenshot.png"), "wb") as f:
                    f.write(initial_screenshot)
            if getattr(args, "eval_mode", "") in ("gui-a11y", "gui-screenshot-a11y") and isinstance(obs, dict):
                initial_a11y_tree = obs.get("accessibility_tree")
                if initial_a11y_tree:
                    with open(os.path.join(example_result_dir, "initial_a11y_tree.xml"), "w", encoding="utf-8") as f:
                        f.write(initial_a11y_tree)
        for action in actions:
            # Capture the timestamp before executing the action
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S%f")
            logger.info("Step %d: %s", step_idx + 1, action)
            # action is a (kind, payload) tuple from PromptAgent's
            # parse_typed_actions; kind tells us which budget-recovery hint to
            # emit on a hard timeout. Non-PromptAgent runners use their own
            # run_single_example_* helpers, so we don't need to defend against
            # raw str/dict shapes here.
            action_kind, action_payload = action
            try:
                obs, reward, done, info = env.step(
                    action,
                    args.sleep_after_execution,
                    bash_timeout=getattr(args, "bash_timeout", _BASH_TIMEOUT_DEFAULT),
                )
                hard_timeout = False
            except SandboxExecuteHardTimeoutError as exc:
                # Sandbox killed the action for exceeding the per-action
                # budget (120s, system-prompted to the model). Don't bubble
                # — let the model self-correct on the next turn. GUI mode has
                # no native text channel in the next obs, so route the
                # feedback through the agent's pending slot; PromptAgent.predict()
                # will prepend it to the next user message. Re-fetch obs
                # explicitly since env.step didn't return one. Break out of
                # the action loop so we don't apply any subsequent actions on
                # top of a half-killed command.
                logger.warning("env.step hit per-action budget cap: %s", exc)
                if action_kind == "bash":
                    detach_hint = (
                        "Going forward, detach long bash operations via "
                        "`nohup CMD > /tmp/job.log 2>&1 < /dev/null & echo $! > /tmp/job.pid` "
                        "and poll `/tmp/job.log` or `kill -0 \"$(cat /tmp/job.pid)\"` in subsequent steps."
                    )
                else:
                    # pyautogui / python — same Popen-detach pattern.
                    detach_hint = (
                        "Going forward, detach long operations via "
                        "`subprocess.Popen(\"nohup CMD > /tmp/job.log 2>&1 < /dev/null &\", shell=True)` "
                        "and poll progress in subsequent steps."
                    )
                agent._pending_runtime_error = (
                    f"Your previous `{action_kind}` action was killed by the sandbox: "
                    "it exceeded the 120s per-action wall-clock budget. "
                    "Only the immediate child was terminated; any grandchild "
                    "processes (e.g. anything launched via subprocess.run / "
                    "os.system / a bash `&` fork) may still be running on the VM. "
                    "If you need a clean state before continuing, run "
                    "`subprocess.run(['pkill', '-f', '<pattern>'])` "
                    "or check with `pgrep -f <pattern>`. " + detach_hint
                )
                obs = env._get_obs()
                reward, done, info = 0.0, False, {"hard_timeout": True}
                hard_timeout = True

            logger.info("Reward: %.2f", reward)
            logger.info("Done: %s", done)
            # Save screenshot and trajectory information
            screenshot_file = f"step_{step_idx + 1}_{action_timestamp}.png"
            with open(os.path.join(example_result_dir, screenshot_file),
                      "wb") as _f:
                _f.write(obs['screenshot'])
            a11y_tree_file = None
            if getattr(args, "eval_mode", "") in ("gui-a11y", "gui-screenshot-a11y"):
                a11y_tree = obs.get("accessibility_tree") if isinstance(obs, dict) else None
                if a11y_tree:
                    a11y_tree_file = f"step_{step_idx + 1}_{action_timestamp}_a11y_tree.xml"
                    with open(os.path.join(example_result_dir, a11y_tree_file), "w", encoding="utf-8") as _f:
                        _f.write(a11y_tree)
            with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
                traj_row = {
                    "step_num": step_idx + 1,
                    "action_timestamp": action_timestamp,
                    "action": {"kind": action_kind, "code": action_payload},
                    "response": response,
                    "reward": reward,
                    "done": done,
                    "info": info,
                    "screenshot_file": screenshot_file,
                }
                if a11y_tree_file:
                    traj_row["accessibility_tree_file"] = a11y_tree_file
                f.write(json.dumps(traj_row))
                f.write("\n")
            if hard_timeout:
                # Skip any remaining actions in this turn — VM state is
                # uncertain (zombie descendants may be running), let the
                # model see the timeout feedback and replan.
                break
            if done:
                logger.info("The episode is done.")
                break
        if not actions:
            # Empty action list — typically a parse failure caught by the
            # agent (model emitted unparseable output; we feed the error back
            # next turn so it can self-correct). The env was not stepped, so
            # nothing else writes a row for this step. Persist a sentinel
            # entry so the trajectory has an unbroken step_num sequence and
            # downstream tooling (truncated detection, post-mortem inspection)
            # can see what happened.
            parse_error = getattr(agent, "_pending_parse_error", None)
            with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
                f.write(json.dumps({
                    "step_num": step_idx + 1,
                    "action": None,
                    "response": response,
                    "parse_error": parse_error,
                    "done": False,
                }))
                f.write("\n")
        step_idx += 1
    time.sleep(20) # Wait for the environment to settle
    result = env.evaluate()
    logger.info("Result: %.2f", result)
    scores.append(result)
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{result}\n")

    # Log task completion to results.json
    log_task_completion(example, result, example_result_dir, args)

    # Only end_recording if we actually started one this session — resume mode
    # skips start_recording so a recording end would error out.
    if record_video_active:
        env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))


def setup_logger(example, example_result_dir):
    runtime_logger = logging.getLogger(f"desktopenv.example.{example['id']}")
    runtime_logger.setLevel(logging.DEBUG)
    runtime_logger.addHandler(logging.FileHandler(os.path.join(example_result_dir, "runtime.log")))
    return runtime_logger


# ---- terminal mode (PromptAgent observation_type="terminal") ---------------
# Output cap per stdout/stderr stream before a "[...truncated]" marker is
# appended. Keeps any single command from blowing up the model's context.
_TERMINAL_OUTPUT_CAP = 8192
# Per-bash-block timeout passed to controller.run_bash_script. Shared default
# for both GUI obs's <action type="bash"> and terminal obs's bash action;
# overridable from the launcher via args.bash_timeout (registered in
# _engiworld_runtime.add_common_engiworld_args).
_BASH_TIMEOUT_DEFAULT = 120
_WAIT_DEFAULT_SECONDS = 120.0


def _coerce_wait_seconds(value, default=_WAIT_DEFAULT_SECONDS):
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return default


def _truncate(text, cap):
    if not text:
        return ""
    if len(text) <= cap:
        return text
    return text[:cap] + f"\n[...truncated, total {len(text)} bytes]"


def _detect_image_ext(data):
    try:
        with Image.open(BytesIO(data)) as im:
            return (im.format or "PNG").lower()
    except Exception:
        return "bin"


def run_single_example_terminal(agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    """Run a task in terminal mode: bash + readimg, no screenshot in model context.

    The agent emits ```bash``` blocks (executed via controller.run_bash_script)
    and ```readimg <path>``` blocks (resolved via controller.get_file). bash
    output goes back as text in the next observation; readimg files come back
    as image_url content. WAIT/DONE/FAIL retain their usual semantics.

    Windows tasks rely on the sandbox image exposing Git Bash as ``bash`` for
    ``/run_bash_script``; if that is missing, the action fails as runtime
    feedback instead of being skipped here.
    """
    runtime_logger = setup_logger(example, example_result_dir)

    env.reset(task_config=example)
    try:
        agent.reset(runtime_logger, vm_ip=env.vm_ip)
    except Exception:
        agent.reset(vm_ip=env.vm_ip)

    time.sleep(180)  # Same boot wait as the GUI runner — snapshot revert + VM ready.

    obs = {"bash_runs": [], "images": []}
    done = False
    step_idx = 0
    bash_timeout = getattr(args, "bash_timeout", _BASH_TIMEOUT_DEFAULT)
    text_only_cli = getattr(args, "eval_mode", "") == "cli-text"

    # Step-level resume (terminal mode): replay recorded bash/readimg actions
    # so the agent picks up where it left off. Same contract as GUI mode.
    resume_attempted = (
        getattr(args, "resume", False)
        and os.path.isfile(os.path.join(example_result_dir, "traj.jsonl"))
    )
    record_video_active = False
    if resume_attempted:
        groups = _read_traj_for_resume(example_result_dir)
        if not groups:
            logger.warning(
                "[resume] traj.jsonl unparseable for %s; falling back to fresh run",
                example.get("id", "<unknown>"),
            )
            _purge_example_dir(example_result_dir)
            if getattr(args, "record_video", False):
                env.controller.start_recording()
                record_video_active = True
        else:
            if getattr(args, "record_video", False):
                logger.warning(
                    "[resume] record_video disabled in resume mode (cannot stitch "
                    "mp4 across sessions); existing recording.mp4 left in place."
                )
            try:
                obs, done, step_idx = _replay_cli_steps(
                    env, agent, groups,
                    sleep_seconds=_RESUME_SLEEP_SECONDS,
                    bash_timeout=bash_timeout,
                    task_config=example,
                    text_only=text_only_cli,
                )
                logger.info(
                    "[resume] replayed %d step(s) for %s; resuming from step %d "
                    "(done_from_replay=%s)",
                    step_idx, example.get("id", "<unknown>"), step_idx + 1, done,
                )
            except Exception as exc:
                logger.warning(
                    "[resume] replay raised %s: %s; falling back to fresh run",
                    type(exc).__name__, exc,
                )
                _purge_example_dir(example_result_dir)
                env.reset(task_config=example)
                try:
                    agent.reset(runtime_logger, vm_ip=env.vm_ip)
                except Exception:
                    agent.reset(vm_ip=env.vm_ip)
                time.sleep(180)
                obs = {"bash_runs": [], "images": []}
                done = False
                step_idx = 0
                if getattr(args, "record_video", False):
                    env.controller.start_recording()
                    record_video_active = True
    else:
        if getattr(args, "record_video", False):
            env.controller.start_recording()
            record_video_active = True

    while not done and step_idx < max_steps:
        response, actions = agent.predict(instruction, obs)
        _flush_llm_attempts(agent, example_result_dir, step_idx + 1)

        # Persist initial prompt artifacts on the first turn.
        if step_idx == 0:
            sys_text = getattr(agent, "_first_system_text", None)
            user_text = getattr(agent, "_first_user_text", None)
            if sys_text:
                with open(os.path.join(example_result_dir, "system_prompt.txt"), "w", encoding="utf-8") as f:
                    f.write(sys_text)
            if user_text:
                with open(os.path.join(example_result_dir, "first_user_prompt.txt"), "w", encoding="utf-8") as f:
                    f.write(user_text)

        actions = actions or []
        exec_blocks = [(k, p) for k, p in actions if k in ("bash", "python")]
        readimg_paths = [] if text_only_cli else [p for k, p in actions if k == "readimg"]
        signals = [(k, p) for k, p in actions if k in ("WAIT", "DONE", "FAIL")]
        terminal_signal = signals[0][0] if signals else None
        terminal_signal_payload = signals[0][1] if signals else ""

        # 1) Run bash/python blocks in order, capture each result.
        bash_runs = []
        for i, (kind, script) in enumerate(exec_blocks):
            ts = datetime.datetime.now().strftime("%Y%m%d@%H%M%S%f")
            first_line = (script.splitlines() or [""])[0][:120]
            logger.info("Step %d %s[%d]: %s", step_idx + 1, kind, i + 1, first_line)
            try:
                if kind == "python":
                    validate_cli_action(kind, script, example, text_only=text_only_cli)
                    result = env.controller.run_python_script(script, timeout=bash_timeout)
                else:
                    validate_cli_action(kind, script, example, text_only=text_only_cli)
                    result = env.controller.run_bash_script(script, timeout=bash_timeout)
            except SandboxExecuteHardTimeoutError as exc:
                # Sandbox killed our command for exceeding the per-action
                # budget (120s, system-prompted to the model). Surface this
                # as a regular terminal-run error so the model sees it inline as
                # next turn's stderr and can self-correct (the system prompt
                # already tells it about the budget and how to detach long
                # work). Note: only the immediate child was killed on the
                # server (subprocess.run semantics), so any grandchildren
                # the command spawned may still be running on the VM — the
                # message below points the model at pkill/pgrep if a clean
                # state is required before retrying.
                logger.warning("%s action hit per-action budget cap: %s", kind, exc)
                result = {
                    "output": "",
                    "error": (
                        f"[{kind} action killed by sandbox: exceeded 120s "
                        "per-action wall-clock budget]\n"
                        "Only the immediate child was terminated; any "
                        "grandchild processes the command spawned may still "
                        "be running on the VM. Use `pgrep -f <pattern>` / "
                        "`pkill -f <pattern>` if you need a clean state, "
                        "or detach long-running work next time via "
                        "`nohup CMD > /tmp/job.log 2>&1 < /dev/null & "
                        "echo $! > /tmp/job.pid`."
                    ),
                    "returncode": -1,
                }
            except CliPolicyViolation as exc:
                logger.warning("%s action rejected by CLI policy: %s", kind, exc)
                result = {
                    "output": "",
                    "error": f"[{kind} action rejected by CLI integrity policy: {exc}]",
                    "returncode": -2,
                }
            except Exception as exc:
                logger.error("%s action failed: %s", kind, exc)
                result = {"output": "", "error": f"[{kind} action raised: {exc}]", "returncode": -1}
            stdout_full = result.get("output") or ""
            stderr_full = result.get("error") or ""
            bash_runs.append({
                "command": script if kind == "bash" else f"[python]\n{script}",
                "stdout": _truncate(stdout_full, _TERMINAL_OUTPUT_CAP),
                "stderr": _truncate(stderr_full, _TERMINAL_OUTPUT_CAP),
                "returncode": result.get("returncode", result.get("return_code", -1)),
                "timestamp": ts,
            })

        # 2) Resolve readimg paths (after bash, so a freshly-written file is fetchable).
        next_images = []
        for path in readimg_paths:
            try:
                data = env.controller.get_file(path)
            except Exception as exc:
                logger.warning("readimg %s failed: %s", path, exc)
                next_images.append((f"{path} [error: {exc}]", b""))
                continue
            if not data:
                next_images.append((f"{path} [error: empty or missing]", b""))
                continue
            # Verify it actually decodes as an image; otherwise the model would
            # see a phantom image_url that downstream APIs will 400 on.
            try:
                with Image.open(BytesIO(data)) as im:
                    im.verify()
            except Exception:
                next_images.append((f"{path} [error: not a recognisable image]", b""))
                continue
            next_images.append((path, data))

        # 3) Apply terminal signal.
        if terminal_signal == "WAIT":
            time.sleep(_coerce_wait_seconds(terminal_signal_payload))
        elif terminal_signal in ("DONE", "FAIL"):
            done = True

        # 4) Persist trajectory + per-step artifacts.
        with open(os.path.join(example_result_dir, "traj.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "step_num": step_idx + 1,
                "response": response,
                "bash_runs": bash_runs,
                "readimg": [{"path": p, "ok": isinstance(d, (bytes, bytearray)) and bool(d)}
                            for p, d in next_images],
                "terminal_signal": terminal_signal,
                "terminal_signal_payload": terminal_signal_payload,
                "done": done,
            }, ensure_ascii=False))
            f.write("\n")
        for i, r in enumerate(bash_runs):
            with open(
                os.path.join(example_result_dir, f"step_{step_idx + 1}_bash_{i + 1}_{r['timestamp']}.txt"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write(f"$ {r['command']}\n[returncode={r['returncode']}]\n")
                f.write(f"[stdout]\n{r['stdout']}\n")
                f.write(f"[stderr]\n{r['stderr']}\n")
        for i, (path, data) in enumerate(next_images):
            if not isinstance(data, (bytes, bytearray)) or not data:
                continue
            ext = _detect_image_ext(bytes(data))
            with open(
                os.path.join(example_result_dir, f"step_{step_idx + 1}_readimg_{i + 1}.{ext}"),
                "wb",
            ) as f:
                f.write(data)

        # 5) Build next obs and advance.
        obs = {"bash_runs": bash_runs, "images": next_images}

        if done:
            logger.info("Episode done (signal=%s).", terminal_signal)
            break

        if not bash_runs and not next_images and terminal_signal is None:
            logger.warning(
                "Step %d: model produced no actionable blocks; advancing anyway.",
                step_idx + 1,
            )

        step_idx += 1

    time.sleep(20)
    result = env.evaluate()
    logger.info("Result: %.2f", result)
    scores.append(result)
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{result}\n")
    log_task_completion(example, result, example_result_dir, args)
    # Skip end_recording if we never started one (resume mode).
    if record_video_active:
        env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))

def run_single_example_human(env, example, max_steps, instruction, args, example_result_dir, scores):
    runtime_logger = setup_logger(example, example_result_dir)
    env.reset(task_config=example)
    time.sleep(120) # Wait for the environment to be ready
    obs = env._get_obs() # Get the initial observation
    
    # Save initial screenshot
    with open(os.path.join(example_result_dir, "initial_state.png"), "wb") as _f:
        _f.write(obs['screenshot'])
    
    # Save trajectory information
    with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
        f.write(json.dumps({
            "instruction": instruction,
            "initial_state": "initial_state.png"
        }))
        f.write("\n")
    
    # Evaluate the result
    result = env.evaluate()
    logger.info("Result: %.2f", result)
    scores.append(result)
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{result}\n")


def run_single_example_kimi(agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    runtime_logger = setup_logger(example, example_result_dir)
    agent.reset(runtime_logger)
    env.reset(task_config=example)
    time.sleep(120) # Wait for the environment to be ready
    obs = env._get_obs() # Get the initial observation
    done = False
    step_idx = 0
    if getattr(args, "record_video", False):
        env.controller.start_recording()
    while not done and step_idx < max_steps:
        response, actions, info_dict = agent.predict(instruction, obs)

        logger.info(f"Got Action: {actions}")
        # Break if no actions. computer_13 路径下 actions[0] 是 dict，不能直接 .lower()。
        first_action = actions[0] if actions else None
        if (
            not actions
            or len(actions) == 0
            or first_action == ""
            or (isinstance(first_action, str) and first_action.lower().startswith("error"))
        ):
            break

        for action in actions:
            # Capture the timestamp before executing the action
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
            logger.info("Step %d: %s", step_idx + 1, action)
            
            obs, reward, done, info = env.step(action, args.sleep_after_execution)

            logger.info(f"Action {action} executed, reward: {reward}, done: {done}")
            # Save screenshot and trajectory information
            with open(os.path.join(example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"),
                      "wb") as _f:
                _f.write(obs['screenshot'])

            with open(os.path.join(example_result_dir, "traj.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "step_num": step_idx + 1,
                    "action": action,
                    "natural_language_action": info_dict.get("action"),
                    "action_timestamp": action_timestamp,
                    "response": response,
                    "reward": reward,
                    "done": done,
                    "info": info,
                    "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png"
                }, ensure_ascii=False))
                f.write("\n")
            if done:
                logger.info("The episode is done.")
                break
        step_idx += 1

    time.sleep(30) # Wait for the environment to settle
    result = env.evaluate()
    logger.info("Result: %.2f", result)
    scores.append(result)
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{result}\n")
    if getattr(args, "record_video", False):
        env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))

def run_single_example_agi(agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    runtime_logger = setup_logger(example, example_result_dir)
    agent.reset(runtime_logger)
    env.reset(task_config=example)
    time.sleep(120) # Wait for the environment to be ready
    obs = env._get_obs() # Get the initial observation
    done = False
    step_idx = 0
    env.controller.start_recording()
    while not done and step_idx < max_steps:
        response, actions = agent.predict(
            instruction,
            obs
        )

        done = not response.get('state_correct', False)

        for action in actions:
            # Capture the timestamp before executing the action
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
            logger.info("Step %d: %s", step_idx + 1, action)
            obs, reward, done, info, step_info = agent.step(action)

            if not done:
                if not response.get('state_correct', False):
                    done = True

            logger.info("Reward: %.2f", reward)
            logger.info("Done: %s", done)
            # Save screenshot and trajectory information
            with open(os.path.join(example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"),
                      "wb") as _f:
                _f.write(obs['screenshot'])

            # Remove pending checks if they exist which will cause issues with json serialization
            if action.get('pending_checks', None):
                del action['pending_checks']

            with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
                f.write(json.dumps({
                    "step_num": step_idx + 1,
                    "action_timestamp": action_timestamp,
                    "action": action,
                    "reward": reward,
                    "done": done,
                    "info": info,
                    "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png"
                }))
                f.write("\n")
            if done:
                logger.info("The episode is done.")
                break
        step_idx += 1
    result = env.evaluate()
    logger.info("Result: %.2f", result)
    scores.append(result)
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{result}\n")
    env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))


def run_single_example_openaicua(agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    runtime_logger = setup_logger(example, example_result_dir)
    agent.reset(runtime_logger)
    env.reset(task_config=example)
    time.sleep(120) # Wait for the environment to be ready
    obs = env._get_obs() # Get the initial observation
    done = False
    step_idx = 0
    env.controller.start_recording()
    while not done and step_idx < max_steps:
        response, actions = agent.predict(
            instruction,
            obs
        )

        done = not response.get('state_correct', False)

        for action in actions:
            # Capture the timestamp before executing the action
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
            logger.info("Step %d: %s", step_idx + 1, action)
            obs, reward, done, info, step_info = agent.step(action)

            if not done:
                if not response.get('state_correct', False):
                    done = True

            logger.info("Reward: %.2f", reward)
            logger.info("Done: %s", done)
            # Save screenshot and trajectory information
            with open(os.path.join(example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"),
                      "wb") as _f:
                _f.write(obs['screenshot'])

            # Remove pending checks if they exist which will cause issues with json serialization
            if action.get('pending_checks', None):
                del action['pending_checks']

            with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
                f.write(json.dumps({
                    "step_num": step_idx + 1,
                    "action_timestamp": action_timestamp,
                    "action": action,
                    "reward": reward,
                    "done": done,
                    "info": info,
                    "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png"
                }))
                f.write("\n")
            if done:
                logger.info("The episode is done.")
                break
        step_idx += 1
    result = env.evaluate()
    logger.info("Result: %.2f", result)
    scores.append(result)
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{result}\n")
    env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))


def run_single_example_gpt54(agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    runtime_logger = setup_logger(example, example_result_dir)
    agent.reset(runtime_logger)
    env.reset(task_config=example)
    time.sleep(120) # Wait for the environment to be ready
    obs = env._get_obs() # Get the initial observation
    done = False
    step_idx = 0
    if getattr(args, "record_video", False):
        env.controller.start_recording()
    while not done and step_idx < max_steps:
        response, actions = agent.predict(
            instruction,
            obs
        )

        logger.info("Agent response: %s", response.get("response", ""))
        logger.info("Agent state_correct: %s", response.get("state_correct", False))
        logger.info("Agent model_usage: %s", response.get("model_usage", {}))

        done = not response.get('state_correct', False)

        for action in actions:
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
            logger.info("Step %d: %s", step_idx + 1, action)
            obs, reward, done, info, step_info = agent.step(action)

            if not done:
                if not response.get('state_correct', False):
                    done = True

            controller_result = info.get("controller_result", {}) if isinstance(info, dict) else {}
            if controller_result:
                logger.info("Controller returncode: %s", controller_result.get("returncode"))
                controller_error = (controller_result.get("error") or "").strip()
                controller_output = (controller_result.get("output") or "").strip()
                if controller_error:
                    logger.warning("Controller stderr: %s", controller_error)
                elif controller_output:
                    logger.info("Controller stdout: %s", controller_output)

            logger.info("Reward: %.2f", reward)
            logger.info("Done: %s", done)
            with open(os.path.join(example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"),
                      "wb") as _f:
                _f.write(obs['screenshot'])

            if action.get('pending_checks', None):
                del action['pending_checks']

            with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
                f.write(json.dumps({
                    "step_num": step_idx + 1,
                    "action_timestamp": action_timestamp,
                    "response": response.get("response", ""),
                    "state_correct": response.get("state_correct", False),
                    "model_usage": response.get("model_usage", {}),
                    "messages": response.get("messages", []),
                    "action": action,
                    "reward": reward,
                    "done": done,
                    "info": info,
                    "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png"
                }))
                f.write("\n")
            if done:
                logger.info("The episode is done.")
                break
        step_idx += 1
    time.sleep(20) # Wait for the environment to settle
    result = env.evaluate()
    logger.info("Result: %.2f", result)
    scores.append(result)
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{result}\n")
    if getattr(args, "record_video", False):
        env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))

def run_single_example_opencua(agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    runtime_logger = setup_logger(example, example_result_dir)
    agent.reset(runtime_logger)
    env.reset(task_config=example)
    time.sleep(120) # Wait for the environment to be ready
    obs = env._get_obs() # Get the initial observation
    done = False
    step_idx = 0
    env.controller.start_recording()
    while not done and step_idx < max_steps:
        response, actions, info_dict = agent.predict(instruction, obs)

        logger.info(f"Got Action: {actions}")
        # Breack if no actions
        if not actions or len(actions)==0 or actions[0]=="" or actions[0].lower().startswith("error"): 
            break

        for action in actions:
            # Capture the timestamp before executing the action
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
            logger.info("Step %d: %s", step_idx + 1, action)
            
            obs, reward, done, info = env.step(action, args.sleep_after_execution)

            logger.info(f"Action {action} executed, reward: {reward}, done: {done}")
            # Save screenshot and trajectory information
            with open(os.path.join(example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"),
                      "wb") as _f:
                _f.write(obs['screenshot'])

            with open(os.path.join(example_result_dir, "traj.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "step_num": step_idx + 1,
                    "action": action,
                    "natural_language_action": info_dict.get("action"),
                    "action_timestamp": action_timestamp,
                    "response": response,
                    "reward": reward,
                    "done": done,
                    "info": info,
                    "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png"
                }, ensure_ascii=False))
                f.write("\n")
            if done:
                logger.info("The episode is done.")
                break
        step_idx += 1

    time.sleep(20) # Wait for the environment to settle
    result = env.evaluate()
    logger.info("Result: %.2f", result)
    scores.append(result)
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{result}\n")
    env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))

def run_single_example_autoglm(agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    runtime_logger = setup_logger(example, example_result_dir)
    try:
        agent.reset(runtime_logger)
    except Exception as e:
        agent.reset()

    env.reset(task_config=example)

    time.sleep(120) # Wait for the environment to be ready
    obs = env._get_obs() # Get the initial observation
    done = False
    step_idx = 0
    if getattr(args, "record_video", False):
        env.controller.start_recording()
    while not done and step_idx < max_steps:
        response, actions = agent.predict(
            instruction,
            obs
        )
        for action in actions:
            # Capture the timestamp before executing the action
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
            logger.info("Step %d: %s", step_idx + 1, action)
            obs, reward, done, info = env.step(action, args.sleep_after_execution)

            logger.info("Reward: %.2f", reward)
            logger.info("Done: %s", done)
            # Save screenshot and trajectory information
            with open(os.path.join(example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"),
                      "wb") as _f:
                _f.write(obs['screenshot'])
            with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
                f.write(json.dumps({
                    "step_num": step_idx + 1,
                    "action_timestamp": action_timestamp,
                    "action": action,
                    "response": response,
                    "reward": reward,
                    "done": done,
                    "info": info,
                    "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png"
                }))
                f.write("\n")
                
            if done:
                logger.info("The episode is done.")
                break
        
        # Invalid Action
        if not actions:
            obs = env._get_obs() # update observation
            
        step_idx += 1
    
    if not done: # not completed the task yet
        env.action_history.append('FAIL')
    
    result = env.evaluate()
    logger.info("Result: %.2f", result)
    scores.append(result)
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{result}\n")
    if getattr(args, "record_video", False):
        env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))

def run_single_example_mano(agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    runtime_logger = setup_logger(example, example_result_dir)
    agent.reset(runtime_logger)
    env.reset(task_config=example)
    time.sleep(120) # Wait for the environment to be ready
    obs = env._get_obs() # Get the initial observation
    done = False
    step_idx = 0
    env.controller.start_recording()
    
    with open(os.path.join(example_result_dir, f"step_0.png"),
      "wb") as _f:
        _f.write(obs['screenshot'])
    while not done and step_idx < max_steps:
        response, actions = agent.predict(
            instruction,
            obs
        )
        if len(actions) > 1:
            if (("pyautogui.hotkey('shift')" in actions[0] or "pyautogui.hotkey('ctrl')" in actions[0]) 
                and "pyautogui.click" in actions[1]):
                hotkey_type = 'shift' if "shift" in actions[0] else 'ctrl'
                action = f"pyautogui.keyDown('{hotkey_type}')\n{actions[1]}\npyautogui.keyUp('{hotkey_type}')"
                actions = [action]  
                
        for action in actions:
            # Capture the timestamp before executing the action
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
            logger.info("Step %d: %s", step_idx + 1, action)
            obs, reward, done, info = env.step(action, args.sleep_after_execution)

            logger.info("Reward: %.2f", reward)
            logger.info("Done: %s", done)
            # Save screenshot and trajectory information
            with open(os.path.join(example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"),
                      "wb") as _f:
                _f.write(obs['screenshot'])
            with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
                f.write(json.dumps({
                    "step_num": step_idx + 1,
                    "action_timestamp": action_timestamp,
                    "action": action,
                    "reward": reward,
                    "done": done,
                    "info": info,
                    "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png",
                    "response":response
                }))
                f.write("\n")
            if done:
                logger.info("The episode is done.")
                break
        step_idx += 1
    result = env.evaluate()
    logger.info("Result: %.2f", result)
    scores.append(result)
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{result}\n")
    env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))
    
def run_single_example_uipath(agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    runtime_logger = setup_logger(example, example_result_dir)
    try:
        agent.reset(runtime_logger)
    except Exception as e:
        agent.reset()

    env.reset(task_config=example)

    time.sleep(120) # Wait for the environment to be ready
    obs = env._get_obs() # Get the initial observation
    done = False
    step_idx = 0
    env.controller.start_recording()
    while not done and step_idx < max_steps:
        response, actions = agent.predict(
            instruction,
            obs,
            args,
            step_idx
        )
        for action in actions:
            # Capture the timestamp before executing the action
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
            logger.info("Step %d: %s", step_idx + 1, action)
            obs, reward, done, info = env.step(action, args.sleep_after_execution)

            logger.info("Reward: %.2f", reward)
            logger.info("Done: %s", done)
            # Save screenshot and trajectory information
            with open(os.path.join(example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"),
                      "wb") as _f:
                _f.write(obs['screenshot'])
            with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
                f.write(json.dumps({
                    "step_num": step_idx + 1,
                    "action_timestamp": action_timestamp,
                    "action": action,
                    "response": response,
                    "reward": reward,
                    "done": done,
                    "info": info,
                    "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png"
                }))
                f.write("\n")
            if done:
                logger.info("The episode is done.")
                break
        step_idx += 1
    result = env.evaluate()
    logger.info("Result: %.2f", result)
    scores.append(result)
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{result}\n")
    env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))


from mm_agents.os_symphony.utils.common_utils import draw_coordinates
from mm_agents.os_symphony.utils.process_context import set_current_result_dir


logger = logging.getLogger("desktopenv.experiment")

def run_single_example_os_symphony(agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    set_current_result_dir(example_result_dir)
    
    agent.reset(result_dir=example_result_dir)
    env.reset(task_config=example)
    time.sleep(30) # Wait for the environment to be ready
    obs = env._get_obs() # Get the initial observation
    done = False
    step_idx = 0
    # env.controller.start_recording()
    start_time = time.time()

    while not done and step_idx < max_steps:
        response, actions = agent.predict(
            instruction,
            obs,
            step_idx == max_steps - 1
        )
        for action in actions:
            # Save screenshot and trajectory information
            if "reflection" in response and response["reflection"].get("is_milestone"):
                img_name = f"step_{step_idx + 1}_milestone.png"
            else:
                img_name = f"step_{step_idx + 1}.png"
                
            with open(os.path.join(example_result_dir, img_name),
                      "wb") as _f:
                _f.write(obs['screenshot'])
            if "coordinates" in response and response["coordinates"]:
                draw_coordinates(
                    image_bytes=obs['screenshot'], 
                    coordinates=response["coordinates"], 
                    save_path=os.path.join(example_result_dir, img_name[:-4] + "_draw.png")
                )

            logger.info("Step %d: %s", step_idx + 1, action)
            obs, reward, done, info = env.step(action, args.sleep_after_execution)
            logger.info("Done: %s", done)

            with open(os.path.join(example_result_dir, "traj.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "instruction": instruction,
                    "step_num": step_idx + 1,
                    "action": action,
                    "response": response,
                    "done": done,
                    "info": info,
                    "screenshot_file": img_name
                }))
                f.write("\n")
            with open(os.path.join(example_result_dir, f"traj_{step_idx+1}.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "step_num": step_idx + 1,
                    "action": action,
                    "response": response,
                    "done": done,
                    "info": info,
                    "screenshot_file": img_name
                }, f, indent=4, ensure_ascii=False)
            if done:
                logger.info("The episode is done.")
                time.sleep(60)
                break
        step_idx += 1
    end_time = time.time()
    result = float(env.evaluate())
    logger.info("Result: %.2f", result)
    scores.append(result)
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{result}\n")

    with open(os.path.join(example_result_dir, "time.txt"), "w", encoding="utf-8") as f:
        f.write(f"{end_time-start_time:.2f}\n")


def run_single_example_evocua(agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    """
    Unified run function for EvoCUAAgent (supporting both S1 and S2 modes).
    """
    runtime_logger = setup_logger(example, example_result_dir)
    
    # Reset Environment
    env.reset(task_config=example)
    
    # Reset Agent
    # Handle agent reset signature differences if any
    try:
        agent.reset(runtime_logger, vm_ip=env.vm_ip)
    except Exception:
        try:
            agent.reset(runtime_logger)
        except Exception:
            agent.reset()

    time.sleep(120) # Wait for the environment to be ready
    obs = env._get_obs() # Get the initial observation
    done = False
    step_idx = 0

    env.controller.start_recording()
    while not done and step_idx < max_steps:
        # EvoCUAAgent.predict unified signature: returns (response, actions)
        # It handles both modes internally.
        predict_res = agent.predict(instruction, obs)
        
        # Check return signature logic
        if len(predict_res) == 3:
            # Compatibility with S1 original signature if agent was updated to match
            response, actions, info_dict = predict_res
        else:
            response, actions = predict_res
            info_dict = {}

        logger.info(f"Step {step_idx + 1} Actions: {actions}")
        
        # Break if no actions (fail-safe)
        if not actions or (len(actions) == 1 and (actions[0] == "" or "error" in actions[0].lower())):
             # Allow "FAIL" or "DONE" to process through execution loop if agent outputs them as actions
             if not (actions and actions[0] in ["FAIL", "DONE"]):
                 logger.warning("No valid actions returned. Breaking loop.")
                 break

        for action in actions:
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S%f")
            logger.info("Executing action: %s", action)
            
            # Execute
            obs, reward, done, info = env.step(action, args.sleep_after_execution)
            
            logger.info("Reward: %.2f", reward)
            logger.info("Done: %s", done)
            
            # Save screenshot
            screenshot_file = f"step_{step_idx + 1}_{action_timestamp}.png"
            with open(os.path.join(example_result_dir, screenshot_file), "wb") as _f:
                _f.write(obs['screenshot'])
            
            # Log Trajectory
            log_entry = {
                "step_num": step_idx + 1,
                "action_timestamp": action_timestamp,
                "action": action,
                "response": response,
                "reward": reward,
                "done": done,
                "info": info,
                "screenshot_file": screenshot_file
            }
            # Add natural language info if available (S1 style)
            if info_dict:
                log_entry["natural_language_action"] = info_dict.get("action")
            
            with open(os.path.join(example_result_dir, "traj.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False))
                f.write("\n")
                
            if done:
                logger.info("The episode is done.")
                break
        
        step_idx += 1
        
    time.sleep(20) # Wait for environment to settle
    result = env.evaluate()
    logger.info("Result: %.2f", result)
    scores.append(result)
    
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{result}\n")
    
    log_task_completion(example, result, example_result_dir, args)

    env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))


def run_single_example_mobileagent_v3(agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    """
    Specialized run function for MobileAgent V3.
    
    This agent has a different interface where it calls agent.step() directly
    which internally handles prediction and execution.
    """
    runtime_logger = setup_logger(example, example_result_dir)
    try:
        agent.reset(runtime_logger)
    except:
        agent.reset()
    env.reset(task_config=example)
    time.sleep(120) # Wait for the environment to be ready
    obs = env._get_obs() # Get the initial observation

    done = False
    step_idx = 0
    
    # save the first step
    action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
    with open(os.path.join(example_result_dir, f"step_{step_idx}_{action_timestamp}.png"), "wb") as _f:
        _f.write(obs['screenshot'])
    
    eval_flag = True
    env.controller.start_recording()
    while not done and step_idx < max_steps:
        global_state, action_code, step_status, reward, done = agent.step(instruction, env, args)
        action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")

        if step_status is False:
            eval_flag = False
            done = True
            reward = None
        else:
            obs = env._get_obs()
            with open(os.path.join(example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"),
                        "wb") as _f:
                _f.write(obs['screenshot'])
        with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
            f.write(json.dumps({
                "step_num": step_idx + 1,
                "step_status": step_status,
                "action_timestamp": action_timestamp,
                "action": action_code,
                "reward": reward,
                "done": done,
                "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png",
            }))
            f.write("\n")
        if done:    
            logger.info("The episode is done.")
            break
        step_idx += 1

    if eval_flag:
        result = env.evaluate()
        logger.info("Result: %.2f", result)
        scores.append(result)
        with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
            f.write(f"{result}\n")
    env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))


def run_single_example_vlaa_gui(agent, env, example, max_steps, instruction, args, example_result_dir, scores, verifier_agent=None):
    def _create_task_runtime_handler(example_result_dir):
        file_handler = logging.FileHandler(
            os.path.join(example_result_dir, "runtime.log"), encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            fmt="[%(asctime)s %(levelname)s %(module)s/%(lineno)d-%(processName)s] %(message)s"
        )
        file_handler.setFormatter(formatter)
        return file_handler


    def _attach_task_runtime_handler(file_handler, logger_names):
        attached_loggers = []
        for logger_name in logger_names:
            task_logger = logging.getLogger(logger_name)
            task_logger.addHandler(file_handler)
            attached_loggers.append(task_logger)
        return attached_loggers
    
    runtime_file_handler = _create_task_runtime_handler(example_result_dir)
    attached_loggers = _attach_task_runtime_handler(
        runtime_file_handler,
        [
            "desktopenv.experiment",
            "desktopenv.agent",
            "desktopenv.searcher_agent",
            "desktopenv.gemini_rotation",
        ],
    )
    try:
        agent.reset()
        env.reset(task_config=example)

        time.sleep(120)  # Wait for the environment to be ready
        obs = env._get_obs()  # Get the initial observation

        with open(os.path.join(example_result_dir, "step_0.png"), "wb") as _f:
            _f.write(obs["screenshot"])

        with open(
            os.path.join(example_result_dir, "instruction.txt"), "w", encoding="utf-8"
        ) as f:
            f.write(instruction)

        done = False
        step_idx = 0
        verifier_rejection_count = 0
        MAX_VERIFIER_REJECTIONS = 3
        traj_lines = [f"Task: {instruction}"]
        env.controller.start_recording()

        while not done and step_idx < max_steps:
            if step_idx == max_steps - 1:
                obs["is_last_step"] = True
            response, actions = agent.predict(instruction, obs)

            if not actions:
                logger.warning(
                    "Step %d: agent returned an empty action list", step_idx + 1
                )
                traj_lines.append(
                    f"Step {step_idx + 1}: EMPTY_ACTIONS (agent returned no actions)"
                )
                step_idx += 1
                continue

            first_action = str(actions[0]).strip()
            first_action_lower = first_action.lower()

            is_done = first_action_lower == "done"
            is_fail = first_action_lower == "fail"

            if is_done:
                if verifier_agent:
                    verdict = verifier_agent.verify_completion(
                        instruction=instruction,
                        observation=obs,
                        trajectory="\n".join(traj_lines),
                        executor_plan=response.get("executor_plan"),
                    )
                    if verdict.get("complete"):
                        logger.info("Verifier accepted completion.")
                        verifier_rejection_count = 0
                        env.step("DONE", args.sleep_after_execution)
                        break

                    verifier_rejection_count += 1
                    reason = verdict.get("reason", "")
                    missing = verdict.get("missing_steps", "")
                    logger.warning(
                        "Verifier rejected completion (%d/%d): %s | Missing: %s",
                        verifier_rejection_count,
                        MAX_VERIFIER_REJECTIONS,
                        reason,
                        missing,
                    )
                    traj_lines.append(
                        f"Verifier rejected DONE: reason={reason}, missing_steps={missing}"
                    )

                    if verifier_rejection_count >= MAX_VERIFIER_REJECTIONS:
                        _infeasibility_kws = (
                            "infeasible",
                            "not possible",
                            "impossible",
                            "cannot be completed",
                            "does not exist",
                            "not supported",
                            "call fail",
                            "bypassed",
                        )
                        _all_rejections = " ".join(
                            line for line in traj_lines if "Verifier rejected" in line
                        ).lower()
                        _recent_reasons = reason.lower() + " " + missing.lower()
                        _combined = _all_rejections + " " + _recent_reasons
                        if any(kw in _combined for kw in _infeasibility_kws):
                            logger.warning(
                                "Verifier rejected %d times with infeasibility signals - emitting FAIL.",
                                verifier_rejection_count,
                            )
                            traj_lines.append(
                                f"Step {step_idx + 1}: FAIL (verifier detected infeasibility after {verifier_rejection_count} rejections)"
                            )
                            env.step("FAIL", args.sleep_after_execution)
                        else:
                            logger.warning(
                                "Verifier rejected %d times consecutively - accepting DONE to avoid infinite loop.",
                                verifier_rejection_count,
                            )
                            env.step("DONE", args.sleep_after_execution)
                        break

                    agent.restart_after_failed_verification(
                        reason=reason,
                        missing_steps=missing,
                    )
                    step_idx += 1
                    continue
                else:
                    env.step("DONE", args.sleep_after_execution)
                    break

            if is_fail:
                logger.info("Agent reported FAIL at step %d", step_idx + 1)
                traj_lines.append(f"Step {step_idx + 1}: FAIL")
                env.step("FAIL", args.sleep_after_execution)
                break

            if first_action_lower == "next":
                step_idx += 1
                continue

            if first_action_lower == "wait":
                time.sleep(5)
                step_idx += 1
                continue

            verifier_rejection_count = 0
            for action in actions:
                action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
                logger.info("Step %d: %s", step_idx + 1, action)
                traj_lines.append(f"Step {step_idx + 1}: {action}")
                obs, reward, done, info = env.step(action, args.sleep_after_execution)

                logger.info("Reward: %.2f", reward)
                logger.info("Done: %s", done)
                info_str = str(info)
                info_str = (
                    info_str if len(info_str) <= 500 else info_str[:500] + "..."
                )
                traj_lines.append(
                    f"Result: reward={reward:.2f}, done={done}, info={info_str}"
                )
                # Save screenshot and trajectory information
                with open(
                    os.path.join(
                        example_result_dir,
                        f"step_{step_idx + 1}_{action_timestamp}.png",
                    ),
                    "wb",
                ) as _f:
                    _f.write(obs["screenshot"])

                response.update(
                    {
                        "step_num": step_idx + 1,
                        "action_timestamp": action_timestamp,
                        "action": action,
                        "reward": reward,
                        "done": done,
                        "info": info,
                        "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png",
                    }
                )
                with open(
                    os.path.join(example_result_dir, "traj.jsonl"),
                    "a",
                    encoding="utf-8",
                ) as f:
                    f.write(json.dumps(response, ensure_ascii=False))
                    f.write("\n")
                if done:
                    logger.info("The episode is done.")
                    break
            step_idx += 1

        time.sleep(20)
        result = env.evaluate()
        logger.info("Result: %.2f", result)
        scores.append(result)
        with open(
            os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8"
        ) as f:
            f.write(f"{result}\n")

        log_task_completion(example, result, example_result_dir, args)
        env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))
    finally:
        for attached_logger in attached_loggers:
            attached_logger.removeHandler(runtime_file_handler)
        runtime_file_handler.close()
