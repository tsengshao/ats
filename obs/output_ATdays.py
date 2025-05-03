import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import netCDF4 as nc
import datetime as dt
import glob
import matplotlib.colors as colors
from matplotlib.colors import LightSource
#from get_topo import get_topo

#%%
def get_PR():

    fname = lambda yr,mo: '/data/huanghuai/DATA/CWB_nc/CWBstation_%04d%02d.nc'%(yr,mo)
    dat = nc.Dataset(fname(1996,12))
    stations = np.array(list(dat.groups.keys()))

    lon = np.array([dat[st]['lon'][0] for st in stations])[:]
    lat = np.array([dat[st]['lat'][0] for st in stations])[:]
    func = np.array([np.sum(dat[st]['its'][:]) for st in stations])
    #ind = np.where((119.8<=lon)&(lon<=122.05)&(21.8<=lat)&(lat<=25.4)&(func>0))[0]
    #stations = stations[ind]
    
    PR_all = {}
    for st in stations:
        PR_all[st] = {'PR':[], 
                      'lon':dat[st]['lon'][0], 
                      'lat':dat[st]['lat'][0], 
                      'z':dat[st]['elev'][0]}
    
    for yr in range(2020, 2021):
        for mo in range(5,10): 
            print(yr,mo)
            dat = nc.Dataset(fname(yr,mo))
            for st in stations:
                PR = dat[st]['PR'][:]
                PR[PR<0] = np.nan
                PR_all[st]['PR'] += [PR]
    for st in stations:
        tmp = np.concatenate(PR_all[st]['PR'])
        tmp = np.roll(tmp, -1)
        PR_all[st]['PR'] = tmp.reshape((-1,24))

    return PR_all

#%%
def get_function_gauge(PR):
    funcgauge = []
    for st in PR.keys():
        PRnum = np.sum(~np.isnan(PR[st]['PR']), axis=1)
        PRfunc = np.mean(PRnum>12)
        if PRfunc>0.4:
            funcgauge += [st]
            
    return np.array(funcgauge)

#%%
def get_ATdays(PR, funcgauge, coor=[119.8,122.1,21.7,25.6]):
    funcgauge1 = []
    
    for st in funcgauge:
        lon = PR[st]['lon'][0]
        lat = PR[st]['lat'][0]
        if (coor[0]<=lon)&(lon<=coor[1])&(coor[2]<=lat)&(lat<=coor[3]):
            funcgauge1 += [st]
            
    
    AM = np.zeros((len(funcgauge1), len(PR['466920']['PR'])))
    PM = np.zeros((len(funcgauge1), len(PR['466920']['PR'])))
    for i, st in enumerate(funcgauge1):
        AM[i] = np.nansum(PR[st]['PR'][:,0:9], axis=1) #+ np.nansum(PR[st][:,22:], axis=1)
        PM[i] = np.nansum(PR[st]['PR'][:,9:], axis=1)
    AMmax = np.max(AM, axis=0)
    AMmean = np.mean(AM, axis=0)
    PMmax = np.max(PM, axis=0)
    PMmean = np.mean(PM, axis=0)
    
    return (AMmean<PMmean)&(AMmax<1)&(PMmax>20)&(PMmax<150)


#%%
datei = dt.datetime(2021,1,1)
#datei = dt.datetime(2005,1,1)
date = []
while datei.year < 2021:
    if (datei.month>=5)&(datei.month<=9):
        date += [datei]
    datei += dt.timedelta(days=1)
date = np.array(date)
PR = get_PR()
#%%
funcgauge = get_function_gauge(PR)
sys.exit()
dayi = get_ATdays(PR, funcgauge, coor=[121.2,121.8,24.8,25.2])
dateAT = date[dayi]
month = np.array([t.month for t in dateAT])
#imonth = (month>=5)&(month<=9)
#dateAT = dateAT[imonth]

##%%
#'''
event  = pd.read_excel('/data/huanghuai/DATA/1980-2020_weather_event_20220601.xlsx')
time_event = np.array([dt.datetime.strptime(str(y), '%Y%m%d') for y in event.yyyymmdd])
NWPTY  = np.array(event.NWPTY, dtype=bool)
TC1000 = np.array(event.TC1000, dtype=bool)
TC500  = np.array(event.TC500, dtype=bool)
SSWF   = np.array(event.SSWF, dtype=bool)
SWF  = np.array(event.SWF, dtype=bool)
FT   = np.array(event.FT, dtype=bool)
NE   = np.array(event.NE, dtype=bool)
#timeWk = time_event[(~TC1000)&(~FT)&(~NE)&(~SSWF)]
timeWk = time_event[(~FT)&(~NE)]
#timeWk = time_event#[FT|NE]

