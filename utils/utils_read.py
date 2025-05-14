import numpy as np
import sys, os
from netCDF4 import Dataset
sys.path.insert(0,'../utils')
from datetime import datetime, timedelta
import h5py
import multiprocessing
import xarray as xr
import warnings

def crop_data(lonb, latb, lon, lat, data, zaxis=0):
    ilon0 = np.argmin(np.abs(lonb[0]-lon))
    ilon1 = np.argmin(np.abs(lonb[1]-lon))+1
    ilat0 = np.argmin(np.abs(latb[0]-lat))
    ilat1 = np.argmin(np.abs(latb[1]-lat))+1
    if zaxis==-1:
        out_data = data[ilat0:ilat1,ilon0:ilon1,...]
    elif zaxis==0:
        out_data = data[..., ilat0:ilat1, ilon0:ilon1]
    else:
        sys.exit('ERROR!! zaxis = 0 or -1, in crop_data')
    return lon[ilon0:ilon1], lat[ilat0:ilat1], out_data

def read_RO_data(filename):
    ## process sounding time
    # wetPf2_C006.2017.007.04.07.G31_2021.0390_nc
    split_name = filename.split('/')[-1]
    yr = int(split_name.split('.')[1])
    julian = int(split_name.split('.')[2])
    hr = int(split_name.split('.')[3])
    mn = int(split_name.split('.')[4])
    sounding_time = datetime(yr,1,1,hr,mn)+timedelta(days=julian-1)

    nc = Dataset(filename)
    if nc.bad == 1:
        print(f'BAD of RO data {filename}')
        return 

    height = nc.variables['MSL_alt'][:]*1e3 #meter
    lon = nc.variables['lon'][:] #degrees_east
    lon[lon<0]+=360
    lat = nc.variables['lat'][:] #degrees_north
    temp = nc.variables['Temp'][:]+273.15 #K
    pres = nc.variables['Pres'][:]*100. #Pa
    qv  = nc.variables['sph'][:]/1000. # kg/kg
    return sounding_time, height, pres, temp, qv, lon, lat

def read_imerg_daily(nowdate, lonb=None, latb=None,cores=5):
    lon, lat, dum = read_imerg(nowdate,lonb,latb)
    sdate         = datetime(nowdate.year, nowdate.month, nowdate.day)
    datelist      = [ sdate + timedelta(minutes=30)*i \
                      for i in range(48) ]
    with multiprocessing.Pool(processes=cores) as pool:
        dum = pool.starmap(read_imerg, \
                      [(datelist[i], lonb, latb) for i in range(len(datelist))]\
                      )
    results   = np.squeeze(np.array([a[2] for a in dum]))
    data      = np.nanmean(results,axis=0)
    return lon, lat, data

def read_imerg(nowtime, lonb=None, latb=None):
    folder = '/data/dadm1/obs/GPM_IMERG/GPM_3IMERGHH.07/'
    # Data
    fname='/2016/247/3B-HHR.MS.MRG.3IMERG.20160903-S033000-E035959.0210.V07B.HDF5'
    f = h5py.File(folder+fname, 'r')
    lon = f['Grid']['lon'][:]
    lat = f['Grid']['lat'][:]
    f.close()
    lon = (lon+360)%360 # convert360
    idx_lon0 = np.argmin(np.abs(lon-0))
    lon = np.roll(lon, -idx_lon0)
  
    julian = nowtime.timetuple().tm_yday
    year = nowtime.timetuple().tm_year
    date = nowtime.strftime('%Y%m%d')
    str1 = nowtime.strftime('%H%M%S')
    str2 = (nowtime+timedelta(minutes=29,seconds=59)).strftime('%H%M%S')
    idx=(nowtime-datetime.strptime(date,'%Y%m%d')).total_seconds()/60
    fname = f'{year:4d}/{julian:03d}/3B-HHR.MS.MRG.3IMERG.{date}-S{str1}-E{str2}.{idx:04.0f}.V07B.HDF5'

    f = h5py.File(folder+fname, 'r')
    rain = f['Grid']['precipitation'][0,:,:].T #[y(1800),x(3600)]
    f.close()
    rain = np.roll(rain, -idx_lon0, axis=1)
    rain[rain<0] = np.nan
    data = rain.copy()
    if lonb and latb:
        lon, lat, data = crop_data(lonb, latb, lon, lat, rain, zaxis=0)
    return lon, lat, data
    

