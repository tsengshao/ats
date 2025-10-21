import numpy as np
import os, sys 
sys.path.insert(0, '..')
import utils.utils_plot_cartopy as ucartopy
import utils.utils_read as uread
import utils.utils_draw as udraw
import utils.utils_cwa as ucwa
import matplotlib as mpl
from datetime import datetime, timedelta
mpl.use('agg')
import matplotlib.pyplot as plt
import multiprocessing
from matplotlib.patches import Rectangle
from scipy.ndimage import gaussian_filter
import pandas as pd


lonb = [105, 137]
latb = [12,   37]
levb = [1000., 700.]

def get_ivt(nowtime, lev_lowb=[1000.,700.]):
    #lev_lowb = [1000., 700.]
    lon_e,  lat_e,  lev_e, u_e   = uread.read_era5_3d('u',nowtime,lonb,latb,lev_lowb)
    lon_e,  lat_e,  lev_e, v_e   = uread.read_era5_3d('v',nowtime,lonb,latb,lev_lowb)
    lon_e,  lat_e,  lev_e, q_e   = uread.read_era5_3d('q',nowtime,lonb,latb,lev_lowb)
    ivt_x = -1./9.8*np.trapz(u_e*q_e, x=lev_e*100., axis=0)
    ivt_y = -1./9.8*np.trapz(v_e*q_e, x=lev_e*100., axis=0)
    # ivt_intensity = np.sqrt(ivt_x**2+ivt_y**2)
    #sw_ivt_dir  = (180+np.arctan2(sw_ivtx_mean,sw_ivty_mean)*180./np.pi)%360
    ivt_zeta = np.gradient(ivt_y,axis=1)/0.25/111000. -\
               np.gradient(ivt_x,axis=0)/(0.25*111000.*np.cos(lat_e[:,None]*np.pi/180))
    return lon_e, lat_e, ivt_x, ivt_y, ivt_zeta

def get_ivt_values(lon, lat, ivt, ivt_z, lonlat=[115.,119.,20.,22]):
    ix0 = np.argmin(np.abs(lon-lonlat[0]))
    ix1 = np.argmin(np.abs(lon-lonlat[1]))+1
    iy0 = np.argmin(np.abs(lat-lonlat[2]))
    iy1 = np.argmin(np.abs(lat-lonlat[3]))+1
    data = ivt[iy0:iy1,ix0:ix1].data
    data_z = gaussian_filter(ivt_z, sigma=4)
    data_z = data_z[iy0:iy1,ix0:ix1].data
    return np.min(data), np.percentile(data, 95), np.mean(data), np.max(data_z)

def decide_weather(sw_ivt, sw_ivt_direct, tc_ivt, tc_ivt_vort_max):
    #if sw_ivt>250 and \
       # sw_ivt_direct>=202.5 and \
       # sw_ivt_direct<=285:
    if sw_ivt>250 and \
       sw_ivt_direct>=200. and \
       sw_ivt_direct<=280. and \
       tc_ivt<1000.:
       return 'sw'
    elif (tc_ivt>500 and tc_ivt_vort_max*1e4>50.) or tc_ivt>1000.:
       return 'tc'
    else:
       return 'other'
    
def get_cwa_station_rainfall(datestr, daily=True):
    wtab_module  = ucwa.weather_table(year_list =np.arange(2001, 2021).tolist(),
                                      month_list=np.arange(5,10).tolist(),
                                      lat_range=(22, 20), lon_range=(115, 119))
    if datestr not in wtab_module.DLIST:
        print('STOP!!, datetime('+datestr+' not in cwa datasets')
        return [0], [0], [0]

    pcp_table = wtab_module.get_cwb_precip_table(datestr, accumulate_daily=daily)
    if daily:
        data = pcp_table['precip']
        idx_not_nan   = np.where(~ np.isnan(data))[0]
        data = data[idx_not_nan].values
        stn_lon = pcp_table['stn_lon'].values[idx_not_nan]
        stn_lat = pcp_table['stn_lat'].values[idx_not_nan]
        idx_sort = np.argsort(data)
        return stn_lon[idx_sort], stn_lat[idx_sort], data[idx_sort]

    else:
        data = pcp_table['precip'] # sereis
        nstn = data.size
        data = np.concatenate(data).reshape(nstn,24)
        idx_not_nan   = np.where(~ np.all(np.isnan(data), axis=1))[0]
        stn_lon = pcp_table['stn_lon'].values[idx_not_nan]
        stn_lat = pcp_table['stn_lat'].values[idx_not_nan]
        data = data[idx_not_nan, :] # remove all nan station
        idx_sort = np.argsort(np.nanmax(data,axis=1))
        return stn_lon[idx_sort], stn_lat[idx_sort], data[idx_sort,:]

