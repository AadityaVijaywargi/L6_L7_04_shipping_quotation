import pytest
from shipping_quote import process_shipments, monitor_container_pressures


# ---------------------------------------------------------------------------
# Code (line/statement) coverage tests
# Goal: execute every statement in shipping_quote.py at least once.
# ---------------------------------------------------------------------------

# Starter test from the repo: ground shipment, normal weight -> line 43
def test_single_ground_shipment():
    shipments = [
        {
            "manifest_approved": True,
            "mode": "ground",
            "is_fragile": False,
            "express_priority": False,
            "packages": [{"weight_kg": 10, "is_hazmat": False}]
        }
    ]
    result = process_shipments(shipments, 20.0)
    assert result["total_quote"] == 60.0
    assert result["status"] == "CLEARED"


# Line 3: invalid input raises ValueError
def test_invalid_shipments_type_raises():
    with pytest.raises(ValueError):
        process_shipments("not a list", 10.0)


# Lines 17, 41, 46: air mode, heavy package (>30 kg) surcharge, express priority
def test_air_heavy_express_shipment():
    shipments = [
        {
            "manifest_approved": True,
            "mode": "air",
            "is_fragile": False,
            "express_priority": True,
            "packages": [{"weight_kg": 40, "is_hazmat": False}]
        }
    ]
    # (10 + 40 * 12 * 1.5) * 1.25 = 730 * 1.25 = 912.5
    result = process_shipments(shipments, 10.0)
    assert result["total_quote"] == 912.5
    assert result["status"] == "CLEARED"


# Lines 10, 21-22, 53: unapproved manifest skipped, unknown mode rejected,
# nothing quoted -> NO_CARGO
def test_unapproved_and_unknown_mode_gives_no_cargo():
    shipments = [
        {"manifest_approved": False, "mode": "air",
         "packages": [{"weight_kg": 5}]},
        {"manifest_approved": True, "mode": "sea",
         "packages": [{"weight_kg": 5}]},
    ]
    result = process_shipments(shipments, 10.0)
    assert result == {"total_quote": 0.0, "status": "NO_CARGO"}


# Lines 31-32, 35-39, 51: invalid weights, hazmat (non-fragile and fragile),
# more than 3 rejections -> FLAGGED_REVIEW
def test_hazmat_and_invalid_weights_flagged_for_review():
    shipments = [
        {
            "manifest_approved": True,
            "mode": "ground",
            "is_fragile": False,
            "packages": [
                {"weight_kg": 5, "is_hazmat": True},   # +50, rejected
                {"weight_kg": 0},                       # rejected
                {"weight_kg": -2},                      # rejected
            ],
        },
        {
            "manifest_approved": True,
            "mode": "ground",
            "is_fragile": True,
            "packages": [
                {"weight_kg": 5, "is_hazmat": True},   # cost -> 0, break
                {"weight_kg": 10},                      # never reached
            ],
        },
    ]
    # first shipment: 10 + 50 = 60; second shipment: 0; rejected = 4
    result = process_shipments(shipments, 10.0)
    assert result == {"total_quote": 60.0, "status": "FLAGGED_REVIEW"}


# Line 59: no pressure data
def test_monitor_no_data():
    assert monitor_container_pressures([]) == "NO_DATA"


# Lines 62-67: two consecutive low readings -> leak
def test_monitor_leak_detected():
    assert monitor_container_pressures([[15.0, 13.0, 12.5]]) == "LEAK_DETECTED"


# Lines 69-70: low readings interrupted by normal ones -> streak reset, stable
def test_monitor_stable_with_streak_reset():
    assert monitor_container_pressures([[15.0, 13.0, 15.0, 13.5, 16.0]]) == "STABLE"
