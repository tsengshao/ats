import numpy as np
import pandas as pd
import sys, os
#import metpy.calc as mpcalc
#from metpy.units import units
sys.path.insert(0, '..')
import utils.utils_read as uread
from datetime import datetime, timedelta
from functools import partial

#   VAR_LIST = {
#        "q"   : { "era5" :"q" , "gfs" : "?" },
#        "T"   : { "era5" :"t" , "gfs" : "?" },
#        "u"   : { "era5" :"u" , "gfs" : "?" },
#        "v"   : { "era5" :"v" , "gfs" : "?" },
#        "z"   : { "era5" :"z" , "gfs" : "?" },
#        "vor" : { "era5" :"vo", "gfs" : "?" },
#    }
#    LEV_LIST = [
#        1000, 975, 950, 925, 900, 850, 800, 750, 700, 650, 600, 550, 500, 450, 400, 350, 300, 250, 200, 150, 100
#    ]
#    T_LIST = [
#        0, 1 
#    ]

# z is geopotential [m^2/s^2] in era5, and is geopotential height [m] in gfs
# vor is relative vorticity in era5, and is absolute vorticity in gfs

## def cal_theta(data_wrapper):
##     # lev 0 = 1000 hPa , lev 1 = 975 hPa ....
##     # or
##     # lev = 1000, 975, ...
##     # time 0 = 00Z, time 1 = 12Z
##     # var = "q", "T", "u", "v", "vor"
##     T = data_wrapper(var="T",lev=1000,time=0)
##     T_mean = np.mean(T,axis=1)
## 
##     ## get dim
##     #print(data_wrapper(var="level"))
##     #print(data_wrapper(var="latitude"))
##     #print(data_wrapper(var="longitude"))
##     
##     return np.mean(T_mean)

##   ### Range ###
##   nowtime = datetime(2015,7,10)
##   lonb = [116., 123.]
##   latb = [16., 26.]
##   read_3d = partial(uread.read_era5_3d,nowtime=nowtime,lonb=lonb,latb=latb)


def cal_CWVatDongsha(data_wrapper):
    ##### D10229001 #####
    # parameters
    rho_w = 1000 # density of water: 1000 kg/m^3
    g = 10 # acceleration of gravity: 10 m/s^2
    # dimension
    level = [1000, 975, 950, 925, 900, 850, 800, 750, 700, 650, 600, 550, 500, 450, 400, 350, 300, 250, 200, 150, 100]
    lons = 29
    lats = 41
    # load
    q = np.zeros([lats,lons,len(level)])
    for i in range(len(level)):
        _,_,_, dum = data_wrapper('q',levb=[level[i], level[i]])
        q[:,:,i] = dum[0][::-1,:]
    # calculation
    cwv = np.zeros([lats,lons])
    for k in range(len(level)-1):
        cwv += (q[:,:,k]+q[:,:,k+1])*(level[k]-level[k+1])*100/2 # *100: convert hPa to Pa
    cwv = cwv/rho_w/g*1000 # *1000: convert m to mm
    # area
    CWVatDongSha = np.mean(cwv[20:25,0:5])
    return CWVatDongSha


def cal_CWVatNETW(data_wrapper):
    ##### B07209016 #####
    # parameters
    rho_w = 1000 # density of water: 1000 kg/m^3
    g = 10 # acceleration of gravity: 10 m/s^2
    # dimension
    level = [1000, 975, 950, 925, 900, 850, 800, 750, 700, 650, 600, 550, 500, 450, 400, 350, 300, 250, 200, 150, 100]
    lons = 29
    lats = 41
    # load
    q = np.zeros([lats,lons,len(level)])
    for i in range(len(level)):
        _,_,_, dum = data_wrapper('q',levb=[level[i], level[i]])
        q[:,:,i] = dum[0][::-1,:]
    # calculation
    cwv = np.zeros([lats,lons])
    for k in range(len(level)-1):
        cwv += (q[:,:,k]+q[:,:,k+1])*(level[k]-level[k+1])*100/2 # *100: convert hPa to Pa
    cwv = cwv/rho_w/g*1000 # *1000: convert m to mm
    # area
    CWVatNETW = np.mean(cwv[4:7,24:27])
    return CWVatNETW

