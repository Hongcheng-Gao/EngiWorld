from pathlib import Path
import json


root = Path(__file__).resolve().parent
report = root / 'report.jsonl'
existing_lines = [line for line in report.read_text(encoding='utf-8').splitlines() if line.strip()]
existing_ids = {json.loads(line)['task_id'] for line in existing_lines}

record_paths = sorted((root / 'logs').glob('*/record.json'))
for record_path in record_paths:
    record = json.loads(record_path.read_text(encoding='utf-8'))
    if record['task_id'] not in existing_ids:
        existing_lines.append(json.dumps(record, ensure_ascii=True, separators=(',', ':')))
        existing_ids.add(record['task_id'])

report.write_text('\n'.join(existing_lines) + '\n', encoding='utf-8')
