import numpy as np
import os, sys 
sys.path.insert(0, '..')
import utils.utils_read as uread
import utils.utils_draw as udraw
import utils.utils_cwa as ucwa
from datetime import datetime, timedelta
import iop_features
from functools import partial
import re
import pandas as pd
from multiprocessing import Pool, cpu_count

features_order = [
    'CWVatDongsha','CWVatNETW', 'WSatBanqiao', 'WSatNETW', 'CrossStraitUatNWTW', 'UatNETW',
    'swUatDongSha', 'swUatDongShaNaN', 'sUatNETW', 'sUatNETWNaN',
    'swDEPTHatNETW', 'MSEatNETW', 'swLAYERatSWTW', 'IVTatDongSha',
    'IVTatDongShaNaN', 'LeeVortex', 'CRHatNETW',
    'deltaCWVatTW', 'deltaLTSatSWTW', #'zetaatETW', 'CAPEatNETW', 'seUatETW',
    #'month',
    #'year','month','day'
]

features_render = {
    'CWVatDongsha'          : {'name' : 'CWV_Dongsha'                            , 'unit': 'mm'        , "coeff": 1.0    },
    'CWVatNETW'             : {'name' : 'CWV_NETW'                               , 'unit': 'mm'        , "coeff": 1.0    },
    'WSatBanqiao'           : {'name' : 'WindShear_Banqiao'                      , 'unit': 'm/s'       , "coeff": 1.0    },
    'WSatNETW'              : {'name' : 'WindShear_NETW'                         , 'unit': 'm/s'       , "coeff": 1.0    },
    'CrossStraitUatNWTW'    : {'name' : 'CrossTaiwanStraitWindSpeed_NWTW'        , 'unit': 'm/s'       , "coeff": 1.0    },
    'UatNETW'               : {'name' : 'WindSpeed_NETW'                         , 'unit': 'm/s'       , "coeff": 1.0    },
    'swUatDongSha'          : {'name' : 'SouthwesterlyWindSpeed_DongSha'         , 'unit': 'm/s'       , "coeff": 1.0    },
    'swUatDongShaNaN'       : {'name' : 'SouthwesterlyWindSpeed_DongSha_NaN'     , 'unit': 'Y/N'       , "coeff": 1.0    },
    'sUatNETW'              : {'name' : 'SoutherlyWindSpeed_NETW'                , 'unit': 'm/s'       , "coeff": 1.0    },
    'sUatNETWNaN'           : {'name' : 'SoutherlyWindSpeed_NETW_NaN'            , 'unit': 'Y/N'       , "coeff": 1.0    },
    'swDEPTHatNETW'         : {'name' : 'SouthwesterlyDepth_NETW'                , 'unit': 'non dim.'  , "coeff": 1.0    },
    'MSEatNETW'             : {'name' : 'MSE_NETW'                               , 'unit': 'K'         , "coeff": 1/1004 },
    'swLAYERatSWTW'         : {'name' : 'SouthwesterlyLayer_SWTW'                , 'unit': 'non dim.'  , "coeff": 1.0    },
    'IVTatDongSha'          : {'name' : 'IVT_Dongsha'                            , 'unit': 'kg/m/s'    , "coeff": 1.0    },
    'IVTatDongShaNaN'       : {'name' : 'IVT_Dongsha_NaN'                        , 'unit': 'Y/N'       , "coeff": 1.0    },
    'LeeVortex'             : {'name' : 'LeeVortex'                              , 'unit': '1E-5 1/s'  , "coeff": 1E5    },
    'CAPEatNETW'            : {'name' : 'CAPE_NETW'                              , 'unit': 'J/kg'      , "coeff": 1.0    },
    'CRHatNETW'             : {'name' : 'CRH_NETW'                               , 'unit': 'non dim.'  , "coeff": 1.0    },
    'deltaCWVatTW'          : {'name' : 'CWVanomaly_TW'                          , 'unit': 'mm'        , "coeff": 1.0    },
    'deltaLTSatSWTW'        : {'name' : 'LTSanomaly_SWTW'                        , 'unit': 'K'         , "coeff": 1.0    },
    'zetaatETW'             : {'name' : 'zeta_ETW'                               , 'unit': 'Y/N'       , "coeff": 1.0    },
    'seUatETW'              : {'name' : 'SoutheasterlyWindSpeed_ETW'             , 'unit': 'non dim.'  , "coeff": 1.0    },
    'month'                 : {'name' : 'Month'                                  , 'unit': 'month'     , "coeff": 1.0    },
}

features_max_min = {}

