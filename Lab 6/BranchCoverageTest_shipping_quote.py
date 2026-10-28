import pytest
from shipping_quote import process_shipments, monitor_container_pressures


# ---------------------------------------------------------------------------
# Branch coverage tests
# Goal: drive every decision in shipping_quote.py to both True and False,
# including loop entry/exit edges and boundary values.
# ---------------------------------------------------------------------------


def ground(packages, **extra):
    shipment = {"manifest_approved": True, "mode": "ground", "packages": packages}
    shipment.update(extra)
    return shipment


# ===================== process_shipments =====================

# --- Line 2: `not isinstance(shipments, list) or handling_fee < 0` ---

def test_b2_true_shipments_not_a_list():
    with pytest.raises(ValueError):
        process_shipments({"mode": "ground"}, 10.0)


def test_b2_true_negative_handling_fee():
    with pytest.raises(ValueError):
        process_shipments([], -0.01)


def test_b2_false_zero_fee_is_valid():
    # boundary: handling_fee == 0 is allowed
    result = process_shipments([ground([{"weight_kg": 10}])], 0.0)
    assert result == {"total_quote": 40.0, "status": "CLEARED"}


# --- Line 8: outer loop entered / not entered ---

def test_b8_empty_shipment_list_skips_loop():
    assert process_shipments([], 10.0) == {"total_quote": 0.0, "status": "NO_CARGO"}


# --- Line 9: manifest approved True / False / missing key ---

def test_b9_true_unapproved_manifest_skipped():
    shipments = [{"manifest_approved": False, "mode": "ground",
                  "packages": [{"weight_kg": 10}]}]
    assert process_shipments(shipments, 10.0)["status"] == "NO_CARGO"


def test_b9_true_missing_approval_defaults_to_unapproved():
    shipments = [{"mode": "ground", "packages": [{"weight_kg": 10}]}]
    assert process_shipments(shipments, 10.0)["status"] == "NO_CARGO"


def test_b9_false_approved_manifest_processed():
    assert process_shipments([ground([{"weight_kg": 1}])], 0.0)["total_quote"] == 4.0


# --- Lines 16/18: air / ground / other transport mode ---

def test_b16_true_air_mode():
    shipments = [{"manifest_approved": True, "mode": "air",
                  "packages": [{"weight_kg": 2}]}]
    # 5 + 2 * 12 = 29
    assert process_shipments(shipments, 5.0) == {"total_quote": 29.0, "status": "CLEARED"}


def test_b18_true_ground_mode_is_default():
    shipments = [{"manifest_approved": True, "packages": [{"weight_kg": 2}]}]
    # mode defaults to ground: 5 + 2 * 4 = 13
    assert process_shipments(shipments, 5.0) == {"total_quote": 13.0, "status": "CLEARED"}


def test_b18_false_unknown_mode_rejected():
    shipments = [{"manifest_approved": True, "mode": "rail",
                  "packages": [{"weight_kg": 2}]},
                 ground([{"weight_kg": 2}])]
    # rail shipment rejected and contributes nothing; ground: 5 + 8 = 13
    assert process_shipments(shipments, 5.0) == {"total_quote": 13.0, "status": "CLEARED"}


# --- Line 26: package loop not entered (no packages) ---

def test_b26_no_packages_charges_only_handling_fee():
    assert process_shipments([ground([])], 7.5) == {"total_quote": 7.5, "status": "CLEARED"}


# --- Line 30: weight <= 0 True / False (boundaries 0 and just above 0) ---

def test_b30_true_zero_weight_rejected():
    result = process_shipments([ground([{"weight_kg": 0}])], 5.0)
    assert result == {"total_quote": 5.0, "status": "CLEARED"}


def test_b30_true_missing_weight_rejected():
    result = process_shipments([ground([{}])], 5.0)
    assert result == {"total_quote": 5.0, "status": "CLEARED"}


def test_b30_false_small_positive_weight():
    result = process_shipments([ground([{"weight_kg": 0.5}])], 0.0)
    assert result == {"total_quote": 2.0, "status": "CLEARED"}


# --- Line 34: hazmat True / False ---
# --- Line 36: fragile True / False (only reachable when hazmat) ---

def test_b34_true_b36_false_hazmat_not_fragile_surcharge():
    result = process_shipments([ground([{"weight_kg": 5, "is_hazmat": True}],
                                       is_fragile=False)], 10.0)
    assert result == {"total_quote": 60.0, "status": "CLEARED"}


def test_b34_true_b36_true_hazmat_fragile_zeroes_shipment_and_breaks():
    packages = [{"weight_kg": 10},                      # +40
                {"weight_kg": 5, "is_hazmat": True},    # cost -> 0, break
                {"weight_kg": 10}]                      # never reached
    result = process_shipments([ground(packages, is_fragile=True)], 10.0)
    assert result == {"total_quote": 0.0, "status": "NO_CARGO"}


def test_b34_false_non_hazmat_package_charged_by_weight():
    result = process_shipments([ground([{"weight_kg": 5, "is_hazmat": False}])], 0.0)
    assert result["total_quote"] == 20.0


# --- Line 40: weight > 30 True / False (boundary 30 vs 30.5) ---

def test_b40_false_weight_exactly_30_standard_rate():
    result = process_shipments([ground([{"weight_kg": 30}])], 0.0)
    assert result["total_quote"] == 120.0          # 30 * 4


