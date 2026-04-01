#!/home/shaoyu/miniforge3/envs/easy/bin/python
from __future__ import annotations

import os
import pathlib
import sys
from multiprocessing import Pool
from datetime import datetime

THIS_DIR = pathlib.Path(__file__).resolve().parent
PARENT_DIR = THIS_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

os.environ.setdefault("MPLCONFIGDIR", "/tmp")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import numpy as np
import pandas as pd

import skewt
from utils import utils_read as uread


def parse_time(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value

    formats = (
        "%Y%m%d",
        "%Y%m%d%H",
        "%Y%m%d%H%M",
        "%Y-%m-%d",
        "%Y-%m-%d %H",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H",
        "%Y-%m-%dT%H:%M",
    )
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise ValueError(f"Unsupported time format: {value}")


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "t", "yes", "y"}:
            return True
        if normalized in {"0", "false", "f", "no", "n"}:
            return False
    raise ValueError(f"Unsupported boolean value: {value}")


def csv_value_matches(series: pd.Series, expected: object) -> pd.Series:
    if isinstance(expected, bool):
        return series.map(parse_bool) == expected
    if expected is None:
        return series.isna()
    return series.astype(str).str.strip() == str(expected)


def wrap_lon(lon: float) -> float:
    return lon % 360.0


def lon_diff(lon: np.ndarray, target_lon: float) -> np.ndarray:
    return np.abs((np.asarray(lon) - target_lon + 180.0) % 360.0 - 180.0)


def coord_token(value: float, positive: str, negative: str, scale: int = 1000) -> str:
    sign = positive if value >= 0.0 else negative
    magnitude = int(round(abs(value) * scale))
    return f"{sign}{magnitude:06d}"


def mean_lon_deg(lon_values: np.ndarray) -> float:
    lon_rad = np.deg2rad(np.asarray(lon_values))
    mean_angle = np.arctan2(np.mean(np.sin(lon_rad)), np.mean(np.cos(lon_rad)))
    return np.rad2deg(mean_angle) % 360.0


def finite_or_nan(value: float | None) -> float:
    return np.nan if value is None else float(value)


def sort_profile(p: np.ndarray, *fields: np.ndarray) -> tuple[np.ndarray, ...]:
    order = np.argsort(np.asarray(p))[::-1]
    out = [np.asarray(p)[order]]
    for field in fields:
        out.append(np.asarray(field)[order])
    return tuple(out)


def valid_profile_mask(*fields: np.ndarray) -> np.ndarray:
    mask = np.ones_like(np.asarray(fields[0]), dtype=bool)
    for field in fields:
        mask &= np.isfinite(np.asarray(field))
    return mask


def get_selector(case: dict) -> dict:
    selector = dict(case.get("selector", {"method": "nearest"}))
    method = selector.get("method", "nearest")
    if method not in {"nearest", "box_mean"}:
        raise ValueError(f"Unsupported selector method: {method}")
    if method == "box_mean":
        selector.setdefault("lon_half_width", 0.5)
        selector.setdefault("lat_half_width", 0.5)
    return selector


