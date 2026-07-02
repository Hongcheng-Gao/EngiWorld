#!/usr/bin/env python3
"""Thread-safe results logging for OSWorld evaluations.

results.json layout (written under <result_dir>/<action_space>/<observation_type>/<model>/,
alongside args.json)::

    {
      "tasks": [
        {"application": "freecad", "task_id": "...-ubuntu",
         "status": "success", "score": 1.0, "step_count": 23,
         "failure_kind": "passed",
         "action_counts": {"wait": 1, "done": 1, "fail": 0, "python": 21,
           "bash": 0, "readimg": 0, "timeout": 0, "parse_error": 0},
         "timestamp": "..."},
        ...
      ],
      "by_application": {
        "freecad": {
          "count": 12, "passed_count": 6, "failed_count": 5, "error_count": 1,
          "failure_breakdown": {"passed": 6, "wrong_score": 3, "truncated": 2,
            "execute_timeout": 0, "sandbox_error": 1, "unknown_error": 0},
          "steps": {"count": 13, "min": 4, "q1": 9, "median": 17,
                     "q3": 28, "max": 45, "mean": 18.4},
          "actions": {
            "all":    {"wait":   {"count": ..., "min": ..., "q1": ...,
                                  "median": ..., "q3": ..., "max": ...,
                                  "mean": ...},
                       "done":    {...},
                       "fail":    {...},
                       "python":  {...},
                       "bash":    {...},
                       "readimg": {...},
                       "timeout":     {...},
                       "parse_error": {...}},
            "passed": {<same shape as "all">},
            "failed": {<same shape as "all">}
          }
        },
        ...
      },
      "overall": {
        "count": 50, "passed_count": 21, "failed_count": 26, "error_count": 3,
        "failure_breakdown": {"passed": ..., "wrong_score": ..., "truncated": ...,
          "execute_timeout": ..., "sandbox_error": ..., "unknown_error": ...},
        "steps": {"count": 53, "min": 1, "q1": ..., "median": ...,
                   "q3": ..., "max": 100, "mean": ...},
        "steps_by_score": {
          "score_zero": {"count": ..., "min": ..., ...},
          "score_one":  {"count": ..., "min": ..., ...}
        },
        "actions": {"all": {...}, "passed": {...}, "failed": {...}}
      }
    }

The ``action_counts`` block on each task tallies what the model actually
emitted and what the runtime did with it, recovered from ``traj.jsonl``:
``wait`` / ``done`` / ``fail`` count terminal signals (or, in GUI mode,
the corresponding sentinel actions); ``python`` counts pyautogui code
actions executed in GUI mode; ``bash`` counts bash blocks executed in
terminal mode and ``readimg`` counts readimg-tool requests in terminal
mode (so ``python`` is 0 under terminal mode, and ``bash`` / ``readimg``
are 0 under GUI mode, by construction); ``timeout`` counts sandbox-
induced per-action kills (``info.hard_timeout`` for GUI, ``"killed by
sandbox"`` in stderr for terminal bash); ``parse_error`` counts step
rows the runner wrote with a non-null ``parse_error`` field (model
produced unparseable output; the runner fed the error back next turn).

The ``actions`` aggregate at app/overall level is a five-number summary
of per-task ``action_counts[kind]`` values (mirroring the ``steps``
boxplot format), split into three buckets:

* ``all``    — every task with a recoverable ``action_counts``,
  including errored tasks (they emitted actions before crashing, same
  convention as ``steps``).
* ``passed`` — ``status == "success"`` and ``score == 1.0``.
* ``failed`` — ``status == "success"`` and ``score == 0.0``.

Errored tasks contribute to ``all`` but neither ``passed`` nor
``failed`` — same partition rule as ``steps_by_score``, so the bucket
distributions are directly comparable to the step distributions.

Score is binary (0.0 or 1.0). ``count`` is the total number of tasks
logged; it partitions exactly into ``passed_count`` (``status == "success"``
and score == 1.0), ``failed_count`` (``status == "success"`` and score
== 0.0), and ``error_count`` (``status == "error"`` — the run crashed).
By construction ``passed_count + failed_count + error_count == count``.
The ``steps`` block is a five-number boxplot summary built from per-task
``step_count`` values, and includes **both** successful and errored tasks
(errored tasks still consumed steps before crashing — keeping them in lets
you see whether failure correlates with hitting the step ceiling). Per-task
``step_count`` is recovered from ``traj.jsonl`` (max ``step_num``) so every
runner contributes regardless of whether it explicitly calls
``log_task_completion``.

``failure_kind`` is a finer-grained classification of every task into one of
six buckets. Passed tasks (score==1.0) get ``passed``. Failed tasks
(status==success, score==0.0) get ``wrong_score`` if the agent emitted
DONE/FAIL on the last step (model thought it was done but the evaluator
disagreed) or ``truncated`` if the run hit ``max_steps`` without ever
emitting DONE. Errored tasks (status==error) are classified by exception
signature: ``execute_timeout`` for the sandbox 120s ``/execute`` hard cap,
``sandbox_error`` for ``SandboxUnavailableError``, and ``unknown_error``
for anything else. Parser failures don't appear here — they're handled
inside ``PromptAgent.predict()`` (caught + fed back to the model) and
manifest at the task level as eventual ``truncated`` / ``wrong_score`` /
``passed`` depending on whether the model recovered. The
``failure_breakdown`` aggregate counts each bucket; its values sum to
``count`` (passed + failed + error).

The overall ``steps_by_score`` block splits the step distribution by score
to compare 失败 / 成功 tasks. Buckets are filtered to
``status == "success"`` (errored tasks have a truncated step_count from the
crash point, so they'd skew the read of the failed-task distribution). The
two buckets partition the successful tasks.
"""

