"""Flask web app: Lab 02/03 DC bias + Lab 04 ngspice CE simulator."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, abort, render_template, request, send_from_directory

from charts import ac_charts, tran_charts
from dc_bias import (
    BiasResult,
    calculate_dc_bias,
    calculate_emitter_bias,
    calculate_fixed_bias,
)
from spice_engine import SpiceError, run_simulation

app = Flask(__name__)
CAPTURE_DIR = Path(__file__).resolve().parent / "docs" / "captures"

MODES = {
    "divider": {
        "label": "Voltage Divider Bias (Lab 02)",
        "resistors": ["r1", "r2", "re"],
    },
    "fixed": {
        "label": "Fixed Bias",
        "resistors": ["rb"],
    },
    "emitter": {
        "label": "Emitter Bias",
        "resistors": ["rb", "re"],
    },
}

DEFAULTS: Dict[str, str] = {
    "vcc": "12",
    "rc": "2.2",
    "rc_unit": "kohm",
    "beta": "100",
    "vbe": "0.7",
    "r1": "100",
    "r1_unit": "kohm",
    "r2": "22",
    "r2_unit": "kohm",
    "rb": "1",
    "rb_unit": "mohm",
    "re": "1",
    "re_unit": "kohm",
}

# Lab 04 CE simulator: reference fixture from the handout.
SIM_DEFAULTS: Dict[str, str] = {
    "vcc": "12",
    "r1": "100", "r1_unit": "kohm",
    "r2": "22", "r2_unit": "kohm",
    "rc": "2.2", "rc_unit": "kohm",
    "re": "1", "re_unit": "kohm",
    "rl": "10", "rl_unit": "kohm",
    "beta": "100",
    "vbe": "0.7",
    "cin": "10",
    "cout": "10",
    "amp": "0.01",
    "freq": "1000",
    "analysis": "dc",
}

ANALYSIS_LABELS = {
    "dc": "DC operating point (.op)",
    "ac": "AC frequency response (.ac)",
    "tran": "Transient waveforms (.tran)",
}

SIM_RESISTORS = ["r1", "r2", "rc", "re", "rl"]
SIM_NUMERIC_FIELDS = ["vcc", "beta", "vbe", "cin", "cout", "amp", "freq"]

UNIT_FACTORS = {
    "ohm": 1.0,
    "kohm": 1_000.0,
    "mohm": 1_000_000.0,
}

LABELS = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rb": "RB",
    "rc": "RC",
    "re": "RE",
    "rl": "RL",
    "cin": "Cin",
    "cout": "Cout",
    "amp": "Amplitude",
    "freq": "Frequency",
    "beta": "Beta",
    "vbe": "VBE",
}

NUMERIC_FIELDS = ["vcc", "rc", "beta", "vbe"]
PRESERVED_FIELDS: List[str] = (
    NUMERIC_FIELDS
    + ["rc_unit"]
    + ["r1", "r1_unit", "r2", "r2_unit", "rb", "rb_unit", "re", "re_unit"]
)


def _number(form: Any, name: str) -> float:
    raw = (form.get(name) or "").strip()
    label = LABELS.get(name, name)
    if not raw:
        raise ValueError(f"กรอก {label} ด้วยครับ")
    try:
        value = float(raw.replace(",", ""))
    except ValueError as exc:
        raise ValueError(f"{label} ต้องเป็นตัวเลข") from exc
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"{label} ต้องเป็นจำนวนจำกัด")
    return value


def _resistance(form: Any, name: str) -> float:
    value = _number(form, name)
    label = LABELS.get(name, name)
    if value <= 0:
        raise ValueError(f"{label} ต้องมากกว่า 0")
    unit = (form.get(f"{name}_unit") or "kohm").strip()
    if unit not in UNIT_FACTORS:
        raise ValueError(f"หน่วยของ {label} ไม่ถูกต้อง")
    ohms = value * UNIT_FACTORS[unit]
    if ohms > 1e12:
        raise ValueError(f"{label} สูงเกินไป")
    return ohms


def parse_form(form: Any, mode: str) -> Dict[str, float]:
    """Validate only the inputs required by the selected circuit."""

    if mode not in MODES:
        raise ValueError("โหมดวงจรไม่รู้จัก กรุณาเลือกโหมดให้ถูกต้อง")

    vcc = _number(form, "vcc")
    if not 0 < vcc <= 100:
        raise ValueError("VCC ต้องอยู่ในช่วง 0–100 V")

    beta = _number(form, "beta")
    if not 1 <= beta <= 100_000:
        raise ValueError("Beta ต้องอยู่ในช่วง 1–100000")

    vbe = _number(form, "vbe")
    if not 0 < vbe <= 10:
        raise ValueError("VBE ต้องอยู่ในช่วง 0–10 V")

    values: Dict[str, float] = {
        "vcc": vcc,
        "rc": _resistance(form, "rc"),
        "beta": beta,
        "vbe": vbe,
    }

    for name in MODES[mode]["resistors"]:
        values[name] = _resistance(form, name)

    return values


def parse_sim_form(form: Any) -> Dict[str, float]:
    """Validate the CE simulator fixture before any netlist is generated."""

    analysis = (form.get("analysis") or "").strip()
    if analysis not in ANALYSIS_LABELS:
        raise ValueError("Analysis mode ไม่รู้จัก กรุณาเลือก DC, AC หรือ Transient")

    values: Dict[str, float] = {
        "analysis": analysis,  # type: ignore[assignment]
        "vcc": _number(form, "vcc"),
        "beta": _number(form, "beta"),
        "vbe": _number(form, "vbe"),
    }
    if not 0 < values["vcc"] <= 100:
        raise ValueError("VCC ต้องอยู่ในช่วง 0–100 V")
    if not 1 <= values["beta"] <= 100_000:
        raise ValueError("Beta ต้องอยู่ในช่วง 1–100000")
    if not 0 < values["vbe"] <= 10:
        raise ValueError("VBE ต้องอยู่ในช่วง 0–10 V")

    for name in SIM_RESISTORS:
        values[name] = _resistance(form, name)

    for name in ("cin", "cout"):
        capacitance_uf = _number(form, name)
        if not 0 < capacitance_uf <= 1000:
            raise ValueError(f"{LABELS[name]} ต้องอยู่ในช่วง 0–1000 µF")
        values[f"{name}_f"] = capacitance_uf * 1e-6

    amp = _number(form, "amp")
    if not 0 < amp <= 1:
        raise ValueError("Amplitude ต้องอยู่ในช่วง 0–1 V peak (small-signal)")
    values["amp"] = amp

    freq = _number(form, "freq")
    if not 1 <= freq <= 10_000_000:
        raise ValueError("Frequency ต้องอยู่ในช่วง 1 Hz–10 MHz")
    values["freq"] = freq

    return values


def _eng(value: float, unit: str) -> str:
    """Format a value with a readable engineering prefix."""

    if unit == "A":
        for factor, prefix in (
            (1.0, "A"),
            (1e-3, "mA"),
            (1e-6, "µA"),
            (1e-9, "nA"),
        ):
            if abs(value) >= factor or factor == 1e-9:
                return f"{value / factor:.3g} {prefix}"
    if unit == "Ω":
        for factor, prefix in (
            (1e6, "MΩ"),
            (1e3, "kΩ"),
            (1.0, "Ω"),
        ):
            if abs(value) >= factor or factor == 1.0:
                return f"{value / factor:.3g} {prefix}"
    return f"{value:.3f} {unit}"


def present(result: BiasResult) -> Dict[str, Any]:
    divider = result.mode == "divider"
    return {
        "mode": result.mode,
        "mode_label": MODES.get(result.mode, {}).get("label", result.mode),
        "vth_label": "VTH" if divider else "VCC (= VTH)",
        "rth_label": "RTH" if divider else "RB (= RTH)",
        "vth": _eng(result.vth, "V"),
        "rth": _eng(result.rth, "Ω"),
        "ib": _eng(result.ib, "A"),
        "ic": _eng(result.ic, "A"),
        "ie": _eng(result.ie, "A"),
        "vb": _eng(result.vb, "V"),
        "ve": _eng(result.ve, "V"),
        "vc": _eng(result.vc, "V"),
        "vce": _eng(result.vce, "V"),
        "region": result.region,
        "warnings": result.warnings,
        "raw": {
            "vth": result.vth,
            "rth": result.rth,
            "ib": result.ib,
            "ic": result.ic,
            "ie": result.ie,
            "vb": result.vb,
            "ve": result.ve,
            "vc": result.vc,
            "vce": result.vce,
        },
    }


@app.route("/", methods=["GET"])
def index():
    requested = request.args.get("mode", "divider")
    error = None
    if requested in MODES:
        mode = requested
    else:
        mode = "divider"
        error = "โหมดวงจรไม่รู้จัก กรุณาเลือกจากรายการ"

    form = DEFAULTS.copy()
    for key in PRESERVED_FIELDS:
        if key in request.args:
            form[key] = request.args[key]
    form["mode"] = mode

    return render_template(
        "index.html",
        form=form,
        mode=mode,
        modes=MODES,
        preserved_fields=PRESERVED_FIELDS,
        error=error,
        result=None,
    )


@app.route("/calculate", methods=["POST"])
def calculate():
    submitted = request.form.to_dict()
    requested_mode = submitted.get("mode", "")
    mode = requested_mode if requested_mode in MODES else "divider"

    try:
        values = parse_form(request.form, requested_mode)
        if requested_mode == "fixed":
            result = calculate_fixed_bias(**values)
        elif requested_mode == "emitter":
            result = calculate_emitter_bias(**values)
        else:
            result = calculate_dc_bias(**values)
    except ValueError as exc:
        return (
            render_template(
                "index.html",
                form=submitted,
                mode=mode,
                modes=MODES,
                preserved_fields=PRESERVED_FIELDS,
                error=str(exc),
                result=None,
            ),
            400,
        )

    return render_template(
        "index.html",
        form=submitted,
        mode=mode,
        modes=MODES,
        preserved_fields=PRESERVED_FIELDS,
        result=present(result),
        error=None,
    )


def _sim_context(
    form: Dict[str, str],
    *,
    error: str | None = None,
    spice_log: str = "",
    result: Any = None,
    charts: Dict[str, str] | None = None,
    analytical: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    analysis = form.get("analysis", "dc")
    if analysis not in ANALYSIS_LABELS:
        analysis = "dc"
    return {
        "form": form,
        "analysis": analysis,
        "analysis_labels": ANALYSIS_LABELS,
        "sim_defaults": SIM_DEFAULTS,
        "sim_resistors": SIM_RESISTORS,
        "sim_numeric_fields": SIM_NUMERIC_FIELDS,
        "error": error,
        "spice_log": spice_log,
        "result": result,
        "charts": charts or {},
        "analytical": analytical,
    }


@app.route("/capture/<path:name>")
def capture(name: str):
    """Serve recorded browser-evidence images for the B1–B8 tabs."""

    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        abort(404)
    return send_from_directory(CAPTURE_DIR, name)


@app.route("/simulator", methods=["GET"])
def simulator():
    """Lab 04 CE simulator page; Lab 3 bias calculator stays at '/'."""

    form = SIM_DEFAULTS.copy()
    for key in SIM_DEFAULTS:
        if key in request.args:
            form[key] = request.args[key]
    return render_template("simulator.html", **_sim_context(form))


@app.route("/simulate", methods=["POST"])
def simulate():
    submitted = request.form.to_dict()

    try:
        values = parse_sim_form(request.form)
    except ValueError as exc:
        return (
            render_template(
                "simulator.html",
                **_sim_context(submitted, error=str(exc)),
            ),
            400,
        )

    analysis = str(values["analysis"])
    analytical = present(
        calculate_dc_bias(
            vcc=values["vcc"],
            r1=values["r1"],
            r2=values["r2"],
            rc=values["rc"],
            re=values["re"],
            beta=values["beta"],
            vbe=values["vbe"],
        )
    )

    try:
        simulation = run_simulation(values, analysis)
    except SpiceError as exc:
        return (
            render_template(
                "simulator.html",
                **_sim_context(
                    submitted,
                    error=str(exc),
                    spice_log=exc.log,
                    analytical=analytical,
                ),
            ),
            400,
        )

    charts: Dict[str, str] = {}
    if analysis == "ac":
        charts = ac_charts(simulation.traces)
    elif analysis == "tran":
        charts = tran_charts(simulation.traces)

    return render_template(
        "simulator.html",
        **_sim_context(
            submitted,
            result=simulation,
            charts=charts,
            analytical=analytical,
        ),
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