def build_selection(lon: np.ndarray, lat: np.ndarray, target_lon: float, target_lat: float, selector: dict) -> dict:
    lon = np.asarray(lon)
    lat = np.asarray(lat)
    target_lon = wrap_lon(target_lon)
    target_lat = float(target_lat)

    if lon.ndim != 1 or lat.ndim != 1:
        raise ValueError("Expected 1-D lon/lat arrays.")

    method = selector["method"]
    if method == "nearest":
        ilon = int(np.argmin(lon_diff(lon, target_lon)))
        ilat = int(np.argmin(np.abs(lat - target_lat)))
        return {
            "method": "nearest",
            "lon_idx": np.array([ilon], dtype=int),
            "lat_idx": np.array([ilat], dtype=int),
            "actual_lon": float(lon[ilon]),
            "actual_lat": float(lat[ilat]),
            "label": f"nearest ({lon[ilon]:.2f}E,{lat[ilat]:.2f}N)",
        }

    lon_half = float(selector["lon_half_width"])
    lat_half = float(selector["lat_half_width"])
    lon_mask = lon_diff(lon, target_lon) <= lon_half
    lat_mask = np.abs(lat - target_lat) <= lat_half
    lon_idx = np.where(lon_mask)[0]
    lat_idx = np.where(lat_mask)[0]
    if lon_idx.size == 0 or lat_idx.size == 0:
        raise ValueError("box_mean selected no grid points.")

    lon_sel = lon[lon_idx]
    lat_sel = lat[lat_idx]
    return {
        "method": "box_mean",
        "lon_idx": lon_idx,
        "lat_idx": lat_idx,
        "actual_lon": float(mean_lon_deg(lon_sel)),
        "actual_lat": float(np.mean(lat_sel)),
        "lon_min": float(np.min(lon_sel)),
        "lon_max": float(np.max(lon_sel)),
        "lat_min": float(np.min(lat_sel)),
        "lat_max": float(np.max(lat_sel)),
        "label": (
            f"box mean lon[{np.min(lon_sel):.2f},{np.max(lon_sel):.2f}] "
            f"lat[{np.min(lat_sel):.2f},{np.max(lat_sel):.2f}]"
        ),
    }


def extract_profile(data: np.ndarray, selection: dict) -> np.ndarray:
    arr = np.asarray(data)
    if arr.ndim != 3:
        raise ValueError("Expected 3-D field with dimensions (lev, lat, lon).")

    lat_idx = selection["lat_idx"]
    lon_idx = selection["lon_idx"]
    subset = arr[:, lat_idx, :][:, :, lon_idx]
    if selection["method"] == "nearest":
        return np.squeeze(subset[:, 0, 0])
    return np.nanmean(subset, axis=(1, 2))


def resolve_time_label(source: str, nowtime: datetime, daily_mean: bool) -> str:
    if source.lower() == "era5" or daily_mean:
        return nowtime.strftime("%Y-%m-%d daily mean")
    return nowtime.strftime("%Y-%m-%d %H:%M")


def resolve_time_token(source: str, nowtime: datetime, daily_mean: bool) -> str:
    if source.lower() == "era5" or daily_mean:
        return nowtime.strftime("%Y%m%d_daymean")
    return nowtime.strftime("%Y%m%d_at%H%M")


def filter_case_dates_from_csv(
    csv_path: str | pathlib.Path,
    *,
    filters: dict[str, object] | None = None,
) -> list[str]:
    csv_path = pathlib.Path(csv_path)
    df = pd.read_csv(csv_path)
    filters = dict(filters or {})

    mask = pd.Series(True, index=df.index)
    for column, expected in filters.items():
        if column not in df.columns:
            raise KeyError(f"Column {column!r} not found in {csv_path}")
        if column == "model" and expected is not None:
            mask &= df[column].astype(str).str.strip().str.lower() == str(expected).strip().lower()
            continue
        mask &= csv_value_matches(df[column], expected)

    return df.loc[mask, "time"].astype(str).tolist()


def build_cases_from_csv_dates(
    csv_path: str | pathlib.Path,
    *,
    model: str,
    lon: float,
    lat: float,
    filters: dict[str, object] | None = None,
    daily_mean: bool = True,
    selector: dict | None = None,
    figure_output_dir: str | pathlib.Path = "./fig",
    profile_output_dir: str | pathlib.Path = "./prof",
    levb: tuple[float, float] = (1000.0, 10.0),
    extra_case_fields: dict | None = None,
) -> list[dict]:
    filters = dict(filters or {})
    filters.setdefault("model", model)
    dates = filter_case_dates_from_csv(csv_path, filters=filters)
    selector_cfg = dict(selector or {"method": "nearest"})
    extra_fields = dict(extra_case_fields or {})

    cases: list[dict] = []
    for time_str in dates:
        case = {
            "model": model,
            "time": time_str,
            "lon": lon,
            "lat": lat,
            "daily_mean": daily_mean,
            "selector": dict(selector_cfg),
            "figure_output_dir": figure_output_dir,
            "profile_output_dir": profile_output_dir,
            "levb": levb,
        }
        case.update(extra_fields)
        cases.append(case)
    return cases


