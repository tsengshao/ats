import os
import sys
import multiprocessing
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from ivt_gsrm_common import (
    SW_IVT_LONLAT,
    TC_IVT_LONLAT,
    lonb,
    latb,
    levb,
    get_ivt_values as get_gsrm_ivt_values,
    get_tw_hourly_rain,
)
sys.path.insert(0, '..')
import utils.utils_cwa as ucwa
import utils.utils_read as uread


SUPPORTED_MODELS = {'nicam', 'icon', 'obs'}
MAX_PROCESSES = 10

# Shared weather-type criteria used by obs, nicam, and icon.
SW_IVT_THRESHOLD = 250.0
SW_IVT_DIR_MIN = 200.0
SW_IVT_DIR_MAX = 280.0
TC_IVT_THRESHOLD = 1000.0
TC_IVT_LOWER_THRESHOLD = 500.0
TC_IVT_VORT_THRESHOLD = 50.0 * 1e-4


def build_obs_datelist():
    datelist = []
    ndays = 30 + 31 + 31 + 30
    for year in range(2001, 2021):
        start_time = datetime(year, 6, 1)
        datelist.extend(
            start_time + timedelta(days=iday)
            for iday in range(ndays)
        )
    return datelist


def build_gsrm_datelist():
    start_time = datetime(2020, 6, 2)
    end_time = datetime(2020, 10, 1)
    ndays = (end_time - start_time).days
    return [
        start_time + timedelta(days=iday)
        for iday in range(ndays)
    ]


def get_obs_ivt(nowtime, lev_lowb=levb):
    lon_obs, lat_obs, lev_obs, u_obs = uread.read_era5_3d('u', nowtime, lonb, latb, lev_lowb)
    lon_obs, lat_obs, lev_obs, v_obs = uread.read_era5_3d('v', nowtime, lonb, latb, lev_lowb)
    lon_obs, lat_obs, lev_obs, q_obs = uread.read_era5_3d('q', nowtime, lonb, latb, lev_lowb)

    u_obs = np.nan_to_num(u_obs, nan=0.0)
    v_obs = np.nan_to_num(v_obs, nan=0.0)
    q_obs = np.nan_to_num(q_obs, nan=0.0)

    ivt_x = -1.0 / 9.8 * np.trapezoid(u_obs * q_obs, x=lev_obs * 100.0, axis=0)
    ivt_y = -1.0 / 9.8 * np.trapezoid(v_obs * q_obs, x=lev_obs * 100.0, axis=0)

    lat_rad = np.deg2rad(lat_obs)
    dlat_m = np.gradient(lat_obs)[:, None] * 111000.0
    dlon_m = np.gradient(lon_obs)[None, :] * 111000.0 * np.cos(lat_rad)[:, None]
    ivt_zeta = np.gradient(ivt_y, axis=1) / dlon_m - np.gradient(ivt_x, axis=0) / dlat_m
    return lon_obs, lat_obs, ivt_x, ivt_y, ivt_zeta


def get_gsrm_ivt(model, nowtime, lev_lowb=levb):
    lon_gs, lat_gs, lev_gs, u_gs = uread.read_gsrm(
        model, 'ua', nowtime, lonb, latb, lev_lowb, daily=True, tw_time=False
    )
    lon_gs, lat_gs, lev_gs, v_gs = uread.read_gsrm(
        model, 'va', nowtime, lonb, latb, lev_lowb, daily=True, tw_time=False
    )
    lon_gs, lat_gs, lev_gs, q_gs = uread.read_gsrm(
        model, 'hus', nowtime, lonb, latb, lev_lowb, daily=True, tw_time=False
    )

    u_gs = np.nan_to_num(u_gs, nan=0.0)
    v_gs = np.nan_to_num(v_gs, nan=0.0)
    q_gs = np.nan_to_num(q_gs, nan=0.0)

    ivt_x = -1.0 / 9.8 * np.trapezoid(u_gs * q_gs, x=lev_gs * 100.0, axis=0)
    ivt_y = -1.0 / 9.8 * np.trapezoid(v_gs * q_gs, x=lev_gs * 100.0, axis=0)

    lat_rad = np.deg2rad(lat_gs)
    dlat_m = np.gradient(lat_gs)[:, None] * 111000.0
    dlon_m = np.gradient(lon_gs)[None, :] * 111000.0 * np.cos(lat_rad)[:, None]
    ivt_zeta = np.gradient(ivt_y, axis=1) / dlon_m - np.gradient(ivt_x, axis=0) / dlat_m
    return lon_gs, lat_gs, ivt_x, ivt_y, ivt_zeta


