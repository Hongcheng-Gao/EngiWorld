import asyncio
from typing import List, Optional, Union, Dict, Any
import json
import os
import hashlib
from pathlib import Path
from omegaconf import DictConfig
from dataclasses import dataclass, asdict
import copy
import logging
import random

from prompts import COMPUTER_USE_PROMPT, COMPUTER_USE_PROMPT_WITH_CALL_USER
from log_config import setup_logging

# Configure shared logging.
setup_logging()
logger = logging.getLogger(__name__)

class TaskLoader:
    def __init__(self, task_cfg: DictConfig, storage_root):
        self.task_file = Path(task_cfg.task_file)
        #self.task_root = Path(task_cfg.task_root)
        self.osworld_root = Path(task_cfg.osworld_root)
        
        self._latest_sha: Optional[str] = None
        self.storage_root = storage_root
        self.resume = task_cfg.resume

    def poll_for_tasks(self) -> List[Dict]:
        """find new tasks json file
        return list of TaskInfo dict if there is new json
        else return []
        """
        self._maybe_refresh_dataset()
        
        tasks_list = [task.to_dict() for task in self._tasks]
        random.shuffle(tasks_list)

        return tasks_list 
    
    def _maybe_refresh_dataset_bak(self):
        
        # check new json
        latest_json = self._find_latest_json()

        if latest_json is None:
            return False # no json file
        
        sha = self._calc_sha1(latest_json)
        if sha == self._latest_sha:
            return False # no change
        
        with open(latest_json) as f:
            data = json.load(f)
            
        raw_tasks = [
            {"task_type": task_type, "task_id": task_id}
            for task_type, task_ids in data.items()
            for task_id in task_ids
        ]
        
        self._tasks = [build_task(raw, self.osworld_root) for raw in raw_tasks]
        self._latest_sha = sha

        logger.info(f"Current task file: {str(latest_json)}")
        logger.info(f"Task count: {len(raw_tasks)}")
        
        return True
    
    def _maybe_refresh_dataset(self):
        
        latest_json = self.task_file
        print("Current tasks file: ", str(latest_json))
        
        with open(latest_json) as f:
            data = json.load(f)
            
        raw_tasks = [
            {"task_type": task_type, "task_id": task_id}
            for task_type, task_ids in data.items()
            for task_id in task_ids
        ]
        
        if self.resume:
            # Filter out completed tasks and tasks of a different type.
            filtered_tasks = []
            storage_root = Path(self.storage_root)

            for raw in raw_tasks:
                task_id = str(raw["task_id"])
                task_type_expected = raw["task_type"]

                # Find all subdirectories starting with task_id, including multiple versions.
                candidate_dirs = [
                    d for d in storage_root.iterdir()
                    if d.is_dir() and d.name.startswith(task_id)
                ]

                # Assume the task is incomplete until a completion record is found.
                task_finished = False

                for d in candidate_dirs:
                    cfg_path = d / "task_config.json"
                    if not cfg_path.exists():
                        print("Configuration file not found.")
                        continue

                    try:
                        with cfg_path.open("r", encoding="utf-8") as cf:
                            cfg = json.load(cf)
                    except Exception:
                        print("Invalid configuration; skipping this directory.")
                        continue

                    # A different task_type denotes a different task; skip this directory.
                    if cfg.get("raw", {}).get("task_type") != task_type_expected:
                        continue

                    # For a matching task_type, check reward.txt.
                    if (d / "reward.txt").exists():
                        task_finished = True
                        break  # A completion record was found; skip the remaining directories.
                if not task_finished:
                    filtered_tasks.append(raw)
            self._tasks = [build_task(raw, self.osworld_root) for raw in filtered_tasks]
            print(f"Total number of tasks: {len(raw_tasks)}, Remained:{len(filtered_tasks)}")

        else:
            self._tasks = [build_task(raw, self.osworld_root) for raw in raw_tasks]
            print(f"Total number of tasks: {len(raw_tasks)}")

        return True
        
    def _find_latest_json(self) -> Optional[Path]:
        files = list(self.task_root.glob("*.json"))
        return max(files, key=lambda p: p.stat().st_mtime) if files else None
    
    @staticmethod
    def _calc_sha1(fp: Path, chunk_size=2<<20) -> str:
        h = hashlib.sha1()
        with fp.open("rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()


@dataclass
class TaskInfo:
    messages: List
    instruction: str
    task_config: Dict

    def to_dict(self):
        return asdict(self)


def build_task(raw: Dict, osworld_root: Path, use_call_user: bool = False) -> TaskInfo:

    task_type = raw["task_type"]
    task_id = raw["task_id"]
    task_path = os.path.join(osworld_root, task_type, task_id + ".json")
    with open(task_path) as f:
        task_data = json.load(f)

    task_data["raw"] = {
        "task_type": task_type,
        "task_id": task_id
    }

    instruction = task_data["instruction"]

    if "human-ground-truth" in task_data and "single-action" in task_data["human-ground-truth"]:
        plan = task_data["human-ground-truth"]["single-action"]
        plan_text = "\n".join(plan)
        instruction = instruction.strip() + "\nHere is an instruction to help you complete the task: \n" + plan_text

    system_prompt = COMPUTER_USE_PROMPT if not use_call_user else COMPUTER_USE_PROMPT_WITH_CALL_USER
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text", 
                    "text": system_prompt.format(
                        instruction=instruction, 
                        language="English"
                )}
            ]
        }
    ]
    

    return TaskInfo(
        messages = messages,
        instruction = instruction,
        task_config = task_data
    )