"""Flask web app for Lab 02/03 BJT DC-bias calculator.

Lab 02: Voltage Divider Bias
Lab 03: adds Fixed Bias and Emitter Bias (single supply)
"""

from __future__ import annotations

from typing import Any, Dict, List

from flask import Flask, render_template, request

from dc_bias import (
    BiasResult,
    calculate_dc_bias,
    calculate_emitter_bias,
    calculate_fixed_bias,
)

app = Flask(__name__)

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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
