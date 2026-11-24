# BJT DC Bias + CE Amplifier Simulator (Lab 03 + Lab 04)

Flask web app that keeps the three Lab 03 analytical DC-bias modes and adds a
Lab 04 common-emitter amplifier simulator driven by **real ngspice runs**
(`.op`, `.ac`, `.tran`).

## What is where

| Path | Role |
| --- | --- |
| `app.py` | Routes: `/` Lab 03 bias calculator, `/simulator` Lab 04 page, `/simulate` runs ngspice |
| `dc_bias.py` | Lab 03 analytical equations — unchanged, used as a labelled reference |
| `spice_engine.py` | Netlist builder + `subprocess.run` adapter + ngspice output parser |
| `charts.py` | Dependency-free SVG plots drawn from parsed simulation arrays |
| `templates/index.html` | Lab 03 form/results (unchanged behaviour, added link to Lab 04) |
| `templates/simulator.html` | CE circuit parameters, analysis selector, status, provenance, plots and an 8-tab B1–B8 evidence panel |
| `docs/validation.md` | A1–A5 (Lab 03) and B1–B8 (Lab 04) browser acceptance records |
| `docs/captures/` | Browser screenshots used as evidence |
| `AGENTS.md` | Rules for AI agents working on this repository |

## Install

Python 3.10+ is required.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### ngspice (external program, not a pip package)

Windows (used for this submission):

1. Download `ngspice-47_64.7z` from
   <https://sourceforge.net/projects/ngspice/files/ng-spice-rework/47/>.
2. Extract it, e.g. to `%LOCALAPPDATA%\Programs\ngspice-47`.
3. Add its `Spice64\bin` folder to `PATH`, or set
   `NGSPICE_EXECUTABLE` to the full path of `ngspice_con.exe`.
4. Verify: `ngspice_con.exe --version`.

Linux/macOS: install ngspice with the system package manager and verify
`ngspice --version`.

## Run

```powershell
.\.venv\Scripts\python.exe app.py
```

Open:

- Lab 03 bias calculator: <http://127.0.0.1:5000/>
- Lab 04 CE simulator: <http://127.0.0.1:5000/simulator>

The server binds to `127.0.0.1:5000` with `debug=False`.

## Lab 04 reference circuit and model

Fixture: VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ,
RL = 10 kΩ, Cin = Cout = 10 µF, source = 10 mV peak at 1 kHz.
RE is **unbypassed** in this baseline.

The BJT uses a reproducible classroom model defined in `spice_engine.py`:

```
.model QNPN_CLASSROOM NPN (IS=2e-15 BF=<beta from form> VAF=100 CJC=10p CJE=20p TF=0.3n)
```

This is not a specific commercial part number. It is shown on the results page
together with the engine version, netlist and ngspice log so results can be
reproduced and audited. Do not expect SPICE and the constant-β/VBE analytical
reference to agree to every digit; they use different models.

## Engineering separation

- DC: `.op` → VB, VE, VC, VCE, IC from ngspice output. Lab 03 analytical values are shown in a separate labelled table.
- AC: `.ac dec 40 1 10meg` → gain (dB) and phase (degrees) versus frequency, with Vin measured at the source node before `Cin`.
- Transient: `.tran` over five periods → Vin/Vout versus time in milliseconds.

All plots are inline SVG generated from numbers parsed out of `wrdata` output
files written by the current run. No trace is hardcoded. If the solver is
missing, fails, times out or returns no data, the page shows an error and no
stale results.

## Notes

- Do not commit `.venv/`, temporary run directories, API keys or large archives (see `.gitignore`).
- Browser checks should be recorded honestly in `docs/validation.md`, including the exact tool used.
