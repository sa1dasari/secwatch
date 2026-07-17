import json
import os
import config


def _load(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default


def _save(path, data):
    os.makedirs(config.STATE_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_seen():
    """Set of accession numbers we've already processed (avoid dupes across runs)."""
    return set(_load(config.SEEN_FILE, []))


def save_seen(seen_set):
    # keep the file bounded -- only need the last few thousand to dedupe against
    trimmed = list(seen_set)[-5000:]
    _save(config.SEEN_FILE, trimmed)


def load_digest_queue():
    return _load(config.DIGEST_QUEUE_FILE, [])


def save_digest_queue(items):
    _save(config.DIGEST_QUEUE_FILE, items)


def append_to_digest_queue(item):
    items = load_digest_queue()
    items.append(item)
    save_digest_queue(items)