def decide_weather_by_criteria(sw_ivt, sw_ivt_dir, tc_ivt, tc_ivt_vort_max):
    if (
        sw_ivt > SW_IVT_THRESHOLD
        and SW_IVT_DIR_MIN <= sw_ivt_dir <= SW_IVT_DIR_MAX
        and tc_ivt < TC_IVT_THRESHOLD
    ):
        return 'sw'

    if (
        (tc_ivt > TC_IVT_LOWER_THRESHOLD and tc_ivt_vort_max  > TC_IVT_VORT_THRESHOLD)
        or tc_ivt > TC_IVT_THRESHOLD
    ):
        return 'tc'

    return 'other'


def criteria_dict():
    return {
        'sw_ivt_threshold': SW_IVT_THRESHOLD,
        'sw_ivt_dir_min': SW_IVT_DIR_MIN,
        'sw_ivt_dir_max': SW_IVT_DIR_MAX,
        'tc_ivt_threshold': TC_IVT_THRESHOLD,
        'tc_ivt_lower_threshold': TC_IVT_LOWER_THRESHOLD,
        'tc_ivt_vort_threshold': TC_IVT_VORT_THRESHOLD,
    }


def check_ats_diurnal(diurnal_array):
    morning = np.nansum(diurnal_array[:, :9], axis=1)
    afternoon = np.nansum(diurnal_array[:, 9:], axis=1)
    morning = np.nanmax(morning)
    afternoon = np.nanmax(afternoon)
    diurnal_idx = (
        (morning < 5)
        * (afternoon > 30)
        * (np.nanmean(morning) < np.nanmean(afternoon))
    )
    return diurnal_idx


def get_cwa_station_rainfall(datestr, daily=True):
    wtab_module = ucwa.weather_table(
        year_list=np.arange(2001, 2021).tolist(),
        month_list=np.arange(5, 10).tolist(),
        lat_range=(22, 20),
        lon_range=(115, 119),
    )
    if datestr not in wtab_module.DLIST:
        print('STOP!!, datetime(' + datestr + ' not in cwa datasets')
        return [0], [0], [0]

    pcp_table = wtab_module.get_cwb_precip_table(datestr, accumulate_daily=daily)
    if daily:
        data = pcp_table['precip']
        idx_not_nan = np.where(~np.isnan(data))[0]
        data = data[idx_not_nan].values
        stn_lon = pcp_table['stn_lon'].values[idx_not_nan]
        stn_lat = pcp_table['stn_lat'].values[idx_not_nan]
        idx_sort = np.argsort(data)
        return stn_lon[idx_sort], stn_lat[idx_sort], data[idx_sort]

    data = pcp_table['precip']
    nstn = data.size
    data = np.concatenate(data).reshape(nstn, 24)
    idx_not_nan = np.where(~np.all(np.isnan(data), axis=1))[0]
    stn_lon = pcp_table['stn_lon'].values[idx_not_nan]
    stn_lat = pcp_table['stn_lat'].values[idx_not_nan]
    data = data[idx_not_nan, :]
    idx_sort = np.argsort(np.nanmax(data, axis=1))
    return stn_lon[idx_sort], stn_lat[idx_sort], data[idx_sort, :]


