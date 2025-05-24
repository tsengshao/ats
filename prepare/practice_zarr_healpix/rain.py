import numpy as np
import healpy as hp
from netCDF4 import Dataset, num2date
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as patches
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import sys, os

# Utilities
class PlotTools_cartopy():
    def __init__(self):
        self.proj = ccrs.PlateCarree()

    def Axe_map(self, fig, gs,
                xlim_, ylim_, **grid_info):
        # Set map extent
        axe  = fig.add_subplot(gs, projection=self.proj)
        axe.set_extent([xlim_[0], xlim_[-1], ylim_[0], ylim_[-1]], crs=self.proj)
        # Set additional grid information
        if len(grid_info)>0:
            if grid_info['xloc_'] is not None:
                axe.set_xticks(grid_info['xloc_'], crs=self.proj)
                #axe.set_xticklabels(['' for i in range(len(grid_info['xloc_']))])  # default: no tick labels
                axe.set_xticklabels([f'{int(i)}E' for i in grid_info['xloc_']],fontsize=16)

            if grid_info['yloc_'] is not None:
                axe.set_yticks(grid_info['yloc_'], crs=self.proj)
                #axe.set_yticklabels(['' for i in range(len(grid_info['yloc_']))])
                axe.set_yticklabels([f'{int(i)}N' for i in grid_info['yloc_']],fontsize=16)
            gl = axe.gridlines(xlocs=grid_info['xloc_'], ylocs=grid_info['yloc_'],
                               draw_labels=False)
        return axe

    def Plot_cartopy_map(self, axe):
        axe.add_feature(cfeature.LAND,color='grey',alpha=0.1)
        axe.coastlines(resolution='50m', color='black', linewidth=1)


def get_nn_lon_lat_index(nside, lons, lats):
    lons2, lats2 = np.meshgrid(lons, lats)
    return np.array(
        hp.ang2pix(nside, lons2, lats2, nest=True, lonlat=True)
    )

def print_healp_resolution(NSIDE):
    ## z05: 1.8deg
    ## z07: 0.46deg
    ## z08: 0.23deg
    ## z09: 0.11deg
    print(\
        "Approximate resolution at NSIDE {} is {:.2} deg".format(\
            NSIDE, hp.nside2resol(NSIDE, arcmin=True) / 60\
        ))
    return hp.nside2resol(NSIDE, arcmin=True) / 60

if __name__=='__main__':
    #dpath   = '/large/sftpgo/data/NICAM/hackathon/2020/2d1h/'
    dpath   = '/large/sftpgo/data/NICAM/hackathon/2020/2d3h/'
    nicam_dicts = {'cwv':dict(fname='sa_vap_atm.nc',\
                              vname='prw',\
                              scale=1, \
                              units='mm'),\
                   'rain':dict(fname='sa_tppn.nc',\
                               vname='pr',\
                               scale=3600.,\
                               units='mm/hr')
                   }
    vname = 'cwv'

    # EastAsia
    lonb  = [90, 150]
    latb  = [-10, 35]
    lonb  = [110, 135]
    latb  = [10, 35]
    zpix_str  = 'z08'
    zpix_str  = 'z09'

    ## ## # TaiwanVVM
    ## lonb = [118.639, 123.447]
    ## latb = [21.2195, 26.0276]
    ## zpix_str  = 'z09'

    vdict=nicam_dicts[vname]
    filename=f"{dpath}/{zpix_str}/{vdict['fname']}"
    nc    = Dataset(filename,'r')
    NSIDE = nc.variables['healpix'].healpix_nside
    time  = nc.variables['time']
    time  = num2date(time[:], calendar=time.calendar, units=time.units)

    idx_t = (datetime(2020,7,20)<=time) * (time < datetime(2020,7,21))
    idx_t = np.nonzero(idx_t)[0]
    idxt = idx_t[-1]
    
    print(f'{filename}\nNSIDE={NSIDE}')
    approx_res = print_healp_resolution(NSIDE)
    lon = np.arange(lonb[0], lonb[-1]+approx_res, approx_res)
    lat = np.arange(latb[0], latb[-1]+approx_res, approx_res)
    latlon_shape = (lat.size, lon.size)


    grid = get_nn_lon_lat_index(NSIDE,lon,lat)
    idx_grid = grid.flatten()
    data = nc.variables[vdict['vname']][idxt, 0, idx_grid].reshape(latlon_shape)
    data *= vdict['scale']

    if vname=='rain':
        bounds=[1, 2, 6, 10, 15, 20, 30, 40, 50, 70, 90, 110, 130, 150, 200, 300]
        cmap  = plt.cm.jet
        norm  = mpl.colors.BoundaryNorm(bounds, cmap.N, extend='max')
    elif vname=='cwv':
        bounds = np.arange(20,80.1,10)
        cmap  = plt.cm.jet
        norm  = mpl.colors.BoundaryNorm(bounds, cmap.N, extend='both')

    plt.close('all')
    # Figure initialize
    fig = plt.figure(figsize=(10,8))
    gs  = mpl.gridspec.GridSpec(1, 1, figure=fig)
    ## Plot:
    plottools = PlotTools_cartopy()
    ax    = plottools.Axe_map(fig, gs[0], xlim_=lonb, ylim_=latb,
                       xloc_=np.arange(int(lonb[0]), int(lonb[1]+0.5), 5), \
                       yloc_=np.arange(int(latb[0]), int(latb[1]+0.5), 5))
    PC = ax.pcolormesh(lon, lat, data,norm=norm,cmap=cmap)
    plt.colorbar(PC, orientation='horizontal')
    #cbar = fig.colorbar(imcwb, orientation='vertical', cax=cax)
    plottools.Plot_cartopy_map(ax)
    ax.set_title(vname+' '+time[idxt].strftime('%Y-%m-%d %H:%M'))
    plt.tight_layout()
