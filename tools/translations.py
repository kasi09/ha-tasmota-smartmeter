#!/usr/bin/env python3
"""Generate strings.json and translations/{en,de}.json from one table.

    python3 tools/translations.py
"""
import json
import os

DEST = os.path.join(os.path.dirname(__file__), "..", "custom_components", "tasmota_smartmeter")

SENSOR = {
    "energy_import": ("Import energy", "Bezug gesamt"),
    "energy_export": ("Export energy", "Einspeisung gesamt"),
    "energy_import_t1": ("Import energy tariff 1", "Bezug Tarif 1"),
    "energy_import_t2": ("Import energy tariff 2", "Bezug Tarif 2"),
    "energy_export_t1": ("Export energy tariff 1", "Einspeisung Tarif 1"),
    "energy_export_t2": ("Export energy tariff 2", "Einspeisung Tarif 2"),
    "power_import": ("Import power", "Bezugsleistung"),
    "power_export": ("Export power", "Einspeiseleistung"),
    "power_net": ("Net power", "Saldo"),
    "power_import_l1": ("Power L1", "Leistung L1"),
    "power_import_l2": ("Power L2", "Leistung L2"),
    "power_import_l3": ("Power L3", "Leistung L3"),
    "reactive_power_import": ("Reactive power import (Q+)", "Blindleistung Bezug (Q+)"),
    "reactive_power_export": ("Reactive power export (Q-)", "Blindleistung Lieferung (Q-)"),
    "reactive_energy_import": ("Reactive energy import (R+)", "Blindenergie Bezug (R+)"),
    "reactive_energy_export": ("Reactive energy export (R-)", "Blindenergie Lieferung (R-)"),
    "collection_energy": ("Collection energy", "Inkasso-Energie"),
    "voltage_l1": ("Voltage L1", "Spannung L1"),
    "voltage_l2": ("Voltage L2", "Spannung L2"),
    "voltage_l3": ("Voltage L3", "Spannung L3"),
    "current_l1": ("Current L1", "Strom L1"),
    "current_l2": ("Current L2", "Strom L2"),
    "current_l3": ("Current L3", "Strom L3"),
    "frequency": ("Grid frequency", "Netzfrequenz"),
    "power_factor": ("Power factor", "Leistungsfaktor"),
}
FIELDS = {"host": ("Host", "Adresse"), "password": ("Web password", "Web-Passwort")}
HELP = {
    "host": ("IP address or host name of the Tasmota reading head.",
             "IP-Adresse oder Name des Tasmota-Lesekopfs."),
    "password": ("Only if a web password is set in Tasmota.",
                 "Nur nötig, wenn in Tasmota ein Web-Passwort gesetzt ist."),
}
ERRORS = {
    "cannot_connect": ("Cannot connect to the device.", "Keine Verbindung zum Gerät."),
    "invalid_auth": ("The web password was rejected.", "Das Web-Passwort wurde abgelehnt."),
    "no_meter_data": ("The device shows no numeric sensor values.",
                      "Das Gerät zeigt keine Messwerte an."),
}
ABORT = {
    "already_configured": ("This device is already configured.", "Dieses Gerät ist bereits eingerichtet."),
    "reauth_successful": ("Password updated.", "Passwort aktualisiert."),
    "reconfigure_successful": ("Connection updated.", "Verbindung aktualisiert."),
    "wrong_device": ("This is a different device.", "Das ist ein anderes Gerät."),
}


def build(i):
    t = lambda pair: pair[i]  # noqa: E731
    fields = {k: t(v) for k, v in FIELDS.items()}
    helps = {k: t(v) for k, v in HELP.items()}
    return {
        "config": {
            "step": {
                "user": {
                    "title": t(("Tasmota smart meter reader", "Tasmota-Stromzähler-Lesekopf")),
                    "description": t((
                        "Reads all values from the device's web page. Nothing on the device is changed.",
                        "Liest alle Werte von der Weboberfläche des Geräts. Am Gerät wird nichts verändert.")),
                    "data": fields, "data_description": helps,
                },
                "reauth_confirm": {
                    "title": t(("Web password", "Web-Passwort")),
                    "data": {"password": fields["password"]},
                    "data_description": {"password": helps["password"]},
                },
                "reconfigure": {
                    "title": t(("Change connection", "Verbindung ändern")),
                    "data": fields, "data_description": helps,
                },
            },
            "error": {k: t(v) for k, v in ERRORS.items()},
            "abort": {k: t(v) for k, v in ABORT.items()},
        },
        "entity": {"sensor": {k: {"name": t(v)} for k, v in SENSOR.items()}},
        "exceptions": {
            "cannot_connect": {"message": t(ERRORS["cannot_connect"])},
            "invalid_auth": {"message": t(ERRORS["invalid_auth"])},
        },
    }


def write(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    write(os.path.join(DEST, "strings.json"), build(0))
    write(os.path.join(DEST, "translations", "en.json"), build(0))
    write(os.path.join(DEST, "translations", "de.json"), build(1))
    print("written:", len(SENSOR), "sensor names")
