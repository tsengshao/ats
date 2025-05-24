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
    ## z15: 0.0018deg
    print(\
        "Approximate resolution at NSIDE {} is {:.2} deg".format(\
            NSIDE, hp.nside2resol(NSIDE, arcmin=True) / 60\
        ))
    return hp.nside2resol(NSIDE, arcmin=True) / 60

if __name__=='__main__':
    #grid    = '2d1h'
    grid    = '220m'
    varlist = ['sa_cldi',
               'sa_cldw',
               'sa_lwu_toa',
               'sa_slp_ecmwf',
               'sa_tppn',
               'sa_vap_atm',
               'ss_t2m',
               'ss_tppn',
               'ss_u10m',
               'ss_v10m']

    #fname   = f'/large/sftpgo/data/NICAM/hackathon/healpix/NICAM_{grid}_z9.zarr'
    fname   = f'/large/sftpgo/data/NICAM/hackathon/220m/data_healpix_15.zarr'
    out_dir = f'/work/shaoyu/GSRMs/prepare/data/nicam/{grid}/'
    NSIDE   = 2**15  # corresponding to z9
    os.system(f'mkdir -p {out_dir}')

    lon = 110. + np.arange(25001) * 0.001
    lat = 10.  + np.arange(25001) * 0.001

    ds    = xr.open_zarr(fname, consolidated=True)
    print(f'{fname}\nNSIDE={NSIDE}')
    approx_res = print_healp_resolution(NSIDE)
    latlon_shape = (lat.size, lon.size)

    idxtime = slice(0,1)
    print(ds.time.isel(time=idxtime))

    for var in varlist:
        print(var)
        grid = get_nn_lon_lat_index(NSIDE,lon,lat)
        data = ds[var].isel(time=idxtime, cell=grid)
        data = clean_attrs(data)

        comp = dict(zlib=True, complevel=4, chunksizes=(1,lat.size, lon.size))  # compression level: 1 (fastest) to 9 (best)
        encoding = {data.name: comp}
        data.to_netcdf(f'{out_dir}/{var}.nc', format='NETCDF4', encoding=encoding)