import json
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
    import msvcrt


def _lock_file(lock) -> None:
    if fcntl is not None:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        return
    lock.seek(0)
    if not lock.read(1):
        lock.write("0")
        lock.flush()
    lock.seek(0)
    msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)


def _unlock_file(lock) -> None:
    if fcntl is not None:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        return
    lock.seek(0)
    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def _model_results_dir(args: Any) -> Path:
    """Resolve <result_dir>/<eval_mode>/<model>/.

    Fail-fast: the runner is expected to pass eval_mode + model. No fallback —
    a missing field is a programmer error, not a recoverable case (a silent
    fallback once let writer and reader land on different paths and the bug
    sat for weeks).
    """
    eval_mode = getattr(args, "eval_mode", None)
    model = getattr(args, "model", None)
    if not eval_mode or not model:
        raise ValueError(
            "_model_results_dir requires args.eval_mode and args.model; "
            f"got eval_mode={eval_mode!r}, model={model!r}"
        )
    return Path(args.result_dir) / eval_mode / model


def _results_file(args: Any) -> Path:
    return _model_results_dir(args) / "results.json"


_EMPTY_STEP_SUMMARY: Dict[str, Any] = {
    "count": 0, "min": None, "q1": None, "median": None,
    "q3": None, "max": None, "mean": None,
}

# Canonical ordering for failure_kind buckets. JSON aggregates always emit
# every key (zeros included) so downstream consumers don't need to special-case
# missing keys.
#
# Note: there's no ``parse_error`` bucket — parse failures are caught inside
# ``PromptAgent.predict()`` and fed back to the model as feedback, so they
# never bubble up as task-level errors. A run that suffers persistent parse
# failures eventually rolls up into ``truncated`` (ran out of max_steps); a
# run that recovers may end as ``passed`` / ``wrong_score`` like any other.
# Per-step parse_error markers are written to ``traj.jsonl`` for post-mortem.
FAILURE_KINDS: tuple = (
    "passed",
    "wrong_score",
    "truncated",
    "execute_timeout",
    "sandbox_error",
    "unknown_error",
)


