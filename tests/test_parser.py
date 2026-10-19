"""The table parser and the meter guard - no Home Assistant needed."""

from custom_components.tasmota_smartmeter.guard import RESET_AFTER, MeterGuard
from custom_components.tasmota_smartmeter.parser import parse_table

from .conftest import TABLE


def test_all_ten_values_time_and_date_skipped() -> None:
    rows = parse_table(TABLE)
    assert [r.obis for r in rows] == [
        "1.7.0", "2.7.0", "1.7.0-2.7.0", "1.8.0", "2.8.0",
        "3.7.0", "4.7.0", "3.8.1", "4.8.1", "1.128.0",
    ]
    byobis = {r.obis: r for r in rows}
    assert byobis["1.8.0"].unit == "kWh" and byobis["1.8.0"].value > 39000
    assert byobis["1.7.0-2.7.0"].key == "z1_1_7_0_minus_2_7_0"
    assert byobis["3.8.1"].unit == "kvarh"
    assert byobis["2.7.0"].text == "Wirk-L. P-"


def test_rows_without_end_marker_do_not_merge() -> None:
    page = "{t}{s}Z1 Zeit{m}10:00:00{s}Z1 1.8.0(A+){m} 5.5 kWh{e}{s}Z1 Datum{m}2026-10-19"
    rows = parse_table(page)
    assert len(rows) == 1 and rows[0].value == 5.5


def test_unknown_labels_and_duplicates() -> None:
    page = "{s}Power{m}12 W{e}{s}Power{m}13 W{e}{s}Leistung &amp; mehr{m}7,5 kW{e}{s}Text{m}abc{e}"
    rows = parse_table(page)
    assert [(r.key, r.value, r.unit) for r in rows] == [
        ("power", 12.0, "W"), ("power_2", 13.0, "W"), ("leistung_mehr", 7.5, "kW")
    ]


def test_guard_holds_back_decrease_and_zero() -> None:
    g = MeterGuard()
    assert g.check(1000.0, "kWh", 0) == 1000.0
    assert g.check(0.0, "kWh", 10) == 1000.0          # reader reboot
    assert g.check(999.999, "kWh", 20) == 1000.0       # jitter
    assert g.check(1000.01, "kWh", 30) == 1000.01


def test_guard_rejects_impossible_jump() -> None:
    g = MeterGuard()
    g.check(1000.0, "kWh", 0)
    assert g.check(33940.0, "kWh", 10) == 1000.0       # glitch
    assert g.check(1000.5, "kWh", 20) == 1000.5        # 0.5 kWh in 20 s = 90 kW: plausible
    assert g.check(1000.6, "Wh", 30) == 1000.6         # unit aware


def test_guard_accepts_persistent_reset() -> None:
    g = MeterGuard()
    g.check(1000.0, "kWh", 0)
    for i in range(1, RESET_AFTER):
        assert g.check(3.0, "kWh", i * 10) == 1000.0
    assert g.check(3.0, "kWh", RESET_AFTER * 10) == 3.0   # meter exchanged
