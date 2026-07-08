import json


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