def cal_WSatBanqiao(data_wrapper):
    ##### D10229003 #####
    # dimension
    level = [850,700]
    lons = 29
    lats = 41
    # load
    u = np.zeros([lats,lons,len(level)])
    v = np.zeros([lats,lons,len(level)])
    for i in range(len(level)):
        _,_,_, dum = data_wrapper('u',levb=[level[i], level[i]])
        u[:,:,i] = dum[0][::-1,:]
        _,_,_, dum = data_wrapper('v',levb=[level[i], level[i]])
        v[:,:,i] = dum[0][::-1,:]
    # calculation
    ws = np.sqrt((u[:,:,1]-u[:,:,0])**2+(v[:,:,1]-v[:,:,0])**2)
    # area
    WSatBanqiao = ws[4,22]
    return WSatBanqiao


def cal_WSatNETW(data_wrapper):
    ##### R09229019 #####
    # dimension
    level = [850,200]
    lons = 29
    lats = 41
    # load
    u = np.zeros([lats,lons,len(level)])
    v = np.zeros([lats,lons,len(level)])
    for i in range(len(level)):
        _,_,_, dum = data_wrapper('u',levb=[level[i], level[i]])
        u[:,:,i] = dum[0][::-1,:]
        _,_,_, dum = data_wrapper('v',levb=[level[i], level[i]])
        v[:,:,i] = dum[0][::-1,:]
    # area 
    uatNETW = np.mean(u[4:9,24:29,:],axis=(0,1))
    vatNETW = np.mean(v[4:9,24:29,:],axis=(0,1))
    # calculation
    WSatNETW = np.sqrt((uatNETW[1]-uatNETW[0])**2+(vatNETW[1]-vatNETW[0])**2)
    return WSatNETW


def cal_CrossStraitUatNWTW(data_wrapper):
    ##### R10229007 #####
    # load
    _,_,_, dum = data_wrapper('v',levb=[700., 700.])
    v = dum[0][::-1,:]
    _,_,_, dum = data_wrapper('u',levb=[700., 700.])
    u = dum[0][::-1,:]
    # area
    uatNWTW = np.mean(u[4:9,12:17])
    vatNWTW = np.mean(v[4:9,12:17])
    # calculation 
    CrossStraitUatNWTW = uatNWTW*(3**0.5/2)+vatNWTW*(1/2)
    return CrossStraitUatNWTW


def cal_UatNETW(data_wrapper):
    ##### R10229007 #####
    # load
    _,_,_, dum = data_wrapper('v',levb=[700., 700.])
    v = dum[0][::-1,:]
    _,_,_, dum = data_wrapper('u',levb=[700., 700.])
    u = dum[0][::-1,:]
    # area
    uatNETW = np.mean(u[4:9,24:29])
    vatNETW = np.mean(v[4:9,24:29])
    # calculation
    UatNETW = np.sqrt(uatNETW**2+vatNETW**2)
    return UatNETW


def cal_swUatDongSha(data_wrapper):
    ##### R10229001 #####
    # dimension
    level = [1000,975,950,925,900,850]
    lons = 29
    lats = 41
    # load
    u = np.zeros([lats,lons,len(level)])
    v = np.zeros([lats,lons,len(level)])
    for i in range(len(level)):
        _,_,_, dum = data_wrapper('u',levb=[level[i], level[i]])
        u[:,:,i] = dum[0][::-1,:]
        _,_,_, dum = data_wrapper('v',levb=[level[i], level[i]])
        v[:,:,i] = dum[0][::-1,:]
    # calculation
    U = np.sqrt(u**2+v**2)
    # area
    uatDongSha = np.mean(u[20:25,0:5,:],axis=(0,1))
    vatDongSha = np.mean(v[20:25,0:5,:],axis=(0,1))
    UatDongSha = np.mean(U[20:25,0:5,:],axis=(0,1))
    # selection
    sw = np.where(np.logical_and(uatDongSha>0,vatDongSha>0))
    # calculation
    if UatDongSha[sw].size == 0:
        return -9999
    swUatDongSha = np.mean(UatDongSha[sw])
    # nan values
    nan = np.where(np.isnan(swUatDongSha)==1)
    if np.size(nan)==1:
       swUatDongSha = -9999
    return swUatDongSha


