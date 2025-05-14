import numpy as np
import sys, os
sys.path.insert(0, '..')
import utils.utils_cwa as ucwa
import utils.utils_read as uread
from datetime import datetime, timedelta
import pandas as pd

def get_ivt_intensity(model, nowtime):
    mname = model.lower()
    lonb = [115, 119]
    latb = [20, 22]
    levb = [1000., 700.]
    lon_e,  lat_e,  lev_e, u_e   = \
        uread.read_gsrm(mname, 'ua',nowtime,lonb,latb,levb,daily=True)
    lon_e,  lat_e,  lev_e, v_e   = \
        uread.read_gsrm(mname, 'va',nowtime,lonb,latb,levb,daily=True)
    lon_e,  lat_e,  lev_e, q_e   = \
        uread.read_gsrm(mname, 'hus',nowtime,lonb,latb,levb,daily=True)
    u_e = np.nan_to_num(u_e,nan=0)
    v_e = np.nan_to_num(v_e,nan=0)
    q_e = np.nan_to_num(q_e,nan=0)
    ivt_x = -1./9.8*np.trapezoid(u_e*q_e, x=lev_e*100., axis=0).mean()
    ivt_y = -1./9.8*np.trapezoid(v_e*q_e, x=lev_e*100., axis=0).mean()
    ivt_intensity = np.sqrt(ivt_x**2+ivt_y**2)
    ivt_direction = (270-np.arctan2(ivt_x,ivt_y)*180/np.pi)%360 
    return ivt_intensity, ivt_direction, ivt_x, ivt_y

def get_ivt_tc(model, nowtime):
    mname = model.lower()
    lonb = [115, 130]
    latb = [15, 30]
    levb = [1000., 700.]
    lon_e,  lat_e,  lev_e, u_e   = \
        uread.read_gsrm(mname, 'ua',nowtime,lonb,latb,levb,daily=True)
    lon_e,  lat_e,  lev_e, v_e   = \
        uread.read_gsrm(mname, 'va',nowtime,lonb,latb,levb,daily=True)
    lon_e,  lat_e,  lev_e, q_e   = \
        uread.read_gsrm(mname, 'hus',nowtime,lonb,latb,levb,daily=True)
    u_e = np.nan_to_num(u_e,nan=0)
    v_e = np.nan_to_num(v_e,nan=0)
    q_e = np.nan_to_num(q_e,nan=0)
    ivt_x = -1./9.8*np.trapezoid(u_e*q_e, x=lev_e*100., axis=0)
    ivt_y = -1./9.8*np.trapezoid(v_e*q_e, x=lev_e*100., axis=0)
    ivt_intensity_max = np.sqrt(ivt_x**2+ivt_y**2).max()
    ivt_is_tc = ivt_intensity_max>1000.
    return ivt_is_tc, ivt_intensity_max

total_ndays = 0
record_date  = []
year_start   = 2020
year_end     = 2020
model        = 'nicam'
#model        = 'icon'

lonb = [120, 122.0]
latb = [21.5, 25.4]

# find tw_mask
lon, lat, landfrac = uread.read_gsrm('nicam', 'sftlf', datetime(1970,1,1), lonb, latb)
lon2d, lat2d = np.meshgrid(lon,lat)
condi  = (120<=lon2d) * (lon2d<=122.0) *\
         (21.5<=lat2d) * (lat2d<=25.4) *\
         (landfrac>0.2)
tw_mask = np.where(condi,True,False)
tw_idx  = np.nonzero(tw_mask)

for year in range(year_start,year_end+1):
    print(year)
    sdate   = datetime(year,6,2)
    edate   = datetime(year,10,1)
    ndays   = int((edate-sdate).total_seconds()/86400)
    total_ndays += ndays
    for iday in range(ndays):
        nowdate = sdate+timedelta(days=iday)
        datestr  = nowdate.strftime('%Y%m%d')
        ivt_intensity, ivt_direction, ivt_x, ivt_y = \
           get_ivt_intensity(model, nowdate)
        tc_day, ivt_intensity_max =  get_ivt_tc(model, nowdate)
        diurnal_array = np.zeros((tw_idx[0].size, 24))
        for ihr in range(24):
            lon, lat, rainfall = uread.read_gsrm(model, 'pr', nowdate+timedelta(hours=ihr), lonb, latb, tw_time=True)
            rainfall *= 3600. #mm/hr
            diurnal_array[:,ihr] = rainfall[tw_idx]
            
        #idx = np.nonzero(~np.all(diurnal_array,axis=1))[0]
        #diurnal_array = diurnal_array[idx,:]
       
        morning = np.nansum(diurnal_array[:,:9],axis=1) 
        afternoon = np.nansum(diurnal_array[:,9:],axis=1)
        morning    = np.nanmax(morning)
        afternoon  = np.nanmax(afternoon)
        # morning    = np.nanpercentile(morning,99)
        # afternoon  = np.nanpercentile(afternoon,99)
        diurnal_cycle   = np.nanmean(diurnal_array, axis=0)
        condiction = (morning<10) *\
                     (afternoon>30) *\
                     (np.nanmean(morning)<np.nanmean(afternoon))
        stacy_idx = (ivt_intensity<400.)#*(ivt_direction<260)*(ivt_direction>190)
        shao_idx  = condiction*stacy_idx*(~tc_day)

        print(nowdate, shao_idx, morning, afternoon, ivt_intensity, tc_day)
        if shao_idx:
            record_date.append(nowdate)
    
np.save(f'shao_ATdays_{year_start:04d}_{year_end:04d}_{model}', record_date)

fout = open(f'shao_ATdays_{year_start:04d}_{year_end:04d}_{model}.txt','w')
for date in record_date:
    mstr=date.strftime('%B')[:3]
    fout.write(f'{date.day:02d}{mstr}{date.year:04d}\n')
fout.close()




