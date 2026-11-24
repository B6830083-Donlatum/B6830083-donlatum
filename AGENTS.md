# AGENTS.md — rules for AI assistants on this repository

## Scope
- Lab 03 analytical DC bias calculator (`app.py`, `dc_bias.py`, `templates/index.html`) is preserved.
- Lab 04 adds one reference CE voltage-divider amplifier simulated by real `ngspice`.

## Provenance rules
- Never invent, hard-code, or reuse stale simulation values. Every plotted number must come from a parsed ngspice output file produced in the current run.
- Show the engine version, analysis mode, BJT model description, netlist and run log on the page.
- Keep SPICE results and Lab 03 analytical results visually and textually separate. State the different model assumptions.
- If ngspice is missing, fails, times out, or output cannot be parsed, return an error state. Do not show a previous successful result with status Success.

## Engineering rules
- Validate all form numbers, units and ranges before writing a netlist.
- Call the solver with `subprocess.run([...], shell=False, timeout=...)` in an isolated temporary working directory.
- Do not edit `dc_bias.py` equations to force agreement with SPICE.
- Do not bypass capacitors for the baseline CE circuit; RE is unbypassed.

## UI rules
- UI polish must not change numerical formulas or replace real plots with placeholder art.
- Axes and units must be visible. Form must only require inputs used by the selected analysis.
- Keep Lab 03 routes working after UI changes.

## Verification
- Record B1–B8 honestly as PASS / FAIL / NOT RUN with the actual tool used.
- Do not claim Playwright MCP if only the built-in browser tool was executed.