def cal_sUatNETW(data_wrapper):
    ##### R10229008 #####
    # dimension
    level = [1000,950,900,850,800]
    lons = 29
    lats = 41
    # load
    u = np.zeros([lats,lons,len(level)])
    v = np.zeros([lats,lons,len(level)])
    for i in range(len(level)):
        _,_,_, dum = data_wrapper('u',levb=[level[i], level[i]])
        u[:,:,i] = dum[0][::-1,:]
        _,_,_, dum = data_wrapper('v',levb=[level[i], level[i]])
        v[:,:,i] = dum[0][::-1,:]
    # calculation
    U = np.sqrt(u**2+v**2)
    # area
    vatNETW = np.mean(v[2:5,24:27,:],axis=(0,1))
    UatNETW = np.mean(U[2:5,24:27,:],axis=(0,1))
    # selection
    s = np.where(vatNETW>0)

    # calculation
    if UatNETW[s].size == 0:
        return -9999
    sUatNETW = np.mean(UatNETW[s])
    # nan values
    nan = np.where(np.isnan(sUatNETW)==1)
    if np.size(nan)==1:
       sUatNETW = -9999
    return sUatNETW


def cal_swDEPTHatNETW(data_wrapper):
    ##### R09229001 #####
    # parameters
    g = 10 # acceleration of gravity: 10 m/s^2
    # dimension
    level = [1000, 975, 950, 925, 900, 850, 800, 750, 700, 650, 600, 550, 500, 450, 400, 350, 300, 250, 200, 150, 100]
    lons = 29
    lats = 41
    # load
    u = np.zeros([lats,lons,len(level)])
    v = np.zeros([lats,lons,len(level)])
    z = np.zeros([lats,lons,len(level)])
    for i in range(len(level)):
        _,_,_, dum = data_wrapper('u',levb=[level[i], level[i]])
        u[:,:,i] = dum[0][::-1,:]
        _,_,_, dum = data_wrapper('v',levb=[level[i], level[i]])
        v[:,:,i] = dum[0][::-1,:]
        _,_,_, dum = data_wrapper('z',levb=[level[i], level[i]])
        z[:,:,i] = dum[0][::-1,:]/g
    # area
    uatNETW = np.mean(u[4:9,24:29,:],axis=(0,1))
    vatNETW = np.mean(v[4:9,24:29,:],axis=(0,1))
    zatNETW = np.mean(z[4:9,24:29,:],axis=(0,1))
    # calculation 
    data = pd.DataFrame({'pressure':level, 'height':zatNETW, 'U-wind':uatNETW, 'V-wind':vatNETW})
    data['WS_wind'] = False
    data.loc[(data['U-wind']>0.)&(data['V-wind']>0.),"WS_wind"] = True
    WS_botton = np.nan; WS_top = np.nan
    try:
      for point in range(3): # p: 1000, 975, 950 hPa
        if data['WS_wind'][point] == True: 
          WS_botton=data['height'][point]
          break
      for point2 in range(point,len(data['WS_wind'])):
        if data['WS_wind'][point2] == True: 
          WS_top=data['height'][point2]
        else: break
    except:
      WS_botton = np.nan; WS_top = np.nan
    Zws = WS_top - WS_botton
    if np.isnan(Zws) : X = 0.
    elif Zws<1000.: X = 0.
    elif Zws<4000.: X = (Zws-1000.)/3000.
    else: X=1.
    swDEPTHatNETW = X
    return swDEPTHatNETW


