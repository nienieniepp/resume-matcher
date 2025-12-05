from typing import Dict, Any, Optional, Tuple
import time



_resume_cache: Dict[str, Dict[str, Any]] = {}
_match_cache: Dict[str, Dict[str, Any]] = {}

DEFAULT_TTL = 3600  # 1 小时


def _is_expired(entry: Dict[str, Any]) -> bool:
    ttl = entry.get("ttl", DEFAULT_TTL)
    ts = entry.get("ts", 0)
    return (time.time() - ts) > ttl


def cache_resume(resume_id: str, data: Dict[str, Any], ttl: int = DEFAULT_TTL) -> None:
    _resume_cache[resume_id] = {"data": data, "ts": time.time(), "ttl": ttl}


def get_cached_resume(resume_id: str) -> Optional[Dict[str, Any]]:
    entry = _resume_cache.get(resume_id)
    if not entry or _is_expired(entry):
        _resume_cache.pop(resume_id, None)
        return None
    return entry["data"]


def cache_match(key: str, data: Dict[str, Any], ttl: int = DEFAULT_TTL) -> None:
    _match_cache[key] = {"data": data, "ts": time.time(), "ttl": ttl}


def get_cached_match(key: str) -> Optional[Dict[str, Any]]:
    entry = _match_cache.get(key)
    if not entry or _is_expired(entry):
        _match_cache.pop(key, None)
        return None
    return entry["data"]

