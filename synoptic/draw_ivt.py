import numpy as np
import os, sys 
sys.path.insert(0, '..')
import utils.utils_plot_cartopy as ucartopy
import utils.utils_read as uread
import utils.utils_draw as udraw
import matplotlib.pyplot as plt
import matplotlib as mpl


lonb = [105., 140.]
latb = [10.,   35.]
levb = [1000., 700.]

def get_ivt(nowtime):
    lev_lowb = [1000., 700.]
    lon_e,  lat_e,  lev_e, u_e   = uread.read_era5_3d('u',nowtime,lonb,latb,lev_lowb)
    lon_e,  lat_e,  lev_e, v_e   = uread.read_era5_3d('v',nowtime,lonb,latb,lev_lowb)
    lon_e,  lat_e,  lev_e, q_e   = uread.read_era5_3d('q',nowtime,lonb,latb,lev_lowb)
    ivt_x = -1./9.8*np.trapezoid(u_e*q_e, x=lev_e*100., axis=0)
    ivt_y = -1./9.8*np.trapezoid(v_e*q_e, x=lev_e*100., axis=0)
    # ivt_intensity = np.sqrt(ivt_x**2+ivt_y**2)
    # ivt_direction = (270-np.arctan2(ivt_x,ivt_y)*180/np.pi)%360 
    return lon_e, lat_e, ivt_x, ivt_y


ats_date = np.load('../obs/shao_ATdays_2005_2020.npy', allow_pickle=True)
nowtime = ats_date[0]

for nowtime in ats_date:
    print(nowtime)
    lon_e, lat_e, ivtx_e, ivty_e = get_ivt(nowtime)
    lon_e, lat_e, _,   z_e   = uread.read_era5_3d('z',nowtime,lonb,latb,[500.,500.])
    z500 = z_e[0]/9.8
    
    topo_bounds= np.arange(0,1200.1,200)
    cmap       = plt.cm.Blues
    norm_      = mpl.colors.BoundaryNorm(topo_bounds, 256, extend='max')
    
    # Figure initialize
    udraw.set_figure_defalut()
    fig = plt.figure(figsize=(12, 8))
    plottools = ucartopy.PlotTools_cartopy()
    ax1   = plottools.Axe_map(fig, 111, xlim_=lonb, ylim_=latb,
                              xloc_=np.arange(lonb[0], lonb[-1]+0.001, 5), 
                              yloc_=np.arange(latb[0], latb[-1]+0.001, 5))
    ax1.set_position([0.05, 0.05, 0.8, 0.85])
    PC = ax1.pcolormesh(lon_e, lat_e, np.sqrt(ivtx_e**2+ivty_e**2),norm=norm_,cmap=cmap)
    cax  = fig.add_axes([ax1.get_position().x1+0.01, ax1.get_position().y0, 0.03, ax1.get_position().height])
    cbar = fig.colorbar(PC, orientation='vertical', cax=cax)
    
    skip = 3
    QV = ax1.quiver(lon_e[::skip], lat_e[::skip], 
                    ivtx_e[::skip,::skip], ivty_e[::skip,::skip],
                    scale_units='xy', scale=600,
                    color='k')
    
    CO = ax1.contour(lon_e, lat_e, z500, levels=[5880.], linewidths=[5], colors=['mediumslateblue'])
    plt.clabel(CO, fmt='%.0f')
    
    plottools.Plot_cartopy_map(ax1)
    datestr=nowtime.strftime("%Y-%m-%d")
    ax1.set_title(f'{datestr}\nERA5 / low-level IVT [kg/m/s] / Z500[5880m]', loc='left', fontweight='bold', fontsize=20)

    datestr=nowtime.strftime("%Y%m%d")
    plt.savefig(f'./fig/era5_ivt_{datestr}.png', facecolor='w', bbox_inches='tight', dpi=400)