def test_b40_true_weight_above_30_heavy_rate():
    result = process_shipments([ground([{"weight_kg": 30.5}])], 0.0)
    assert result["total_quote"] == 183.0          # 30.5 * 6


def test_b40_true_air_heavy_rate():
    shipments = [{"manifest_approved": True, "mode": "air",
                  "packages": [{"weight_kg": 50}]}]
    assert process_shipments(shipments, 0.0)["total_quote"] == 900.0   # 50 * 18


# --- Line 45: express priority True / False ---

def test_b45_true_express_multiplier():
    result = process_shipments([ground([{"weight_kg": 10}], express_priority=True)], 20.0)
    assert result == {"total_quote": 75.0, "status": "CLEARED"}   # 60 * 1.25


def test_b45_false_no_express():
    result = process_shipments([ground([{"weight_kg": 10}], express_priority=False)], 20.0)
    assert result == {"total_quote": 60.0, "status": "CLEARED"}


# --- Line 50: rejected_parcels > 3 True / False (boundary 3 vs 4) ---

def test_b50_false_exactly_three_rejections_not_flagged():
    packages = [{"weight_kg": 0}, {"weight_kg": -1}, {"weight_kg": 0}, {"weight_kg": 10}]
    result = process_shipments([ground(packages)], 0.0)
    assert result == {"total_quote": 40.0, "status": "CLEARED"}


def test_b50_true_four_rejections_flagged():
    packages = [{"weight_kg": 0}, {"weight_kg": -1}, {"weight_kg": 0},
                {"weight_kg": 2, "is_hazmat": True}, {"weight_kg": 10}]
    result = process_shipments([ground(packages)], 0.0)
    assert result == {"total_quote": 90.0, "status": "FLAGGED_REVIEW"}   # 50 + 40


def test_b50_true_flagged_from_rejected_modes():
    shipments = [{"manifest_approved": True, "mode": m, "packages": []}
                 for m in ("sea", "rail", "drone", "pigeon")]
    result = process_shipments(shipments, 10.0)
    assert result == {"total_quote": 0.0, "status": "FLAGGED_REVIEW"}


# --- Line 52: total_quote == 0 True / False ---

def test_b52_true_zero_total_no_cargo():
    shipments = [{"manifest_approved": True, "mode": "sea", "packages": []}]
    assert process_shipments(shipments, 10.0) == {"total_quote": 0.0, "status": "NO_CARGO"}


def test_b52_false_cleared_with_rounding():
    shipments = [ground([{"weight_kg": 1.111}]), ground([{"weight_kg": 2.222}])]
    # 4.444 + 8.888 = 13.332 -> 13.33
    assert process_shipments(shipments, 0.0) == {"total_quote": 13.33, "status": "CLEARED"}


# --- Combined multi-shipment scenario (several branches in one run) ---

def test_mixed_shipments_end_to_end():
    shipments = [
        {"manifest_approved": True, "mode": "air", "express_priority": True,
         "packages": [{"weight_kg": 40}, {"weight_kg": 10}]},
        ground([{"weight_kg": 5, "is_hazmat": True}]),
        {"manifest_approved": False, "mode": "air", "packages": [{"weight_kg": 99}]},
    ]
    # air: (10 + 40*18 + 10*12) * 1.25 = 850 * 1.25 = 1062.5
    # ground hazmat: 10 + 50 = 60 ; unapproved skipped
    result = process_shipments(shipments, 10.0)
    assert result == {"total_quote": 1122.5, "status": "CLEARED"}


# ================= monitor_container_pressures =================

# --- Line 58: no data True / False ---

def test_m58_true_empty_list():
    assert monitor_container_pressures([]) == "NO_DATA"


def test_m58_true_none():
    assert monitor_container_pressures(None) == "NO_DATA"


# --- Line 61/63: containers with no readings (inner loop not entered) ---

def test_m63_empty_container_is_stable():
    assert monitor_container_pressures([[]]) == "STABLE"


# --- Line 64: psi < 14 True / False (boundary 14.0 is not low) ---

def test_m64_false_boundary_14_is_normal():
    assert monitor_container_pressures([[14.0, 14.0, 14.0]]) == "STABLE"


# --- Line 66: streak >= 2 False (single dip) / True (two in a row) ---

def test_m66_false_single_low_reading_stable():
    assert monitor_container_pressures([[15.0, 13.9, 15.0]]) == "STABLE"


def test_m66_false_low_reading_at_end_stable():
    assert monitor_container_pressures([[15.0, 15.0, 13.0]]) == "STABLE"


def test_m66_true_two_consecutive_low_readings_leak():
    assert monitor_container_pressures([[13.9, 13.9]]) == "LEAK_DETECTED"


# --- Line 69: streak reset (alternating low/normal never leaks) ---

def test_m69_alternating_readings_reset_streak():
    assert monitor_container_pressures([[13.0, 15.0, 13.0, 15.0, 13.0]]) == "STABLE"


# --- Streak resets per container (outer loop repeats) ---

def test_m62_streak_does_not_carry_across_containers():
    # last reading of first container is low, first of second is low:
    # separate containers, so no leak
    assert monitor_container_pressures([[15.0, 13.0], [13.0, 15.0]]) == "STABLE"


def test_m61_leak_in_later_container():
    logs = [[15.0, 15.5], [14.5, 13.0, 15.0], [16.0, 12.0, 11.0]]
    assert monitor_container_pressures(logs) == "LEAK_DETECTED"
