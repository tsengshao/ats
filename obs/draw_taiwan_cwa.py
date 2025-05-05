import numpy as np
import sys, os
sys.path.insert(0, '../')
import utils.utils_cwa as ucwa
import utils.utils_read as uread
import utils.utils_draw as udraw
import utils.utils_plot_cartopy as ucartopy
import matplotlib.pyplot as plt


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

def read_cwa_pcp_series(datelist:list):
    wtab_module  = ucwa.weather_table(year_list =np.arange(2005, 2021).tolist(),
                                      month_list=np.arange(5,10).tolist(), 
                                      lat_range=(22, 20), lon_range=(115, 119))
    output = np.zeros((len(datelist), 24))
    for i, dd in enumerate(datelist):
        # Data initialize
        dd = dd.strftime('%Y%m%d')
        print(dd)
        pcp_table = wtab_module.get_cwb_precip_table(str(dd), accumulate_daily=False)
        series = np.nanmean(np.vstack(pcp_table['precip'].values),axis=0)
        output[i,:] = series.copy()

    return datelist, output

if __name__=='__main__':
    ats_date          = np.load('shao_ATdays_2005_2020_wtc.npy', allow_pickle=True)
    ats_date_huai     = np.load('AT_days.npy', allow_pickle=True)

    # ------ taiwan obs composite -----
    ## _, all_series_huai = read_cwa_pcp_series(ats_date_huai)
    ## _, all_series_shao = read_cwa_pcp_series(ats_date)
    ##
    ## udraw.set_figure_defalut()
    ## fig, ax = plt.subplots(figsize=(8,6))
    ## #plt.plot(all_series_huai.T, color='0.8', linewidth=1, alpha=0.3)
    ## plt.plot(np.nanmean(all_series_huai,axis=0), color='0', linewidth=5, label=f'huai {len(ats_date_huai)}')
    ## plt.plot(np.nanmean(all_series_shao,axis=0), color='C0', linewidth=5, label=f'shao {len(ats_date)}')
    ## #plt.title(f'Obs. ({len(ats_date)} days)')
    ## plt.title(f'Obs.')
    ## plt.legend()
    ## xticks = np.arange(1,24, 1)
    ## plt.xticks(xticks, [f'{i:02d}' for i in xticks])
    ## plt.yticks(np.arange(0,6))
    ## plt.xlim(8, 23)
    ## plt.ylim(0,3)
    ## plt.grid(True)
    ## plt.xlabel('LT')
    ## plt.ylabel('mm/hr')
    ## plt.tight_layout()
    ## plt.savefig('./fig/pcp_series_shao_2005_2020_old.png',dpi=250)
    ## plt.show()
    ## sys.exit()

    ### ----- draw composite map over taiwan -----
    stn_lon, stn_lat, composite_shao    = Cal_cwa_dpcp_comp(ats_date.tolist())
    stn_lon, stn_lat, composite_huai    = Cal_cwa_dpcp_comp(ats_date_huai.tolist())
    ucartopy.Plot_cwb_comp(rainfall_label='weak', stn_lon=stn_lon, stn_lat=stn_lat, precip_array=composite_shao, figtitle='ATS shao', figname='ats_shao')
    ucartopy.Plot_cwb_comp(rainfall_label='weak', stn_lon=stn_lon, stn_lat=stn_lat, precip_array=composite_huai, figtitle='ATS huai', figname='ats_huai')

    
    



