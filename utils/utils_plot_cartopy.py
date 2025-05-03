import matplotlib.pyplot as plt 
import matplotlib as mpl
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt 
import matplotlib as mpl
import xarray as xr
import numpy as np

# Utilities
class PlotTools_cartopy():
    def __init__(self):
        self.proj = ccrs.PlateCarree()
        self.ds_topo = xr.open_dataset('../data/TOPO.nc')  # TaiwanVVM topography, available upon request

    def Axe_map(self, fig, gs,
                xlim_, ylim_, **grid_info):
        # Set map extent
        axe  = fig.add_subplot(gs, projection=self.proj)
        axe.set_extent([xlim_[0], xlim_[-1], ylim_[0], ylim_[-1]], crs=self.proj)
        # Set additional grid information
        if len(grid_info)>0:
            if grid_info['xloc_'] is not None:
                axe.set_xticks(grid_info['xloc_'], crs=self.proj)
                axe.set_xticklabels(['' for i in range(len(grid_info['xloc_']))])  # default: no tick labels
            if grid_info['yloc_'] is not None:
                axe.set_yticks(grid_info['yloc_'], crs=self.proj)
                axe.set_yticklabels(['' for i in range(len(grid_info['yloc_']))])
            gl = axe.gridlines(xlocs=grid_info['xloc_'], ylocs=grid_info['yloc_'],
                               draw_labels=False)
        return axe

    def Plot_cartopy_map(self, axe):
        axe.add_feature(cfeature.LAND,color='grey',alpha=0.1)
        axe.coastlines(resolution='50m', color='black', linewidth=1)

    def Plot_vvm_map(self, axe, color, linewidth):
        axe.contour(self.ds_topo.lon, self.ds_topo.lat, self.ds_topo.topo, 
                    levels=np.array([-1e-3, 1e-3]), 
                    colors=color, linewidths=linewidth)
    
    def Plot_vvm_topo(self, axe, color, linewidth=None):
        topo_bounds= np.arange(0, 3500.1, 500)
        alpha_list = [0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        cmap_topo  = mpl.colors.ListedColormap([(0, 0, 0, i) for i in alpha_list])
        norm_      = mpl.colors.BoundaryNorm(topo_bounds, cmap_topo.N, extend='max')
        imtopoh    = axe.contourf(self.ds_topo.lon, self.ds_topo.lat, self.ds_topo.topo*1e2, 
                                  levels=topo_bounds, 
                                  cmap=cmap_topo, norm=norm_, extend='max', antialiased=1)
        if linewidth is not None:
            axe.contour(self.ds_topo.lon, self.ds_topo.lat, self.ds_topo.topo*1e2, levels=np.array([499.99, 500.01]), 
                        colors=color, linewidths=linewidth)
        else:
            pass
        return imtopoh
        
    def Plot_twcwb_pcp(self, axe, 
                       lon, lat, precip,
                       s, alpha, precip_bounds=[1, 2, 6, 10, 15, 20, 30, 40, 50, 70, 90, 110, 130, 150, 200, 300], edgecolors=None):
        bounds= np.array(precip_bounds)
        cmap  = plt.cm.jet
        norm  = mpl.colors.BoundaryNorm(bounds, cmap.N, extend='both')
        im    = axe.scatter(lon, lat, c=precip, s=s, 
                            cmap=cmap, norm=norm, alpha=alpha, edgecolors=edgecolors)
        return im



def Plot_cwb_comp(rainfall_label:str, stn_lon, stn_lat, precip_array, figtitle=False, figname=False):
    if rainfall_label=='strong':
        bounds    = np.array([2, 5, 10, 15, 25, 40, 50, 70, 90])
        alpha     = 0.7
    elif rainfall_label=='weak':
        bounds    = np.array([1, 5, 10, 15, 25])
        alpha     = 0.75
    # Figure initialize
    fig = plt.figure(figsize=(4, 8))
    gs  = mpl.gridspec.GridSpec(1, 1, figure=fig)
    ## Plot:
    plottools = PlotTools_cartopy()
    ax1   = plottools.Axe_map(fig, gs[0], xlim_=[119.95, 122.05], ylim_=[21.85, 25.5],
                              xloc_=np.arange(120, 122.1, 1), yloc_=np.arange(22, 25.1, 1))
    plottools.Plot_vvm_map(ax1, '0.5', 1.5)  # coastline
    temp = np.argsort(precip_array)
    imcwb = plottools.Plot_twcwb_pcp(ax1, stn_lon[temp], stn_lat[temp], precip_array[temp], s=75, alpha=alpha, precip_bounds=bounds)
    cax  = fig.add_axes([ax1.get_position().x1+0.06, ax1.get_position().y0, 0.03, ax1.get_position().height])
    cbar = fig.colorbar(imcwb, orientation='vertical', cax=cax)
    cbar.solids.set(alpha=1)  # Default: set cbar to full color (w/out tranparency)
    cbar.set_ticks(ticks=bounds, labels=[int(i) for i in bounds])
    cbar.set_label('mm/day', fontsize=16)
    cbar.ax.tick_params(labelsize=13)
    cbar.outline.set_linewidth(1.5)

    topo_bounds= np.arange(0, 3500.1, 500)
    imtopoh    = plottools.Plot_vvm_topo(ax1, '0.5', 0.5)
    cax  = fig.add_axes([ax1.get_position().x0,ax1.get_position().y0-0.06, ax1.get_position().width, 0.015])
    cbar = fig.colorbar(imtopoh, orientation='horizontal', cax=cax, extend='max')
    cbar.set_ticks(ticks=topo_bounds, labels=[f"{i/1e3:.1f}" for i in topo_bounds])
    cbar.ax.tick_params(labelsize=13)
    cbar.set_label('Topography Height (km)', fontsize=16)
    cbar.outline.set_linewidth(1.5)

    ax1.set_xticklabels([f'{int(i)}E' for i in np.arange(120, 122.1, 1)], fontsize=16)
    ax1.set_yticklabels([f'{int(i)}N' for i in np.arange(22, 25.1, 1)], fontsize=16)
    if figtitle:
        ax1.set_title(f'{figtitle}', loc='left', fontsize=20)
    else:
        ax1.set_title('CWA precipitation', fontsize=16)
    if figname:
        plt.savefig(f'./fig/{figname}.png', facecolor='w', bbox_inches='tight', dpi=400)
    else:
        plt.show()