df = pd.read_csv('../iop_routine/features_nan_sep_weak_afternoon_date.csv')
features_max_min = df.agg(['min', 'max']).T.to_dict('index')


##  df_max = df.max(axis=0)
##  df_min = df.min(axis=0)
##  for idx, row in df_max.iteritems():
##      if idx not in features_max_min.keys():
##          features_max_min[idx] = {}
##      features_max_min[idx]["max"] = row
##  for idx, row in df_min.iteritems():
##      features_max_min[idx]["min"] = row

#print(features_max_min)


def get_feature(nowtime):
    lonb = [116., 123.]
    latb = [16., 26.]
    read_3d = partial(uread.read_era5_3d,nowtime=nowtime,lonb=lonb,latb=latb)
    
    feature_ori_val = dict()
    feature_ret_val = dict()
    for feature in features_order :
        cal_func_name = feature
        nan_feature = False
        searched = re.search(r"(.+)NaN$",feature)
        if searched :
            cal_func_name =  searched[1]
            nan_feature = True
    
        ret_val = 0.0
        if feature == "month" :
            # month
            month_int = int(today_date[5:7])
            ret_val = (month_int - 5) / (10 - 5)
            feature_ori_val[feature] = "{:02d}".format(month_int)
        elif nan_feature:
            # nan case
            func_ret = iop_features.__dict__["cal_" + cal_func_name](read_3d)
            if func_ret < -9998 :
                ret_val = 1.0
                feature_ori_val[feature] = "Y"
            else:
                ret_val = 0.0
                feature_ori_val[feature] = "N"
        else:
            # normal case
            func_ret = iop_features.__dict__["cal_" + cal_func_name](read_3d)
            if func_ret < -9998 :
                func_ret = 0.0  # nan 
            max_val = features_max_min[cal_func_name]["max"]
            min_val = features_max_min[cal_func_name]["min"]
            ret_val = (func_ret - min_val) / (max_val - min_val)
            feature_ori_val[feature] = "{:10.2f}".format(func_ret * features_render[feature]["coeff"])
            if features_render[feature]["unit"] == "Y/N" :
                if func_ret > 0.5 :
                    feature_ori_val[feature] = "Y"
                else:
                    feature_ori_val[feature] = "N"
        feature_ret_val[feature] = ret_val
        #print(feature,'%.2f'%func_ret,'%.3f'%ret_val, f'(min,max)=({min_val:.1f},{max_val:.1f})')
    return feature_ori_val, feature_ret_val


# ---- Parallel execution and DataFrame merging --------------------
def run_parallel(datetimes: list[datetime], processes: int | None = None
                 ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    datetimes : list of datetime objects
    processes : number of processes to use (default = CPU count)
    return    : two DataFrames (df1, df2) indexed by datetime
    """
    if not datetimes:
        # Return empty DataFrames if input list is empty
        return (pd.DataFrame(index=pd.DatetimeIndex([], name="time")),
                pd.DataFrame(index=pd.DatetimeIndex([], name="time")))

    if processes is None:
        processes = max(1, min(cpu_count(), len(datetimes)))

    # Use Pool.map to keep result order same as input order
    with Pool(processes=processes) as pool:
        results = pool.map(get_feature, datetimes,
                           chunksize=max(1, len(datetimes)//(processes*4) or 1))

    # Combine outputs into dicts {datetime: dict}
    map1 = {dt: d1 for dt, (d1, d2) in zip(datetimes, results)}
    map2 = {dt: d2 for dt, (d1, d2) in zip(datetimes, results)}

    # Convert to DataFrame (rows = datetimes, columns = dict keys)
    df1 = pd.DataFrame.from_dict(map1, orient="index")
    df2 = pd.DataFrame.from_dict(map2, orient="index")

    # Convert index to DatetimeIndex and sort
    df1.index = pd.DatetimeIndex(df1.index, name="time")
    df2.index = pd.DatetimeIndex(df2.index, name="time")
    df1 = df1.sort_index()
    df2 = df2.sort_index()

    return df1, df2

### Rage ###
if __name__=="__main__":
    os.system('mkdir -p ./csv')
    ndays = 30+31+31+30
    nproc = 25
    for yr in range(2000,2021):
        print(yr)
        #feat_ori_val, feat_ret_val = get_feature(nowtime)
        initime = datetime(yr,6,1)
        datelist = [initime + timedelta(days=i) for i in range(ndays)]
        df_ori_val, df_ret_val = run_parallel(datelist, processes=nproc)
        df_ori_val.to_csv(f'./csv/ori_val_{yr:04d}.csv', index=True)
        df_ret_val.to_csv(f'./csv/ret_val_{yr:04d}.csv', index=True)


