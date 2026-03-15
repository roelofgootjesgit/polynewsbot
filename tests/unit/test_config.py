"""Tests for config loading."""
from src.config.loader import load_config


def test_load_default_config():
    cfg = load_config()
    assert isinstance(cfg, dict)
    assert "polymarket" in cfg
    assert "news" in cfg
    assert "edge" in cfg
    assert "risk" in cfg
    assert "execution" in cfg
    assert "logging" in cfg


def test_config_has_risk_defaults():
    cfg = load_config()
    risk = cfg["risk"]
    assert risk["max_position_pct"] == 0.01
    assert risk["max_cluster_pct"] == 0.03
    assert risk["max_total_exposure_pct"] == 0.10


def test_config_has_edge_defaults():
    cfg = load_config()
    edge = cfg["edge"]
    assert edge["fee_rate"] == 0.02
    assert isinstance(edge["bands"], list)
    assert len(edge["bands"]) == 3


def test_config_dry_run_default():
    cfg = load_config()
    assert cfg["execution"]["dry_run"] is True
