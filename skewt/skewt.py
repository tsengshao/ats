#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skew-T log-p with parcel ascent (dry to LCL, then moist)
- constants grouped in one place
- thermodynamic utilities separated and documented
- clean SkewX projection
- one entry-point function to plot

Usage:
  python skewt_parcel.py         # expects data.txt in ./ with p,h,T,K Td,K q(g/kg)
  or import and call plot_skewt(...)
"""

from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, ScalarFormatter, NullFormatter
from matplotlib import transforms, axis as maxis, spines as mspines
from matplotlib.projections import register_projection
from matplotlib.axes import Axes
from dataclasses import dataclass
from scipy.interpolate import interp1d

# =========================================================
# =============== Physical constants (SI) =================
# =========================================================
@dataclass(frozen=True)
class Const:
    RD: float   = 287.05      # dry-air gas constant [J kg-1 K-1]
    RV: float   = 461.5       # water-vapor gas constant [J kg-1 K-1]
    CP: float   = 1004.0      # cp of dry air [J kg-1 K-1]
    G: float    = 9.81        # gravity [m s-2]
    LV0: float  = 2.5e6       # latent heat (approx const) [J kg-1]
    T0: float   = 273.15      # in K
    P0: float   = 1000.0      # reference pressure [hPa]
    @property
    def EPS(self) -> float:    # epsilon = Rd/Rv
        return self.RD / self.RV

C = Const()

# =========================================================
# ================= SkewX projection ======================
# =========================================================
class SkewXTick(maxis.XTick):
    def update_position(self, loc):
        """Update tick location and control visibility for both sides."""
        self._loc = loc
        super().update_position(loc)

        # Determine which side (lower or upper) should show the tick
        lower = self._need_lower()
        upper = self._need_upper()

        # Directly control visibility of tick lines and labels
        # This is safer than overriding tick1On / label1On in new Matplotlib
        self.tick1line.set_visible(lower)
        self.label1.set_visible(lower)
        self.tick2line.set_visible(upper)
        #self.label2.set_visible(upper)

    def _has_default_loc(self):
        """Return True if tick has no defined location."""
        return self.get_loc() is None

    @staticmethod
    def _in_interval(interval, x):
        """Return True if value x is within the given interval (lo, hi)."""
        lo, hi = interval
        return (lo <= x) and (x <= hi)

    def _need_lower(self):
        """Return True if tick should appear on the lower x-axis."""
        return self._has_default_loc() or self._in_interval(self.axes.lower_xlim, self.get_loc())

    def _need_upper(self):
        """Return True if tick should appear on the upper x-axis."""
        return self._has_default_loc() or self._in_interval(self.axes.upper_xlim, self.get_loc())

    def get_view_interval(self):
        """Return the x-axis view interval (required by Matplotlib)."""
        return self.axes.xaxis.get_view_interval()


# ===============================================================
# SkewXAxis class: provide custom tick creation for skew-T axes
# ===============================================================
class SkewXAxis(maxis.XAxis):
    def _get_tick(self, major):
        """Create a SkewXTick. Only two positional args are allowed."""
        tick = SkewXTick(self.axes, None)
        tick._major = bool(major)  # optional tag for major/minor
        return tick

    def get_view_interval(self):
        """Return the x-axis limits for the skew projection."""
        return self.axes.upper_xlim[0], self.axes.lower_xlim[1]


class SkewSpine(mspines.Spine):
    def _adjust_location(self):
        pts = self._path.vertices
        pts[:, 0] = self.axes.upper_xlim if self.spine_type == 'top' else self.axes.lower_xlim

class SkewXAxes(Axes):
    name = 'skewx'
    def _init_axis(self):
        self.xaxis = SkewXAxis(self)
        self.spines['top'].register_axis(self.xaxis)
        self.spines['bottom'].register_axis(self.xaxis)
        self.yaxis = maxis.YAxis(self)
        self.spines['left'].register_axis(self.yaxis)
        self.spines['right'].register_axis(self.yaxis)
    def _gen_axes_spines(self):
        return {'top': SkewSpine.linear_spine(self, 'top'),
                'bottom': mspines.Spine.linear_spine(self, 'bottom'),
                'left': mspines.Spine.linear_spine(self, 'left'),
                'right': mspines.Spine.linear_spine(self, 'right')}
    def _set_lim_and_transforms(self):
        rot = 45  # skew angle
        Axes._set_lim_and_transforms(self)
        self.transDataToAxes = self.transScale + self.transLimits + transforms.Affine2D().skew_deg(rot, 0)
        self.transData = self.transDataToAxes + self.transAxes
        self._xaxis_transform = (transforms.blended_transform_factory(
            self.transScale + self.transLimits, transforms.IdentityTransform()) +
            transforms.Affine2D().skew_deg(rot, 0)) + self.transAxes
    @property
    def lower_xlim(self): return self.axes.viewLim.intervalx
    @property
    def upper_xlim(self):
        pts = [[0., 1.], [1., 1.]]
        return self.transDataToAxes.inverted().transform(pts)[:, 0]

register_projection(SkewXAxes)

# =========================================================
# =============== Thermodynamic utilities =================
# =========================================================
def cal_potential_temperature(P_hPa: np.ndarray, T_K: np.ndarray) -> np.ndarray:
    """theta = T (P0/P)^(Rd/Cp)"""
    return T_K * (C.P0 / P_hPa) ** (C.RD / C.CP)

def cal_temperature_from_theta(P_hPa: np.ndarray, theta_K: np.ndarray) -> np.ndarray:
    """T = theta (P/P0)^(Rd/Cp)"""
    return theta_K * (P_hPa / C.P0) ** (C.RD / C.CP)


def cal_dewpoint_from_p_T_q(p_hPa, T_K, q_kgkg):
    """Return dewpoint temperature (K) from p [hPa], T [K], q [kg/kg]."""
    Ta_C = np.asarray(T_K-273.15)
    # 1. relative humidity
    e_hPa = (q_kgkg * p_hPa) / (0.622 + 0.378 * q_kgkg)
    es_hPa = cal_goff_gratch_es_hPa(T_K)
    RH_pct = e_hPa/es_hPa*100.
    # 2. Magnus equation
    a, b = 17.625, 243.04
    gamma = np.log(RH_pct/100.0) + (a*Ta_C)/(b + Ta_C)
    Td_C = (b * gamma) / (a - gamma)
    return Td_C

def cal_goff_gratch_es_hPa(T_K: np.ndarray) -> np.ndarray:
    """Saturation vapor pressure over liquid/ice (Goff-Gratch)."""
    T = np.asarray(T_K)
    
    #liquid
    esl = 10.0 ** (
        -7.90298 * (373.16 / T - 1.0)
        + 5.02808 * np.log10(373.16 / T)
        - 1.3816e-7 * (10.0 ** (11.344 * (1.0 - T / 373.16)) - 1.0)
        + 8.1328e-3 * (10.0 ** (-3.49149 * (373.16 / T - 1.0)) - 1.0)
        + np.log10(1013.246)
    )

    return esl

def cal_qv_rv_from_e(P_hPa: np.ndarray, e_hPa: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return specific humidity q and mixing ratio r from vapor pressure e and pressure P."""
    P = np.asarray(P_hPa)
    e = np.asarray(e_hPa)
    denom = np.clip(P - e, 1e-6, None)         # prevent division by 0
    r = C.EPS * e / denom                      # kg/kg
    q = r / (1.0 + r)                          # kg/kg
    return q, r