def summarize_weather(model, nowtime, lon, lat, ivtx, ivty, ivtzeta, diurnal_rain):
    ivt = np.sqrt(ivtx ** 2 + ivty ** 2)

    _, _, sw_ivtx_mean, _ = get_gsrm_ivt_values(
        lon, lat, ivtx, ivtzeta, SW_IVT_LONLAT
    )
    _, _, sw_ivty_mean, _ = get_gsrm_ivt_values(
        lon, lat, ivty, ivtzeta, SW_IVT_LONLAT
    )
    sw_ivt_mean = np.sqrt(sw_ivtx_mean ** 2 + sw_ivty_mean ** 2)
    sw_ivt_dir = (180.0 + np.arctan2(sw_ivtx_mean, sw_ivty_mean) * 180.0 / np.pi) % 360.0

    _, tc_ivt_max, _, tc_ivt_zeta_max = get_gsrm_ivt_values(
        lon, lat, ivt, ivtzeta, TC_IVT_LONLAT
    )
    wtype = decide_weather_by_criteria(sw_ivt_mean, sw_ivt_dir, tc_ivt_max, tc_ivt_zeta_max)

    output = {
        'time': nowtime.strftime('%Y-%m-%d'),
        'model': model,
        'wtype': wtype,
        'diurnal_rain': bool(diurnal_rain),
        'sw_ivt_mean': sw_ivt_mean,
        'sw_ivt_dir': sw_ivt_dir,
        'tc_ivt_max': tc_ivt_max,
        'tc_ivt_zeta_max': tc_ivt_zeta_max,
    }
    output.update(criteria_dict())
    return output


def export_obs_row(nowtime):
    lon_obs, lat_obs, ivtx_obs, ivty_obs, ivtzeta_obs = get_obs_ivt(nowtime)
    _, _, stn_rain_hr = get_cwa_station_rainfall(nowtime.strftime('%Y%m%d'), daily=False)
    diurnal_rain = check_ats_diurnal(stn_rain_hr)
    return summarize_weather(
        'obs',
        nowtime,
        lon_obs,
        lat_obs,
        ivtx_obs,
        ivty_obs,
        ivtzeta_obs,
        diurnal_rain,
    )


def export_gsrm_row(model, nowtime):
    lon_gs, lat_gs, ivtx_gs, ivty_gs, ivtzeta_gs = get_gsrm_ivt(model, nowtime)
    # _, _, _, rain_land = get_tw_hourly_rain(model, nowtime)
    lon_tw, lat_tw, tw_mask, _, rain_land = get_tw_hourly_rain(model, nowtime)
    diurnal_rain = check_ats_diurnal(rain_land)
    return summarize_weather(
        model,
        nowtime,
        lon_gs,
        lat_gs,
        ivtx_gs,
        ivty_gs,
        ivtzeta_gs,
        diurnal_rain,
    )


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python export_weather_csv.py <nicam|icon|obs>')

    model = sys.argv[1].lower()
    if model not in SUPPORTED_MODELS:
        raise SystemExit(f'Unsupported model: {model}')

    if model == 'obs':
        datelist = build_obs_datelist()
        worker = export_obs_row
        work_items = datelist
    else:
        datelist = build_gsrm_datelist()
        worker = None
        work_items = [(model, nowtime) for nowtime in datelist]

    nproc = min(len(work_items), os.cpu_count() or 1, MAX_PROCESSES)
    with multiprocessing.Pool(processes=nproc) as pool:
        if model == 'obs':
            results = pool.map(worker, work_items)
        else:
            results = pool.starmap(export_gsrm_row, work_items)

    os.makedirs('./csv', exist_ok=True)
    df = pd.DataFrame(results)
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time')
    df['year'] = df['time'].dt.year
    df['time'] = df['time'].dt.strftime('%Y-%m-%d')

    for year, year_df in df.groupby('year', sort=True):
        outfile = f'./csv/{model}_{year}.csv'
        year_df = year_df.drop(columns='year')
        year_df.to_csv(outfile, index=False)
        print(f'write -> {outfile}')


if __name__ == '__main__':
    main()