def cal_MSEatNETW(data_wrapper):
    ##### B10229010 #####
    # parameters
    Cp = 1004 # heat capacity at constant pressure: 1004 J/K/kg
    g = 10 # acceleration of gravity: 10 m/s^2
    Lv = 2.5*10**6 # latent heat: 2500000 J/kg
    # dimension
    level = [1000, 950, 900, 850, 800, 750, 700]
    lons = 29
    lats = 41
    # load
    T = np.zeros([lats,lons,len(level)])
    z = np.zeros([lats,lons,len(level)])
    q = np.zeros([lats,lons,len(level)])
    for i in range(len(level)):
        _,_,_, dum = data_wrapper('t',levb=[level[i], level[i]])
        T[:,:,i] = dum[0][::-1,:]
        _,_,_, dum = data_wrapper('z',levb=[level[i], level[i]])
        z[:,:,i] = dum[0][::-1,:]
        _,_,_, dum = data_wrapper('q',levb=[level[i], level[i]])
        q[:,:,i] = dum[0][::-1,:]
    # calculation
    mse = Cp*T+z+Lv*q
    # area
    MSEatNETW = np.mean(mse[4:7,24:27,:])
    return MSEatNETW


def cal_swLAYERatSWTW(data_wrapper):
    ##### D08229002 #####
    # dimension
    level = [1000, 975, 950, 925, 900, 850, 800, 750, 700]
    lons = 29
    lats = 41
    # load
    u = np.zeros([lats,lons,len(level)])
    v = np.zeros([lats,lons,len(level)])
    for i in range(len(level)):
        _,_,_, dum = data_wrapper('u',levb=[level[i], level[i]])
        u[:,:,i] = dum[0][::-1,:]
        _,_,_, dum = data_wrapper('v',levb=[level[i], level[i]])
        v[:,:,i] = dum[0][::-1,:]
    # area
    uatSWTW = np.mean(u[16:29,4:17,:],axis=(0,1))
    vatSWTW = np.mean(v[16:29,4:17,:],axis=(0,1))
    # calculation
    FD = np.sign(uatSWTW)*np.arctan(vatSWTW/uatSWTW)*180/np.pi
    U = np.sqrt(uatSWTW**2+vatSWTW**2)     
    FDcondition = np.where(np.logical_and(FD>=30,FD<=80))
    Ucondition = np.where(U>=0.5)
    condition = np.intersect1d(FDcondition,Ucondition)
    swLAYERatSWTW = len(condition)/len(level)
    return swLAYERatSWTW


def cal_IVTatDongSha(data_wrapper):
    ##### R10229019 & B08209014 #####
    # parameters
    g = 10 # acceleration of gravity: 10 m/s^2
    # dimension
    level = [1000, 975, 950, 925, 900, 850, 800, 750, 700, 650, 600, 550, 500]
    lons = 29
    lats = 41
    # load
    u = np.zeros([lats,lons,len(level)])
    v = np.zeros([lats,lons,len(level)])
    q = np.zeros([lats,lons,len(level)])
    for i in range(len(level)):
        _,_,_, dum = data_wrapper('q',levb=[level[i], level[i]])
        q[:,:,i] = dum[0][::-1,:]
        _,_,_, dum = data_wrapper('v',levb=[level[i], level[i]])
        v[:,:,i] = dum[0][::-1,:]
        _,_,_, dum = data_wrapper('u',levb=[level[i], level[i]])
        u[:,:,i] = dum[0][::-1,:]
    # calculation
    WS_wind = np.zeros([lats,lons,len(level)])
    WS_wind[(u>0.)&(v>0.)] = 1
    ivt = np.zeros([lats,lons])
    for i in range(lats):
        for j in range(lons):
            WS_bottom = np.nan
            WS_top = np.nan
            for point in range(3): # p: 1000, 975, 950 hPa
                if WS_wind[i,j,point]==1:
                   WS_bottom = point
                   break
            for point2 in range(point,len(level)):
                if WS_wind[i,j,point2]==1:
                   WS_top = point2
                else: 
                   break
            if np.isnan(WS_top)==0 and np.isnan(WS_top)==0:
               ivt_x,ivt_y = 0,0
               for k in range(WS_bottom,WS_top):
                   ivt_x += (q[i,j,k]*u[i,j,k]+q[i,j,k+1]*u[i,j,k+1])*(level[k]-level[k+1])*100/2 # *100: convert hPa to Pa
                   ivt_y += (q[i,j,k]*v[i,j,k]+q[i,j,k+1]*v[i,j,k+1])*(level[k]-level[k+1])*100/2 # *100: convert hPa to Pa
               ivt[i,j] = np.sqrt((ivt_x/g)**2+(ivt_y/g)**2)
            else:
               ivt[i,j] = np.nan   
    # area
    if np.isnan(ivt[20:25,0:5]).all():
        return -9999

    IVTatDongSha = np.nanmean(ivt[20:25,0:5])
    # nan values
    nan = np.where(np.isnan(IVTatDongSha)==1)
    if np.size(nan)==1:
       IVTatDongSha = -9999
    return IVTatDongSha


