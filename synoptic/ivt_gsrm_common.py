from datetime import datetime, timedelta

import numpy as np
from scipy.ndimage import gaussian_filter

import sys
sys.path.insert(0, '..')
import utils.utils_read as uread


SW_IVT_LONLAT = [115.0, 119.0, 20.0, 22.0]
TC_IVT_LONLAT = [115.0, 127.5, 17.0, 29.5]

lonb = [105.0, 137.0]
latb = [12.0, 37.0]
levb = [1000.0, 700.0]

tw_lonb = [119.5, 122.5]
tw_latb = [21.5, 26.0]
tw_land_lonb = [120.0, 122.0]
tw_land_latb = [21.5, 25.4]

_TW_MASK_CACHE = None


def get_ivt_values(lon, lat, ivt, ivt_z, lonlat):
    ix0 = np.argmin(np.abs(lon - lonlat[0]))
    ix1 = np.argmin(np.abs(lon - lonlat[1])) + 1
    iy0 = np.argmin(np.abs(lat - lonlat[2]))
    iy1 = np.argmin(np.abs(lat - lonlat[3])) + 1

    data = ivt[iy0:iy1, ix0:ix1]
    data_z = gaussian_filter(ivt_z, sigma=4)
    data_z = data_z[iy0:iy1, ix0:ix1]
    return np.nanmin(data), np.nanpercentile(data, 95), np.nanmean(data), np.nanmax(data_z)


def get_tw_mask(model):
    global _TW_MASK_CACHE
    if _TW_MASK_CACHE is not None:
        return _TW_MASK_CACHE

    lon_mask, lat_mask, landfrac = uread.read_gsrm(
        model, 'sftlf', datetime(1970, 1, 1), tw_lonb, tw_latb
    )
    lon2d, lat2d = np.meshgrid(lon_mask, lat_mask)
    mask = (
        (tw_land_lonb[0] <= lon2d)
        * (lon2d <= tw_land_lonb[1])
        * (tw_land_latb[0] <= lat2d)
        * (lat2d <= tw_land_latb[1])
        * (landfrac > 0.2)
    )
    _TW_MASK_CACHE = (lon_mask, lat_mask, mask.astype(bool))
    return _TW_MASK_CACHE


def get_tw_hourly_rain(model, nowtime):
    lon_mask, lat_mask, tw_mask = get_tw_mask(model)
    rain_hourly = []
    for ihr in range(24):
        _, _, rain = uread.read_gsrm(
            model, 'pr', nowtime + timedelta(hours=ihr), tw_lonb, tw_latb, tw_time=True
        )
        rain_hourly.append(rain * 3600.0)
    rain_hourly = np.stack(rain_hourly, axis=0)
    rain_hourly = np.where(np.isnan(rain_hourly), np.nan, rain_hourly)
    rain_land = rain_hourly[:, tw_mask].T
    return lon_mask, lat_mask, tw_mask, rain_hourly, rain_land
