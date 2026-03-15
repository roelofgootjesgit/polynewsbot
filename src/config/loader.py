"""
Configuration loader: YAML + .env + deep merge.
Adapted from OCLW bot config pattern.
"""
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(_PROJECT_ROOT / "configs" / ".env")
load_dotenv(_PROJECT_ROOT / ".env")
_DEFAULT_PATH = _PROJECT_ROOT / "configs" / "default.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load config: default.yaml → override yaml → env overrides."""
    default: dict[str, Any] = {}
    if _DEFAULT_PATH.exists():
        with open(_DEFAULT_PATH, "r", encoding="utf-8") as f:
            default = yaml.safe_load(f) or {}

    cfg_path = Path(path) if path else Path(os.getenv("CONFIG_PATH", str(_DEFAULT_PATH)))
    if not cfg_path.is_absolute():
        cfg_path = _PROJECT_ROOT / cfg_path

    merged = dict(default)
    if cfg_path != _DEFAULT_PATH and cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            overrides = yaml.safe_load(f) or {}
        _deep_merge(merged, overrides)

    _apply_env_overrides(merged)
    return merged


def _apply_env_overrides(cfg: dict[str, Any]) -> None:
    """Override specific config values from environment variables."""
    env_map = {
        "POLYMARKET_API_KEY": ("polymarket", "api_key"),
        "POLYMARKET_SECRET": ("polymarket", "secret"),
        "POLYMARKET_WALLET_PRIVATE_KEY": ("polymarket", "wallet_private_key"),
        "POLYMARKET_CHAIN_ID": ("polymarket", "chain_id"),
        "NEWSAPI_KEY": ("news", "newsapi_key"),
        "OPENAI_API_KEY": ("ai", "openai_api_key"),
        "DRY_RUN": ("execution", "dry_run"),
        "LOG_FILE": ("logging", "file_path"),
    }
    for env_var, key_path in env_map.items():
        val = os.getenv(env_var)
        if val is None:
            continue
        section = cfg
        for key in key_path[:-1]:
            section = section.setdefault(key, {})
        final_key = key_path[-1]
        if val.lower() in ("true", "false"):
            section[final_key] = val.lower() == "true"
        elif val.isdigit():
            section[final_key] = int(val)
        else:
            section[final_key] = val


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