# Per-task ``action_counts`` buckets. ``wait``/``done``/``fail`` come from the
# model's terminal signals; ``python`` is the count of pyautogui code actions
# executed in GUI mode; ``bash`` is the count of bash blocks in terminal mode
# and ``readimg`` is the count of readimg requests (terminal mode only — the
# model can fetch arbitrary images from the VM via this tool); these three
# are mutually exclusive by mode (GUI mode has python only, terminal mode
# has bash + readimg). ``timeout`` counts sandbox-side per-action kills
# (``info.hard_timeout`` for GUI, ``"killed by sandbox"`` stderr substring
# for terminal bash). ``parse_error`` counts step rows the runner wrote
# with a non-null ``parse_error`` field — these are model outputs that
# failed to parse, fed back to the model next turn as feedback (see
# ``PromptAgent._pending_parse_error``).
ACTION_KINDS: tuple = (
    "wait",
    "done",
    "fail",
    "python",
    "bash",
    "readimg",
    "timeout",
    "parse_error",
)


def _empty_action_counts() -> Dict[str, int]:
    return {k: 0 for k in ACTION_KINDS}


# Three task partitions for the action distribution: ``all`` includes every
# task with a recoverable counts dict (errored ones counted), ``passed`` and
# ``failed`` are filtered to ``status == "success"`` and split by score.
# Same partition rule as ``steps_by_score``.
ACTION_BUCKETS: tuple = ("all", "passed", "failed")


def _empty_action_distributions() -> Dict[str, Dict[str, Any]]:
    """{kind: empty_step_summary}, one entry per ACTION_KINDS."""
    return {k: dict(_EMPTY_STEP_SUMMARY) for k in ACTION_KINDS}


# Substring patterns for classifying error-task ``err_message`` strings into
# the three error subkinds. Order matters: more specific patterns first.
# These match against ``f"{type(exc).__name__}: {exc}"`` emitted by
# ``_engiworld_runtime._worker``. Patterns chosen for stability — they're
# either the exception class name or fixed substrings baked into the
# exception's f-string at construction.
#
# Note: ``execute_timeout`` is retained for backward compatibility with
# historical batches. The current runtime catches ``SandboxExecuteHardTimeoutError``
# in ``lib_run_single.py`` (both terminal and GUI paths) and feeds the
# timeout back to the model as in-task feedback rather than letting it
# bubble up as a worker-level error, so new tasks should not match this
# pattern. If you delete it, ``reconcile_results_from_disk`` will silently
# rebucket old ``execute_timeout`` rows into ``unknown_error`` and
# corrupt historical aggregates — leave it.
_ERROR_PATTERNS: tuple = (
    ("execute_timeout", (
        "SandboxExecuteHardTimeoutError",
        "/execute hit sandbox-side",
        "timed out after 120 seconds",
    )),
    ("sandbox_error", (
        "SandboxUnavailableError",
        "sandbox marked unavailable",
        "still failing after",
        "refusing to retry because",
    )),
)


def _empty_failure_breakdown() -> Dict[str, int]:
    return {k: 0 for k in FAILURE_KINDS}


def _empty_steps_by_score() -> Dict[str, Dict[str, Any]]:
    return {
        "score_zero": dict(_EMPTY_STEP_SUMMARY),
        "score_one": dict(_EMPTY_STEP_SUMMARY),
    }


def _empty_doc() -> Dict[str, Any]:
    return {
        "tasks": [],
        "by_application": {},
        "overall": {
            "count": 0, "passed_count": 0, "failed_count": 0, "error_count": 0,
            "failure_breakdown": _empty_failure_breakdown(),
            "steps": dict(_EMPTY_STEP_SUMMARY),
            "steps_by_score": _empty_steps_by_score(),
        },
    }


