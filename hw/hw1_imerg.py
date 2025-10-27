import numpy as np
import os, sys 
sys.path.insert(0, '..')
import utils.utils_plot_cartopy as ucartopy
import utils.utils_read as uread
import utils.utils_draw as udraw
import matplotlib as mpl
from datetime import datetime, timedelta
mpl.use('agg')
import matplotlib.pyplot as plt
import multiprocessing
import pandas as pd


lonb = [105, 137]
latb = [12,   37]
levb = [1000., 700.]

def draw_gpm_and_local_rain(nowtime):
    print(nowtime)
    df = pd.read_csv(f'./csv/weather_{nowtime.year}.csv')
    idx = df['time']==nowtime.strftime('%Y-%m-%d')
    df_wtype = df[idx].iloc[0]

    #lon_i, lat_i, rain_i  = uread.read_imerg_daily(nowtime, lonb, latb,cores=1)
    #rain_i *= 24   #convert unit to mm/d
    lon_i, lat_i, rain_i  = uread.read_imerg_from_dailydata(nowtime,lonb,latb)

    lon_e, lat_e, suf_geo_e  = uread.read_era5_2d('suf_geo', nowtime,lonb,latb)
    topo_e = suf_geo_e/9.8

    ## lon_e, lat_e, mslp_e  = uread.read_era5_2d('msl', nowtime,lonb,latb)
    ## mslp_e /= 100. # hPa
    ## lon_e, lat_e, _, u_e  = uread.read_era5_3d('u',nowtime,lonb,latb,[1000., 1000.])
    ## u_e = u_e[0]
    ## lon_e, lat_e, _, v_e  = uread.read_era5_3d('v',nowtime,lonb,latb,[1000., 1000.])
    ## v_e = v_e[0]

    sw_ivt_lonlat = [115.,119.,20.,22]
    tc_ivt_lonlat = [115.,130.,17.,32.]

    #rain_bounds = np.array([1, 3, 5, 7, 10, 15, 20, 30, 35])
    rain_bounds = [1, 2, 5, 10, 15, 20, 30, 50, 100]
    rain_cmap        = plt.cm.jet
    rain_cmap.set_under((1,1,1,0.))
    rain_norm        = mpl.colors.BoundaryNorm(rain_bounds, 256, extend='max')

    topo_bounds= np.arange(0,3500.1,500)
    topo_cmap       = plt.cm.Greys
    topo_norm       = mpl.colors.BoundaryNorm(topo_bounds, 256, extend='max')
    
    # Figure initialize
    udraw.set_figure_defalut()
    fig = plt.figure(figsize=(12, 8))
    plottools = ucartopy.PlotTools_cartopy()
    ax1   = plottools.Axe_map(fig, 111, xlim_=lonb, ylim_=latb,
                              xloc_=np.arange(lonb[0], lonb[-1]+0.001, 5), 
                              yloc_=np.arange(latb[0], latb[-1]+0.001, 5))
    ax1.set_position([0.05, 0.05, 0.8, 0.85])
    c = ax1.get_position()
    h = c.height/4
    h0 = c.height/3
    cax1  = fig.add_axes([c.x1+0.01, c.y0+h0*0, 0.03, h])
    cax2  = fig.add_axes([c.x1+0.01, c.y0+h0*1, 0.03, h])
    #cax3  = fig.add_axes([c.x1+0.01, c.y0+h0*2, 0.03, h])

    # Taiwan TOPO
    CO=ax1.contourf(lon_e, lat_e, np.where(topo_e>50,topo_e,np.nan),
                 cmap = topo_cmap, levels=topo_bounds, extend='max')
    cbar = fig.colorbar(CO, orientation='vertical', cax=cax1)
    cbar.ax.set_title('TOPO[m]', fontsize=15, y=1.05, loc='left')

    # Imerg
    rain_i = np.where(rain_i>1,rain_i,np.nan)
    PC = ax1.pcolormesh(lon_i, lat_i, rain_i, alpha=0.8, norm=rain_norm,cmap=rain_cmap)
    cbar = fig.colorbar(PC, orientation='vertical', cax=cax2)
    cbar.ax.set_title('rain[mm/d]', fontsize=15, y=1.05, loc='left')
   
    ## # quiver, wind 
    ## skip = 3
    ## QV = ax1.quiver(lon_e[::skip], lat_e[::skip], 
    ##                 u_e[::skip,::skip], v_e[::skip,::skip],
    ##                 scale_units='xy', scale=20,
    ##                 color='k')
   
    ## # mean_sea_level_pressure
    ## CO = ax1.contour(lon_e, lat_e, mslp_e, levels=np.arange(800,1051,2), linewidths=[2], colors=['k'])
    ## plt.clabel(CO, fmt='%.0f')

    plottools.Plot_cartopy_map(ax1)
    datestr=nowtime.strftime("%Y-%m-%d")
    ax1.set_title(f'{datestr}\nIMERG',
        loc='left', fontweight='bold', fontsize=20)
    wtype_str    = df_wtype['wtype']
    diurnal_flag = '1' if df_wtype['diurnal_rain'] else '0'
    #print(nowtime, f', {wtype_str:>15s}, {diurnal_str:>15s}')
    ax1.set_title(wtype_str, loc='right', fontweight='bold', fontsize=20)

    datestr=nowtime.strftime("%Y%m%d")
    plt.savefig(f'hw1_imerg_{datestr}_{wtype_str}_{diurnal_flag}.png', facecolor='w', bbox_inches='tight', dpi=400)


if __name__=='__main__':
    ## datelist = []
    ## initime = datetime(2001,6,1)
    ## ndays = 30
    ## datelist += [ [initime + timedelta(days=iday) ] for iday in range(ndays) ]

    ## datelist = []
    ## initime = datetime(2001,6,19)
    ## ndays = 2
    ## datelist += [ [initime + timedelta(days=iday) ] for iday in range(ndays) ]
    ## datelist = [[datetime(2001,6,28)], [datetime(2001,6,4)]]

    datelist = [\
                [datetime(2018, 6,24)],
               ]

    cores = 1
    # Use multiprocessing to fetch variable data in parallel
    with multiprocessing.Pool(processes=cores) as pool:
        results = pool.starmap(draw_gpm_and_local_rain,
            datelist)
   
