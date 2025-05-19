import numpy as np
import xarray as xr
import glob
import pandas as pd
from vvmtools.analyze import DataRetriever
import os, sys
sys.path.insert(0,'..')
import utils.utils_read as uread
import utils.utils_draw as udraw
import utils.utils_plot_cartopy as ucartopy
import matplotlib.pyplot as plt

def cal_vvm_dpcp(case:str, date:str, swsuffix:str='', domain_range:tuple=(None, None, None, None), land_only:bool=True):
    # Check
    print(f"Calculating daily precipitation. The Land-only option is now: {land_only}.")
    # Calculation
    j1, j2, i1, i2 = domain_range
    if case == 'sw':
        vvmtools_date  = DataRetriever(f"./vvm/case_sw_{date}{swsuffix}")  # data available upon request
    elif case == 'at':
        vvmtools_date  = DataRetriever(f"./vvm/tpe{date}nor")
    else:
        raise ValueError("Argument `case` should be either 'sw' or 'at'.")
    arr_pcp_all    = vvmtools_date.get_var_parallel(var='sprec', time_steps=np.arange(145))
    arr_day_pcp    = np.sum(arr_pcp_all, axis=0)*3600/6
    plottools = ucartopy.PlotTools_cartopy()
    if land_only:
        arr_day_pcp = np.where(plottools.ds_topo.topo>0, arr_day_pcp, np.nan)
    return arr_day_pcp[j1:j2, i1:i2]

# Composite
def Cal_vvm_dpcp_comp(case:str, datelist:list, land_only:bool=False):
    # Check for available simulation
    if case not in ('sw', 'at'):
        raise ValueError("Argument `case` should be either 'sw' or 'at'.")
    # Calculation
    counter = 1
    for i, dd in enumerate(datelist):
        # Data initialize
        if i < 1:
            arr_day_pcp = cal_vvm_dpcp(case=case, date=dd, land_only=land_only)[..., np.newaxis]
        else:
            try:
                temp    = cal_vvm_dpcp(case=case, date=dd, land_only=land_only)[..., np.newaxis]
            except:
                temp    = cal_vvm_dpcp(case=case, date=dd, swsuffix=f'_sim{counter}', land_only=land_only)[..., np.newaxis]
                counter+= 1
            arr_day_pcp = np.concatenate((arr_day_pcp, temp), axis=-1)
    mean_pcp = np.nanmean(arr_day_pcp, axis=-1)
    return mean_pcp

if __name__=='__main__':
    dlist_atsim32 = ['20050702', '20050712', '20050723',
                     '20060623', '20060718', '20060721',
                     '20070830', 
                     '20080715',
                     '20090707', '20090817', '20090827',
                     '20100629', '20100630', '20100802', '20100803', '20100912',
                     '20110702', '20110723', '20110802', '20110816', '20110821',
                     '20120819',
                     '20130630', '20130703', '20130705', '20130723', '20130807', 
                     '20140703', '20140711', '20140714', '20140825', 
                     '20150613']

    case='at'
    datestr='20140711'

    ## ----- composite -----
    figname=f'{case.upper()}_composite'
    pcp = Cal_vvm_dpcp_comp(case, dlist_atsim32, True)
    plottools, fig, ax, cax0, cax_topo = ucartopy.create_taiwan_axes()
    lon_gs = plottools.ds_topo.lon.values
    lat_gs = plottools.ds_topo.lat.values

    composite = np.zeros((1,lat.size_gs,lon_gs.size))
    composite[0] = pcp/3600/24

    ##### save data
    time = pd.date_range("2020-01-01", periods=1)
    # Create dataset
    ds = xr.Dataset(
        data_vars={
            "rain": (("time", "lat", "lon"), composite,
                     {
                         "long_name": "composite rainfall of afternoon thunderstorm",
                         "units": "kg/m^2/s",  # correct physical units
                         "coordinates": "lon lat",
                         "_FillValue": np.nan
                     })
        },
        coords={
            "lon": ("lon", lon_gs, {
                "standard_name": "longitude",
                "long_name": "longitude",
                "units": "degrees_east",
                "axis": "X"
            }),
            "lat": ("lat", lat_gs, {
                "standard_name": "latitude",
                "long_name": "latitude",
                "units": "degrees_north",
                "axis": "Y"
            }),
            "time": ("time", time,)
        },
        attrs={
            "title": "CF-compliant test file",
            "Conventions": "CF-1.8",
            "institution": "OpenAI Atmospheric Lab",
            "source": "Synthetic data",
            "history": "created with xarray"
        }
    )
    
    # Save with NetCDF4 Classic format (recommended for GrADS)
    ds.to_netcdf(f"../data/rainfall_composite/rcomp_taiwanvvm.nc", format="NETCDF4_CLASSIC")

