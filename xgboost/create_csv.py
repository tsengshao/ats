import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def merged_csv(yr0, yr1, fname_fmt):
    dfs = []
    for iyr in range(yr0, yr1+1):
        fname = fname_fmt.format(iyr=iyr)
        df = pd.read_csv(fname)
        dfs.append(df)
    merged_df = pd.concat(dfs, ignore_index=True)
    merged_df["time"] = pd.to_datetime(merged_df["time"])
    merged_df = merged_df.set_index('time')
    return merged_df

yr0=2019
yr1=2020
table_flag = f'{yr0}_{yr1}'

fname_fmt  = '../feature/csv/ret_val_{iyr}.csv'
df_feature = merged_csv(yr0, yr1, fname_fmt)

fname_fmt  = '../synoptic/csv/weather_{iyr}.csv'
df_weather = merged_csv(yr0, yr1, fname_fmt)

mask = (df_weather['wtype'] == 'other') & (df_weather['diurnal_rain'])
df_Y = pd.DataFrame({
    'Y_flag': np.where(mask, 1, 0)
}, index=df_weather.index)

df_feature.to_csv(f'input_{table_flag}.csv')
df_Y.to_csv(f'output_{table_flag}.csv')



