import netCDF4 as nc
from datetime import datetime
import numpy as np

### Time ###
forecast_time = 48
tt = int(forecast_time/3)
now = datetime.now()
current_time = now.strftime("%Y")
yyyy = now.strftime("%Y")
mm = now.strftime("%m")
dd = now.strftime("%d")

### Load Dimension ###
url = 'http://nomads.ncep.noaa.gov:80/dods/gfs_0p25/gfs'+yyyy+mm+dd+'/gfs_0p25_00z'
Dataset = nc.Dataset(url)
lon = Dataset.variables['lon'][:] # longitude
lat = Dataset.variables['lat'][:] # latitude
lev = Dataset.variables['lev'][:] # level

### Range ###
lon0,lon1 = 100,140
lat0,lat1 = 5,45
x0,x1 = np.argmin(np.abs(lon0-lon)),np.argmin(np.abs(lon1-lon))
y0,y1 = np.argmin(np.abs(lat0-lat)),np.argmin(np.abs(lat1-lat))

### Load Variables for 48 hours later ###
q = Dataset.variables['spfhprs'][tt,:21,y0:y1+1,x0:x1+1] # specific humidity
T = Dataset.variables['tmpprs'][tt,:21,y0:y1+1,x0:x1+1] # temperature
u = Dataset.variables['ugrdprs'][tt,:21,y0:y1+1,x0:x1+1] # u-wind
v = Dataset.variables['vgrdprs'][tt,:21,y0:y1+1,x0:x1+1] # v-wind
z = Dataset.variables['hgtprs'][tt,:21,y0:y1+1,x0:x1+1] # geopotential height
zeta = Dataset.variables['absvprs'][tt,:21,y0:y1+1,x0:x1+1] # absolute vorticity
cwv = Dataset.variables['pwatclm'][tt,y0:y1+1,x0:x1+1]

print(q.shape)
