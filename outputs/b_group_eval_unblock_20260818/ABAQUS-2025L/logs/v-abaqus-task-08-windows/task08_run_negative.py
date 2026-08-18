#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DESKTOP = r'C:\Users\user\Desktop'
BASE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[5]
TASK = REPO / 'task' / 'task-v' / 'abaqus' / 'task-08'


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Remote:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip('/')

    def execute(self, command: list[str]) -> dict:
        request = urllib.request.Request(
            self.base_url + '/execute',
            data=json.dumps({'command': command, 'shell': False}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(request, timeout=900) as response:
            return json.loads(response.read().decode('utf-8'))

    def upload(self, source: Path, target: str) -> dict:
        result = subprocess.run(
            ['curl', '-sS', '--max-time', '900', '-F', 'file_path=' + target,
             '-F', 'file_data=@' + str(source), self.base_url + '/setup/upload'],
            capture_output=True, text=True, check=True, timeout=910)
        return {'source': str(source), 'target': target, 'sha256': sha256(source),
                'response': result.stdout}

    def entries(self) -> list[dict]:
        result = self.execute([
            'powershell', '-NoProfile', '-Command',
            r'Get-ChildItem -LiteralPath C:\Users\user\Desktop -Force | '
            r'Select-Object Name,Length | ConvertTo-Json -Compress'])
        text = result.get('output', '').strip()
        if not text:
            return []
        value = json.loads(text)
        return value if isinstance(value, list) else [value]

    def read(self, name: str) -> str:
        result = self.execute([
            'powershell', '-NoProfile', '-Command',
            "$p='%s\\%s'; if(Test-Path -LiteralPath $p){Get-Content -LiteralPath $p -Raw}" %
            (DESKTOP, name)])
        return result.get('output', '')

    def cleanup(self) -> dict:
        command = (
            "Stop-Process -Name abq2025le,ABQLauncher,SMAPcae,standard,pre -Force "
            "-ErrorAction SilentlyContinue; "
            "$paths=@('%s\\Contact-Seed.cae','%s\\Job-Contact.cae',"
            "'%s\\Job-Contact.odb','%s\\eval.py','%s\\eval_result.txt',"
            "'%s\\eval_detail.txt'); $existing=@($paths | Where-Object "
            "{ Test-Path -LiteralPath $_ }); if($existing.Count -gt 0){ "
            "Remove-Item -LiteralPath $existing -Force -ErrorAction Stop }; exit 0" %
            ((DESKTOP,) * 6))
        return self.execute(['powershell', '-NoProfile', '-Command', command])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', required=True,
                        choices=('init_only', 'missing_odb', 'wrong_load'))
    parser.add_argument('--base-url', default='http://127.0.0.1:15233')
    args = parser.parse_args()
    remote = Remote(args.base_url)
    if remote.entries():
        raise SystemExit('Desktop is not empty before negative test')

    seed = TASK / 'init_file' / 'Contact-Seed.cae'
    gt_cae = TASK / 'ground_truth' / 'Job-Contact.cae'
    gt_odb = TASK / 'ground_truth' / 'Job-Contact.odb'
    wrong_cae = BASE / 'Job-Contact-WrongLoad.cae'
    evaluator = TASK / 'eval.py'
    candidate = wrong_cae if args.case == 'wrong_load' else gt_cae
    include_candidate = args.case != 'init_only'
    include_odb = args.case not in ('init_only', 'missing_odb')
    record = {'case': args.case, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'desktop_before': remote.entries(), 'uploads': [],
              'eval_sha256': sha256(evaluator)}
    try:
        record['uploads'].append(remote.upload(seed, DESKTOP + r'\Contact-Seed.cae'))
        if include_candidate:
            record['uploads'].append(remote.upload(candidate,
                                                   DESKTOP + r'\Job-Contact.cae'))
        if include_odb:
            record['uploads'].append(remote.upload(gt_odb, DESKTOP + r'\Job-Contact.odb'))
        record['uploads'].append(remote.upload(evaluator, DESKTOP + r'\eval.py'))
        record['evaluation'] = remote.execute([
            'cmd.exe', '/c',
            r'C:\SIMULIA\Commands\abaqus.bat cae noGUI=C:\Users\user\Desktop\eval.py'])
        record['detail'] = remote.read('eval_detail.txt')
        record['passed_negative'] = (
            record['evaluation'].get('returncode') == 0 and
            record['evaluation'].get('output') == 'False\n')
    finally:
        record['desktop_after_eval'] = remote.entries()
        record['cleanup'] = remote.cleanup()
        record['desktop_after_cleanup'] = remote.entries()
        record['cleanup_ok'] = (
            record['cleanup'].get('returncode') == 0 and
            record['cleanup'].get('status') == 'success' and
            not record['desktop_after_cleanup'])
        record['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (BASE / ('negative_' + args.case + '.json')).write_text(
            json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'case': args.case,
                      'passed_negative': record.get('passed_negative'),
                      'stdout': record.get('evaluation', {}).get('output'),
                      'desktop_after_cleanup': record['desktop_after_cleanup']}))
    return 0 if record.get('passed_negative') and record.get('cleanup_ok') else 1


if __name__ == '__main__':
    raise SystemExit(main())
