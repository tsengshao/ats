import numpy as np
import os, sys 
sys.path.insert(0, '..')
import utils.utils_plot_cartopy as ucartopy
import utils.utils_read as uread
import utils.utils_draw as udraw
import matplotlib.pyplot as plt
import matplotlib as mpl
from datetime import timedelta, datetime


lonb = [105., 140.]
latb = [10.,   35.]

lonb = [110., 135.]
latb = [10.,   35.]
levb = [1000., 700.]

def get_ivt(model, nowtime):
    lev_lowb = [1000., 700.]
    lon_gs,  lat_gs,  lev_gs, u_gs   = uread.read_gsrm(model, 'ua',nowtime,lonb,latb,lev_lowb,daily=True)
    lon_gs,  lat_gs,  lev_gs, v_gs   = uread.read_gsrm(model, 'va',nowtime,lonb,latb,lev_lowb,daily=True)
    lon_gs,  lat_gs,  lev_gs, q_gs   = uread.read_gsrm(model, 'hus',nowtime,lonb,latb,lev_lowb,daily=True)
    u_gs = np.nan_to_num(u_gs,nan=0)
    v_gs = np.nan_to_num(v_gs,nan=0)
    q_gs = np.nan_to_num(q_gs,nan=0)
    ivt_x = -1./9.8*np.trapezoid(u_gs*q_gs, x=lev_gs*100., axis=0)
    ivt_y = -1./9.8*np.trapezoid(v_gs*q_gs, x=lev_gs*100., axis=0)
    # ivt_intensity = np.sqrt(ivt_x**2+ivt_y**2)
    # ivt_direction = (270-np.arctan2(ivt_x,ivt_y)*180/np.pi)%360 
    return lon_gs, lat_gs, ivt_x, ivt_y

# ats_date = np.load('../obs/shao_ATdays_2005_2020.npy', allow_pickle=True)
# nowtime = ats_date[0]

s_date = datetime(2020,6,1)
e_date = datetime(2020,10,1)
ndays  = int((e_date-s_date).total_seconds()/86400)
#model  = 'icon'
model  = 'nicam'
os.system(f'mkdir -p ./fig/{model}')

ats_date = np.load(f'../obs/shao_ATdays_2020_2020_{model}.npy', allow_pickle=True)
ndays = np.size(ats_date)

for iday in range(ndays):
    #nowtime = s_date + timedelta(days=iday)
    nowtime = ats_date[iday]
    print(nowtime)
    lon_e, lat_e, ivtx_e, ivty_e = get_ivt(model, nowtime)
    lon_e, lat_e, _,   z_e   = uread.read_gsrm(model, 'zg',nowtime,lonb,latb,[500.,500.], daily=True)
    lon_e, lat_e,   pr_e   = uread.read_gsrm(model, 'pr',nowtime,lonb,latb, daily=True,tw_time=True)
    z500 = z_e[0]
    pr_e = pr_e*3600*24

    topo_bounds= np.arange(0,1200.1,200)
    cmap       = plt.cm.Blues
    norm_      = mpl.colors.BoundaryNorm(topo_bounds, 256, extend='max')
    
    # Figure initialize
    udraw.set_figure_defalut()
    #fig = plt.figure(figsize=(12, 8))
    fig = plt.figure(figsize=(10, 8))
    plottools = ucartopy.PlotTools_cartopy()
    ax1   = plottools.Axe_map(fig, 111, xlim_=lonb, ylim_=latb,
                              xloc_=np.arange(lonb[0], lonb[-1]+0.001, 5), 
                              yloc_=np.arange(latb[0], latb[-1]+0.001, 5))
    ax1.set_position([0.05, 0.05, 0.8, 0.85])
    PC = ax1.pcolormesh(lon_e, lat_e, np.sqrt(ivtx_e**2+ivty_e**2),norm=norm_,cmap=cmap)
    cax  = fig.add_axes([ax1.get_position().x1+0.01, ax1.get_position().y0, 0.03, ax1.get_position().height])
    cbar = fig.colorbar(PC, orientation='vertical', cax=cax)
    
    skip = 5
    QV = ax1.quiver(lon_e[::skip], lat_e[::skip], 
                    ivtx_e[::skip,::skip], ivty_e[::skip,::skip],
                    scale_units='xy', scale=600,
                    color='k')
    
    CO = ax1.contour(lon_e, lat_e, z500, levels=[5880.], linewidths=[4], colors=['mediumslateblue'])
    plt.clabel(CO, fmt='%.0f')

    # rainfall
    CO2 = ax1.contourf(lon_e, lat_e, pr_e, levels=[25, 1000000], colors=['r'], alpha=0.5)
    
    plottools.Plot_cartopy_map(ax1)
    datestr=nowtime.strftime("%Y-%m-%d")
    ax1.set_title(f'{datestr}\n{model.upper()}', loc='left', fontweight='bold', fontsize=20)
    ax1.set_title(f'rainfall>25mm/day [red]\nlow-level IVT [kg/m/s] / Z500[5880m]', loc='right', fontweight='bold', fontsize=15)

    datestr=nowtime.strftime("%Y%m%d")
    plt.savefig(f'./fig/{model}/ivt_{datestr}.png', facecolor='w', bbox_inches='tight', dpi=300)

