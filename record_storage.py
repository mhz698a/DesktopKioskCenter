import json


def load_records(path, fields):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []

    records = []
    for item in data:
        if isinstance(item, dict):
            records.append({
                key: str(item.get(key, "") or "")
                for key, _label in fields
            })
    return records


def save_records(path, records):
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(records, indent=2, ensure_ascii=False)
    temporary_path.write_text(payload, encoding="utf-8")
    temporary_path.replace(path)
