import os
import sys
from datetime import datetime, timedelta

import matplotlib as mpl
mpl.use('agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, '..')
import utils.utils_draw as udraw
import utils.utils_plot_cartopy as ucartopy
import utils.utils_read as uread


lonb = [105, 137]
latb = [12, 37]
levb = [1000.0, 700.0]

RAIN_BOUNDS = [1, 2, 5, 10, 15, 20, 30, 50, 100]
TOPO_BOUNDS = np.arange(0, 3500.1, 500)
SUPPORTED_MODELS = {'nicam', 'icon'}


def load_weather_label(model, nowtime):
    csvfile = f'./csv/{model}_{nowtime.year}.csv'
    if not os.path.exists(csvfile):
        return 'unknown', '0'

    df = pd.read_csv(csvfile, usecols=['time', 'wtype', 'diurnal_rain'])
    idx = pd.to_datetime(df['time']) == nowtime
    if np.sum(idx) < 1:
        return 'unknown', '0'

    df_wtype = df[idx].iloc[0]
    wtype = df_wtype['wtype']
    diurnal_flag = '1' if df_wtype['diurnal_rain'] else '0'
    return wtype, diurnal_flag


def draw_gsrm_rain(model, nowtime):
    print(model, nowtime)

    lon_gs, lat_gs, rain_gs = uread.read_gsrm(
        model, 'pr', nowtime, lonb, latb, daily=True, tw_time=True,
    )
    # lon_e, lat_e, suf_geo_e = uread.read_era5_2d('suf_geo', nowtime, lonb, latb)
    # topo_e = suf_geo_e / 9.8
    topo_lon, topo_lat, topo_height = uread.read_gsrm(
        model, 'orog', nowtime
    )

    rain_gs = rain_gs * 3600.0 * 24.0
    rain_gs = np.where(rain_gs > RAIN_BOUNDS[0], rain_gs, np.nan)

    rain_cmap = plt.cm.jet
    rain_cmap.set_under((1, 1, 1, 0.0))
    rain_norm = mpl.colors.BoundaryNorm(RAIN_BOUNDS, 256, extend='max')

    topo_cmap = plt.cm.Greys
    topo_norm = mpl.colors.BoundaryNorm(TOPO_BOUNDS, 256, extend='max')

    udraw.set_figure_defalut()
    fig = plt.figure(figsize=(12, 8))
    plottools = ucartopy.PlotTools_cartopy()
    ax1 = plottools.Axe_map(
        fig,
        111,
        xlim_=lonb,
        ylim_=latb,
        xloc_=np.arange(lonb[0], lonb[-1] + 0.001, 5),
        yloc_=np.arange(latb[0], latb[-1] + 0.001, 5),
    )
    ax1.set_position([0.05, 0.05, 0.8, 0.85])
    c = ax1.get_position()
    h = c.height / 4
    h0 = c.height / 3
    cax1 = fig.add_axes([c.x1 + 0.01, c.y0 + h0 * 0, 0.03, h])
    cax2 = fig.add_axes([c.x1 + 0.01, c.y0 + h0 * 1, 0.03, h])

    topo = ax1.contourf(
        topo_lon,
        topo_lat,
        np.where(topo_height > 50, topo_height, np.nan),
        cmap=topo_cmap,
        levels=TOPO_BOUNDS,
        extend='max',
    )
    cbar = fig.colorbar(topo, orientation='vertical', cax=cax1)
    cbar.ax.set_title('TOPO[m]', fontsize=15, y=1.05, loc='left')

    rain = ax1.pcolormesh(
        lon_gs,
        lat_gs,
        rain_gs,
        alpha=0.8,
        norm=rain_norm,
        cmap=rain_cmap,
    )
    cbar = fig.colorbar(rain, orientation='vertical', cax=cax2, extend='max')
    cbar.ax.set_title('rain[mm/d]', fontsize=15, y=1.05, loc='left')

    plottools.Plot_cartopy_map(ax1)
    datestr = nowtime.strftime('%Y-%m-%d')
    ax1.set_title(
        f'{datestr}\n{model.upper()}',
        loc='left',
        fontweight='bold',
        fontsize=20,
    )

    wtype_str, diurnal_flag = load_weather_label(model, nowtime)
    ax1.set_title(wtype_str, loc='right', fontweight='bold', fontsize=20)

    outdir = f'./fig/{model}'
    os.makedirs(outdir, exist_ok=True)
    outfile = (
        f'{outdir}/imerg_{nowtime.strftime("%Y%m%d")}_{wtype_str}_{diurnal_flag}.png'
    )
    plt.savefig(outfile, facecolor='w', bbox_inches='tight', dpi=400)
    plt.close(fig)
    print(nowtime, '->', outfile)


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python draw_imerg_gsrm.py <nicam|icon>')

    model = sys.argv[1].lower()
    if model not in SUPPORTED_MODELS:
        raise SystemExit(f'Unsupported model: {model}')

    start_time = datetime(2020, 6, 2)
    end_time = datetime(2020, 10, 1)
    ndays = (end_time - start_time).days

    for iday in range(ndays):
        nowtime = start_time + timedelta(days=iday)
        draw_gsrm_rain(model, nowtime)


if __name__ == '__main__':
    main()
