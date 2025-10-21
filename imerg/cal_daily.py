import numpy as np
import sys, os
from utils import utils_read as uread
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from netCDF4 import Dataset, date2num
import multiprocessing

#100,140,10,40
lonb = [100.001, 140.001]
latb = [10.001, 40.001]

nowtime=datetime(2017,9,1)

def create_daily_imerg(nowtime):
    yr  = nowtime.year
    mo  = nowtime.month
    ndays = (datetime(yr,mo,1)+relativedelta(months=1) - datetime(yr,mo,1)).days
    dates = [datetime(yr,mo,1)+n*timedelta(days=1) for n in range(ndays)]
    lon, lat, _ = uread.read_imerg(dates[0], lonb=lonb, latb=latb)
    
    #fname=f'imerg_daily_{yr:04d}{mo:02d}.nc'
    path=f'../data/imerg/day/{yr:04d}'
    fname=f'{path}/IMERG_EA_{yr:04d}{mo:02d}_day.nc'
    os.system(f'rm -rf {fname}')
    os.system(f'mkdir -p {path}')
    ncout = Dataset(fname, 'w')
    ncout.history  = "Created " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # create lontitude
    ncout.createDimension('lon', lon.size)
    ncvar = ncout.createVariable('lon', 'f4', ['lon'])
    attrs = {'standard_name':'longitude',\
             'long_name':'longitude',\
             'units':'degrees_east',\
             'axis':'X',\
            }
    ncvar.setncatts(attrs)
    ncvar[:] = lon
    
    # create latitude
    ncout.createDimension('lat', lat.size)
    ncvar = ncout.createVariable('lat', 'f4', ['lat'])
    attrs = {'standard_name':'latitude',\
             'long_name':'latitude',\
             'units':'degrees_north',\
             'axis':'Y',\
            }
    ncvar.setncatts(attrs)
    ncvar[:] = lat
    
    # create time
    ncout.createDimension('time', None)
    ncvar = ncout.createVariable('time', '<f4', ['time'])
    attrs = {'standard_name':'time',\
             'long_name':'time',\
             'units':'days since 1900-01-01 00:00:00',\
             'calendar':'gregorian',\
             'axis':'T',\
            }
    ncvar.setncatts(attrs)
    ncvar[:] = date2num(dates,units=ncvar.units,calendar=ncvar.calendar)
    
    # create time
    ncrain = ncout.createVariable('rain', '<f4', \
                                 ['time','lat','lon'], fill_value=-999.99,\
                                 compression='zlib',significant_digits=4)
    attrs = {'standard_name':'rain',\
             'long_name':'rain',\
             'units':'mm/day',\
            }
    
    ncrain.setncatts(attrs)
    
    for idy in range(ndays):
        #nowdate = dates[idy]
        print(dates[idy])
        _, _, data = uread.read_imerg_daily(dates[idy], lonb=lonb, latb=latb, cores=1)
        ncrain[idy] = data*24
    ncout.close()

if __name__=='__main__':
    datelist = []
    for yr in range(2001,2021):
        for mo in range(6,10):
            datelist += [ [datetime(yr,mo,1)] ]

    cores = 20
    # Use multiprocessing to fetch variable data in parallel
    with multiprocessing.Pool(processes=cores) as pool:
        results = pool.starmap(create_daily_imerg,
            datelist)
   



