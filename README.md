# Tasmota Smart Meter — Home Assistant integration

Reads **all values** of a Tasmota IR reading head on an electricity meter
(SML or scripted meters, e.g. Austrian/German smart meters) directly over
HTTP — ready for the **Energy dashboard**.

## Why not the Tasmota integration?

The official Tasmota integration gets its values over MQTT from the device's
JSON telemetry. With many meter scripts that JSON carries only part of the
values (e.g. 5 of 10). The device's **web page** shows everything the meter
script decodes. This integration reads that page:

* every numeric row becomes a sensor — import/export energy and power,
  net power, reactive power and energy, voltages, currents, frequency …
* known OBIS codes get translated names and the right device and state
  classes; unknown rows are classified by their unit
* **nothing on the device is changed** — no MQTT setup, no script edits
* local polling every 10 s

## Statistics stay clean

A meter reading is `total_increasing` in Home Assistant, and HA counts every
decrease as a new meter cycle — the next value is added to the long-term
statistics in full. A reader that reboots and briefly reports `0 kWh` would
therefore double your yearly consumption. This integration holds back:

* readings that go down (a real meter exchange is accepted after 5 minutes)
* jumps larger than 250 kW could deliver in the elapsed time

## Installation

1. HACS → ⋮ → *Custom repositories* → add this repository, category
   *Integration*.
2. Install **Tasmota Smart Meter**, restart Home Assistant.
3. *Settings → Devices & services → Add integration → Tasmota Smart Meter*,
   enter the IP address of the reading head (and the web password, if set).
4. *Settings → Dashboards → Energy*: use **Import energy** as grid
   consumption and **Export energy** as return to grid.

## License

Apache-2.0