def _read_step_count_from_traj(result_dir: Union[str, Path]) -> Optional[int]:
    """Recover the max step_num from <result_dir>/traj.jsonl.

    Each runner in lib_run_single.py writes 1-based ``step_num`` for every
    executed step (one or more rows per step when an action emits multiple
    pyautogui calls). Taking the max collapses that to a single per-task
    step count. Error rows (no ``step_num``) are ignored. Returns None when
    the file is missing or has no usable rows — those tasks won't be counted
    in the step distribution.
    """
    p = Path(result_dir) / "traj.jsonl"
    if not p.exists():
        return None
    max_step: Optional[int] = None
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict) or "step_num" not in obj:
                    continue
                try:
                    n = int(obj["step_num"])
                except (TypeError, ValueError):
                    continue
                if max_step is None or n > max_step:
                    max_step = n
    except OSError:
        return None
    return max_step


def _count_actions_from_traj(result_dir: Union[str, Path]) -> Optional[Dict[str, int]]:
    """Tally ``ACTION_KINDS`` buckets across every step row in ``traj.jsonl``.

    Returns the per-task counts dict, or ``None`` when the file is missing or
    has no parseable rows. We tolerate two on-disk schemas:

    * GUI mode (``run_single_example``): rows carry ``action`` (str:
      ``"WAIT"`` / ``"DONE"`` / ``"FAIL"`` / pyautogui code, or ``None`` when
      parse failed) and may carry ``info.hard_timeout`` to mark a sandbox
      per-action kill.
    * Terminal mode (``run_single_example_terminal``): rows carry
      ``terminal_signal`` (``"WAIT"`` / ``"DONE"`` / ``"FAIL"`` / ``None``)
      and ``bash_runs`` (list of executed bash blocks, each with a possibly
      timeout-marked ``stderr``).

    Errored tasks contribute whatever they emitted before crashing — same
    convention as ``step_count``.
    """
    p = Path(result_dir) / "traj.jsonl"
    if not p.exists():
        return None
    counts = _empty_action_counts()
    seen_any = False
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                # Top-level Error sentinels (no step_num) aren't actionable rows.
                if "step_num" not in obj:
                    continue
                seen_any = True
                # parse_error is keyed off the field directly so an empty-action
                # row without a populated parse_error string still doesn't get
                # miscounted (rare: agent never set _pending_parse_error).
                if obj.get("parse_error") is not None:
                    counts["parse_error"] += 1
                # Terminal-mode rows have terminal_signal / bash_runs and never
                # have GUI-mode 'action' as a string.
                if "terminal_signal" in obj or "bash_runs" in obj or "readimg" in obj:
                    sig = obj.get("terminal_signal")
                    if sig == "WAIT":
                        counts["wait"] += 1
                    elif sig == "DONE":
                        counts["done"] += 1
                    elif sig == "FAIL":
                        counts["fail"] += 1
                    for br in obj.get("bash_runs") or []:
                        counts["bash"] += 1
                        stderr = br.get("stderr") if isinstance(br, dict) else ""
                        if stderr and "killed by sandbox" in stderr:
                            counts["timeout"] += 1
                    # Each readimg request counts as one action; ok=True/False
                    # are not split — the model still spent a turn on it. Use
                    # ``readimg in obj`` over ``obj.get('readimg')`` because an
                    # empty list is a valid "no readimg this step" signal.
                    counts["readimg"] += len(obj.get("readimg") or [])
                    continue
                # GUI mode. PromptAgent writes ``action`` as
                # ``{"kind": "WAIT"|"DONE"|"FAIL"|"pyautogui", "code": ...}``
                # (lib_run_single.py:477). Older runners may still emit a bare
                # string — keep that branch for backwards compatibility.
                action = obj.get("action")
                if isinstance(action, dict):
                    kind = action.get("kind")
                    if kind == "WAIT":
                        counts["wait"] += 1
                    elif kind == "DONE":
                        counts["done"] += 1
                    elif kind == "FAIL":
                        counts["fail"] += 1
                    elif kind == "pyautogui":
                        counts["python"] += 1
                elif isinstance(action, str):
                    s = action.strip()
                    if s == "WAIT":
                        counts["wait"] += 1
                    elif s == "DONE":
                        counts["done"] += 1
                    elif s == "FAIL":
                        counts["fail"] += 1
                    else:
                        counts["python"] += 1
                info = obj.get("info")
                if isinstance(info, dict) and info.get("hard_timeout"):
                    counts["timeout"] += 1
    except OSError:
        return None
    return counts if seen_any else None


