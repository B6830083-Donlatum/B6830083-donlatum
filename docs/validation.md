# Validation — Lab 03 regression + Lab 04 browser acceptance

## Tools actually used

- **Browser evidence:** OpenCode **built-in Browser Tool (Chromium in the OpenCode desktop app)**. Playwright MCP was **not exposed in this session**, so no Playwright MCP result is claimed.
- **Engine:** `ngspice-47 : Circuit level simulation program` (portable Windows build), invoked by `spice_engine.run_simulation` through `subprocess.run([...], shell=False, timeout=30)` in a temporary directory.
- **UI review:** Impeccable installed with `npx impeccable install`; the bundled `detect` command was run once on `templates/simulator.html` and `templates/index.html`.

All numbers below were read from the live page or from ngspice output produced in the current run. No result is copied from a previous run.

## Lab 04 acceptance B1–B8

| Case | Method / input | Observed result | Evidence | Status |
| --- | --- | --- | --- | --- |
| **B1 · Regression** | Built-in Browser Tool: opened `/`, calculated `fixed`, `emitter`, `divider` with the Lab 03 default fixture. | Fixed: IC 1.13 mA, VCE 9.514 V. Emitter: IC 1.03 mA, VCE 8.705 V. Divider: IC 1.23 mA, VCE 8.052 V. Mode switching kept the three analytical outcomes. | `captures/B1_lab3_regression.png` | **PASS** |
| **B2 · DC SPICE** | `/simulator` → analysis DC → default 12 V / 100 kΩ / 22 kΩ / 2.2 kΩ / 1 kΩ / 10 kΩ / 10 µF / 10 mV / 1 kHz → Run Simulation. | Status Success. Engine: `ngspice-47 : Circuit level simulation program`. VB 1.95507 V, VE 1.25451 V, VC 9.26556 V, VCE 8.01105 V, IC 0.00124293 A (1.2429 mA). Separate Lab 03 analytical reference: IC 1.23 mA, VCE 8.052 V. Model description, netlist and ngspice log are disclosed in page `<details>` blocks. | `captures/B2_dc_spice.png` | **PASS** |
| **B3 · Change RE** | Changed only RE from 1 kΩ to 2 kΩ, then reran DC. | Operating point changed: VB 1.95507 → 2.05135 V, IC 0.00124293 → 0.00067715 A, VCE 8.01105 → 9.14348 V. The previous result was replaced, not retained. | `captures/B3_change_RE.png` | **PASS** |
| **B4 · AC** | Selected `AC frequency response (.ac)` and ran with amplitude 20 mV (source input change also exercised here). | Two real SVG plots rendered from parsed `wrdata`: gain (dB vs log-frequency Hz) and phase (degrees vs log-frequency Hz). Peak gain in sweep 4.86 dB. Lower −3 dB ≈ 1.884 Hz. Upper −3 dB correctly reported as **not determined in sweep range (1 Hz – 10 MHz)**. Phase at 1 kHz ≈ −179.87° from parsed `vp(out) − vp(in)` converted from radians. | `captures/B4_ac_bode.png` | **PASS** |
| **B5 · Transient** | Selected `Transient waveforms (.tran)` at the specified 10 mV peak / 1 kHz fixture. | Vin/Vout versus time in ms rendered from 2008 parsed points. Vin peak 0.0099999 V, Vout peak 0.0175006 V, \|Vout/Vin\| peak 1.7501. Parsed traces have a negative Vout/Vin slope ratio of −1.74884, confirming the expected common-emitter inversion. | `captures/B5_tran_10mV_1kHz.png` | **PASS** |
| **B6 · Change Source** | In transient mode, changed amplitude 10 mV → 20 mV and reran. | Vin peak 0.0099999 → 0.0199998 V; Vout peak 0.0175006 → 0.0350252 V; gain stayed ≈ 1.75. The waveform plot changed with the new ngspice run, so it is not hard-coded. | `captures/B5_tran_10mV_1kHz.png` (before), `captures/B6_change_amplitude.png` (after) | **PASS** |
| **B7 · Invalid / Fail** | Set RE = 0 and submitted. | HTTP 400 error state: **“RE ต้องมากกว่า 0”**. No `Status: Success` badge and no `Simulation results` section were present; the successful prior result was not shown. | `captures/B6_validation_error.png` | **PASS** |
| **B8 · UI** | Built-in Browser Tool on desktop page, and a 390 px-wide iframe viewport (`captures/phone_frame.html`) rendered by the same Chromium browser. Analysis mode was switched in both sizes. | Desktop: cards, form, plots, units and status readable. 390 px frame: `window.innerWidth = 390`, `.grid` computed to one column (`307px`), button remained readable/tappable (157 px wide), mode selector switched to AC successfully. No essential content was clipped. | `captures/B8_desktop.png`, `captures/B8_mobile_390px_frame.png`, `captures/UI_after_impeccable_desktop.png`, `captures/UI_after_impeccable_mobile_390px.png` | **PASS** |

**B7 limitation:** the “engine not available” variant was not triggered in the browser because ngspice was successfully installed. The adapter code has that error path, but its browser behaviour is **NOT RUN**. B7 is marked PASS from the RE=0 invalid-input branch required by the handout.

**B8 limitation:** the phone check is a **390 CSS pixel iframe viewport** in Chromium, not a physical phone or Playwright MCP device emulation. This is stated explicitly to avoid overclaiming.

## Impeccable UI review

Impeccable `detect --json templates/simulator.html templates/index.html` reported:

- 3 warnings for `side-tab` accent borders in `templates/simulator.html` (`.notice` used `border-left` with `border-radius`).
- 1 advisory for low-contrast error text in `templates/index.html` (`#f87171` on the dark error surface measured 4.46:1, just under AA 4.5:1).

Fixes made without changing any numerical formula or simulation output:

- `.notice` now uses a full `1px solid #8cc9bb` border and an 8 px radius.
- `--err` changed to `#ff9d9d` for adequate contrast on the dark card.

Before/after screenshots are in `captures/B8_desktop.png` → `captures/UI_after_impeccable_desktop.png` and `captures/B8_mobile_390px_frame.png` → `captures/UI_after_impeccable_mobile_390px.png`.

## Provenance checks performed

- DC, AC and transient values were re-run after the `wrdata` parser was corrected; the parser accounts for ngspice repeating the x-axis value before each vector and writing two components for complex AC vectors.
- AC phase uses `vp(out) − vp(in)`; this build returns radians, so the parser converts to degrees before plotting.
- AC gain uses `vdb(out) − vdb(in)`, not the absolute `vdb(out)` alone.
- The −3 dB search starts after the peak and does not report a crossing when none exists.
- On invalid input, the template omits the entire results section, preventing a stale Success state.

## Reproduce

```powershell
.\.venv\Scripts\python.exe app.py
# open http://127.0.0.1:5000/ and http://127.0.0.1:5000/simulator
```
