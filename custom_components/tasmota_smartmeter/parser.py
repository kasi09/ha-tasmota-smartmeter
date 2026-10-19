"""Parse the sensor table of a Tasmota web page (``/?m=1``).

Tasmota sends its sensor rows in a compact markup::

    {t}{s}Z1 Zeit{m}14:54:25{s}Z1 1.8.0(Energie A+){m} 39717.090 kWh{e}...

``{s}`` starts a row, ``{m}`` separates label and value, ``{e}`` ends it.
Rows with text values (time, date) end WITHOUT ``{e}`` - a pattern over
``{s}...{m}...{e}`` would merge them with the next row, so the page is split
at ``{s}`` first.

The JSON endpoint (``Status 10``) often carries only part of the values; the
web table shows everything the meter script decodes.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

_TAG = re.compile(r"<[^>]*>")
_SPACE = re.compile(r"\s+")
_VALUE = re.compile(r"^(-?\d+(?:[.,]\d+)?)\s*([A-Za-z%°µμ/²³]*)$")
_LABEL = re.compile(
    r"^(?:(?P<prefix>[A-Za-z]+\d*)\s+)?"
    r"(?P<obis>\d+\.\d+\.\d+(?:\s*-\s*\d+\.\d+\.\d+)?)"
    r"\s*(?:\((?P<text>.*)\))?$"
)
_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Row:
    """One numeric row of the sensor table."""

    key: str            # stable id, e.g. "z1_1_8_0"
    label: str          # as shown by Tasmota, e.g. "Z1 1.8.0(Energie A+)"
    prefix: str | None  # meter prefix, e.g. "Z1"
    obis: str | None    # normalised OBIS code, e.g. "1.8.0" or "1.7.0-2.7.0"
    text: str | None    # description from the label, e.g. "Energie A+"
    value: float
    unit: str | None


def _clean(text: str) -> str:
    return _SPACE.sub(" ", _TAG.sub("", html.unescape(text))).strip()


def _slug(text: str) -> str:
    return _SLUG.sub("_", text.lower()).strip("_")


def parse_table(page: str) -> list[Row]:
    """All numeric rows of the page, in page order, keys unique."""
    rows: list[Row] = []
    seen: set[str] = set()
    for chunk in page.split("{s}")[1:]:
        if "{m}" not in chunk:
            continue
        raw_label, rest = chunk.split("{m}", 1)
        label = _clean(raw_label)
        value_text = _clean(rest.split("{e}")[0])
        match = _VALUE.match(value_text)
        if not label or not match:
            continue
        value = float(match.group(1).replace(",", "."))
        unit = match.group(2) or None

        lab = _LABEL.match(label)
        if lab:
            prefix = lab.group("prefix")
            obis = re.sub(r"\s*-\s*", "-", lab.group("obis"))
            text = (lab.group("text") or "").strip() or None
            key = _slug(f"{prefix or ''}_{obis.replace('-', '_minus_')}")
        else:
            prefix, obis, text = None, None, label
            key = _slug(label)
        base, n = key, 2
        while key in seen:
            key, n = f"{base}_{n}", n + 1
        seen.add(key)
        rows.append(Row(key, label, prefix, obis, text, value, unit))
    return rows
