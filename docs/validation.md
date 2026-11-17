# Lab 03 · Browser validation (A1–A5)

-url: http://127.0.0.1:5000/
-method: OpenCode Browser (browser tool)
-common inputs: VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V
-tolerance: |ΔIC| ≤ 0.01 mA, |ΔVCE| ≤ 0.02 V (compared with unrounded hand calculations)

| Case | Mode / input | Expected (independent calculation) | Observed on page | Method | Status |
|---|---|---|---|---|---|
| A1 | Divider · R1=100 kΩ, R2=22 kΩ, RE=1 kΩ | IC ≈ 1.2297 mA, VCE ≈ 8.0527 V (must match Lab 02) | IC = 1.23 mA, VCE = 8.052 V, Region = Forward-Active | OpenCode Browser | PASS |
| A2 | Fixed · RB=1 MΩ (RE not required) | IB = 11.3 µA, IC = 1.1300 mA, VCE = 9.5140 V | IB = 11.3 µA, IC = 1.13 mA, VCE = 9.514 V | OpenCode Browser | PASS |
| A3 | Emitter · RB=1 MΩ, RE=1 kΩ | IB ≈ 10.2634 µA, IC ≈ 1.0263 mA, VCE ≈ 8.7055 V | IB = 10.3 µA, IC = 1.03 mA, VCE = 8.705 V | OpenCode Browser | PASS |
| A4 | Emitter · same as A3 but RE=2 kΩ | IC must decrease: ≈ 0.9401 mA, VCE ≈ 8.0328 V | IC = 940 µA, VCE = 8.033 V (decreased from 1.03 mA) | OpenCode Browser | PASS |
| A5 | Fixed · RB=0 | Error telling user to fix RB; app must not crash and must not show previous result | Error `RB ต้องมากกว่า 0` shown; no stale result block | OpenCode Browser | PASS |

## Evidence

- `Lab03_A1_Evidence.docx` — Word document containing the A1 screenshot.
- `evidence/A1_lab02.png` — raw screenshot of A1 result page.

## Notes

- Switching mode reloads the form with only the relevant resistor inputs:
  Fixed shows RB only, Emitter shows RB + RE, Divider shows R1 + R2 + RE.
- Unknown mode is rejected in Flask with HTTP 400 and message `โหมดวงจรไม่รู้จัก ...`.
- Divider equations and A1 numeric results are unchanged from Lab 02; only the
  model-validity warning threshold now follows the Lab 03 spec (VCE ≤ 0.2 V).
