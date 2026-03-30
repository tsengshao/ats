import os
import sys
import multiprocessing
from datetime import datetime, timedelta

import matplotlib as mpl
mpl.use('agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from scipy.ndimage import gaussian_filter

sys.path.insert(0, '..')
import utils.utils_draw as udraw
import utils.utils_plot_cartopy as ucartopy
import utils.utils_read as uread


lonb = [105.0, 137.0]
latb = [12.0, 37.0]
levb = [1000.0, 700.0]

tw_lonb = [119.5, 122.5]
tw_latb = [21.5, 26.0]
tw_land_lonb = [120.0, 122.0]
tw_land_latb = [21.5, 25.4]

RAIN_BOUNDS = [1, 2, 5, 10, 15, 20, 30, 50, 100]
IVT_BOUNDS = np.arange(0, 1000.1, 250)
TOPO_BOUNDS = np.arange(0, 3500.1, 500)
QUIVER_SKIP = {
    'nicam': 6,
    'icon': 6,
}
SW_IVT_LONLAT = [115.0, 119.0, 20.0, 22.0]
TC_IVT_LONLAT = [115.0, 130.0, 17.0, 32.0]

_TW_MASK_CACHE = None
MAX_PROCESSES = 10


def get_ivt(model, nowtime, lev_lowb=levb):
    lon_gs, lat_gs, lev_gs, u_gs = uread.read_gsrm(
        model, 'ua', nowtime, lonb, latb, lev_lowb, daily=True, tw_time=True
    )
    lon_gs, lat_gs, lev_gs, v_gs = uread.read_gsrm(
        model, 'va', nowtime, lonb, latb, lev_lowb, daily=True, tw_time=True
    )
    lon_gs, lat_gs, lev_gs, q_gs = uread.read_gsrm(
        model, 'hus', nowtime, lonb, latb, lev_lowb, daily=True, tw_time=True
    )

    u_gs = np.nan_to_num(u_gs, nan=0.0)
    v_gs = np.nan_to_num(v_gs, nan=0.0)
    q_gs = np.nan_to_num(q_gs, nan=0.0)

    ivt_x = -1.0 / 9.8 * np.trapezoid(u_gs * q_gs, x=lev_gs * 100.0, axis=0)
    ivt_y = -1.0 / 9.8 * np.trapezoid(v_gs * q_gs, x=lev_gs * 100.0, axis=0)

    lat_rad = np.deg2rad(lat_gs)
    dlat_m = np.gradient(lat_gs)[:, None] * 111000.0
    dlon_m = np.gradient(lon_gs)[None, :] * 111000.0 * np.cos(lat_rad)[:, None]
    ivt_zeta = np.gradient(ivt_y, axis=1) / dlon_m - np.gradient(ivt_x, axis=0) / dlat_m
    return lon_gs, lat_gs, ivt_x, ivt_y, ivt_zeta


def get_ivt_values(lon, lat, ivt, ivt_z, lonlat):
    ix0 = np.argmin(np.abs(lon - lonlat[0]))
    ix1 = np.argmin(np.abs(lon - lonlat[1])) + 1
    iy0 = np.argmin(np.abs(lat - lonlat[2]))
    iy1 = np.argmin(np.abs(lat - lonlat[3])) + 1

    data = ivt[iy0:iy1, ix0:ix1]
    data_z = gaussian_filter(ivt_z, sigma=4)
    data_z = data_z[iy0:iy1, ix0:ix1]
    return np.nanmin(data), np.nanpercentile(data, 95), np.nanmean(data), np.nanmax(data_z)


def get_tw_mask(model):
    global _TW_MASK_CACHE
    if _TW_MASK_CACHE is not None:
        return _TW_MASK_CACHE

    lon_mask, lat_mask, landfrac = uread.read_gsrm(
        model, 'sftlf', datetime(1970, 1, 1), tw_lonb, tw_latb
    )
    lon2d, lat2d = np.meshgrid(lon_mask, lat_mask)
    mask = (
        (tw_land_lonb[0] <= lon2d)
        * (lon2d <= tw_land_lonb[1])
        * (tw_land_latb[0] <= lat2d)
        * (lat2d <= tw_land_latb[1])
        * (landfrac > 0.2)
    )
    _TW_MASK_CACHE = (lon_mask, lat_mask, mask.astype(bool))
    return _TW_MASK_CACHE


def get_tw_hourly_rain(model, nowtime):
    lon_mask, lat_mask, tw_mask = get_tw_mask(model)
    rain_hourly = []
    for ihr in range(24):
        _, _, rain = uread.read_gsrm(
            model, 'pr', nowtime + timedelta(hours=ihr), tw_lonb, tw_latb, tw_time=True
        )
        rain_hourly.append(rain * 3600.0)
    rain_hourly = np.stack(rain_hourly, axis=0)
    rain_hourly = np.where(np.isnan(rain_hourly), np.nan, rain_hourly)
    rain_land = rain_hourly[:, tw_mask].T
    return lon_mask, lat_mask, tw_mask, rain_hourly, rain_land


def draw_ivt_gsrm(model, nowtime, only_output_flag=False):
    lon_gs, lat_gs, ivtx_gs, ivty_gs, ivtzeta_gs = get_ivt(model, nowtime)
    ivt_gs = np.sqrt(ivtx_gs ** 2 + ivty_gs ** 2)

    _, _, sw_ivtx_mean, _ = get_ivt_values(lon_gs, lat_gs, ivtx_gs, ivtzeta_gs, SW_IVT_LONLAT)
    _, _, sw_ivty_mean, _ = get_ivt_values(lon_gs, lat_gs, ivty_gs, ivtzeta_gs, SW_IVT_LONLAT)
    sw_ivt_mean = np.sqrt(sw_ivtx_mean ** 2 + sw_ivty_mean ** 2)
    sw_ivt_dir = (180.0 + np.arctan2(sw_ivtx_mean, sw_ivty_mean) * 180.0 / np.pi) % 360.0
    _, tc_ivt_max, _, tc_ivt_zeta_max = get_ivt_values(
        lon_gs, lat_gs, ivt_gs, ivtzeta_gs, TC_IVT_LONLAT
    )

    _, _, _, z_gs = uread.read_gsrm(
        model, 'zg', nowtime, lonb, latb, [500.0, 500.0], daily=True, tw_time=True
    )
    lon_pr, lat_pr, pr_gs = uread.read_gsrm(
        model, 'pr', nowtime, lonb, latb, daily=True, tw_time=True
    )
    z500 = z_gs[0]
    pr_gs = pr_gs * 3600.0 * 24.0
    pr_gs = np.where(pr_gs > 0.0, pr_gs, np.nan)

    lon_tw, lat_tw, tw_mask, _, rain_land = get_tw_hourly_rain(model, nowtime)
    _, _, pr_tw = uread.read_gsrm(
        model, 'pr', nowtime, tw_lonb, tw_latb, daily=True, tw_time=True
    )
    pr_tw = pr_tw * 3600.0 * 24.0
    pr_tw = np.where(pr_tw > 0.0, pr_tw, np.nan)

    output = {
        'time': nowtime,
        'model': model,
        'sw_ivt_mean': sw_ivt_mean,
        'sw_ivt_dir': sw_ivt_dir,
        'tc_ivt_max': tc_ivt_max,
        'tc_ivt_zeta_max': tc_ivt_zeta_max,
    }
    if only_output_flag:
        return output

    rain_cmap = plt.cm.jet
    rain_cmap.set_under((1, 1, 1, 0.0))
    rain_norm = mpl.colors.BoundaryNorm(RAIN_BOUNDS, 256, extend='max')

    ivt_cmap = plt.cm.Blues
    ivt_norm = mpl.colors.BoundaryNorm(IVT_BOUNDS, 256, extend='max')

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
    cax3 = fig.add_axes([c.x1 + 0.01, c.y0 + h0 * 2, 0.03, h])

    ax2 = plt.gcf().add_axes((c.x0, c.y0 + c.height * 3 / 5, c.height * 0.8 / 5, c.height * 2 / 5))
    c2 = ax2.get_position()
    wdum = c.width * (5 * 3 / (lonb[1] - lonb[0])) - c2.width
    ax3 = plt.gcf().add_axes((c2.x1, c2.y1 - c.height / 7, wdum, c.height * 1 / 7))

    txt = (
        f"tc_ivt_95th:{tc_ivt_max:8.1f}\n"
        f"tc_ivt_vort_max:{tc_ivt_zeta_max * 1e4:0.1f}" + r"$10^{-4}$ 1/s" + "\n"
        f"sw_ivt_mean:{sw_ivt_mean:8.1f} ({sw_ivt_dir:.1f}deg)"
    )
    bbox = dict(boxstyle='square', fc='1', ec='0')
    ax1.text(
        0.98,
        0.98,
        txt,
        ha='right',
        va='top',
        ma='left',
        transform=ax1.transAxes,
        bbox=bbox,
    )
    for box in [TC_IVT_LONLAT, SW_IVT_LONLAT]:
        ax1.add_patch(
            Rectangle(
                xy=[box[0], box[2]],
                width=box[1] - box[0],
                height=box[3] - box[2],
                facecolor='none',
                edgecolor='k',
                transform=plottools.proj,
                zorder=50,
            )
        )

    #ds_topo = plottools.ds_topo
    topo_lon, topo_lat, topo_height = uread.read_gsrm(
        model, 'orog', nowtime
    )
    ds_topo_vvm = plottools.ds_topo
    topo_vvm_lon = ds_topo_vvm.lon
    topo_vvm_lat = ds_topo_vvm.lat
    topo_vvm_hei = ds_topo_vvm.height

    print('topo_min_max', np.nanmin(topo_height), np.nanmax(topo_height))
    #topo_height = ds_topo.height * 1e3
    topo = ax1.contourf(
        topo_lon,
        topo_lat,
        np.where(topo_height > 0, topo_height, np.nan),
        levels=TOPO_BOUNDS,
        cmap=topo_cmap,
        norm=topo_norm,
        extend='max',
    )
    cbar = fig.colorbar(topo, orientation='vertical', cax=cax1)
    cbar.ax.set_title('TOPO[m]', fontsize=15, y=1.05, loc='left')

    ivt = ax1.pcolormesh(lon_gs, lat_gs, ivt_gs, cmap=ivt_cmap, norm=ivt_norm, alpha=0.85)
    cbar = fig.colorbar(ivt, orientation='vertical', cax=cax3, extend='max')
    cbar.ax.set_title('IVT\n[kg/m/s]', fontsize=15, y=1.05, loc='left')

    lon2d, lat2d = np.meshgrid(lon_pr, lat_pr)
    mask = (
        (tw_lonb[0] <= lon2d)
        * (lon2d <=tw_lonb[1]) 
        * (tw_latb[0] <= lat2d)
        * (lat2d <= tw_latb[1])
        * (pr_gs > 1)
    )
    # mask = (
    #     (tw_land_lonb[0] <= lon2d)
    #     * (lon2d <= tw_land_lonb[1])
    #     * (tw_land_latb[0] <= lat2d)
    #     * (lat2d <= tw_land_latb[1])
    # )
    rain = ax1.pcolormesh(
        lon_pr,
        lat_pr,
        np.where(mask, pr_gs, np.nan),
        cmap=rain_cmap,
        norm=rain_norm,
        alpha=1,
    )
    # rain = ax1.contour(lon_pr, lat_pr, pr_gs, levels=1, linewidths=[1])
    cbar = fig.colorbar(rain, orientation='vertical', cax=cax2, extend='max')
    cbar.ax.set_title('rain[mm/d]', fontsize=15, y=1.05, loc='left')

    skip = QUIVER_SKIP[model]
    ax1.quiver(
        lon_gs[::skip],
        lat_gs[::skip],
        ivtx_gs[::skip, ::skip],
        ivty_gs[::skip, ::skip],
        scale_units='xy',
        scale=600,
        color='k',
    )

    contour = ax1.contour(
        lon_gs,
        lat_gs,
        z500,
        levels=[5880.0],
        linewidths=[5],
        colors=['0.3'],
    )
    plt.clabel(contour, fmt='%.0f')

    ax2.contour(
        topo_vvm_lon, 
        topo_vvm_lat, 
        np.where(topo_vvm_hei > 0, topo_vvm_hei, 0), 
        levels=[0.001],
        colors=['k'],
        linewidths=[1],
    )
    ax2.contourf(
        topo_lon, 
        topo_lat, 
        np.where(topo_height > 0, topo_height, np.nan),
        levels=TOPO_BOUNDS,
        cmap=topo_cmap,
        norm=topo_norm,
    )
    rain=ax2.pcolormesh(
        lon_tw,
        lat_tw,
        pr_tw,
        cmap=rain_cmap,
        norm=rain_norm,
        alpha=0.5,
    )
    ax2.axis((119.8, 122.2, 21.8, 25.6))
    ax2.set_xticks([])
    ax2.set_yticks([])

    x = np.arange(1, 25)
    for igrid in range(rain_land.shape[0]):
        ax3.plot(x, rain_land[igrid], color='0.9', lw=0.5)
    ax3.plot(x, np.nanmean(rain_land, axis=0), color='#D70801')
    ax3.set_xticks(np.arange(6, 25, 3))
    ax3.set_yticks([0, 1, 2, 3])
    ax3.tick_params(axis='y', left=False, labelleft=False, right=True, labelright=True)
    ax3.axis((5, 24, 0, 2.9))
    ax3.text(0.02, 0.98, f'mean ({rain_land.shape[0]})', va='top', ha='left', transform=ax3.transAxes)
    ax3.grid(True)

    plottools.Plot_cartopy_map(ax1)
    datestr = nowtime.strftime('%Y-%m-%d')
    ax1.set_title(
        f'{datestr}\n{model.upper()} / low-level IVT [kg/m/s] / Z500[5880m]',
        loc='left',
        fontweight='bold',
        fontsize=20,
    )

    outdir = f'./fig/{model}/ivt'
    os.makedirs(outdir, exist_ok=True)
    outfile = f'{outdir}/ivt_{nowtime.strftime("%Y%m%d")}.png'
    plt.savefig(outfile, facecolor='w', bbox_inches='tight', dpi=300)
    plt.close(fig)
    print(nowtime, '->', outfile)
    return output


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python draw_ivt_gsrm_new.py <nicam|icon>')

    model = sys.argv[1].lower()
    if model not in QUIVER_SKIP:
        raise SystemExit(f'Unsupported model: {model}')

    start_time = datetime(2020, 6, 2)
    end_time = datetime(2020, 10, 1)
    ndays = (end_time - start_time).days

    datelist = [
        (model, start_time + timedelta(days=iday))
        for iday in range(ndays)
    ]

    nproc = min(len(datelist), os.cpu_count() or 1, MAX_PROCESSES)
    with multiprocessing.Pool(processes=nproc) as pool:
        pool.starmap(draw_ivt_gsrm, datelist)


if __name__ == '__main__':
    main()
