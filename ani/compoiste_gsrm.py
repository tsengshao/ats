import numpy as np
import os, sys 
sys.path.insert(0, '..')
import utils.utils_plot_cartopy as ucartopy
import utils.utils_read as uread
import utils.utils_draw as udraw
import matplotlib.pyplot as plt
import matplotlib as mpl
from datetime import timedelta, datetime
import pandas as pd
import xarray as xr

lonb = [110., 135.]
latb = [10.,   35.]

model = 'icon'
ds = pd.read_csv(f'../obs/shao_ATdays_2020_2020_{model}.txt', header=None)
ds = pd.to_datetime(ds[0])
nday = ds.size

lon_gs,  lat_gs,  pr_gs = \
    uread.read_gsrm(model,'pr',ds.iloc[0],lonb,latb,daily=True,tw_time=True)
composite = np.zeros([1,lat_gs.size, lon_gs.size])
for i in range(nday):
    lon_gs,  lat_gs,  pr_gs = \
        uread.read_gsrm(model,'pr',ds.iloc[i],lonb,latb,daily=True,tw_time=True)
    composite[0,...] += pr_gs / nday

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
ds.to_netcdf(f"../data/rainfall_composite/rcomp_{model}.nc", format="NETCDF4_CLASSIC")