def _read_last_done_from_traj(result_dir: Union[str, Path]) -> Optional[bool]:
    """Return the ``done`` field of the latest traj.jsonl row that has a
    ``step_num`` (i.e. an actual step row, not an Error sentinel). Used to
    distinguish ``wrong_score`` (loop exited early because agent emitted
    DONE/FAIL) from ``truncated`` (loop exited because it hit max_steps).
    Returns None when the file is missing, empty, or has no usable rows.
    """
    p = Path(result_dir) / "traj.jsonl"
    if not p.exists():
        return None
    last_done: Optional[bool] = None
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict) or "step_num" not in obj:
                    continue
                if "done" in obj:
                    last_done = bool(obj["done"])
    except OSError:
        return None
    return last_done


def _classify_error_message(msg: Optional[str]) -> str:
    """Bucket an error-task ``err_message`` into one of the four error kinds."""
    if not msg:
        return "unknown_error"
    for kind, patterns in _ERROR_PATTERNS:
        for pat in patterns:
            if pat in msg:
                return kind
    return "unknown_error"


def classify_outcome(
    *,
    status: str,
    score: float,
    error_message: Optional[str],
    result_dir: Union[str, Path],
) -> str:
    """Classify a task into one of ``FAILURE_KINDS``.

    ``status == "success"``:
      - ``score == 1.0`` → ``passed``
      - ``score == 0.0`` and the last traj.jsonl step had ``done == True``
        → ``wrong_score`` (agent emitted DONE/FAIL but evaluator disagreed)
      - ``score == 0.0`` otherwise → ``truncated`` (hit max_steps without DONE,
        or no traj.jsonl available — both mean the model never declared done)

    ``status == "error"``: pattern-match ``error_message`` against
    ``_ERROR_PATTERNS`` to pick ``execute_timeout`` / ``sandbox_error`` /
    ``parse_error`` / ``unknown_error``.
    """
    if status == "error":
        return _classify_error_message(error_message)
    if float(score) == 1.0:
        return "passed"
    last_done = _read_last_done_from_traj(result_dir)
    if last_done:
        return "wrong_score"
    return "truncated"


def _step_summary(values: List[int]) -> Dict[str, Any]:
    """Five-number summary + count + mean. q1/q3 use the inclusive method
    (NumPy default / R type-7), which matches what most boxplot tools draw.
    With <2 points q1/q3 collapse to None — there isn't a meaningful quartile.
    """
    if not values:
        return dict(_EMPTY_STEP_SUMMARY)
    vs = sorted(values)
    n = len(vs)
    q1: Optional[float] = None
    q3: Optional[float] = None
    if n >= 2:
        qs = statistics.quantiles(vs, n=4, method="inclusive")
        q1, _q2, q3 = qs
    return {
        "count": n,
        "min": vs[0],
        "q1": q1,
        "median": float(statistics.median(vs)),
        "q3": q3,
        "max": vs[-1],
        "mean": sum(vs) / n,
    }


def _action_distributions(counts_list: List[Dict[str, int]]) -> Dict[str, Dict[str, Any]]:
    """For one bucket of tasks, a five-number summary per action kind.

    Returns ``{kind: step_summary}`` — same shape as ``steps`` but keyed by
    action kind, so the JSON consumer can treat action distributions and
    step distributions identically. Tasks without ``action_counts`` are
    expected to have been pre-filtered by the caller.
    """
    if not counts_list:
        return _empty_action_distributions()
    return {
        kind: _step_summary([int(c.get(kind, 0) or 0) for c in counts_list])
        for kind in ACTION_KINDS
    }