def cal_LeeVortex(data_wrapper):
    ##### R10229007 #####
    # load
    _,_,_, dum = data_wrapper('u',levb=[950., 950.])
    u = dum[0][::-1,:]
    _,_,_, dum = data_wrapper('v',levb=[950., 950.])
    v = dum[0][::-1,:]
    zeta = np.gradient(v,axis=1) / (0.25*111000.) \
         - np.gradient(u,axis=0) / (0.25*111000.)

    # area
    zetaatNETW = np.mean(zeta[4:9,24:29])
    zetaatNWTW = np.mean(zeta[4:9,12:17])
    # calculation
    LeeVortex = np.abs(zetaatNETW)-np.abs(zetaatNWTW)
    return LeeVortex



def cal_CRHatNETW(data_wrapper):
    ##### R08229007 #####
    # parameters
    A = 2.53*10**11 # [Pa]
    B = 5420 # [K]
    epsilon = 0.622
    # dimension
    level = [850, 800, 750, 700, 650, 600, 550, 500]
    lons = 29
    lats = 41
    # load
    T = np.zeros([lats,lons,len(level)])
    q = np.zeros([lats,lons,len(level)])
    for i in range(len(level)):
        _,_,_, dum = data_wrapper('t',levb=[level[i], level[i]])
        T[:,:,i] = dum[0][::-1,:]
        _,_,_, dum = data_wrapper('q',levb=[level[i], level[i]])
        q[:,:,i] = dum[0][::-1,:]
    P = np.tile(level,(lats,lons,1))
    # calculation
    es = A*np.exp(-B/T)
    qs = epsilon*es/(P*100-es) # *100: convert hPa to Pa
    intq = np.zeros([lats,lons])
    intqs = np.zeros([lats,lons])
    for k in range(len(level)-1):
        intq += (q[:,:,k]+q[:,:,k+1])*(level[k]-level[k+1])*100/2 # *100: convert hPa to Pa
        intqs += (qs[:,:,k]+qs[:,:,k+1])*(level[k]-level[k+1])*100/2 # *100: convert hPa to Pa
    crh = intq/intqs
    # area
    CRHatNETW = np.mean(crh[4:7,24:27])
    return CRHatNETW


def cal_deltaCWVatTW(data_wrapper):
    ##### B07209010 #####
    # parameters
    rho_w = 1000 # density of water: 1000 kg/m^3
    g = 10 # acceleration of gravity: 10 m/s^2
    # dimension
    level = [1000, 975, 950, 925, 900, 850, 800, 750, 700, 650, 600, 550, 500, 450, 400, 350, 300, 250, 200, 150, 100]
    lons = 29
    lats = 41
    # load
    q = np.zeros([lats,lons,len(level)])
    for i in range(len(level)):
        _,_,_, dum = data_wrapper('q',levb=[level[i], level[i]])
        q[:,:,i] = dum[0][::-1,:]
    # calculation
    cwv_ws = np.load('weak_synoptic_without_rain_CWV.npy')
    cwv_bar = np.mean(cwv_ws[:,0:9,12:])
    cwv = np.zeros([lats,lons])
    for k in range(len(level)-1):
        cwv += (q[:,:,k]+q[:,:,k+1])*(level[k]-level[k+1])*100/2 # *100: convert hPa to Pa
    cwv = cwv/rho_w/g*1000 # *1000: convert m to mm
    cwv_delta = cwv-cwv_bar
    # area
    deltaCWVatTW = np.mean(cwv_delta[0:9,12:])
    return deltaCWVatTW    