def read_raw_fields(source: str, nowtime: datetime, levb: tuple[float, float], daily_mean: bool) -> dict:
    source = source.lower()
    if source == "era5":
        lon, lat, lev, q = uread.read_era5_3d("q", nowtime, levb=levb)
        _, _, _, t = uread.read_era5_3d("t", nowtime, levb=levb)
        _, _, _, u = uread.read_era5_3d("u", nowtime, levb=levb)
        _, _, _, v = uread.read_era5_3d("v", nowtime, levb=levb)
        _, _, _, z = uread.read_era5_3d("z", nowtime, levb=levb)
        z = z / skewt.C.G
        source_label = "ERA5"
    elif source in {"nicam", "icon"}:
        lon, lat, lev, q = uread.read_gsrm(source, "hus", nowtime, levb=levb, daily=daily_mean)
        _, _, _, t = uread.read_gsrm(source, "ta", nowtime, levb=levb, daily=daily_mean)
        _, _, _, u = uread.read_gsrm(source, "ua", nowtime, levb=levb, daily=daily_mean)
        _, _, _, v = uread.read_gsrm(source, "va", nowtime, levb=levb, daily=daily_mean)
        _, _, _, z = uread.read_gsrm(source, "zg", nowtime, levb=levb, daily=daily_mean)
        source_label = source.upper()
    else:
        raise ValueError(f"Unsupported source: {source}")

    return {
        "source": source,
        "source_label": source_label,
        "lon": np.asarray(lon),
        "lat": np.asarray(lat),
        "lev": np.asarray(lev),
        "q": np.asarray(q),
        "t": np.asarray(t),
        "u": np.asarray(u),
        "v": np.asarray(v),
        "z": np.asarray(z),
        "daily_mean": bool(daily_mean),
        "time_label": resolve_time_label(source, nowtime, daily_mean),
        "time_token": resolve_time_token(source, nowtime, daily_mean),
    }


def build_profile(case: dict) -> dict:
    source = case["model"].lower()
    nowtime = parse_time(case["time"])
    levb = tuple(case.get("levb", (1000.0, 100.0)))
    daily_mean = bool(case.get("daily_mean", source != "era5"))
    selector = get_selector(case)

    raw = read_raw_fields(source, nowtime, levb, daily_mean)
    selection = build_selection(raw["lon"], raw["lat"], case["lon"], case["lat"], selector)

    p, t, q, u, v, z = sort_profile(
        raw["lev"],
        extract_profile(raw["t"], selection),
        extract_profile(raw["q"], selection),
        extract_profile(raw["u"], selection),
        extract_profile(raw["v"], selection),
        extract_profile(raw["z"], selection),
    )

    mask = valid_profile_mask(p, t, q, u, v, z) & (p > 0.0) & (q >= 0.0)
    p = p[mask]
    t = t[mask]
    q = q[mask]
    u = u[mask]
    v = v[mask]
    z = z[mask]

    if p.size < 3:
        raise ValueError("Profile has too few valid levels.")

    td = skewt.cal_dewpoint_from_p_T_q(p, t, q)
    qvs, _ = skewt.cal_qv_rv_saturated(p, t)
    the = skewt.cal_equivalent_potential_temperature(p, q, t)
    thes = skewt.cal_equivalent_potential_temperature(p, qvs, t)
    parcel_lev, parcel_t, parcel_qv, parcel_thes, lev_idx = skewt.parcel_profile(p[0], t[0], q[0])
    lcl_p = float(parcel_lev[lev_idx])
    cape, cin, _, lfc_p, el_p = skewt.cape_cin_tv_style(
        parcel_t, parcel_qv, parcel_lev, t, q, p, lcl_p=lcl_p
    )

    cwv = -1.0 * np.trapezoid(q, p * 100.0) / skewt.C.G
    ivtx = -1.0 * np.trapezoid(q * u, p * 100.0) / skewt.C.G
    ivty = -1.0 * np.trapezoid(q * v, p * 100.0) / skewt.C.G
    ivt_mag = float(np.hypot(ivtx, ivty))

    ivt700 = compute_layer_ivt(p, q, u, v, pbot=1000.0, ptop=700.0)

    return {
        "source": source,
        "source_label": raw["source_label"],
        "requested_lon": float(case["lon"]),
        "requested_lat": float(case["lat"]),
        "actual_lon": float(selection["actual_lon"]),
        "actual_lat": float(selection["actual_lat"]),
        "selector": selection,
        "time": nowtime,
        "time_label": raw["time_label"],
        "time_token": raw["time_token"],
        "daily_mean": daily_mean,
        "p": p,
        "t": t,
        "td_c": td,
        "q": q,
        "u": u,
        "v": v,
        "z": z,
        "the": the,
        "thes": thes,
        "parcel_lev": parcel_lev,
        "parcel_t": parcel_t,
        "parcel_thes": parcel_thes,
        "cape": float(cape),
        "cin": float(cin),
        "lcl": lcl_p,
        "lfc": lfc_p,
        "el": el_p,
        "cwv": float(cwv),
        "ivtx": float(ivtx),
        "ivty": float(ivty),
        "ivt_mag": ivt_mag,
        "ivt_1000_700": ivt700,
    }