def _steps_by_score(tasks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Five-number summaries split by score bucket (overall only).

    Only ``status == "success"`` tasks contribute — errored tasks have a
    truncated step_count captured at the crash point, which would skew the
    read of the failed-task distribution. Score is binary (0.0 or 1.0), so
    the two buckets fully partition the successful tasks.
    """
    zero: List[int] = []
    one: List[int] = []
    for t in tasks:
        if t.get("status") != "success":
            continue
        sc = t.get("step_count")
        if not isinstance(sc, int):
            continue
        if float(t.get("score", 0.0)) == 1.0:
            one.append(sc)
        else:
            zero.append(sc)
    return {
        "score_zero": _step_summary(zero),
        "score_one": _step_summary(one),
    }


def _compute_aggregates(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_app_acc: Dict[str, Dict[str, Any]] = {}
    for t in tasks:
        app = t.get("application", "unknown")
        bucket = by_app_acc.setdefault(
            app,
            {
                "passed_count": 0,
                "failed_count": 0,
                "error_count": 0,
                "steps": [],
                # Three task partitions for the action distribution. ``all``
                # = every task with a counts dict (errored ones counted, same
                # convention as ``steps``); ``passed`` and ``failed`` are
                # filtered to status==success and split by score.
                "actions_all": [],
                "actions_passed": [],
                "actions_failed": [],
                "failure_breakdown": _empty_failure_breakdown(),
            },
        )
        sc = t.get("step_count")
        if isinstance(sc, int):
            bucket["steps"].append(sc)
        ac = t.get("action_counts")
        if isinstance(ac, dict):
            bucket["actions_all"].append(ac)
            if t.get("status") == "success":
                if float(t.get("score", 0.0)) == 1.0:
                    bucket["actions_passed"].append(ac)
                else:
                    bucket["actions_failed"].append(ac)
        kind = t.get("failure_kind")
        if kind not in FAILURE_KINDS:
            # Defensive backfill so aggregates stay coherent even if a writer
            # forgot to set failure_kind. ``reconcile_results_from_disk``
            # rewrites this field unconditionally on every run, so this branch
            # only fires for entries written outside the canonical path.
            kind = "unknown_error" if t.get("status") == "error" else (
                "passed" if float(t.get("score", 0.0)) == 1.0 else "truncated"
            )
        bucket["failure_breakdown"][kind] += 1
        if t.get("status") == "error":
            bucket["error_count"] += 1
            continue
        if float(t.get("score", 0.0)) == 1.0:
            bucket["passed_count"] += 1
        else:
            bucket["failed_count"] += 1

    by_application: Dict[str, Dict[str, Any]] = {}
    total_passed = 0
    total_failed = 0
    total_error = 0
    all_steps: List[int] = []
    all_actions = {b: [] for b in ACTION_BUCKETS}
    overall_breakdown = _empty_failure_breakdown()
    for app in sorted(by_app_acc):
        b = by_app_acc[app]
        pc = int(b["passed_count"])
        fc = int(b["failed_count"])
        ec = int(b["error_count"])
        steps: List[int] = b["steps"]
        all_steps.extend(steps)
        for bucket_name in ACTION_BUCKETS:
            all_actions[bucket_name].extend(b[f"actions_{bucket_name}"])
        for k in FAILURE_KINDS:
            overall_breakdown[k] += b["failure_breakdown"][k]
        by_application[app] = {
            "count": pc + fc + ec,
            "passed_count": pc,
            "failed_count": fc,
            "error_count": ec,
            "failure_breakdown": dict(b["failure_breakdown"]),
            "steps": _step_summary(steps),
            "actions": {
                bucket_name: _action_distributions(b[f"actions_{bucket_name}"])
                for bucket_name in ACTION_BUCKETS
            },
        }
        total_passed += pc
        total_failed += fc
        total_error += ec

    overall = {
        "count": total_passed + total_failed + total_error,
        "passed_count": total_passed,
        "failed_count": total_failed,
        "error_count": total_error,
        "failure_breakdown": overall_breakdown,
        "steps": _step_summary(all_steps),
        "steps_by_score": _steps_by_score(tasks),
        "actions": {
            bucket_name: _action_distributions(all_actions[bucket_name])
            for bucket_name in ACTION_BUCKETS
        },
    }
    return {"by_application": by_application, "overall": overall}


def _normalize_doc(raw: Any) -> Dict[str, Any]:
    """Coerce on-disk content (legacy list, partial dict, garbage) into the new schema."""
    if isinstance(raw, list):
        doc = {"tasks": list(raw)}
    elif isinstance(raw, dict):
        doc = dict(raw)
        doc.setdefault("tasks", [])
        if not isinstance(doc["tasks"], list):
            doc["tasks"] = []
    else:
        doc = _empty_doc()
    doc.update(_compute_aggregates(doc["tasks"]))
    return doc


def _read_doc(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return _empty_doc()
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return _empty_doc()
        return _normalize_doc(json.loads(content))
    except (json.JSONDecodeError, OSError):
        return _empty_doc()


def _write_doc(path: Path, doc: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def _upsert(tasks: List[Dict[str, Any]], entry: Dict[str, Any]) -> None:
    """Insert or replace by (application, task_id)."""
    key = (entry.get("application"), entry.get("task_id"))
    for i, t in enumerate(tasks):
        if (t.get("application"), t.get("task_id")) == key:
            tasks[i] = entry
            return
    tasks.append(entry)


def _with_lock(path: Path, mutate):
    """Run `mutate(doc) -> doc` while holding an exclusive lock on the results file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Sidecar lockfile (dotfile so it doesn't clutter `ls`). We can't lock the
    # results file directly because we write atomically via tmp+rename, which
    # would invalidate any lock held on the old inode.
    lock_path = path.parent / ("." + path.name + ".lock")
    with open(lock_path, "a+") as lock:
        _lock_file(lock)
        try:
            doc = _read_doc(path)
            new_doc = mutate(doc)
            _write_doc(path, new_doc)
        finally:
            _unlock_file(lock)


# -------- public API ----------------------------------------------------


def extract_domain_from_path(result_path: str) -> str:
    """Pull the domain (penultimate path component) out of a task result dir."""
    parts = Path(result_path).parts
    return parts[-2] if len(parts) >= 2 else "unknown"


def append_task_result(
    task_id: str,
    domain: str,
    score: float,
    result_dir: str,
    args: Any,
    error_message: Optional[str] = None,
    step_count: Optional[int] = None,
) -> None:
    """Upsert one task entry and recompute aggregates.

    ``step_count`` is optional: callers that already track ``step_idx`` can
    pass it explicitly; otherwise we recover it from ``traj.jsonl`` so every
    runner — including ones that never call into us directly — still
    contributes to the step distribution after ``reconcile_results_from_disk``.
    """
    if step_count is None:
        step_count = _read_step_count_from_traj(result_dir)
    status = "error" if error_message else "success"
    entry = {
        "application": domain,
        "task_id": task_id,
        "status": status,
        "score": float(score),
        "step_count": step_count,
        "action_counts": _count_actions_from_traj(result_dir),
        "failure_kind": classify_outcome(
            status=status,
            score=float(score),
            error_message=error_message,
            result_dir=result_dir,
        ),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if error_message:
        entry["err_message"] = error_message

    path = _results_file(args)

    def _mutate(doc: Dict[str, Any]) -> Dict[str, Any]:
        _upsert(doc["tasks"], entry)
        doc.update(_compute_aggregates(doc["tasks"]))
        return doc

    try:
        _with_lock(path, _mutate)
        steps_str = "?" if step_count is None else str(step_count)
        print(
            f"📝 Logged result: {domain}/{task_id} -> {entry['status']} "
            f"(score: {score}, steps: {steps_str})"
        )
    except Exception as e:
        # Don't let logging errors break the main evaluation loop.
        print(f"⚠️  Failed to log result for {task_id}: {e}")


def log_task_completion(
    example: Dict, result: float, result_dir: str, args: Any,
    step_count: Optional[int] = None,
) -> None:
    task_id = Path(result_dir).name
    domain = extract_domain_from_path(result_dir)
    append_task_result(task_id, domain, result, result_dir, args,
                       step_count=step_count)


def log_task_error(
    example: Dict, error_msg: str, result_dir: str, args: Any,
    step_count: Optional[int] = None,
) -> None:
    task_id = Path(result_dir).name
    domain = extract_domain_from_path(result_dir)
    append_task_result(task_id, domain, 0.0, result_dir, args,
                       error_message=error_msg, step_count=step_count)


def reconcile_results_from_disk(args: Any) -> None:
    """Walk the model dir; ensure every result.txt has a tasks entry and aggregates are fresh.

    All derived fields (``step_count``, ``action_counts``, ``failure_kind``)
    and the aggregates are unconditionally recomputed from the on-disk
    ``traj.jsonl`` / ``result.txt`` / ``err_message`` state. Existing
    entries are kept only for the parts that disk can't reproduce
    (``status``, ``score``, ``timestamp``, ``err_message``); anything
    derived gets overwritten with no backwards-compat shim.
    """
    model_dir = _model_results_dir(args)
    if not model_dir.is_dir():
        return
    path = _results_file(args)

    def _mutate(doc: Dict[str, Any]) -> Dict[str, Any]:
        # Append entries for any task that finished on disk but isn't yet
        # represented in the JSON. Errored tasks (no result.txt) only
        # exist if a previous run logged them via log_task_error — those
        # stay in the list as-is for the score/err_message fields.
        seen = {(t.get("application"), t.get("task_id")) for t in doc["tasks"]}
        for domain_dir in sorted(model_dir.iterdir()):
            if not domain_dir.is_dir() or domain_dir.name == "summary":
                continue
            for ex_dir in sorted(domain_dir.iterdir()):
                if not ex_dir.is_dir():
                    continue
                rt = ex_dir / "result.txt"
                if not rt.exists():
                    continue
                key = (domain_dir.name, ex_dir.name)
                if key in seen:
                    continue
                try:
                    score = float(rt.read_text(encoding="utf-8").strip())
                except (OSError, ValueError):
                    continue
                ts = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(rt.stat().st_mtime)
                )
                doc["tasks"].append(
                    {
                        "application": domain_dir.name,
                        "task_id": ex_dir.name,
                        "status": "success",
                        "score": score,
                        "timestamp": ts,
                    }
                )
                seen.add(key)
        # Unconditionally rebuild every derived field from disk. No
        # backwards-compat path: any stale value from an older schema is
        # simply overwritten with the freshly computed one.
        for t in doc["tasks"]:
            app = t.get("application")
            tid = t.get("task_id")
            if not (app and tid):
                continue
            ex_path = model_dir / app / tid
            t["step_count"] = _read_step_count_from_traj(ex_path)
            t["action_counts"] = _count_actions_from_traj(ex_path)
            t["failure_kind"] = classify_outcome(
                status=t.get("status", "success"),
                score=float(t.get("score", 0.0)),
                error_message=t.get("err_message"),
                result_dir=ex_path,
            )
        doc.update(_compute_aggregates(doc["tasks"]))
        return doc

    try:
        _with_lock(path, _mutate)
    except Exception as e:
        print(f"⚠️  reconcile_results_from_disk failed: {e}")