def cal_deltaLTSatSWTW(data_wrapper):
    ##### R10229029 #####
    # parameters
    Cp = 1004 # heat capacity at constant pressure: 1004 J/K/kg
    Rd = 287 # gas constant of dry air: 287 J/K/kg
    # dimension
    lons = 29
    lats = 41
    # load
    _,_,_, t700 = data_wrapper('t',levb=[700., 700.])
    theta700 = t700[0][::-1,:]*(1000/700)**(Rd/Cp)
    _,_,_, t1000 = data_wrapper('t',levb=[1000., 1000.])
    theta1000 = t1000[0][::-1,:]*(1000/1000)**(Rd/Cp)
    # calculation
    lts_ws = np.load('weak_synoptic_without_rain_LTS.npy')
    lts_bar = np.mean(lts_ws[:,20:25,0:5])
    lts = theta700-theta1000
    lts_delta = lts-lts_bar
    # area
    deltaLTSatSWTW = np.mean(lts_delta[20:25,0:5])
    return deltaLTSatSWTW

"""
def cal_zetaatETW(data_wrapper):
    ##### R09229012 #####
    # dimension
    level = [1000, 950, 900, 850]
    lons = 29
    lats = 41
    # load
    zeta00 = np.zeros([lats,lons,len(level)])
    zeta12 = np.zeros([lats,lons,len(level)])
    for i in range(len(level)):
        zeta00[:,:,i] = data_wrapper(var="vor",lev=level[i],time=0)
        zeta12[:,:,i] = data_wrapper(var="vor",lev=level[i],time=1)
    # calculation
    zeta = (np.mean(zeta00[4:15,21:,:])+np.mean(zeta12[4:15,21:,:]))/2
    if zeta<0:
       X = -1
    elif zeta>=0:
       X = 1 
    zetaatETW = X  
    return zetaatETW 


def cal_seUatETW(data_wrapper):
    ##### R09229012 #####
    # dimension
    level = [1000, 950, 900, 850]
    lons = 29
    lats = 41
    # load
    u00 = np.zeros([lats,lons,len(level)])
    u12 = np.zeros([lats,lons,len(level)])
    v00 = np.zeros([lats,lons,len(level)])
    v12 = np.zeros([lats,lons,len(level)])
    for i in range(len(level)):
        u00[:,:,i] = data_wrapper(var="u",lev=level[i],time=0)
        u12[:,:,i] = data_wrapper(var="u",lev=level[i],time=1)
        v00[:,:,i] = data_wrapper(var="v",lev=level[i],time=0)
        v12[:,:,i] = data_wrapper(var="v",lev=level[i],time=1)
    # calculation
    u = (np.mean(u00[4:7,23:26,:])+np.mean(u12[4:7,23:26,:]))/2
    v = (np.mean(v00[4:7,23:26,:])+np.mean(v12[4:7,23:26,:]))/2
    U = np.sqrt(u**2+v**2)
    #WD = mpcalc.wind_direction(u*units.knot,v*units.knot)
    #WD = \((180+180/\pi *\text{atan2}(U,V))\quad (\bmod 360)\)
    WD = (180+180./3.1415 * np.arctan2(u,v)) % 360
    if U<5 and WD.m>135 and WD.m<180:
       X = 1
    else:
       X = -1
    seUatETW = X
    return seUatETW

"""