iswk = np.array([d in timeWk for d in dateAT])
dateAT = dateAT[iswk]

#'''
dayi = np.array([d in dateAT for d in date])
print(len(funcgauge), len(dateAT))

np.save('Taipei_TrueLab_20.npy', dateAT)

#%%
fname = lambda yr,mo: '/home/huanghuai/DATA/CWB_nc/CWBstation_%04d%02d.nc'%(yr,mo)

#fname = lambda yr: '/home/huanghuai/DATA/obs/SFC_nc/SFC_%04d.nc'%(yr,mo)
dat = nc.Dataset(fname(1996,12))
lon = np.array([dat[st]['lon'][0] for st in funcgauge])
lat = np.array([dat[st]['lat'][0] for st in funcgauge])
elev = np.array([dat[st]['elev'][0] for st in funcgauge])
PRs = np.array([np.nanmean(np.nansum(PR[st]['PR'][dayi][:,10:], axis=1)) for st in funcgauge])
#%%
#lonV, latV, sprec = read_VVM(dtype = 'cln')

#%%
#xx, yy, zz = get_topo(coor=[120.9,122,24.4,25.4])

topo = nc.Dataset('/home/huanghuai/huanghuai/DATA/MAP/TOPO_1km.nc')
xx = topo['lon'][:]
yy = topo['lat'][:]
zz = topo['topo'][:]


county = gpd.read_file(r'/home/huanghuai/DATA/MAP/twcounty/twcounty.shp')

levels = np.array([0,2,5,7,10,15])
colors = [(0,0,0,0),(0.3,0.4,1),(0,0.8,0.2),(1,1,0),(1,0,0),(0.8,0,0.8)]
sizes = [10,20,30,60,80,100]

f,ax = plt.subplots(figsize=(6,6), dpi=300)
county.boundary.plot(ax=ax, color='k')
for i in range(len(levels)-1):
    ist = (levels[i]<=PRs)&(PRs<=levels[i+1])

    ax.scatter(lon[ist], lat[ist], fc=colors[i], s=sizes[i],zorder=500, label=f'{levels[i]}, {levels[i+1]}', ec='k', lw=0.3)
    #plt.show()
    #ax.scatter(0,i, c=colors[i], zorder=500, label=f'{levels[i]}, {levels[i+1]}')
c = ax.contourf(xx, yy, zz+np.nan, levels=levels, colors=colors, extend='max')
#c = ax.contourf(lonV, latV, np.mean(sprec, axis=0), levels=levels, colors=colors, extend='max')
plt.colorbar(c, shrink=0.4, aspect=10, extendfrac=1/(len(levels)-1))
#ax.legend()
#ax.contourf(xx, yy, zz, colors=[(0,0,0,0),(0,0,0,0.15),(0,0,0,0.3)], zorder=1, levels=[0,500,2000], extend='max', antialiased=1)
ax.axis([119.8, 122.05, 21.8, 25.4])
ax.grid()
ax.axis([121,122,24.5,25.4])
#plt.savefig('fig_funcgauge',dpi=300)




#%%
#istation = (119.9<=lon)&(lon<=121.1)&(22.3<=lat)&(lat<=24.5)&(elev>1500)
#istation = (120.3<=lon)&(lon<=120.9)&(23.2<=lat)&(lat<=23.8)&(elev>1000)

#print(istation.sum())
PRmt = np.array([PR[st][dayi] for st in funcgauge])
#PRdy = 
PRmn = np.nanmean(PRmt, axis=(0))
PRinit = np.zeros(PRmn.shape)
for s in range(len(PRmn)):
    try: 
        init = np.where(PRmn[s]>=0.5)[0]
        init = init[init>10][0]
    except: init=0
    PRinit[s] = np.roll(PRmn[s], -init)
    if init==0: 
        #PRinit[s] = np.nan
        print(s)

PRinit = np.roll(PRinit, 3)
t_shift = np.arange(-12,12)+10


time_c, sprec_c = read_VVM_diurnal(dtype='cln')
time_d, sprec_d = read_VVM_diurnal(dtype='dty')
time_d, sprec3_d = read_VVM_diurnal(dtype='dtyP3K')

