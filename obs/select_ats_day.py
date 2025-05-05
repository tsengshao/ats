import numpy as np
import sys, os
sys.path.insert(0, '..')
import utils.utils_cwa as ucwa
import utils.utils_read as uread
from datetime import datetime, timedelta
import pandas as pd

def get_ivt_intensity(nowtime):
    lonb = [115, 119]
    latb = [20, 22]
    levb = [1000., 700.]
    lon_e,  lat_e,  lev_e, u_e   = uread.read_era5_3d('u',nowtime,lonb,latb,levb)
    lon_e,  lat_e,  lev_e, v_e   = uread.read_era5_3d('v',nowtime,lonb,latb,levb)
    lon_e,  lat_e,  lev_e, q_e   = uread.read_era5_3d('q',nowtime,lonb,latb,levb)
    ivt_x = -1./9.8*np.trapezoid(u_e*q_e, x=lev_e*100., axis=0).mean()
    ivt_y = -1./9.8*np.trapezoid(v_e*q_e, x=lev_e*100., axis=0).mean()
    ivt_intensity = np.sqrt(ivt_x**2+ivt_y**2)

    ivt_direction = (270-np.arctan2(ivt_x,ivt_y)*180/np.pi)%360 
    return ivt_intensity, ivt_direction, ivt_x, ivt_y

def get_ivt_tc(nowtime):
    lonb = [115, 130]
    latb = [15, 30]
    levb = [1000., 700.]
    lon_e,  lat_e,  lev_e, u_e   = uread.read_era5_3d('u',nowtime,lonb,latb,levb)
    lon_e,  lat_e,  lev_e, v_e   = uread.read_era5_3d('v',nowtime,lonb,latb,levb)
    lon_e,  lat_e,  lev_e, q_e   = uread.read_era5_3d('q',nowtime,lonb,latb,levb)
    ivt_x = -1./9.8*np.trapezoid(u_e*q_e, x=lev_e*100., axis=0)
    ivt_y = -1./9.8*np.trapezoid(v_e*q_e, x=lev_e*100., axis=0)
    ivt_intensity_max = np.sqrt(ivt_x**2+ivt_y**2).max()
    ivt_is_tc = ivt_intensity_max>1000.
    return ivt_is_tc, ivt_intensity_max
wtab_module  = ucwa.weather_table(year_list =np.arange(2005, 2021).tolist(),
                                  month_list=np.arange(5,10).tolist(), 
                                  lat_range=(22, 20), lon_range=(115, 119))

huang_date = np.load('AT_days.npy', allow_pickle=True)
datestr = '20200726'
datestr = huang_date[-30].strftime('%Y%m%d')

sdate   = datetime(2008,5,1)
edate   = datetime(2008,9,1)
ndays   = int((edate-sdate).total_seconds()/86400)

table = pd.DataFrame(np.zeros((2,2)),\
                     columns=['huai_no','huai_yes'],index=['shao_no','shao_yes'])
total_ndays = 0
record_date  = []
year_start   = 2005
year_end     = 2020
for year in range(year_start,year_end+1):
    print(year)
    sdate   = datetime(year,6,1)
    edate   = datetime(year,10,1)
    ndays   = int((edate-sdate).total_seconds()/86400)
    total_ndays += ndays
    for iday in range(ndays):
        nowdate = sdate+timedelta(days=iday)
        datestr  = nowdate.strftime('%Y%m%d')
        pcp_table       = wtab_module.get_cwb_precip_table(datestr,
                                                           accumulate_daily=False)
        ivt_intensity, ivt_direction, ivt_x, ivt_y = get_ivt_intensity(nowdate)
        tc_day, ivt_intensity_max =  get_ivt_tc(nowdate)

        diurnal_array = np.vstack(pcp_table['precip'])
        idx = np.nonzero(~np.all(diurnal_array,axis=1))[0]
        diurnal_array = diurnal_array[idx,:]
       
        morning = np.nansum(diurnal_array[:,:9],axis=1) 
        afternoon = np.nansum(diurnal_array[:,9:],axis=1)
        morning    = np.nanmax(morning)
        afternoon  = np.nanmax(afternoon)
        # morning    = np.nanpercentile(morning,99)
        # afternoon  = np.nanpercentile(afternoon,99)
        diurnal_cycle   = np.nanmean(diurnal_array, axis=0)
        condiction = (morning<10) *\
                     (afternoon>50) *\
                     (np.nanmean(morning)<np.nanmean(afternoon))
        huai_idx  = np.any(huang_date==nowdate)
        stacy_idx = (ivt_intensity<400.)#*(ivt_direction<260)*(ivt_direction>190)
        shao_idx  = condiction*stacy_idx*(~tc_day)

        index_shao = 1 if shao_idx else 0
        index_huai = 1 if huai_idx else 0
        table.iloc[index_shao,index_huai] += 1
        if index_shao:
            record_date.append(nowdate)
    
        ##  if (shao_idx != huai_idx):
        ##      print(f'morning:{np.nanmax(morning)}, afternoon:{np.nanmax(afternoon)}')
        ##      print(f'{datestr}, idx={condiction}, huai={huai_idx} stacy={stacy_idx}')
        ##      print(f'{ivt_intensity:.1f}, {ivt_direction:.1f}, {ivt_x:.1f}, {ivt_y:.1f}')
        ##      print(f'{datestr}, summary --> {shao_idx} {shao_idx == huai_idx}')
        ##      print('')
        ##  #print(f'{datestr}, number of available station : ',idx.size)
        ##  #print(f'ATS: {condiction}, diurnal ...')
        ##  #print(diurnal_cycle)
np.save(f'shao_ATdays_{year_start:04d}_{year_end:04d}', record_date)



