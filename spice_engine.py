"""ngspice adapter for the Lab 04 CE amplifier simulator.

This module only builds a netlist, invokes the external ngspice executable,
and parses the data that ngspice writes. It never computes circuit physics
itself: every plotted number comes from a real solver run.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence

ANALYSES = ("dc", "ac", "tran")
MODEL_NAME = "QNPN_CLASSROOM"
MODEL_DESCRIPTION = (
    "QNPN_CLASSROOM - NPN reference model defined in spice_engine.py "
    "(IS=2e-15 A, BF from form, VAF=100 V). "
    "This is a reproducible teaching model, not a specific commercial part."
)
TIMEOUT_SECONDS = 30


class SpiceError(RuntimeError):
    """Raised when ngspice is missing, fails, times out, or yields no data."""

    def __init__(self, message: str, log: str = "") -> None:
        super().__init__(message)
        self.log = log


@dataclass
class SimulationResult:
    analysis: str
    engine: str
    model: str
    values: Dict[str, float] = field(default_factory=dict)
    traces: List[Dict[str, Any]] = field(default_factory=list)
    netlist: str = ""
    log: str = ""
    warnings: List[str] = field(default_factory=list)


def find_ngspice() -> str:
    """Locate ngspice without ever using a shell command string."""

    candidates: List[str] = []
    env_path = os.environ.get("NGSPICE_EXECUTABLE", "").strip()
    if env_path:
        candidates.append(env_path)
    which_con = shutil.which("ngspice_con")
    if which_con:
        candidates.append(which_con)
    which = shutil.which("ngspice")
    if which:
        candidates.append(which)
    bin_dir = (
        Path.home()
        / "AppData"
        / "Local"
        / "Programs"
        / "ngspice-47"
        / "Spice64"
        / "bin"
    )
    candidates.append(str(bin_dir / "ngspice_con.exe"))
    candidates.append(str(bin_dir / "ngspice.exe"))
    candidates.append("/usr/local/bin/ngspice")
    candidates.append("/usr/bin/ngspice")

    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise SpiceError(
        "ไม่พบ ngspice executable กรุณาติดตั้ง ngspice และเพิ่ม into PATH "
        "หรือตั้งค่า NGSPICE_EXECUTABLE"
    )


def engine_version(executable: str) -> str:
    try:
        completed = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
        text = (completed.stdout or "") + (completed.stderr or "")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            if "ngspice-" in line.lower():
                return line.lstrip("* ").strip()
        return lines[0] if lines else "ngspice (version unknown)"
    except (OSError, subprocess.SubprocessError):
        return "ngspice (version unknown)"


def _num(value: float) -> str:
    """Write a validated float in a SPICE-safe form."""

    return f"{value:.9g}"


def build_netlist(params: Dict[str, float], analysis: str) -> str:
    """Create one analysis-specific netlist for the reference CE circuit."""

    if analysis not in ANALYSES:
        raise SpiceError(f"Analysis mode ไม่รู้จัก: {analysis}")

    vcc = params["vcc"]
    r1, r2, rc, re, rl = (params[k] for k in ("r1", "r2", "rc", "re", "rl"))
    cin, cout = params["cin_f"], params["cout_f"]
    amp, freq, beta = params["amp"], params["freq"], params["beta"]

    source = (
        f"VIN IN 0 DC 0 AC {_num(amp)} "
        f"SIN(0 {_num(amp)} {_num(freq)} 0 0 0)"
    )
    model = (
        f".model {MODEL_NAME} NPN "
        f"(IS=2e-15 BF={_num(beta)} VAF=100 CJC=10p CJE=20p TF=0.3n)"
    )

    lines = [
        "* Lab 04 - CE amplifier, voltage-divider bias, unbypassed RE",
        f"VCC VCC 0 DC {_num(vcc)}",
        "VSENSE VCC CSNODE DC 0",
        f"R1 VCC BASE {_num(r1)}",
        f"R2 BASE 0 {_num(r2)}",
        f"RC CSNODE COLL {_num(rc)}",
        f"RE EMIT 0 {_num(re)}",
        "Q1 COLL BASE EMIT " + MODEL_NAME,
        f"CIN IN BASE {_num(cin)}",
        f"COUT COLL OUT {_num(cout)}",
        f"RL OUT 0 {_num(rl)}",
        source,
        model,
        ".control",
    ]

    if analysis == "dc":
        lines += [
            "  op",
            "  wrdata results.txt v(base) v(emit) v(coll) v(coll,emit) i(vsense)",
        ]
    elif analysis == "ac":
        lines += [
            "  ac dec 40 1 10meg",
            "  wrdata results.txt frequency vdb(out) vp(out) vdb(in) vp(in)",
        ]
    else:
        period = 1.0 / freq
        tstop = 5.0 * period
        tstep = tstop / 2000.0
        lines += [
            f"  tran {_num(tstep)} {_num(tstop)} 0",
            "  wrdata results.txt time v(in) v(out)",
        ]

    lines += ["  quit", ".endc", ".end", ""]
    return "\n".join(lines)


def _parse_wrdata(
    path: Path,
    names: Sequence[str],
    components: Sequence[int],
) -> List[Dict[str, float]]:
    """Parse ngspice wrdata output.

    ngspice writes one line per point. For each requested vector it writes the
    x-axis value again, followed by one real component, or two components for
    a complex vector (real then imaginary). We keep the first component.
    """

    raw_lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not raw_lines:
        raise SpiceError("ngspice เขียนไฟล์ผลลัพธ์ว่าง (wrdata ไม่มีข้อมูล)")

    rows: List[Dict[str, float]] = []
    for line in raw_lines:
        try:
            parts = [float(part) for part in line.replace(",", " ").split()]
        except ValueError:
            continue

        cursor = 0
        row: Dict[str, float] = {}
        for name, count in zip(names, components):
            cursor += 1  # skip the repeated x-axis value
            if cursor + count > len(parts):
                raise SpiceError(
                    f"ngspice output ขาดข้อมูลของ {name} (wrdata column ไม่ครบ)"
                )
            row[name] = parts[cursor]
            cursor += count
        rows.append(row)

    if not rows:
        raise SpiceError("ไม่สามารถแปลงข้อมูลตัวเลขจาก ngspice output ได้")
    return rows


def _keyed(rows: List[Dict[str, float]], wanted: str) -> str:
    """Find a wrdata column by its ngspice spelling."""

    if not rows:
        return wanted
    for key in rows[0]:
        if key == wanted or key.lower() == wanted.lower():
            return key
    raise SpiceError(f"ngspice output ไม่มีคolumn {wanted}")


def run_simulation(params: Dict[str, float], analysis: str) -> SimulationResult:
    """Run one real ngspice analysis and return parsed engineering data."""

    executable = find_ngspice()
    version = engine_version(executable)
    netlist = build_netlist(params, analysis)

    columns = {
        "dc": ["v(base)", "v(emit)", "v(coll)", "v(coll,emit)", "i(vsense)"],
        "ac": ["frequency", "vdb(out)", "vp(out)", "vdb(in)", "vp(in)"],
        "tran": ["time", "v(in)", "v(out)"],
    }[analysis]
    # Number of written components per vector: frequency is complex in .ac;
    # all other requested vectors are real scalar expressions.
    components = {
        "dc": [1, 1, 1, 1, 1],
        "ac": [2, 1, 1, 1, 1],
        "tran": [1, 1, 1],
    }[analysis]

    with tempfile.TemporaryDirectory(prefix="lab04-ngspice-") as tmp:
        workdir = Path(tmp)
        (workdir / "circuit.cir").write_text(netlist, encoding="utf-8")

        try:
            completed = subprocess.run(
                [
                    executable,
                    "-b",
                    "-o",
                    "ngspice.log",
                    "circuit.cir",
                ],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SpiceError(
                f"ngspice หมดเวลา ({TIMEOUT_SECONDS} s) กรุณาลดช่วงความถี่/เวลา",
                exc.stdout or "",
            ) from exc
        except OSError as exc:
            raise SpiceError(f"เรียก ngspice ไม่ได้: {exc}") from exc

        log_path = workdir / "ngspice.log"
        log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        if not log.strip():
            log = (completed.stdout or "") + (completed.stderr or "")

        if completed.returncode != 0:
            raise SpiceError(
                f"ngspice exit code {completed.returncode} (การจำลองไม่สำเร็จ)",
                log,
            )

        data_path = workdir / "results.txt"
        if not data_path.exists():
            raise SpiceError("ngspice ไม่ได้เขียนไฟล์ results.txt", log)

        rows = _parse_wrdata(data_path, columns, components)

    result = SimulationResult(
        analysis=analysis,
        engine=version,
        model=MODEL_DESCRIPTION,
        netlist=netlist,
        log=log,
    )

    if analysis == "dc":
        vb_key = _keyed(rows, "v(base)")
        ve_key = _keyed(rows, "v(emit)")
        vc_key = _keyed(rows, "v(coll)")
        vce_key = _keyed(rows, "v(coll,emit)")
        ic_key = _keyed(rows, "i(vsense)")
        last = rows[-1]
        result.values = {
            "vb": last[vb_key],
            "ve": last[ve_key],
            "vc": last[vc_key],
            "vce": last[vce_key],
            "ic": last[ic_key],
        }
        if result.values["ic"] <= 0:
            result.warnings.append("IC ≤ 0: วงจรอยู่ในย่าน Cutoff ตามผล ngspice")
        if result.values["vce"] <= 0.2:
            result.warnings.append("VCE ≤ 0.2 V: ผลจำลองอยู่ใกล้/ในย่าน Saturation")
    elif analysis == "ac":
        f_key = _keyed(rows, "frequency")
        out_db_key = _keyed(rows, "vdb(out)")
        out_ph_key = _keyed(rows, "vp(out)")
        in_db_key = _keyed(rows, "vdb(in)")
        in_ph_key = _keyed(rows, "vp(in)")

        freqs = [row[f_key] for row in rows]
        gains = [row[out_db_key] - row[in_db_key] for row in rows]
        # ngspice vp() returns radians in this build; convert to degrees.
        phases = [
            (
                (math.degrees(row[out_ph_key] - row[in_ph_key]) + 180.0) % 360.0
            ) - 180.0
            for row in rows
        ]
        result.traces = [
            {
                "name": "Gain |Vout/Vin| (dB)",
                "x": freqs,
                "y": gains,
                "color": "#0f7d8c",
            },
            {
                "name": "Phase Vout/Vin (deg)",
                "x": freqs,
                "y": phases,
                "color": "#b05a25",
            },
        ]

        peak_index = max(range(len(gains)), key=gains.__getitem__)
        target = gains[peak_index] - 3.0
        rising = next(
            (
                f
                for f, g in zip(freqs[: peak_index + 1], gains[: peak_index + 1])
                if g >= target
            ),
            None,
        )
        falling = next(
            (f for f, g in zip(freqs[peak_index:], gains[peak_index:]) if g <= target),
            None,
        )
        result.values["gain_peak_db"] = gains[peak_index]
        if rising is not None:
            result.values["f_low_3db_hz"] = rising
        if falling is not None:
            result.values["f_high_3db_hz"] = falling
        if rising is None and falling is None:
            result.warnings.append(
                "-3 dB point not determined in sweep range (1 Hz - 10 MHz)"
            )
    else:
        t_key = _keyed(rows, "time")
        vin_key = _keyed(rows, "v(in)")
        vout_key = _keyed(rows, "v(out)")
        result.traces = [
            {
                "name": "Vin (V)",
                "x": [row[t_key] for row in rows],
                "y": [row[vin_key] for row in rows],
                "color": "#0f7d8c",
            },
            {
                "name": "Vout (V)",
                "x": [row[t_key] for row in rows],
                "y": [row[vout_key] for row in rows],
                "color": "#b05a25",
            },
        ]
        vin_peak = max(abs(v) for v in result.traces[0]["y"])
        vout_peak = max(abs(v) for v in result.traces[1]["y"])
        result.values = {"vin_peak_v": vin_peak, "vout_peak_v": vout_peak}
        if vin_peak > 0:
            result.values["gain_peak_abs"] = vout_peak / vin_peak

    return result