def compute_layer_ivt(
    p: np.ndarray, q: np.ndarray, u: np.ndarray, v: np.ndarray, *, pbot: float, ptop: float
) -> dict:
    mask = (p <= pbot) & (p >= ptop)
    if np.count_nonzero(mask) < 2:
        return {"u": np.nan, "v": np.nan, "mag": np.nan}

    pu = -1.0 * np.trapezoid(q[mask] * u[mask], p[mask] * 100.0) / skewt.C.G
    pv = -1.0 * np.trapezoid(q[mask] * v[mask], p[mask] * 100.0) / skewt.C.G
    return {"u": float(pu), "v": float(pv), "mag": float(np.hypot(pu, pv))}


def default_base_name(profile: dict) -> str:
    lon_token = coord_token(profile["actual_lon"], "E", "W")
    lat_token = coord_token(profile["actual_lat"], "N", "S")
    selector_token = profile["selector"]["method"]
    return f"{profile['source']}_{profile['time_token']}_{lon_token}_{lat_token}_{selector_token}"


def save_profile_txt(profile: dict, output_dir: pathlib.Path, base_name: str) -> pathlib.Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    outpath = output_dir / f"prof_{base_name}.txt"
    data = np.column_stack(
        [
            profile["p"],
            profile["t"],
            profile["q"] * 1000.0,
            profile["u"],
            profile["v"],
        ]
    )
    header = "    P[hPa]       T[K]   Qv[g/kg]     U[m/s]     V[m/s]"
    np.savetxt(outpath, data, fmt="%10.4f %10.4f %10.4f %10.1f %10.1f", header=header, comments="")
    return outpath