def check_ats_diurnal(diurnal_array):
    #idx = np.nonzero(~np.all(diurnal_array,axis=1))[0]
    #diurnal_array = diurnal_array[idx,:]

    morning = np.nansum(diurnal_array[:,:9],axis=1)
    afternoon = np.nansum(diurnal_array[:,9:],axis=1)
    morning    = np.nanmax(morning)
    afternoon  = np.nanmax(afternoon)
    #morning    = np.nanpercentile(morning,95)
    #afternoon  = np.nanpercentile(afternoon,95)
    diurnal_cycle   = np.nanmean(diurnal_array, axis=0)
    diurnal_idx = (morning<10) *\
                 (afternoon>30) *\
                 (np.nanmean(morning)<np.nanmean(afternoon))
    return diurnal_idx


#ats_date = np.load('../obs/shao_ATdays_2005_2020.npy', allow_pickle=True)
#nowtime = ats_date[0]

#for nowtime in ats_date:
def draw_ivt_and_local_rain(nowtime, only_output_flag=False):
    #print(nowtime)
    lon_e, lat_e, ivtx_e, ivty_e, ivtzeta_con_e = get_ivt(nowtime)
    ivts_e = np.sqrt(ivtx_e**2+ivty_e**2)
    lon_e, lat_e, _,   z_e   = uread.read_era5_3d('z',nowtime,lonb,latb,[500.,500.])
    z500 = z_e[0]/9.8

    sw_ivt_lonlat = [115.,119.,20.,22]
    _, _, sw_ivtx_mean, _ = get_ivt_values(lon_e, lat_e, ivtx_e, ivtzeta_con_e, lonlat=sw_ivt_lonlat)
    _, _, sw_ivty_mean, _ = get_ivt_values(lon_e, lat_e, ivty_e, ivtzeta_con_e, lonlat=sw_ivt_lonlat)
    sw_ivt_mean = np.sqrt(sw_ivtx_mean**2+sw_ivty_mean**2)
    sw_ivt_dir  = (180+np.arctan2(sw_ivtx_mean,sw_ivty_mean)*180./np.pi)%360

    tc_ivt_lonlat = [115.,130.,17.,32.]
    _, tc_ivt_max, _, tc_ivt_zeta_max  = get_ivt_values(lon_e, lat_e, ivts_e, ivtzeta_con_e, lonlat=tc_ivt_lonlat)
    wtype_str = decide_weather(sw_ivt_mean, sw_ivt_dir, tc_ivt_max, tc_ivt_zeta_max)
    
    stn_lon, stn_lat, stn_rain = \
        get_cwa_station_rainfall(nowtime.strftime('%Y%m%d'), daily=True)
    stn_lon_hr, stn_lat_hr, stn_rain_hr = \
        get_cwa_station_rainfall(nowtime.strftime('%Y%m%d'), daily=False)

    flag_diurnal = check_ats_diurnal(stn_rain_hr)

    output = {'time':nowtime,
              'wtype':wtype_str,
              'diurnal_rain':flag_diurnal,
              'sw_ivt_mean':sw_ivt_mean,
              'sw_ivt_dir':sw_ivt_dir,
              'tc_ivt_max':tc_ivt_max,
              'tc_ivt_zeta_max':tc_ivt_zeta_max,
             }
    if only_output_flag: return output

    #rain_bounds = np.array([1, 3, 5, 7, 10, 15, 20, 30, 35])
    rain_bounds = [1, 2, 5, 10, 15, 20, 30, 50, 100]
    rain_cmap        = plt.cm.jet
    rain_cmap.set_under((1,1,1,0.))
    rain_norm        = mpl.colors.BoundaryNorm(rain_bounds, 256, extend='max')

    ivt_bounds= np.arange(0,1000.1,250)
    ivt_cmap       = plt.cm.Blues
    ivt_norm       = mpl.colors.BoundaryNorm(ivt_bounds, 256, extend='max')
    
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
    cax3  = fig.add_axes([c.x1+0.01, c.y0+h0*2, 0.03, h])

    ax2   = plt.gcf().add_axes((c.x0, c.y0+c.height*3/5, c.height*0.8/5, c.height*2/5))
    c2    = ax2.get_position()
    wdum  = c.width*(5*3/(lonb[1]-lonb[0])) - c2.width
    ax3   = plt.gcf().add_axes((c2.x1, c2.y1-c.height/7, wdum, c.height*1/7))
    #ax3   = plt.gcf().add_axes((c2.x0, c2.y0-c.height*1/5, c2.width, c.height*1/5))

    txt = (f"tc_ivt_95th:{tc_ivt_max:8.1f}\n"
           f"tc_ivt_vort_max:{tc_ivt_zeta_max*1e4:0.1f}"+r"$10^{-4}$ 1/s"+"\n"
           f"sw_ivt_mean:{sw_ivt_mean:8.1f} ({sw_ivt_dir:.1f}deg)")
    bbox = dict(boxstyle='square', fc='1', ec='0')
    ax1.text(0.98, 0.98, txt,
             ha='right', va='top', ma='left',
             transform=ax1.transAxes,
             bbox=bbox,
            )
    r = tc_ivt_lonlat
    for r in [tc_ivt_lonlat, sw_ivt_lonlat]:
        ax1.add_patch(Rectangle(xy=[r[0],r[2]], width=r[1]-r[0], height=r[3]-r[2],
                        facecolor='none', edgecolor='k',
                        transform=plottools.proj, zorder=50))

    # IVT strength
    PC = ax1.pcolormesh(lon_e, lat_e, np.sqrt(ivtx_e**2+ivty_e**2),norm=ivt_norm,cmap=ivt_cmap)
    cbar = fig.colorbar(PC, orientation='vertical', cax=cax3)
    cbar.ax.set_title('IVT\n[kg/m/s]', fontsize=15, y=1.05, loc='left')
   
    # IVT quiver 
    skip = 3
    QV = ax1.quiver(lon_e[::skip], lat_e[::skip], 
                    ivtx_e[::skip,::skip], ivty_e[::skip,::skip],
                    scale_units='xy', scale=600,
                    color='k')
   
    # 5880 
    CO = ax1.contour(lon_e, lat_e, z500, levels=[5880.], linewidths=[5], colors=['0.3'])
    plt.clabel(CO, fmt='%.0f')

    # Taiwan TOPO
    ds_topo = plottools.ds_topo
    topo_height = ds_topo.height*1e3
    CO=ax1.contourf(ds_topo.lon, ds_topo.lat, 
                 np.where(topo_height>0,topo_height,np.nan),
                 cmap = topo_cmap, norm = topo_norm, extend='max')
    cbar = fig.colorbar(CO, orientation='vertical', cax=cax1)
    cbar.ax.set_title('TOPO[m]', fontsize=15, y=1.05, loc='left')

    # cwa station rainfall
    stn_rain = np.where(stn_rain>0., stn_rain, np.nan)
    IM    = ax1.scatter(stn_lon, stn_lat, c=stn_rain, s=20, 
                        cmap=rain_cmap, norm=rain_norm, alpha=0.7, edgecolor='none')
    cbar = fig.colorbar(IM, orientation='vertical', cax=cax2, extend='max')
    cbar.ax.set_title('rain[mm/d]', fontsize=15, y=1.05, loc='left')

    # subplots
    CO    = ax2.contour(ds_topo.lon, ds_topo.lat, 
                 ds_topo.height, levels=[0.001], colors=['k'], linewidths=[1])
    CO    = ax2.contourf(ds_topo.lon, ds_topo.lat, 
                 np.where(topo_height>0,topo_height,np.nan),
                 cmap = topo_cmap, norm = topo_norm)
    IM    = ax2.scatter(stn_lon, stn_lat, c=stn_rain, s=20, 
                 cmap=rain_cmap, norm=rain_norm, alpha=0.7, edgecolor='none')
    ax2.axis((119.8, 122.2, 21.8, 25.6))
    ax2.set_xticks([])
    ax2.set_yticks([])

    # subplots, ax3, timeseries
    x = np.arange(1,25)
    nstn = stn_rain_hr.shape[0]
    for istn in range(nstn):
        ax3.plot(x, stn_rain_hr[istn], color='0.9', lw=0.5)
    ax3.plot(x, np.nanmean(stn_rain_hr,axis=0), color='#D70801')
    ax3.set_xticks(np.arange(6,25,3))
    ax3.set_yticks([0,1,2,3])
    ax3.tick_params(axis='y', left=False, labelleft=False, right=True, labelright=True)
    ax3.axis((5,24,0,2.9))
    diurnal_str='diurnal' if flag_diurnal else 'non-diurnal'
    #ax3.text(0.5,0.98,f'mean ({nstn})', va='top', ha='center', transform=ax3.transAxes)
    ax3.text(0.02,0.98,f'mean ({nstn})\n{diurnal_str}', va='top', ha='left', transform=ax3.transAxes)
    plt.grid()

    plottools.Plot_cartopy_map(ax1)
    datestr=nowtime.strftime("%Y-%m-%d")
    ax1.set_title(f'{datestr}\nERA5 / low-level IVT [kg/m/s] / Z500[5880m]',
        loc='left', fontweight='bold', fontsize=20)
    wtype_str = decide_weather(sw_ivt_mean, sw_ivt_dir, tc_ivt_max, tc_ivt_zeta_max)
    distr = '1' if flag_diurnal else '0'
    print(nowtime, f', {wtype_str:>15s}, {diurnal_str:>15s}')
    ax1.set_title(wtype_str, loc='right', fontweight='bold', fontsize=20)

    datestr=nowtime.strftime("%Y%m%d")
    plt.savefig(f'./fig_ivt/era5_ivt_{datestr}_{wtype_str}_{distr}.png', facecolor='w', bbox_inches='tight', dpi=400)
    return output


if __name__=='__main__':
    # datelist = []
    # initime = datetime(2018,6,1)
    # ndays = 30
    # datelist += [ [initime + timedelta(days=iday) ] for iday in range(ndays) ]

    datelist = []
    #initime = datetime(2007,6,16)
    initime = datetime(2009,9,26)
    ndays = 1
    datelist += [ [initime + timedelta(days=iday) ] for iday in range(ndays) ]
    datelist = [[t[0], False] for t in datelist]

    ## ####### DRAW #######
    ## datelist = []
    ## ndays = 30+31+31+30
    ## y0=2001
    ## y1=2020
    ## for yr in range(y0,y1+1):
    ## #for yr in range(2001,2021):
    ##     initime = datetime(yr,6,1)
    ##     datelist += [ [initime + timedelta(days=iday) ] for iday in range(ndays) ]
    ## #datelist = [[t[0], False] for t in datelist]

    cores = 20
    # Use multiprocessing to fetch variable data in parallel
    with multiprocessing.Pool(processes=cores) as pool:
        results = pool.starmap(draw_ivt_and_local_rain,
            datelist)
    # df = pd.DataFrame(results).set_index('time')
    # df.to_csv(f'./csv/weather_{y0}.csv')
   
