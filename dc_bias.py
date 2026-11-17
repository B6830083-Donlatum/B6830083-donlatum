"""DC bias calculations for three NPN common-emitter bias circuits.

Functions:
    calculate_fixed_bias      - RB from VCC to base, emitter grounded
    calculate_emitter_bias    - RB from VCC to base, RE from emitter to ground
    calculate_dc_bias         - voltage divider R1/R2 with RE (Lab 02)

All functions accept SI units (ohm, A, V) and return the same BiasResult
shape so Flask and the template can display every mode identically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

VCE_SATURATION = 0.2  # V - Lab 03 model-validity limit


@dataclass
class BiasResult:
    mode: str
    vth: float
    rth: float
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: str
    warnings: List[str] = field(default_factory=list)


def _result_from_ib(
    mode: str,
    vth: float,
    rth: float,
    ib: float,
    beta: float,
    vcc: float,
    rc: float,
    vbe: float,
    re_for_ve: float,
) -> BiasResult:
    """Build the common result dict from the already-solved base current."""

    ic = beta * ib
    ie = (beta + 1) * ib
    ve = ie * re_for_ve
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    warnings: List[str] = []
    if ib <= 0:
        region = "Cutoff"
        warnings.append(
            f"IB ({ib:.3g} A) ≤ 0: ทรานซิสเตอร์อยู่ในย่าน Cutoff "
            "แบบจำลอง Forward-Active ใช้ไม่ได้"
        )
    elif vce <= VCE_SATURATION or vc < vb:
        region = "Saturation"
        warnings.append(
            f"VCE ({vce:.3f} V) ≤ {VCE_SATURATION:.1f} V หรือ VC ต่ำกว่า VB "
            "แบบจำลอง Forward-Active อาจใช้ไม่ได้ "
            "ค่าที่แสดงเป็นการคำนวณต่อตามสมการเดิม"
        )
    else:
        region = "Forward-Active"

    if vc < 0 and region != "Saturation":
        warnings.append("VC ติดลบจากการคำนวณ ควรตรวจค่า RC ใหม่")

    return BiasResult(
        mode=mode,
        vth=vth,
        rth=rth,
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=warnings,
    )


def calculate_fixed_bias(
    vcc: float,
    rb: float,
    rc: float,
    beta: float,
    vbe: float,
) -> BiasResult:
    """Fixed bias: IB = (VCC - VBE) / RB, emitter grounded."""

    vth = vcc          # Thevenin source seen at RB is VCC
    rth = rb           # with RB as the Thevenin resistance
    ib = 0.0 if vth <= vbe else (vth - vbe) / rth

    return _result_from_ib(
        mode="fixed",
        vth=vth,
        rth=rth,
        ib=ib,
        beta=beta,
        vcc=vcc,
        rc=rc,
        vbe=vbe,
        re_for_ve=0.0,
    )


def calculate_emitter_bias(
    vcc: float,
    rb: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> BiasResult:
    """Emitter bias: IB = (VCC - VBE) / [RB + (beta+1)RE]."""

    vth = vcc
    rth = rb
    denominator = rth + (beta + 1) * re
    ib = 0.0 if vth <= vbe else (vth - vbe) / denominator

    return _result_from_ib(
        mode="emitter",
        vth=vth,
        rth=rth,
        ib=ib,
        beta=beta,
        vcc=vcc,
        rc=rc,
        vbe=vbe,
        re_for_ve=re,
    )


def calculate_dc_bias(
    vcc: float,
    r1: float,
    r2: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> BiasResult:
    """Voltage-divider bias (Lab 02), unchanged equations."""

    vth = vcc * r2 / (r1 + r2)
    rth = (r1 * r2) / (r1 + r2)
    denominator = rth + (beta + 1) * re
    ib = 0.0 if vth <= vbe else (vth - vbe) / denominator

    return _result_from_ib(
        mode="divider",
        vth=vth,
        rth=rth,
        ib=ib,
        beta=beta,
        vcc=vcc,
        rc=rc,
        vbe=vbe,
        re_for_ve=re,
    )
