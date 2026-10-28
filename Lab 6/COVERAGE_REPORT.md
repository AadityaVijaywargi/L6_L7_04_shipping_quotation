# Lab 6: Code and Branch Coverage Report (Shipping Quote)

Module under test: `shipping_quote.py` (`process_shipments`, `monitor_container_pressures`)
Tools: Python 3.10.4, pytest 8.2.2, coverage 7.16.2

## 1. Baseline (starter test `test_shipping_quote.py`)

| Metric | Result |
|--------|--------|
| Line coverage | **49%** (27 of 53 statements missed) |
| Branch coverage | **45%** (10 of 36 branches partially covered) |

Missing lines: `3, 10, 17, 21-22, 31-32, 35-39, 41, 46, 51, 53, 58-70`

The one starter test only runs the "happy path": an approved ground shipment with one normal-weight package.
These paths never run: input validation, unapproved manifests, air and unknown transport modes, invalid weights, hazmat handling, the heavy-parcel surcharge, express priority, the `FLAGGED_REVIEW` and `NO_CARGO` outcomes, and all of `monitor_container_pressures`.

## 2. Code (line) coverage: `CodeCoverageTest_shipping_quote.py`

Commands:
```
coverage run -m pytest CodeCoverageTest_shipping_quote.py
coverage report -m
```

Result: **8 tests passed, line coverage 100%** (53/53 statements). Screenshot: `screenshots/code_coverage.png`

| Test | Statements targeted |
|------|---------------------|
| `test_single_ground_shipment` | ground rate, normal weight (19, 43) |
| `test_invalid_shipments_type_raises` | `ValueError` (3) |
| `test_air_heavy_express_shipment` | air rate, >30 kg surcharge, express ×1.25 (17, 41, 46) |
| `test_unapproved_and_unknown_mode_gives_no_cargo` | skip unapproved, reject unknown mode, `NO_CARGO` (10, 21-22, 53) |
| `test_hazmat_and_invalid_weights_flagged_for_review` | weight ≤ 0, hazmat non-fragile, hazmat fragile break, `FLAGGED_REVIEW` (31-32, 35-39, 51) |
| `test_monitor_no_data` | `NO_DATA` (59) |
| `test_monitor_leak_detected` | streak counter, `LEAK_DETECTED` (62-67) |
| `test_monitor_stable_with_streak_reset` | streak reset, `STABLE` (69-70) |

Each test aims at one group of statements that the baseline missed, so this is the smallest suite that runs every line.

## 3. Branch coverage: `BranchCoverageTest_shipping_quote.py`

Commands:
```
coverage run --branch -m pytest BranchCoverageTest_shipping_quote.py
coverage report -m
```

Result: **38 tests passed, branch coverage 100%** (36/36 branches, 0 partial). Screenshot: `screenshots/branch_coverage.png`

Tests are named by the source line of the decision they drive (`b<line>` for `process_shipments`, `m<line>` for `monitor_container_pressures`). Each decision gets at least one test for its True outcome and one for its False outcome:

| Line | Decision | True case | False case |
|------|----------|-----------|------------|
| 2 | invalid list **or** fee < 0 | non-list input; fee −0.01 | fee = 0 (boundary) |
| 8 | outer `for` loop | shipments present | empty list (loop skipped) |
| 9 | manifest not approved | `False`; key missing | approved |
| 16 | mode == air | air | ground / other |
| 18 | mode == ground | explicit and default mode | unknown mode → rejected |
| 26 | package `for` loop | packages present | empty package list |
| 30 | weight ≤ 0 | 0, missing weight | 0.5 |
| 34 | hazmat | hazmat package | normal package |
| 36 | fragile (inside hazmat) | cost zeroed + `break` | +50 surcharge |
| 40 | weight > 30 | 30.5, 50 (air) | exactly 30 (boundary) |
| 45 | express priority | ×1.25 | no multiplier |
| 50 | rejected > 3 | 4 rejections (parcels or modes) | exactly 3 (boundary) |
| 52 | total == 0 | `NO_CARGO` | `CLEARED` with rounding |
| 58 | no pressure data | `[]`, `None` | data present |
| 61/63 | container / reading loops | multiple containers | empty container `[[]]` |
| 64 | psi < 14 | 13.9 | 14.0 (boundary) |
| 66 | streak ≥ 2 | two consecutive lows | single dip; dip at end |
| 69 | streak reset | alternating low/normal stays `STABLE` | — |

The suite also includes a mixed end-to-end scenario, and a check that a low streak does not carry over from one container to the next.

## 4. Line vs. branch coverage

Line coverage alone can mislead. Take the `if` with no `else` on line 45: a suite whose shipments are all `express_priority=True` runs line 46 and scores 100% line coverage, yet it never checks the plain, non-express price. Branch coverage reports line 45 as a partial branch (`45->48` missing). The same applies to the inner hazmat `break` on line 38 and to loops that are never skipped (empty `packages`, an empty container).
The branch suite also tests boundaries that line coverage never asks for, such as weight exactly 30, psi exactly 14.0, exactly 3 rejections, and a fee of 0. These are where off-by-one mistakes (`>` vs `>=`) would show up.

Note: coverage.py measures branch outcomes, not individual conditions. For the compound condition on line 2 (`A or B`), the branch suite still tests each part on its own: one test where only A is true, one where only B is true, and one where neither is.

## 5. Summary

| Suite | Tests | Line coverage | Branch coverage |
|-------|-------|---------------|-----------------|
| Starter (`test_shipping_quote.py`) | 1 | 49% | 45% |
| `CodeCoverageTest_shipping_quote.py` | 8 | 100% | 100% |
| `BranchCoverageTest_shipping_quote.py` | 38 | 100% | 100% |