#'''
#ax2 = ax.twinx()
#%%
#[ax2.plot(t_shift, PP, c='gray', lw=0.2) for PP in PRinit]
sprecc_hr = np.sum(np.array([sprec_c[:,i+1::6] for i in range(6)]), axis=0)
sprecd_hr = np.sum(np.array([sprec_d[:,i+1::6] for i in range(6)]), axis=0)
sprecd3_hr = np.sum(np.array([sprec3_d[:,i+1::6] for i in range(6)]), axis=0)

import scipy.signal as ss

mean_d = np.nanmean(sprec_d, axis=0)
mean_d3 = np.nanmean(sprec3_d, axis=0)
corr = ss.correlate(mean_d, mean_d3)
lags = ss.correlation_lags(len(mean_d), len(mean_d3))

lag = lags[np.argmax(corr)]

x = mean_d[20:140]
y = np.roll(mean_d3, lag)[20:140]
a, b = np.polyfit(x, y, 1)
a = np.max(mean_d3)/np.max(mean_d)
print(lag*10, 'min lag')
print(a, 'times pr')

plt.figure()
plt.plot(lags, corr)

plt.figure()
plt.plot(mean_d)
plt.plot(mean_d3)
plt.plot(np.roll(mean_d3, lag))

plt.figure()
plt.plot(mean_d*a)
plt.plot(np.roll(mean_d3, lag))

#%%
f, axs = plt.subplots(1,3, figsize=(9,2.3))
ax = axs[0]
[ax.plot(np.arange(24), PP, c='gray', lw=0.1) for PP in np.nanmean(PRmt, axis=0)]
ax.plot(np.arange(24), np.nanmean(PRmn, axis=0), c='k', lw=3, label='obs', zorder=2000)
#plt.plot(np.arange(1,25),np.nanmean(sprecc_hr, axis=0), c='b', lw=3, label='cln', zorder=2000)
#[plt.plot(np.arange(1,25),PP, c='b', lw=0.2) for PP in sprecc_hr]
ax = axs[1]
ax.plot(np.arange(1,25),np.nanmean(sprecd_hr, axis=0), c=(0.1,0.7,0.3), lw=3, label='dty', zorder=2000)
[ax.plot(np.arange(1,25),PP, c=(0.1,0.7,0.3), lw=0.2) for PP in sprecd_hr]
ax = axs[2]
ax.plot(np.arange(1,25),np.nanmean(sprecd3_hr, axis=0), c='r', lw=3, label='dtyP3K', zorder=2000)
[ax.plot(np.arange(1,25),PP, c='r', lw=0.2) for PP in sprecd3_hr]
#ax.set_ylim(0,100)
#ax.legend()
[ax.set_ylabel('precp. (mm h$^{-1}$)', x=0.05) for ax in axs]
#ax2.set_ylim(0,25)
#ax2.set_ylabel('precp. (mm/hr)')
[ax.set_xlabel('Time (h)')for ax in axs]
[ax.set_xlim(6,24) for ax in axs]
[ax.set_xticks(np.arange(6,25,3)) for ax in axs]
[ax.set_ylim(0,3.5) for ax in axs]
[ax.grid(ls='--') for ax in axs]
axs[0].set_title('Observation', loc='left', fontsize=14)
axs[1].set_title('Current', loc='left', fontsize=14)
axs[2].set_title('Future', loc='left', fontsize=14)
f.subplots_adjust(hspace=0.5, wspace=0.3)
plt.show()

#plt.plot(np.nanmean(PRmt>1, axis=(0,1)), c='k', lw=3)
#plt.plot(np.nanmean(PRmt>1, axis=(0)).T, c='k', lw=0.1)
'''
for i in range(dayi.sum()//5):
    for j in range(5):
        ij = i*5+j
        plt.plot(np.nanmean(PRmt, axis=0)[ij], label=dateAT[ij])
    plt.legend()
    plt.show()
    
'''
#%%
'''
time = dat['466920']['time']
time = nc.num2date(time[:], time.units).reshape((-1,24))[:,0]

t = np.arange(24)
PREC = dat['C0U710']['PR'][:].reshape((-1,24))

i0 = 51
i0 *= 5
for i in range(i0,i0+5):
    plt.plot(t, PREC[i], label=time[i])
    plt.legend()

'''





