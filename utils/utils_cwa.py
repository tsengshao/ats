import numpy as np
import pandas as pd
import glob
from datetime import datetime, timedelta

class weather_table():
    def __init__(self, year_list:list, month_list:list,
                 special_start_date:str=False, special_end_date:str=False,
                 lat_range=(None, None), lon_range=(None, None)):
        self.YEARS     = year_list
        self.MONTHS    = month_list
        self.STARTDATE = self._convert_to_dobj(special_start_date) if special_start_date else None
        self.ENDDATE   = self._convert_to_dobj(special_end_date) if special_end_date else None
        self.LATRANGE  = lat_range if lat_range[0]>lat_range[1] and \
                         lat_range[0] is not None and lat_range[1] is not None \
                         else lat_range[::-1]  # for ERA5 data
        self.LONRANGE  = lon_range

        self._create_date_list()

    def _convert_to_dobj(self, date):
        """
        Convert a date string into a datetime object.
        Two types of string format are supported: 20051218 or 2005-12-18.
        """
        if isinstance(date, str):
            if len(date)>8:
                dateobj = datetime.strptime(date, '%Y-%m-%d')
            else:
                dateobj = datetime.strptime(date, '%Y%m%d')
        else:
            dateobj = date
        return dateobj

    def _create_date_list(self):
        """
        Create date list (of strings and datetime objects) in specific months for specific year range.
        Supports discrete month choices, designated start date and end date.
        !!Future adjustment!!: discrete year choices
        """
        start_date = self.STARTDATE if self.STARTDATE is not None else datetime(self.YEARS[0], 1, 1)
        end_date   = self.ENDDATE if self.ENDDATE is not None else datetime(self.YEARS[-1], 12, 31)
        # All dates in the year range (datetime objects and strings)
        self._dlist= [start_date+timedelta(days=i) for i in range((end_date-start_date).days+1)]
        self.DLIST = [(start_date+timedelta(days=i)).strftime("%Y%m%d") for i in range((end_date-start_date).days+1)]
        # Addtionally select months
        self._dlist_month= [dobj for dobj in self._dlist if dobj.month in self.MONTHS]
        self.DLIST_Month = [dobj.strftime("%Y%m%d") for dobj in self._dlist if dobj.month in self.MONTHS]

    def _cal_for_all_dates(self, datelist, func, func_config={}, cores=10):
        """
        Call the calculation methods (for single day) and return results for a range of days.
        *Can handle single/multiple outputs from func.
        
        :param datelist: List of dates for iterating calculation
        :type  datelist: list
        :param func: Funciton(method) to call
        :type  func: function
        :param func_config: Parameters for func
        :type  func_config: dict, optional, default={}
        
        :return: Calculation result for each day
        :rtype : tuple or list
        """
        # Create a partial function that pre-binds the config to the func
        func_with_config = partial(func, **func_config)
        with multiprocessing.Pool(processes=cores) as pool:
            results = pool.map(func_with_config, datelist)  # func result * number of processes

        # Create nested list to handle various amount of outputs
        output_num = len(results[0]) if isinstance(results[0], tuple) else 1  # check multi-/single output
        nest_list  = [[] for _ in range(output_num)]        # nested list handling func output
        # Store outputs in individual lists
        for output in results:                              # output: output for single call of func
            if output_num > 1:
                for i, val in enumerate(output):
                    nest_list[i].append(val)
            else:
                nest_list[0].append(output)
        return tuple(nest_list) if output_num > 1 else nest_list[0]

    def get_cwb_precip_table(self, date:str, accumulate_daily=False):
        # File list
        cwb_root  = '/data/dadm1/obs/CWB_WeatherStation'
        cwb_fpath = f'{cwb_root}/{date[:4]}/{date[4:6]}/{date}'  # CWA data has to be downloaded
        cwb_flist = sorted(glob.glob(f'{cwb_fpath}/{date}*'))
        # Define column widths based on README
        col_widths = [7, 10, 9, 7, 7, 7, 7, 7, 7, 7, 7, 3]
        # Define the column names
        col_names = ['stno', 'lon', 'lat', 'elv', 'PS', 'T', 'RH',
                     'WS', 'WD', 'PP', 'odSS01', 'ojits']
        # Use read_fwf to read the fixed-width formatted file
        for hh in range(len(cwb_flist)):
            data = pd.read_fwf(cwb_flist[hh], widths=col_widths, names=col_names)
            cwb_lon, cwb_lat, cwb_pcp = data[['lon', 'lat', 'PP']].values.T
            self.cwb_LON = cwb_lon
            self.cwb_LAT = cwb_lat

            if accumulate_daily:                              # target_pcp is daily precip.
                if hh<1:
                    target_pcp = cwb_pcp
                else:
                    target_pcp = np.add(target_pcp, cwb_pcp)

            else:                                            # target_pcp is hourly precip.
                if hh<1:
                    target_pcp= cwb_pcp[np.newaxis, ...]
                else:
                    target_pcp= np.concatenate((target_pcp, cwb_pcp[np.newaxis, ...]), axis=0)
        target_pcp    = np.where(target_pcp>=0., target_pcp, np.nan)
        if accumulate_daily:
            pcp_table = pd.DataFrame({'stn_lon':cwb_lon, 'stn_lat':cwb_lat, 'precip':target_pcp})
        else:
            #pcp_table = target_pcp.copy()
            #raise ValueError("Table for hourly precipitation isn't built yet.")
            pcp_table = pd.DataFrame({'stn_lon':cwb_lon, 'stn_lat':cwb_lat, 'precip':target_pcp.T.tolist()})
        return pcp_table

    def get_binned_dprecip_day(self, date,
                               select_region:tuple=(None, None, None, None)):
        """
        Binned the daily precip. for all CWA stations in the selected region. Return counts in those bins.
        """
        # Set PDF bins
        bounds      = np.array([1, 2, 6, 10, 15, 20, 30, 40, 50, 70, 90, 110, 130, 150, 200, 300])  # 16
        bin_array   = np.zeros(bounds.shape[0]+1)  # 17
        # Get daily precip.
        dpcp_table = self.get_cwb_precip_table(date, accumulate_daily=True)
        # Select region
        lon_min, lon_max, lat_min, lat_max = select_region
        dpcp_table_reg = dpcp_table[(dpcp_table['stn_lon']>=lon_min)&
                                    (dpcp_table['stn_lon']< lon_max)&
                                    (dpcp_table['stn_lat']>=lat_min)&
                                    (dpcp_table['stn_lat']< lat_max)]
        dpcp_reg       = np.asarray(dpcp_table_reg['precip'])
        # Loop for all bins
        for i in range(bin_array.shape[0]):        # i = 0 ~ 16
            if i < 1:                              # i = 0
                cond         = (dpcp_reg>=0)&(dpcp_reg<bounds[i])
            elif i > bin_array.shape[0]-2:         # i = 16
                cond         = (dpcp_reg>=bounds[i-1])
            else:                                  # i = 1~15
                cond         = (dpcp_reg>=bounds[i-1])&(dpcp_reg<bounds[i])
            bin_array[i] = dpcp_reg[cond].shape[0]
        # Check calculation
        # print("Total number of stations:   ", dpcp_reg.shape[0])
        # print("Total number of >=0 precip.:", bin_array.sum())
        # print("Total number of <0  precip.:", np.isnan(dpcp_reg).sum())
        return bin_array

    def get_binned_dprecip_drange(self, datelist,
                                  select_region:tuple=(None, None, None, None),
                                  probability=False):
        """
        Get the binned counts of precip. in a range of dates. Return PDF if `probability` is set to True.
        """
        func_config = {'select_region':select_region}
        count_dates = self._cal_for_all_dates(datelist=datelist,
                                              func=self.get_binned_dprecip_day,
                                              func_config=func_config)
        count_dates = sum(count_dates)   # sum the result from different days
        if probability:
            return count_dates/count_dates.sum()
        else:
            return count_dates



if __name__=='__main__':
    wtab_module_all  = weather_table(year_list =np.arange(2020, 2021).tolist(),
                                     month_list=np.arange(4, 10).tolist(), 
                                     lat_range=(22, 20), lon_range=(115, 119))
    datestr = wtab_module_all.DLIST_Month[0]
    datestr = '20200723'
    pcp_daily_table = wtab_module_all.get_cwb_precip_table(datestr, 
                                                           accumulate_daily=True)
    pcp_table       = wtab_module_all.get_cwb_precip_table(datestr,
                                                           accumulate_daily=False)
    diurnal_array = np.vstack(pcp_table['precip'])
    idx = np.nonzero(~np.all(diurnal_array,axis=1))[0]
    diurnal_cycle   = np.nanmean(diurnal_array[idx,:], axis=0)

    print(f'{datestr}, number of available station : ',idx.size)
    print('diurnal ...')
    print(diurnal_cycle)