def plot_profile_figure(
    profile: dict,
    *,
    output_dir: pathlib.Path,
    base_name: str,
    show: bool = False,
    dpi: int = 300,
    plot_config: dict | None = None,
) -> pathlib.Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / f"skewt_{base_name}.png"
    title = (
        f"{profile['source_label']}  {profile['time_label']}  "
        f"lon={profile['actual_lon']:.2f}E lat={profile['actual_lat']:.2f}N  "
        f"{profile['selector']['label']}"
    )
    ivt700 = profile["ivt_1000_700"]
    cfg = dict(plot_config or {})
    cfg["additional_text"] = (
        f"CWV: {profile['cwv']:.1f} mm\n"
        f"IVT: {profile['ivt_mag']:.1f} kg/m/s\n"
        f"IVT 1000-700: {ivt700['mag']:.1f}\n"
        f"({ivt700['u']:.1f}, {ivt700['v']:.1f}) kg/m/s"
    )
    skewt.plot_skewt_mse(
        profile["p"],
        profile["t"] - 273.15,
        profile["td_c"],
        profile["z"],
        profile["parcel_lev"],
        profile["parcel_t"],
        profile["the"],
        profile["thes"],
        profile["parcel_thes"],
        profile["cape"],
        profile["cin"],
        profile["lcl"],
        finite_or_nan(profile["lfc"]),
        finite_or_nan(profile["el"]),
        u=profile["u"],
        v=profile["v"],
        title=title,
        plot_config=cfg,
        savepath=str(png_path),
        show=show,
        dpi=dpi,
    )
    return png_path


def process_case(case: dict) -> dict:
    profile = build_profile(case)
    figure_output_dir = pathlib.Path(case.get("figure_output_dir", THIS_DIR / "fig"))
    profile_output_dir = pathlib.Path(case.get("profile_output_dir", THIS_DIR / "prof"))
    base_name = case.get("base_name", default_base_name(profile))
    fig_path = plot_profile_figure(
        profile,
        output_dir=figure_output_dir,
        base_name=base_name,
        show=bool(case.get("show", False)),
        dpi=int(case.get("dpi", 300)),
        plot_config=case.get("plot_config"),
    )
    prof_path = save_profile_txt(profile, profile_output_dir, base_name)
    return {"profile": profile, "figure_path": fig_path, "profile_path": prof_path}


def process_case_safe(case: dict) -> dict:
    try:
        result = process_case(case)
        profile = result["profile"]
        print(
            f"{profile['source_label']} {profile['time_label']} "
            f"actual lon/lat=({profile['actual_lon']:.3f}, {profile['actual_lat']:.3f}) "
            f"selector={profile['selector']['method']}",
            flush=True,
        )
        print(f"figure: {result['figure_path']}", flush=True)
        print(f"profile: {result['profile_path']}", flush=True)
        print(" ", flush=True)
        return {"ok": True, "case": case, "result": result}
    except FileNotFoundError as exc:
        nowtime = parse_time(case["time"])
        print(
            f"FileNotFoundError for source={case['model']}, time={nowtime:%Y-%m-%d}: {exc}",
            flush=True,
        )
        return {"ok": False, "case": case, "error_type": "FileNotFoundError", "error": str(exc)}
    except Exception as exc:
        nowtime = parse_time(case["time"])
        print(
            f"{type(exc).__name__} for source={case['model']}, time={nowtime:%Y-%m-%d}: {exc}",
            flush=True,
        )
        return {"ok": False, "case": case, "error_type": type(exc).__name__, "error": str(exc)}


def run_cases_parallel(cases: list[dict], nproc: int = 5) -> list[dict]:
    with Pool(processes=nproc) as pool:
        return pool.map(process_case_safe, cases)


def main() -> None:
    model = "icon"
    filters = {
        #"wtype": "other",
        #"diurnal_rain": True,
        "model": model, 
    }
    csv_path = THIS_DIR.parent / "synoptic" / "csv" / f"{model}_2020.csv"
    cases = build_cases_from_csv_dates(
        csv_path,
        model=model,
        # TPE location
        lon=121.514689,
        lat=25.037363,
        filters=filters,
        daily_mean=True,
        selector={
            "method": "box_mean",
            "lon_half_width": 0.125,
            "lat_half_width": 0.125,
        },
        figure_output_dir=f"./fig/{model}",
        profile_output_dir=f"./prof/{model}",
    )
    if not cases:
        print(f"No cases found in {csv_path} for filters={filters}.")
        return

    nproc = min(5, len(cases))
    run_cases_parallel(cases, nproc=nproc)


if __name__ == "__main__":
    main()
