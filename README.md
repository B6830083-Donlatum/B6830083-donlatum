# BJT DC Bias Web App (Lab 02 + Lab 03)

Flask web app for DC operating point calculation of three NPN bias circuits.

## Modes

| Mode | Extra inputs | Function |
|---|---|---|
| Voltage Divider Bias (Lab 02) | R1, R2, RE | `calculate_dc_bias()` |
| Fixed Bias | RB | `calculate_fixed_bias()` |
| Emitter Bias | RB, RE | `calculate_emitter_bias()` |

Shared inputs for every mode: VCC, RC, β, VBE. Inputs can be entered in Ω, kΩ or MΩ and are converted to SI before calculation.

## Run

```powershell
cd "C:\Users\B6830083\Documents\Default Project"
py -3 -m pip install flask
py -3 app.py
```

Open <http://127.0.0.1:5000/>.

Select a circuit in the dropdown and press **ใช้โหมดนี้** to reload the form with only the fields that circuit uses, then press **คำนวณ**.

## File layout

- `app.py` — routes, mode selection, input validation, unit conversion, result formatting.
- `dc_bias.py` — three separate calculation functions returning the same `BiasResult` shape.
- `templates/index.html` — Jinja form and result display.
- `docs/validation.md` — A1–A5 browser acceptance table.
- `Lab03_A1_Evidence.docx` — Word evidence with A1 screenshot.
- `evidence/A1_lab02.png` — raw A1 screenshot.

## Model

Forward-active approximation with constant β and VBE. All functions return
`vb_v`, `ve_v`, `vc_v`, `vce_v`, `ic_ma`-equivalent formatted values plus
`region` and `warnings`. If IB ≤ 0 or VCE ≤ 0.2 V, the page shows a warning that
the forward-active model may not be valid.