def read_oisst(varname,nowtime,lonb=None,latb=None):
    # /data/dadm1/obs/OISST/oisst-avhrr-v02r01.198201.nc
    # varname : 'sst', 'ice', 'err', ...
    yyyy   = nowtime.year
    mm     = nowtime.month
    it     = int((nowtime-datetime(yyyy,mm,1)).total_seconds()/86400)
    fname  = f'/data/dadm1/obs/OISST/oisst-avhrr-v02r01.{yyyy:04d}{mm:02d}.nc'
    nc     = Dataset(fname,'r')
    lon    = nc.variables['lon'][:]
    lat    = nc.variables['lat'][:]
    data   = nc.variables[varname][it,0,:,:]
    nc.close()
    if lonb and latb:
        lon, lat, data = crop_data(lonb, latb, lon, lat, data, zaxis=0)
    return lon, lat, data

def read_gsrm(model,varname,nowtime,lonb=None,latb=None,levb=None, daily=False,tw_time=False):
    # /data/C.shaoyu/hackathon/icon/PT1H_inst/vas.nc
    mname = model.lower()
    vname = varname.lower()
    if varname in ['pr', 'uas', 'vas']:
        grid_dict = {'icon':'PT1H_inst', 'nicam':'2d1h'}
        dtype = '2d'
    elif varname in ['clivi', 'clwvi', 'hflsd', 'hfssd', 'prw',	'ps']:
        grid_dict = {'icon':'PT3H_mean', 'nicam':'2d3h'}
        dtype = '2d'
    elif varname in ['hur', 'hus', 'qall', 'ta', 'ua', 'va', 'wa', 'zg']:
        grid_dict = {'icon':'PT6H_inst', 'nicam':'3d6h'}
        dtype = '3d'
    elif varname in ['orog', 'sftlf']:
        grid_dict = {'nicam':'2dbc'}
        dtype = '2d'
    grid = grid_dict[mname]
    fname=f'/data/C.shaoyu/hackathon/{mname}/{grid}/{vname}.nc'
    ds = xr.open_dataset(fname)

    # process time position 
    if mname=='nicam' and grid_dict['nicam']=='2d1h':
        datatime = nowtime+timedelta(minutes=30)
    elif mname=='nicam' and grid_dict['nicam']=='2d3h':
        datatime = nowtime+timedelta(minutes=90)
    else:
        datatime = nowtime
    if tw_time: datatime = datatime-timedelta(hours=8)
    tstr=datatime.strftime('%Y-%m-%dT%H:%M:%S')
    if daily: tstr = tstr[:10]

    # if topography, only on time 
    if grid=='2dbc': tstr='1970-01-01T00:00:00'

    if daily and tw_time:
       d1 = datatime - timedelta(hours=8)
       d2 = datatime + timedelta(hours=15)
       tstr1 = d1.strftime('%Y-%m-%dT%H:%M:%S')
       tstr2 = d2.strftime('%Y-%m-%dT%H:%M:%S')
       tstr = slice(tstr1, tstr2)

    data_da = ds[vname].sel(time=tstr)
    data = np.squeeze(ds[vname].sel(time=tstr).values)
    if daily:
        #data = np.nanmean(data,axis=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            data = np.nanmean(data, axis=0)

    lon  = ds.lon.values
    lat  = ds.lat.values
    if dtype=='3d':
        if mname=='nicam':
            lev = ds.lev.values
        elif mname=='icon':
            lev = ds.pressure.values/100.
        if lev[-1] - lev[0] > 0: # reverse levs
            lev  = lev[::-1]
            data = data[::-1, ...]
    if lonb and latb:
        lon, lat, data = crop_data(lonb, latb, lon, lat, data, zaxis=0)
    if levb and dtype=='3d':
        ilev0 = np.argmin(np.abs(lev-levb[0]))
        ilev1 = np.argmin(np.abs(lev-levb[1]))+1
        data = data[ilev0:ilev1,:,:]
        lev  = lev[ilev0:ilev1]
    if dtype=='3d':
        return lon, lat, lev, data
    elif dtype=='2d':
        return lon, lat, data
    
