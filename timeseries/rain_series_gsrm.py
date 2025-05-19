import numpy as np
import sys, os
sys.path.insert(0, '..')
import utils.utils_read as uread
import utils.utils_draw as udraw
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

lonb = [119.5, 122.5]
latb = [21.5, 26]

# find tw_mask
lon, lat, landfrac = uread.read_gsrm('nicam', 'sftlf', datetime(1970,1,1), lonb, latb)
lon2d, lat2d = np.meshgrid(lon,lat)
condi  = (120<=lon2d) * (lon2d<=122.0) *\
         (21.5<=lat2d) * (lat2d<=25.4) *\
         (landfrac>0.2)
tw_mask = np.where(condi,True,False)
tw_idx  = np.nonzero(tw_mask)

model = 'icon'
#model = 'nicam'
ds = pd.read_csv(f'../obs/shao_ATdays_2020_2020_{model}.txt', header=None)
ds = pd.to_datetime(ds[0])
ndays = ds.size

diurnal_array = np.zeros((24,ndays))
for iday in range(ndays):
    nowdate = ds.iloc[iday]
    for ihr in range(24):
        lon, lat, rainfall = uread.read_gsrm(model, 'pr', nowdate+timedelta(hours=ihr), lonb, latb, tw_time=True)
        rainfall *= 3600. #mm/hr
        diurnal_array[ihr, iday] = np.nanmean(rainfall[tw_idx])

udraw.set_figure_defalut()
fig, ax = plt.subplots(figsize=(6,5.5))
x = np.arange(0,24)
for i in range(diurnal_array.shape[1]):
    plt.plot(x, diurnal_array[:,i], lw=2, c='0.8')
plt.plot(x, diurnal_array.mean(axis=1), lw=8, c='k')
plt.xticks(np.arange(0,25,3), fontsize=20)
plt.yticks([0,1,2,3], fontsize=20)
plt.xlim(6,24)
plt.ylim(0,3.5)
plt.grid(True)
plt.xlabel('Time (h)',fontsize=20)
plt.ylabel('precip. (mm h'+'$^{-1}$'+')', fontsize=20)
plt.title(f'{model.upper()}', fontsize=20, fontweight='bold')
plt.title(f'{ndays:d}', fontsize=15, fontweight='bold', loc='right')
plt.savefig(f'./fig/series_{model}.png', dpi=250, bbox_inches='tight')





