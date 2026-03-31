from __future__ import annotations

import argparse
import os
import pathlib
import sys
from datetime import datetime

import numpy as np

THIS_DIR = pathlib.Path(__file__).resolve().parent
PARENT_DIR = THIS_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

os.environ.setdefault("MPLCONFIGDIR", "/tmp")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import skewt
from utils import utils_read as uread


def parse_time(time_str: str) -> datetime:
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
            return datetime.strptime(time_str, fmt)
        except ValueError:
            pass
    raise ValueError(f"Unsupported time format: {time_str}")


def wrap_lon(lon: float) -> float:
    return lon % 360.0


def lon_diff(lon: np.ndarray, target_lon: float) -> np.ndarray:
    return np.abs((lon - target_lon + 180.0) % 360.0 - 180.0)


def nearest_xy(lon: np.ndarray, lat: np.ndarray, target_lon: float, target_lat: float) -> tuple[int, int]:
    lon = np.asarray(lon)
    lat = np.asarray(lat)
    target_lon = wrap_lon(target_lon)

    if lon.ndim != 1 or lat.ndim != 1:
        raise ValueError("Expected 1-D lon/lat arrays.")

    ilon = int(np.argmin(lon_diff(lon, target_lon)))
    ilat = int(np.argmin(np.abs(lat - target_lat)))
    return ilat, ilon


def sort_profile(p: np.ndarray, *fields: np.ndarray) -> tuple[np.ndarray, ...]:
    order = np.argsort(p)[::-1]
    out = [np.asarray(p)[order]]
    for field in fields:
        out.append(np.asarray(field)[order])
    return tuple(out)


def valid_profile_mask(*fields: np.ndarray) -> np.ndarray:
    mask = np.ones_like(np.asarray(fields[0]), dtype=bool)
    for field in fields:
        arr = np.asarray(field)
        mask &= np.isfinite(arr)
    return mask


def read_era5_profile(nowtime: datetime, lon: float, lat: float, levb: tuple[float, float]) -> dict:
    lon_arr, lat_arr, lev, q = uread.read_era5_3d("q", nowtime, levb=levb)
    _, _, _, t = uread.read_era5_3d("t", nowtime, levb=levb)
    _, _, _, u = uread.read_era5_3d("u", nowtime, levb=levb)
    _, _, _, v = uread.read_era5_3d("v", nowtime, levb=levb)
    _, _, _, z = uread.read_era5_3d("z", nowtime, levb=levb)

    ilat, ilon = nearest_xy(lon_arr, lat_arr, lon, lat)
    profile = {
        "p": lev,
        "t": t[:, ilat, ilon],
        "q": q[:, ilat, ilon],
        "u": u[:, ilat, ilon],
        "v": v[:, ilat, ilon],
        "z": z[:, ilat, ilon] / skewt.C.G,
        "lon": float(lon_arr[ilon]),
        "lat": float(lat_arr[ilat]),
        "source_label": "ERA5",
    }
    return profile


def read_gsrm_profile(model: str, nowtime: datetime, lon: float, lat: float, levb: tuple[float, float]) -> dict:
    lon_arr, lat_arr, lev, q = uread.read_gsrm(model, "hus", nowtime, levb=levb, daily=True)
    _, _, _, t = uread.read_gsrm(model, "ta", nowtime, levb=levb, daily=True)
    _, _, _, u = uread.read_gsrm(model, "ua", nowtime, levb=levb, daily=True)
    _, _, _, v = uread.read_gsrm(model, "va", nowtime, levb=levb, daily=True)
    _, _, _, z = uread.read_gsrm(model, "zg", nowtime, levb=levb, daily=True)

    ilat, ilon = nearest_xy(lon_arr, lat_arr, lon, lat)
    profile = {
        "p": lev,
        "t": t[:, ilat, ilon],
        "q": q[:, ilat, ilon],
        "u": u[:, ilat, ilon],
        "v": v[:, ilat, ilon],
        "z": z[:, ilat, ilon],
        "lon": float(lon_arr[ilon]),
        "lat": float(lat_arr[ilat]),
        "source_label": model.upper(),
    }
    return profile


def read_profile(source: str, nowtime: datetime, lon: float, lat: float, levb: tuple[float, float]) -> dict:
    source = source.lower()
    if source == "era5":
        return read_era5_profile(nowtime, lon, lat, levb)
    if source in {"nicam", "icon"}:
        return read_gsrm_profile(source, nowtime, lon, lat, levb)
    raise ValueError(f"Unsupported source: {source}")


