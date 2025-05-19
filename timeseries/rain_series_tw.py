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
        vvmtools_date  = DataRetriever(f"../vvm/case_sw_{date}{swsuffix}")  # data available upon request
    elif case == 'at':
        vvmtools_date  = DataRetriever(f"../vvm/tpe{date}nor")
    else:
        raise ValueError("Argument `case` should be either 'sw' or 'at'.")
    arr_pcp_all    = vvmtools_date.get_var_parallel(var='sprec', time_steps=np.arange(145))
    arr_pcp_all    *= 3600.
    print(arr_pcp_all.shape)
    plottools = ucartopy.PlotTools_cartopy()
    idx_tw    = np.nonzero(plottools.ds_topo.topo>0)
    series = np.zeros(24)
    for i in range(24):
        t0 = i*6+1
        t1 = (i+1)*6+1
        print(t0, t1)
        print(arr_pcp_all[t0:t1,idx_tw[0],idx_tw[1]].shape)
        series[i] = np.mean(arr_pcp_all[t0:t1,idx_tw[0],idx_tw[1]])
    return series

if __name__=='__main__':
    dlist = ['20050702', '20050712', '20050723',
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
    diurnal_array = np.zeros((24, len(dlist)))
    for idy in range(len(dlist)):
        dd = dlist[idy]
        diurnal_array[:,idy] = cal_vvm_dpcp(case=case, date=dd)
        
    udraw.set_figure_defalut()
    fig, ax = plt.subplots(figsize=(6,5.5))
    x = np.arange(1,25)
    for i in range(diurnal_array.shape[1]):
        plt.plot(x, diurnal_array[:,i], lw=2, c='0.8')
    plt.plot(x, diurnal_array.mean(axis=1), lw=8, c='k')
    plt.xticks(np.arange(0,25,3), fontsize=20)
    plt.yticks([0,1,2,3], fontsize=20)
    plt.xlim(6,24)
    plt.ylim(0,3.5)
    plt.grid(True)
    plt.xlabel('Time (h)', fontsize=20)
    plt.ylabel('precip. (mm h'+'$^{-1}$'+')', fontsize=20)
    plt.title(f'TaiwanVVM', fontsize=20, fontweight='bold')
    plt.title(f'{diurnal_array.shape[1]:d}', fontsize=15, fontweight='bold', loc='right')
    plt.savefig(f'./fig/series_taiwanvvm.png', dpi=250, bbox_inches='tight')





