import numpy as np
import sys, os
sys.path.insert(0, '../')
import utils.utils_cwa as ucwa
import utils.utils_read as uread
import utils.utils_plot_cartopy as ucartopy


def Cal_cwa_dpcp_comp(datelist:list, pcp_filter_min=0.):
    wtab_module  = ucwa.weather_table(year_list =np.arange(2005, 2021).tolist(),
                                      month_list=np.arange(5,10).tolist(), 
                                      lat_range=(22, 20), lon_range=(115, 119))
    for i, dd in enumerate(datelist):
        # Data initialize
        dd = dd.strftime('%Y%m%d')
        print(dd)
        if i < 1:
            pcp_table = wtab_module.get_cwb_precip_table(str(dd), accumulate_daily=True)
            pcp_comp  = pcp_table['precip'].values[:, np.newaxis]
        else:
            temp = wtab_module.get_cwb_precip_table(str(dd), accumulate_daily=True)['precip'].values
            pcp_comp  = np.concatenate((pcp_comp, temp[:, np.newaxis]), axis=1)
    print(pcp_comp.shape)
    daily_max = np.nanmax(pcp_comp, axis=0)
    mask      = daily_max>pcp_filter_min
    print(pcp_comp[..., mask].shape)
    mean_pcp  = np.nanmean(pcp_comp[..., mask], axis=1)
    return pcp_table['stn_lon'], pcp_table['stn_lat'], mean_pcp



if __name__=='__main__':
    ats_date          = np.load('shao_ATdays_2005_2020.npy', allow_pickle=True)
    ats_date_huai     = np.load('AT_days.npy', allow_pickle=True)
    stn_lon, stn_lat, composite_shao    = Cal_cwa_dpcp_comp(ats_date.tolist())
    stn_lon, stn_lat, composite_huai    = Cal_cwa_dpcp_comp(ats_date_huai.tolist())
    
    # datestr      = ats_date[100].strftime('%Y%m%d')
    # pcp_daily_table = wtab_module.get_cwb_precip_table(datestr, 
    #                                                    accumulate_daily=True)
    
    ucartopy.Plot_cwb_comp(rainfall_label='weak', stn_lon=stn_lon, stn_lat=stn_lat, precip_array=composite_shao, figtitle='ATS shao', figname='ats_shao')
    ucartopy.Plot_cwb_comp(rainfall_label='weak', stn_lon=stn_lon, stn_lat=stn_lat, precip_array=composite_huai, figtitle='ATS huai', figname='ats_huai')