def build_skewt_inputs(profile: dict) -> dict:
    p, t, q, u, v, z = sort_profile(
        profile["p"], profile["t"], profile["q"], profile["u"], profile["v"], profile["z"]
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
    lcl_p = parcel_lev[lev_idx]
    cape_tv, cin_tv, _, lfc_p, el_p = skewt.cape_cin_tv_style(
        parcel_t, parcel_qv, parcel_lev, t, q, p, lcl_p=lcl_p
    )
    cwv = -1.0 * np.trapezoid(q, p * 100.0) / skewt.C.G
    ivtx = -1.0 * np.trapezoid(q * u, p * 100.0) / skewt.C.G
    ivty = -1.0 * np.trapezoid(q * v, p * 100.0) / skewt.C.G

    return {
        "p": p,
        "t_c": t - 273.15,
        "td_c": td,
        "z": z,
        "the": the,
        "thes": thes,
        "parcel_lev": parcel_lev,
        "parcel_t": parcel_t,
        "parcel_thes": parcel_thes,
        "cape": cape_tv,
        "cin": cin_tv,
        "lcl": lcl_p,
        "lfc": lfc_p,
        "el": el_p,
        "cwv": cwv,
        "ivtx": ivtx,
        "ivty": ivty,
    }


def finite_or_nan(value: float | None) -> float:
    return np.nan if value is None else float(value)


def default_output_path(source: str, nowtime: datetime, lon: float, lat: float) -> pathlib.Path:
    stamp = nowtime.strftime("%Y%m%d%H%M")
    return THIS_DIR / f"skewt_{source.lower()}_{stamp}_{lon:.2f}_{lat:.2f}.png"


def plot_profile(
    source: str,
    nowtime: datetime,
    lon: float,
    lat: float,
    *,
    levb: tuple[float, float] = (1000.0, 100.0),
    savepath: str | None = None,
    show: bool = False,
) -> tuple[dict, dict, pathlib.Path]:
    profile = read_profile(source, nowtime, lon, lat, levb)
    skewt_input = build_skewt_inputs(profile)
    output_path = pathlib.Path(savepath) if savepath else default_output_path(source, nowtime, lon, lat)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    title = (
        f"{profile['source_label']} {nowtime:%Y-%m-%d} "
        f"nearest=({profile['lon']:.2f}E,{profile['lat']:.2f}N)"
    )
    skewt.plot_skewt_mse(
        skewt_input["p"],
        skewt_input["t_c"],
        skewt_input["td_c"],
        skewt_input["z"],
        skewt_input["parcel_lev"],
        skewt_input["parcel_t"],
        skewt_input["the"],
        skewt_input["thes"],
        skewt_input["parcel_thes"],
        skewt_input["cape"],
        skewt_input["cin"],
        skewt_input["lcl"],
        finite_or_nan(skewt_input["lfc"]),
        finite_or_nan(skewt_input["el"]),
        title=title,
        savepath=str(output_path),
        show=show,
    )
    return profile, skewt_input, output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read ERA5/NICAM/ICON daily-mean profile at nearest grid point and plot Skew-T."
    )
    parser.add_argument("source", choices=["era5", "nicam", "icon"])
    parser.add_argument("time", help="e.g. 20180719 or 2018-07-19T00:00")
    parser.add_argument("lon", type=float)
    parser.add_argument("lat", type=float)
    parser.add_argument("--pmin", type=float, default=100.0)
    parser.add_argument("--pmax", type=float, default=1000.0)
    parser.add_argument("--output", default=None)
    parser.add_argument("--show", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    nowtime = parse_time(args.time)
    levb = (args.pmax, args.pmin)
    try:
        profile, skewt_input, output_path = plot_profile(
            args.source,
            nowtime,
            args.lon,
            args.lat,
            levb=levb,
            savepath=args.output,
            show=args.show,
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            f"Input data not found for source={args.source}, time={nowtime:%Y-%m-%d}: {exc}"
        ) from exc

    print(
        f"{profile['source_label']} nearest grid point: "
        f"lon={profile['lon']:.3f}, lat={profile['lat']:.3f}"
    )
    print(
        f"CAPE={skewt_input['cape']:.2f} J/kg, CIN={skewt_input['cin']:.2f} J/kg, "
        f"LCL={skewt_input['lcl']:.1f} hPa, "
        f"LFC={np.nan if skewt_input['lfc'] is None else skewt_input['lfc']:.1f} hPa, "
        f"EL={np.nan if skewt_input['el'] is None else skewt_input['el']:.1f} hPa"
    )
    print(
        f"CWV={skewt_input['cwv']:.2f} mm, "
        f"IVTx={skewt_input['ivtx']:.2f} kg/m/s, "
        f"IVTy={skewt_input['ivty']:.2f} kg/m/s"
    )
    print(f"saved: {output_path}")


if __name__ == "__main__":
    main()