def read_era5_2d(varname, nowtime,lonb=None,latb=None):
    yyyy   = nowtime.year
    mm     = nowtime.month
    nctype = 'SFC'
    it     = int((nowtime-datetime(yyyy,mm,1)).total_seconds()/86400)
    era5_dir = f'/data/dadm1/reanalysis/ERA5/{nctype}/day/{varname}/{yyyy:04d}'
    nc  = Dataset(f'{era5_dir}/ERA5_{nctype}_{varname}_{yyyy:04d}{mm:02d}_r1440x721_day.nc','r')
    lon = nc.variables['longitude'][:]
    lat = nc.variables['latitude'][::-1]
    data = nc.variables[varname][it,::-1,:]
    nc.close()
    if lonb and latb:
        lon, lat, data = crop_data(lonb, latb, lon, lat, data, zaxis=0)
    return lon, lat, data
    
def read_era5_3d(varname, nowtime,lonb=None,latb=None,levb=None):
    yyyy   = nowtime.year
    mm     = nowtime.month
    nctype = 'PRS'
    it     = int((nowtime-datetime(yyyy,mm,1)).total_seconds()/86400)
    era5_dir = f'/data/dadm1/reanalysis/ERA5/{nctype}/day/{varname}/{yyyy:04d}'
    nc  = Dataset(f'{era5_dir}/ERA5_{nctype}_{varname}_{yyyy:04d}{mm:02d}_r1440x721_day.nc','r')
    lon = nc.variables['longitude'][:]
    lat = nc.variables['latitude'][::-1]
    lev = nc.variables['level'][::-1]
    data = nc.variables[varname][it,::-1,::-1,:]
    nc.close()
    if lonb and latb:
        lon, lat, data = crop_data(lonb, latb, lon, lat, data, zaxis=0)
    if levb:
        ilev0 = np.argmin(np.abs(lev-levb[0]))
        ilev1 = np.argmin(np.abs(lev-levb[1]))+1
        data = data[ilev0:ilev1,:,:]
        lev  = lev[ilev0:ilev1]
    return lon, lat, lev, data
    
def read_rgb_file(path, product_name, nowtime, lonb=None, latb=None):
    #201702100000_c_east_asia_rgb_2km.nc
    #201702100000_microphysics_24hr_b14_2km_rgb_e.nc
    tstr  = nowtime.strftime('%Y%m%d%H%M')
    fname = f'{path}/{tstr}_{product_name}_2km_rgb.nc'
    nc    = Dataset(fname, 'r')
    lon   = nc.variables['lon'][:]
    lat   = nc.variables['lat'][:]
    rband = nc.variables['red_band'][0,:,:]
    gband = nc.variables['green_band'][0,:,:]
    bband = nc.variables['blue_band'][0,:,:]
    rgb_data = np.stack((rband, gband, bband), axis=-1)
    rgb_data = np.where(rgb_data<0,0,rgb_data*255).astype(int)
    if lonb and latb:
        lon, lat, rgb_data = crop_data(lonb, latb, lon, lat, rgb_data, zaxis=-1)

    return lon, lat, rgb_data

