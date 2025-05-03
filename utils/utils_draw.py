import numpy as np
import matplotlib.pyplot as plt 
import sys, os
import matplotlib as mpl 
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap

def set_figure_defalut():
  plt.close('all')
  plt.rcParams.update({'font.size':16,
                       'axes.linewidth':2,
                       'lines.linewidth':5})

def set_black_background():
  plt.rcParams.update({
                       'axes.edgecolor': 'white',
                       'axes.facecolor': 'black',
                       'figure.edgecolor': 'black',
                       'figure.facecolor': 'black',
                       'text.color': 'white',
                       'xtick.color': 'white',
                       'ytick.color': 'white',
                       'axes.labelcolor': 'white',
                      })  

def get_cmap(name='colorful'):
  if name=='pwo':
    top = mpl.colormaps['Purples_r']
    bottom = mpl.colormaps['Oranges']
    newcolors = np.vstack((top(np.linspace(0.3, 1, 128)),\
                           bottom(np.linspace(0, 0.7, 128)),\
                         ))  
    newcmp = mpl.colors.ListedColormap(newcolors, name='OrangeBlue')
  elif name=='colorful':
    colors = ['w', '#00BFFF', '#3CB371', '#F0E68C', '#FFA500', '#FF6347']
    nodes = np.linspace(0,1,len(colors))
    newcmp = mpl.colors.LinearSegmentedColormap.from_list("cmap", list(zip(nodes, colors)))
  return newcmp

def create_basemap_figure(lon, lat, figsize=None):
    plt.close('all')
    set_figure_defalut()
    lon_range = lon.max()-lon.min()
    lat_range = lon.max()-lon.min()
    fig_ratio = (lat_range/lon_range+0.1)
    figsize = (8,fig_ratio*8) if figsize is None else figsize
    fig, ax = plt.subplots(figsize=figsize)

    m = Basemap(llcrnrlon=lon.min(), urcrnrlon=lon.max(),\
                llcrnrlat=lat.min(), urcrnrlat=lat.max(),\
                resolution='i', ax=ax)
    m.drawparallels(np.arange(np.round(lat.min(),1),lat.max(),10), \
                    labels=[1, 0, 0, 0], linewidth=0.01, color='k', zorder=1)
    m.drawmeridians(np.arange(np.round(lon.min(),1),lon.max(),10), \
                    labels=[0, 0, 0, 1], linewidth=0.01, color='k', zorder=1)
    m.drawcoastlines(linewidth=1.,color='gold', zorder=3)
    return fig, ax, m

