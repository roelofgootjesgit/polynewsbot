"""Tests for order manager (dry-run mode)."""
from src.execution.order_manager import OrderManager


def _make_cfg(dry_run=True):
    return {"execution": {"dry_run": dry_run, "max_retry": 3}}


def test_dry_run_order():
    om = OrderManager(_make_cfg(dry_run=True))
    order = om.submit_order(
        client=None,
        token_id="token-abc-123",
        side="buy",
        price=0.55,
        size=10.0,
        event_id="evt-1",
        market_id="mkt-1",
    )
    assert order.dry_run is True
    assert order.status == "filled"
    assert order.filled == 10.0
    assert order.order_id.startswith("dry-")


def test_dry_run_cancel():
    om = OrderManager(_make_cfg(dry_run=True))
    order = om.submit_order(None, "token-1", "buy", 0.50, 5.0)
    # Already filled in dry-run, cancel should fail
    assert not om.cancel(order.internal_id)


def test_get_open_orders():
    om = OrderManager(_make_cfg(dry_run=True))
    om.submit_order(None, "token-1", "buy", 0.50, 5.0)
    om.submit_order(None, "token-2", "sell", 0.60, 3.0)
    # All dry-run orders are immediately filled
    assert len(om.get_open_orders()) == 0
    assert len(om.get_all_orders()) == 2


def test_state_persistence(tmp_path, monkeypatch):
    import src.execution.order_manager as om_module
    state_file = tmp_path / "orders_state.json"
    monkeypatch.setattr(om_module, "_STATE_FILE", state_file)

    om = OrderManager(_make_cfg(dry_run=True))
    om.submit_order(None, "token-1", "buy", 0.50, 5.0)
    om.submit_order(None, "token-2", "sell", 0.60, 3.0)

    assert state_file.exists()

    om2 = OrderManager(_make_cfg(dry_run=True))
    restored = om2.load_state()
    assert restored == 2
    assert len(om2.get_all_orders()) == 2
