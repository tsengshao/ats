import numpy as np
import healpy as hp
import xarray as xr
import sys, os

def clean_attrs(ds):
    if isinstance(ds, xr.Dataset):
        for var in ds.variables:
            ds[var].attrs = {
                k: (int(v) if isinstance(v, (bool, np.bool_)) else v)
                for k, v in ds[var].attrs.items()
            }
    ds.attrs = {
        k: (int(v) if isinstance(v, (bool, np.bool_)) else v)
        for k, v in ds.attrs.items()
    }
    return ds

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
    grid    = 'PT1H_inst'
    varlist = ['pr']
    varlist = ['uas', 'vas']

    fname   = f'/large/sftpgo/data/ICON/d3hp003.zarr/{grid}_z9_atm'
    out_dir = f'/work/shaoyu/GSRMs/prepare//data/icon/{grid}/'
    NSIDE   = 512  # corresponding to z9
    os.system(f'mkdir -p {out_dir}')

    lon = 110. + np.arange(251) * 0.1
    lat = 10.  + np.arange(251) * 0.1

    ds    = xr.open_zarr(fname, consolidated=True)
    print(f'{fname}\nNSIDE={NSIDE}')
    approx_res = print_healp_resolution(NSIDE)
    latlon_shape = (lat.size, lon.size)

    ti = ds.time
    idxt0 = np.argmin(np.abs(ti-np.datetime64('2020-06-01T00:00')).values)
    idxt1 = np.argmin(np.abs(ti-np.datetime64('2021-03-01T00:00')).values)+1
    print(ds.time.isel(time=slice(idxt0, idxt1)))
    print(f'CDO:  -seltimestep,{idxt0+1}/{idxt1-1}')

    for var in varlist:
        grid = get_nn_lon_lat_index(NSIDE,lon,lat)
        data = ds[var].isel(time=slice(idxt0,idxt1), cell=grid)
        data = clean_attrs(data)

        comp = dict(zlib=True, complevel=4, chunksizes=(1,lat.size, lon.size))  # compression level: 1 (fastest) to 9 (best)
        encoding = {data.name: comp}
        data.to_netcdf(f'{out_dir}/{var}.nc', format='NETCDF4', encoding=encoding)

