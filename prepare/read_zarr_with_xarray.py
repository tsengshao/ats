import numpy as np
import healpy as hp
import xarray as xr
from netCDF4 import Dataset, num2date
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as patches
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import sys, os

def get_nn_lon_lat_index(nside, lons, lats):
    lons2, lats2 = np.meshgrid(lons, lats)
    da = xr.DataArray(
        hp.ang2pix(nside, lons2, lats2, nest=True, lonlat=True),
        coords=[("lat", lats), ("lon", lons)],
    )
    da.coords['lat'].attrs['units'] = 'degrees_north'
    da.coords['lat'].attrs['standard_name'] = 'latitude'
    
    da.coords['lon'].attrs['units'] = 'degrees_east'
    da.coords['lon'].attrs['standard_name'] = 'longitude'
    return da

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
    dpath   = '/large/sftpgo/data/NICAM/hackathon/healpix'
    nicam_dicts = {'cwv':dict(fname='NICAM_2d3h_{zpix_str}.zarr',\
                              vname='prw',\
                              scale=1, \
                              units='mm'),\
                   'rain':dict(fname='NICAM_2d3h_{zpix_str}.zarr',\
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
    zpix_str  = 'z8'
    zpix_str  = 'z9'

    ## ## # TaiwanVVM
    ## lonb = [118.639, 123.447]
    ## latb = [21.2195, 26.0276]
    ## zpix_str  = 'z09'

    vdict=nicam_dicts[vname]
    filename=f"{dpath}/{vdict['fname'].format(zpix_str=zpix_str)}"
    #nc    = Dataset(filename,'r')
    ds    = xr.open_dataset(filename)
    NSIDE = ds.healpix.healpix_nside
    time_str = '2020-07-20 00:30:00'
    time_str2 = '2020-07-21 00:30:00'
    #time  = nc.variables['time']
    #time  = num2date(time[:], calendar=time.calendar, units=time.units)

    # idx_t = (datetime(2020,7,20)<=time) * (time < datetime(2020,7,21))
    # idx_t = np.nonzero(idx_t)[0]
    # idxt = idx_t[-1]
    
    print(f'{filename}\nNSIDE={NSIDE}')
    approx_res = print_healp_resolution(NSIDE)
    lon = np.arange(lonb[0], lonb[-1]+approx_res, approx_res)
    lat = np.arange(latb[0], latb[-1]+approx_res, approx_res)
    latlon_shape = (lat.size, lon.size)

    grid = get_nn_lon_lat_index(NSIDE,lon,lat)
    data = ds[vdict['vname']].sel(time=slice(time_str,time_str2)).isel(cell=grid)
    data *= vdict['scale']

    comp = dict(zlib=True, complevel=4, chunksizes=(1,lat.size, lon.size))  # compression level: 1 (fastest) to 9 (best)
    encoding = {data.name: comp}
    data.to_netcdf('output_compressed.nc', format='NETCDF4', encoding=encoding)
    sys.exit()

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
    data_time_str = data.time.values.astype(str)[:19]
    ax.set_title(vname+' '+data_time_str)
    plt.tight_layout()