def cal_qv_rv_saturated(P_hPa: np.ndarray, T_K: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Saturated q and r at (P, T)."""
    es = cal_goff_gratch_es_hPa(T_K)
    return cal_qv_rv_from_e(P_hPa, es)

def cal_equivalent_potential_temperature(P_hPa: np.ndarray, qv: np.ndarray, T_K: np.ndarray) -> np.ndarray:
    """Very simple theta_e approximation for diagnostics."""
    return (T_K + C.LV0 / C.CP * qv) * (C.P0 / P_hPa) ** (C.RD / C.CP)

def moist_adiabatic_lapse_rate(T_K: float, P_hPa: float) -> tuple[float, float, float]:
    """
    gamma_m [K/m], qv_sat [kg/kg], r_sat [kg/kg]
    gamma_m = g * (1 + (Lv * r_s)/(Rd * T)) / (Cp + (Lv^2 * r_s * eps)/(Rd * T^2))
    """
    qsat, rsat = cal_qv_rv_saturated(P_hPa, T_K)
    Lv = C.LV0
    num = C.G * (1.0 + (Lv * rsat) / (C.RD * T_K))
    den = C.CP + (Lv**2 * rsat * C.EPS) / (C.RD * T_K**2)
    return float(num / den), float(qsat), float(rsat)

def cal_height_from_pressure(p_hPa, t_K, qv_kgkg):
    p_Pa = p_hPa*100.
    tv_K   = t_K*(1+0.608*qv_kgkg)
    dz      = np.log(p_Pa[:-1]/p_Pa[1:]) * \
                C.RD/C.G * \
                0.5*(tv_K[1:]+tv_K[:-1])
    height  = np.append([0],np.cumsum(dz)) #meter
    return height

from scipy.optimize import brentq

def T_from_thetae(thetae_K: float, p_hPa: float) -> float:
    """
    Invert thetae at a given pressure to get saturated temperature T [K].
    thetae is conserved (pseudo-adiabatic), qv = qvs(T,p).

    Solve F(T) = theta_e(T,p) - thetae_K = 0 with brentq.
    """
    def F(T):
        qvs, _ = cal_qv_rv_saturated(p_hPa, T)
        thetae = cal_equivalent_potential_temperature(p_hPa, qvs, T)
        return float(thetae - thetae_K)

    # Robust bracket: £ce increases monotonically with T at fixed p
    a, b = 180.0, 360.0  # K, wide physical range for troposphere
    Fa, Fb = F(a), F(b)

    # If no sign change (rare), expand once; otherwise fall back to bisection around dry guess
    if Fa * Fb > 0.0:
        a, b = 160.0, 420.0
        Fa, Fb = F(a), F(b)
        if Fa * Fb > 0.0:
            # last resort: return dry-adiabatic estimate (won't usually happen)
            return np.nan

    return brentq(F, a, b, xtol=1e-6, rtol=1e-8, maxiter=100)

# =========================================================
# =============== Parcel ascent (dry and moist) =============
# =========================================================
def parcel_profile(p0_hPa: float, T0_K: float, q0: float,
                   p_top_hPa: float = 100.0, nlev: int = 1001) -> ParcelProfile:
    """
    Build parcel temperature profile from p0 to p_top.
    - Dry-adiabatic ascent to LCL (found by |q0 - qsat_dry| minimum)
    - Above LCL, invert thetae at each pressure level

    Returns:
      ParcelProfile with arrays from surface->top (descending pressure).
    """
    p = np.linspace(p0_hPa, p_top_hPa, nlev)  # decreasing
    # Dry leg
    T_dry = T0_K * (p / p0_hPa) ** (C.RD / C.CP)
    qsat_dry, _ = cal_qv_rv_saturated(p, T_dry)

    lcl_idx = int(np.argmin(np.abs(q0 - qsat_dry)))
    T = np.zeros_like(p)
    qv = np.zeros_like(p)
    theta_es = np.zeros_like(p)
    T[:lcl_idx+1] = T_dry[:lcl_idx+1]
    qv[:lcl_idx+1] = q0
    theta_es[:lcl_idx+1] = cal_equivalent_potential_temperature(p[:lcl_idx+1], qsat_dry[:lcl_idx+1], T_dry[:lcl_idx+1])
    theta_es[lcl_idx+1:] = cal_equivalent_potential_temperature(p[lcl_idx+1], qsat_dry[lcl_idx+1], T_dry[lcl_idx+1])
    
    # Moist segment: invert theta_es at each pressure level
    for k in range(lcl_idx + 1, len(p)):
        T[k] = T_from_thetae(theta_es[lcl_idx+1], p[k])
        qv[k], _     = cal_qv_rv_saturated(p[k], T[k])
        
    # Edge case: never reaches LCL (very dry)
    if lcl_idx >= len(p) - 1:
        theta_es[:] = cal_equivalent_potential_temperature(p, qsat_dry, T_dry)

    return p, T, qv, theta_es, lcl_idx

def compute_cape_cin_LCL_LFC_EL(parcel_lev, parcel_thes, pres_env, thes_env, LCL_p=None, Rd=287.0):
    """
    Compute CIN, CAPE, LCL, LFC, and EL using theta_e-based buoyancy.
    """

    # Convert to arrays
    p_par = np.asarray(parcel_lev, dtype=float)
    th_par = np.asarray(parcel_thes, dtype=float)
    p_env = np.asarray(pres_env, dtype=float)
    th_env = np.asarray(thes_env, dtype=float)

    # Ensure pressures are descending (surface to top)
    if p_par[0] < p_par[-1]:
        p_par, th_par = p_par[::-1], th_par[::-1]

    # Interpolate environmental theta_e to parcel levels
    th_env_on_par = np.interp(np.log(p_par[::-1]), np.log(p_env[::-1]), th_env[::-1])[::-1]

    # Difference (environment - parcel)
    diff = th_env_on_par - th_par
    lnp = np.log(p_par)

    if (LCL_p is not None) and np.isfinite(LCL_p):
        idx_LCL = int(np.searchsorted(-p_par, -float(LCL_p), side="left"))
    else:
        # Estimate LCL index (first region where parcel_thes becomes constant)
        dth = np.abs(np.diff(th_par))
        tol = max(1e-6, 1e-6 * np.nanmax(np.abs(th_par)))
        idx_LCL = np.where(dth < tol)[0]
        idx_LCL = int(idx_LCL[0] + 1) if idx_LCL.size else None
        LCL_p = float(p_par[idx_LCL]) if idx_LCL is not None else None

    # Identify LFC (first crossing: stable ¡÷ unstable) and EL (unstable ¡÷ stable)
    sgn = np.sign(diff)
    LFC_p = None
    EL_p = None
    idx_LFC = idx_EL = None

    if idx_LCL is None:
        start = 0
    else:
        start = idx_LCL

    cross_up = np.where((sgn[:-1] > 0) & (sgn[1:] <= 0))[0]
    if cross_up.size:
        idx_LFC = int(cross_up[cross_up >= start][0] + 1) if np.any(cross_up >= start) else None
    if idx_LFC is not None:
        cross_down = np.where((sgn[:-1] <= 0) & (sgn[1:] > 0))[0]
        if cross_down.size:
            after = cross_down[cross_down >= idx_LFC]
            if after.size:
                idx_EL = int(after[0] + 1)

    LFC_p = float(p_par[idx_LFC]) if idx_LFC is not None else None
    EL_p = float(p_par[idx_EL]) if idx_EL is not None else None

    # Integrate CIN (stable layer) and CAPE (buoyant layer)
    CIN = 0.0
    CAPE = 0.0

    if idx_LFC is not None:
        mask_cin = (diff[:idx_LFC] > 0)
        if np.any(mask_cin):
            CIN = Rd * np.trapezoid(diff[:idx_LFC][mask_cin], lnp[:idx_LFC][mask_cin])

    if (idx_LFC is not None) and (idx_EL is not None) and (idx_EL > idx_LFC):
        seg = diff[idx_LFC:idx_EL]
        x = lnp[idx_LFC:idx_EL]
        if np.any(seg < 0):
            CAPE = Rd * np.trapezoid(seg[seg < 0], x[seg < 0])

    return CIN, CAPE, LCL_p, LFC_p, EL_p

import numpy as np

def cape_cin_tv_style(T_parcel, qv_parcel, press_parcel,
                              T_env, qv_env, press_env,
                              lcl_p=None, lfc_p=None, el_p=None, Rd=287.0):
    """
    Compute CAPE and CIN using Tv, following theta_es-style crossing logic.
    Parcel and environment may have different pressure grids.

    Inputs
    ------
    T_parcel : (n1,) K
    qv_parcel: (n1,) kg/kg
    press_parcel : (n1,) hPa, strictly decreasing (surface -> top)
    T_env    : (n2,) K
    qv_env   : (n2,) kg/kg
    press_env: (n2,) hPa, strictly decreasing (surface -> top)
    lcl_p, lfc_p, el_p : float or None, hPa
    Rd = 287.0  # J kg^-1 K^-1

    Returns
    -------
    CAPE : float, J/kg (>=0)
    CIN  : float, J/kg (<=0 by convention)
    LFC_p, EL_p : float or None, hPa
    """

    # --- basic checks
    T_parcel = np.asarray(T_parcel, float)
    qv_parcel = np.asarray(qv_parcel, float)
    T_env = np.asarray(T_env, float)
    qv_env = np.asarray(qv_env, float)
    p_par = np.asarray(press_parcel, float) 
    p_env = np.asarray(press_env, float)

    if np.any(np.diff(p_par) >= 0) or np.any(np.diff(p_env) >= 0):
        raise ValueError("pressures must strictly decrease with index (surface -> top).")

    # --- interpolate environment to parcel grid
    # to compute consistent Tv difference
    qv_env_i = np.interp(np.log(p_par[::-1]), np.log(p_env[::-1]), qv_env[::-1])[::-1]
    T_env_i  = np.interp(np.log(p_par[::-1]), np.log(p_env[::-1]), T_env[::-1])[::-1]
    Tv_env_i = T_env_i * (1.0 + 0.61 * np.clip(qv_env_i, 0.0, None))

    Tv_env = T_env * (1.0 + 0.61 * np.clip(qv_env, 0.0, None))
    Tv_env_i  = np.interp(np.log(p_par[::-1]), np.log(p_env[::-1]), Tv_env[::-1])[::-1]
    Tv_par = T_parcel * (1.0 + 0.61 * np.clip(qv_parcel, 0.0, None))

    # diff > 0 means stable (CIN region), diff < 0 means buoyant (CAPE region)
    #diff = T_env_i - T_parcel ## for correct level
    diff = Tv_env_i - Tv_par ## for bouyant 
    sgn = np.sign(diff)
    lnp = np.log(p_par)

    # --- determine start index from LCL
    if (lcl_p is not None) and np.isfinite(lcl_p):
        idx_LCL = int(np.searchsorted(-p_par, -float(lcl_p), side="left"))
    else:
        # Dry leg
        T_dry = T_parcel[0] * (p_par / p_par[0]) ** (C.RD / C.CP)
        qsat_dry, _ = cal_qv_rv_saturated(p_par, T_dry)
        idx_LCL = int(np.argmin(np.abs(qv_env[0] - qsat_dry)))
    LCL_p = float(p_par[idx_LCL]) if idx_LCL is not None else None

    # --- find LFC, EL indices (if not supplied)
    idx_LFC = None
    idx_EL = None
    start = idx_LCL


    if (lfc_p is not None) and np.isfinite(lfc_p) and \
       (el_p is not None) and np.isfinite(el_p):
        idx_EL = int(np.argmin(np.abs(p_par - float(el_p))))
        idx_LFC = int(np.argmin(np.abs(p_par - float(lfc_p))))
    else:
        cross_up = np.where((sgn[:-1] > 0) & (sgn[1:] <= 0))[0]
        if cross_up.size:
            idx_LFC = int(cross_up[cross_up >= start][0] + 1) if np.any(cross_up >= start) else None
        if idx_LFC is not None:
            cross_down = np.where((sgn[:-1] <= 0) & (sgn[1:] > 0))[0]
            if cross_down.size:
                after = cross_down[cross_down >= idx_LFC]
                if after.size:
                    idx_EL = int(after[0] + 1)

    # --- pressures at LFC/EL
    LFC_p = float(p_par[idx_LFC]) if idx_LFC is not None else None
    EL_p  = float(p_par[idx_EL])  if idx_EL  is not None else None

    ## print(diff[:idx_LFC])
    ## print(diff[idx_LFC:idx_EL])
    ## print(diff[idx_EL:])


    # --- integrate CIN (stable region) and CAPE (buoyant region)
    CIN = 0.0
    CAPE = 0.0

    # CIN: from surface to LFC, where diff > 0
    if idx_LFC is not None and idx_LFC > 0:
        mask_cin = diff[:idx_LFC] > 0.0
        if np.any(mask_cin):
            CIN = Rd * np.trapezoid(diff[:idx_LFC][mask_cin], lnp[:idx_LFC][mask_cin])
    else:
        mask_cin = diff > 0.0
        if np.any(mask_cin):
            CIN = Rd * np.trapezoid(diff[mask_cin], lnp[mask_cin])

    # CAPE: between LFC and EL (or to top if no EL)
    if (idx_LFC is not None) and (idx_EL is not None) and (idx_EL > idx_LFC):
        seg = diff[idx_LFC:idx_EL]
        x = lnp[idx_LFC:idx_EL]
        mask_cap = seg < 0.0
        if np.any(mask_cap):
            CAPE = Rd * np.trapezoid(seg[mask_cap], x[mask_cap])
    elif (idx_LFC is not None) and (idx_EL is None):
        seg = diff[idx_LFC:]
        x = lnp[idx_LFC:]
        mask_cap = seg < 0.0
        if np.any(mask_cap):
            CAPE = Rd * np.trapezoid(seg[mask_cap], x[mask_cap])

    CAPE = float(max(CAPE, 0.0))
    CIN  = float(min(CIN, 0.0))
    return CAPE, CIN, LCL_p, LFC_p, EL_p

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import ScalarFormatter, NullFormatter


DEFAULT_PLOT_CONFIG = {
    "layout": "three_panel",
    "figsize": None,
    "width_ratios": None,
    "wind_xlim": (-20.0, 20.0),
    "additional_text": None,
    #"wind_arrow_count": 12,
    #"wind_arrow_x": 0.84,
    "wind_arrow_scale": 35.0,
    "wind_arrow_width": 0.010,
    "wind_key_value": 5.0,
    "wind_key_label": "5 m/s",
}


def _resolve_plot_config(plot_config):
    cfg = dict(DEFAULT_PLOT_CONFIG)
    if plot_config:
        cfg.update(plot_config)

    layout = cfg["layout"]
    if layout == "two_panel":
        cfg["figsize"] = cfg["figsize"] or (11, 6)
        cfg["width_ratios"] = cfg["width_ratios"] or [2.2, 1.0]
    elif layout == "three_panel":
        cfg["figsize"] = cfg["figsize"] or (14, 6)
        cfg["width_ratios"] = cfg["width_ratios"] or [2.3, 1.0, 1.0]
    else:
        raise ValueError(f"Unsupported layout: {layout}")
    return cfg


def _finite_or_nan(value):
    return np.nan if value is None else float(value)


def _setup_pressure_axis(ax, plim, yticks):
    ax.set_yscale('log')
    ax.set_ylim(*plim)
    ax.set_yticks(yticks)
    ax.yaxis.set_major_formatter(ScalarFormatter())
    ax.yaxis.set_minor_formatter(NullFormatter())


def _choose_wind_arrow_levels(p, count):
    if len(p) <= count:
        return np.arange(len(p))
    idx = np.linspace(0, len(p) - 1, count).round().astype(int)
    return np.unique(idx)


def _pressure_to_axes_y(ax, pressure_value):
    xy_disp = ax.transData.transform((0.0, pressure_value))
    xy_axes = ax.transAxes.inverted().transform(xy_disp)
    return float(xy_axes[1])


def _add_wind_profile_arrows(ax_wind, p, u, v, plot_cfg):
    #x_center = float(plot_cfg["wind_arrow_x"])
    #arrow_idx = _choose_wind_arrow_levels(np.asarray(p), int(plot_cfg["wind_arrow_count"]))
    x_center = 0.85
    arrow_idx = np.arange(len(p), dtype=int)
    p = np.asarray(p)
    u = np.asarray(u)
    v = np.asarray(v)
    y_axes = np.array([_pressure_to_axes_y(ax_wind, p[idx]) for idx in arrow_idx], dtype=float)
    #mask = (y_axes >= 0.02) & (y_axes <= 0.98)
    mask = np.ones(len(y_axes), dtype=bool)
    if not np.any(mask):
        return None

    arrow_idx = arrow_idx[mask]
    y_axes = y_axes[mask]

    quiver_kwargs = dict(
        pivot='tail',
        angles='uv',
        scale_units='width',
        scale=float(plot_cfg["wind_arrow_scale"]),
        width=float(plot_cfg["wind_arrow_width"]),
        headwidth=3.5,
        headlength=4.5,
        headaxislength=4.0,
        color='0.25',
        transform=ax_wind.transAxes,
        clip_on=False,
        zorder=4,
    )

    q_main = None
    p_alpha = 300.
    for pressure_mask, alpha in ((p[arrow_idx] >= p_alpha, None),
                                 (p[arrow_idx] < p_alpha, 0.5),
                                ):
        if not np.any(pressure_mask):
            continue
        q = ax_wind.quiver(
            np.full(np.count_nonzero(pressure_mask), x_center, dtype=float),
            y_axes[pressure_mask],
            u[arrow_idx][pressure_mask],
            v[arrow_idx][pressure_mask],
            alpha=alpha,
            **quiver_kwargs,
        )
        if q_main is None:
            q_main = q

    return q_main


def _add_skewt_background(ax_skew):
    Tmin, Tmax, nt = -120.0, 100.0, 221
    pbot, ptop, npres = 1000.0, 100.0, 200
    TgC = np.linspace(Tmin, Tmax, nt)
    Pg = np.linspace(pbot, ptop, npres)
    TT, PP = np.meshgrid(TgC + 273.15, Pg)
    TH = cal_potential_temperature(PP, TT)
    q_sat, _ = cal_qv_rv_saturated(PP, TT)
    THES = cal_equivalent_potential_temperature(PP, q_sat, TT)
    ax_skew.contour(TT - 273.15, PP, TH, np.arange(203.15, 430, 10),
                    colors='sienna', linestyles='--', linewidths=0.8, alpha=0.85, zorder=1)
    ax_skew.contour(TT - 273.15, PP, THES, np.arange(240, 450, 15),
                    colors='purple', linestyles='--', linewidths=0.9, alpha=0.75, zorder=1)

    p_rv = np.linspace(1000.0, 600.0, 80)
    rv_levels_gkg = np.array([0.5, 1.0, 2.0, 4.0, 8.0, 12.0, 24.0])
    for rv_gkg in rv_levels_gkg:
        rv_kgkg = rv_gkg / 1000.0
        e_hPa = rv_kgkg * p_rv / (C.EPS + rv_kgkg)
        t_rv = np.array([brentq(lambda T: cal_goff_gratch_es_hPa(T) - e, 180.0, 330.0) for e in e_hPa])
        ax_skew.plot(
            t_rv - 273.15,
            p_rv,
            color='teal',
            linestyle=':',
            linewidth=0.8,
            alpha=0.9,
            zorder=1,
        )
        ax_skew.text(
            t_rv[-1] - 273.15,
            p_rv[-1] - 10,
            f"{rv_gkg:g}",
            color='teal',
            fontsize=8,
            alpha=0.75,
            ha='center',
            va='bottom',
            zorder=1,
        )


def _plot_wind_panel(ax_wind, p, u, v, plot_cfg, plim, yticks, additional_text):
    ax_wind.plot(u, p, color='tab:blue', lw=2.0, label='u')
    ax_wind.plot(v, p, color='tab:orange', lw=2.0, label='v')
    ax_wind.axvline(0.0, color='0.6', lw=1.0)
    _setup_pressure_axis(ax_wind, plim, yticks)
    ax_wind.tick_params(axis='y', which='both', labelleft=False)
    ax_wind.grid(True, which='major', linestyle='--', alpha=0.35)
    ax_wind.set_xlim(*plot_cfg["wind_xlim"])
    ax_wind.set_xlabel('Wind [m/s]', fontsize=14)
    ax_wind.tick_params(axis='both', labelsize=12)
    ax_wind.legend(loc='lower left', fontsize=10)
    q = _add_wind_profile_arrows(ax_wind, p, u, v, plot_cfg)
    if q is not None:
        ax_wind.quiverkey(
            q,
            X=0.125,
            Y=0.175,
            U=float(plot_cfg["wind_key_value"]),
            label=str(plot_cfg["wind_key_label"]),
            labelpos='S',
            coordinates='axes',
            color='0.25',
        )


# ---------- Plot ----------
def plot_skewt_mse(
    p, T, Td, hei,
    parcel_lev, parcel_t,
    the, thes, parcel_thes,
    CAPE, CIN, LCL, LFC, EL,
    *,
    u=None,
    v=None,
    tlim=(-40, 40),
    plim=(1000, 100),
    title="Skew-T & MSE",
    plot_config=None,
    show=True,
    savepath=None,
    dpi=300
):
    """
    Plot Skew-T with configurable 2-panel or 3-panel layout.
    """
    plot_cfg = _resolve_plot_config(plot_config)
    layout = plot_cfg["layout"]
    fig = plt.figure(figsize=plot_cfg["figsize"])
    gs = GridSpec(
        1, len(plot_cfg["width_ratios"]), figure=fig,
        width_ratios=plot_cfg["width_ratios"],
        left=0.08, right=0.96, top=0.92, bottom=0.10, wspace=0.10
    )

    yticks = np.array([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])
    axes = {}

    ax_skew = fig.add_subplot(gs[0, 0], projection='skewx')
    axes["skewt"] = ax_skew
    ax_skew.grid(True, which="major", linestyle='--', alpha=0.5)
    ax_skew.semilogy(T, p, 'r', lw=2.0, label='T')
    ax_skew.semilogy(Td, p, 'g', lw=2.0, label='Td')
    ax_skew.axvline(0, color='b', lw=1.0)
    ax_skew.semilogy(parcel_t - 273.15, parcel_lev, 'k', lw=2.0, label='Parcel')

    info_text = (
        f"CAPE: {CAPE:.2f} J/kg\n"
        f"CIN: {CIN:.2f} J/kg\n"
        f"EL: {_finite_or_nan(EL):.1f} hPa\n"
        f"LFC: {_finite_or_nan(LFC):.1f} hPa\n"
        f"LCL: {_finite_or_nan(LCL):.1f} hPa"
    )
    if plot_cfg.get("additional_text"):
        info_text = f"{info_text}\n\n{plot_cfg['additional_text']}"
    ax_skew.text(
        0.03, 0.98, info_text,
        transform=ax_skew.transAxes,
        fontsize=14, va='top', ha='left',
        bbox=dict(facecolor='white', alpha=0.8, edgecolor='none')
    )

    _setup_pressure_axis(ax_skew, plim, yticks)
    ax_skew.set_xticks(np.arange(-100, 41, 10))
    ax_skew.set_xticklabels(['' if x <= -50 else f'{x}' for x in np.arange(-100, 41, 10)])
    ax_skew.set_xlim(*tlim)
    ax_skew.set_xlabel('Temperature (degC)', fontsize=16)
    ax_skew.set_ylabel('Pressure [hPa]', fontsize=16)
    ax_skew.tick_params(axis='both', labelsize=14)
    ax_skew.legend(loc='lower left', fontsize=12)
    _add_skewt_background(ax_skew)

    ax_mse = fig.add_subplot(gs[0, 1], aspect='auto')
    axes["thetae"] = ax_mse
    ax_mse.plot(the, p, 'tab:blue', lw=2.0, label=r'$\theta_e$')
    ax_mse.plot(thes, p, 'tab:red', lw=2.0, label=r'$\theta_{es}$')
    ax_mse.plot(parcel_thes, parcel_lev, 'k', lw=2.0, label=r'Parcel $\theta_{es}$')
    _setup_pressure_axis(ax_mse, plim, yticks)
    ax_mse.set_xticks(np.arange(300, 401, 10))
    ax_mse.set_xticklabels(['' if x % 20 != 0 else f'{x}' for x in np.arange(300, 401, 10)])
    ax_mse.tick_params(axis='y', which='both', labelleft=False)
    ax_mse.set_xlim(320, 390)
    ax_mse.grid(True, which='major', linestyle='--', alpha=0.5)
    ax_mse.grid(True, which='minor', linestyle='--', alpha=0.2)
    ax_mse.set_xlabel(r'$\theta_e$ & $\theta_{es}$ [K]', fontsize=16)
    ax_mse.tick_params(axis='both', labelsize=14)
    ax_mse.legend(loc='upper left', fontsize=12)

    if layout == "three_panel":
        if u is None or v is None:
            raise ValueError("u and v are required for three_panel layout.")
        ax_wind = fig.add_subplot(gs[0, 2], aspect='auto')
        axes["wind"] = ax_wind
        _plot_wind_panel(ax_wind, p, u, v, plot_cfg, plim, yticks, plot_cfg.get("additional_text"))

    fig.suptitle(title, fontsize=16)

    if savepath:
        fig.savefig(savepath, dpi=dpi, bbox_inches='tight')
        print(f"Figure saved to {savepath}")

    if show:
        plt.show()

    return fig, axes


if __name__=="__main__":
    # Example: read sample sounding file (p, h, T, Td, q)
    #p, h, T, Td, q = np.loadtxt("data.txt", usecols=range(5), unpack=True)
    p, T, q, u, v = np.loadtxt("prof_20180906_at030.txt", usecols=range(5), unpack=True, skiprows=1)
    T -= 273.15
    pres       = p #hPa !!
    temp       = T+273.15
    qv         = q/1000.

    hei        = cal_height_from_pressure(pres, temp, qv)
    Td         = cal_dewpoint_from_p_T_q(pres, temp, qv)
    th         = cal_potential_temperature(pres,temp)
    qvs, rvs   = cal_qv_rv_saturated(pres, temp)
    the        = cal_equivalent_potential_temperature(pres,qv,temp)
    thes       = cal_equivalent_potential_temperature(pres,qvs,temp)
    parcel_lev, parcel_t, parcel_qv, parcel_thes, lev_idx = parcel_profile(pres[0], temp[0], qv[0])
    lcl_p = parcel_lev[lev_idx]
    CIN, CAPE, LCL, LFC, EL = compute_cape_cin_LCL_LFC_EL(parcel_lev, parcel_thes, pres, thes, LCL_p=lcl_p)
    CAPE_tv, CIN_tv, LCLp_tv, LFCp_tv, ELp_tv = cape_cin_tv_style(parcel_t, parcel_qv, parcel_lev, temp, qv, pres, lcl_p)#, LCL, LFC, EL)
    CWV = -1*np.trapezoid(qv,pres*100.)/C.G
    ivtx = -1*np.trapezoid(qv*u,pres*100.)/C.G
    ivty = -1*np.trapezoid(qv*v,pres*100.)/C.G
    print(f"-----")
    print(f"CIN = {CIN:.2f} J/kg, CAPE = {CAPE:.2f} J/kg")
    print(f"LCL = {LCL:.1f} hPa, LFC = {LFC:.1f} hPa, EL = {EL:.1f} hPa")
    print(f"-----")
    print(f"CINtv = {CIN_tv:.2f} J/kg, CAPEtv = {CAPE_tv:.2f} J/kg")
    print(f"LCLtv = {LCLp_tv:.1f} hPa, LFCtv = {LFCp_tv:.1f} hPa, ELtv = {ELp_tv:.1f} hPa")
    print(f"-----")
    print(f"CWV = {CWV:.2f} mm, IVTx = {ivtx:.2f} kg/m/s, IVTy = {ivty:.2f} kg/m/s")
    plot_skewt_mse(
        p, T, Td, hei,
        parcel_lev, parcel_t,
        the, thes, parcel_thes,
        #CAPE, CIN, LCL, LFC, EL,
        CAPE_tv, CIN_tv, LCL, LFC, EL,
        u=u, v=v,
        savepath="skewt_case1.png",
        show=False,
    )
