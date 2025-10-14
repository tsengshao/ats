import netCDF4
import numpy as np
import os
import cdsapi
import pathlib
import datetime
import pickle

class DataWrapper:
    VAR_LIST = {
        "q"   : { "era5" :"q" , "gfs" : "q" },
        "T"   : { "era5" :"t" , "gfs" : "T" },
        "u"   : { "era5" :"u" , "gfs" : "u" },
        "v"   : { "era5" :"v" , "gfs" : "v" },
        "z"   : { "era5" :"z" , "gfs" : "z" },
        "vor" : { "era5" :"vo", "gfs" : "vor" },
    }
    LEV_LIST = [
        1000, 975, 950, 925, 900, 850, 800, 750, 700, 650, 600, 550, 500, 450, 400, 350, 300, 250, 200, 150, 100 
    ]


    ER5_NC_NAME = "era5"

    def __init__(self,path,data_type="era5"):
        self.path = pathlib.Path(path)
        self.data_type = data_type
        

    def get_data(self,forecast_day=2,date:str="2015-01-01",var="u",lev=0,time=0):
        year  = date[0:4]
        month = date[5:7]
        day   = date[8:10]
        date_obj = datetime.datetime.strptime(date,"%Y-%m-%d")
        julian_day = date_obj.timetuple().tm_yday

        assert time < 2 # 00Z 12Z

        if self.data_type == "era5":
            nc_file = pathlib.Path(self.path.as_posix() + "/" + self.ER5_NC_NAME + "-" + year + ".nc")
            if not nc_file.is_file():
                self.load_era5_net(year)
            assert nc_file.is_file()

            nf = netCDF4.Dataset(nc_file.as_posix())
            
            if not var in ["time","level","latitude","longitude"]:
                if lev >= 100:
                    lev_idx = self.LEV_LIST.index(lev)
                    return nf.variables[self.VAR_LIST[var]["era5"]][(julian_day-1)*forecast_day+time,lev_idx,:,:]
                else:
                    return nf.variables[self.VAR_LIST[var]["era5"]][(julian_day-1)*forecast_day+time,lev,:,:]
            else:
                return nf.variables[var][:]
        else:
            # GFS

            ### Time ###
            forecast_time = forecast_day * 24 
            tt = int(forecast_time/3)
            yyyy = date_obj.strftime("%Y")
            mm = date_obj.strftime("%m")
            dd = date_obj.strftime("%d")

            ### Load Dimension ###
            if not os.path.isfile( self.path.as_posix() + "/"  + yyyy + mm + dd + "_"  + str(forecast_day * 24) + ".pickle" ) :
                url = 'http://nomads.ncep.noaa.gov:80/dods/gfs_0p25/gfs'+yyyy+mm+dd+'/gfs_0p25_00z'
                Dataset = netCDF4.Dataset(url)
                _lon = Dataset.variables['lon'][:] # longitude
                _lat = Dataset.variables['lat'][:] # latitude
                _lev = Dataset.variables['lev'][:] # level

                ### Range ###
                lon0,lon1 = 116,123
                lat0,lat1 = 16,26
                x0,x1 = np.argmin(np.abs(lon0-_lon)),np.argmin(np.abs(lon1-_lon))
                y0,y1 = np.argmin(np.abs(lat0-_lat)),np.argmin(np.abs(lat1-_lat))
                #print(lon.shape,x0,x1,y0,y1)
                _lon = _lon[x0:x1+1]
                _lat = _lat[y0:y1+1]

                ### Load Variables for 48 hours later ###
                q1 = Dataset.variables['spfhprs'][tt,:21,y0:y1+1,x0:x1+1] # specific humidity
                T1 = Dataset.variables['tmpprs'][tt,:21,y0:y1+1,x0:x1+1] # temperature
                u1 = Dataset.variables['ugrdprs'][tt,:21,y0:y1+1,x0:x1+1] # u-wind
                v1 = Dataset.variables['vgrdprs'][tt,:21,y0:y1+1,x0:x1+1] # v-wind
                z1 = Dataset.variables['hgtprs'][tt,:21,y0:y1+1,x0:x1+1] # geopotential height
                zeta1 = Dataset.variables['absvprs'][tt,:21,y0:y1+1,x0:x1+1] # absolute vorticity
                q2 = Dataset.variables['spfhprs'][tt+4,:21,y0:y1+1,x0:x1+1] # specific humidity
                T2 = Dataset.variables['tmpprs'][tt+4,:21,y0:y1+1,x0:x1+1] # temperature
                u2 = Dataset.variables['ugrdprs'][tt+4,:21,y0:y1+1,x0:x1+1] # u-wind
                v2 = Dataset.variables['vgrdprs'][tt+4,:21,y0:y1+1,x0:x1+1] # v-wind
                z2 = Dataset.variables['hgtprs'][tt+4,:21,y0:y1+1,x0:x1+1] # geopotential height
                zeta2 = Dataset.variables['absvprs'][tt+4,:21,y0:y1+1,x0:x1+1] # absolute vorticity

                #cwv = Dataset.variables['pwatclm'][tt,y0:y1+1,x0:x1+1]

                out_obj = dict()
                out_obj ={
                    "q" : [q1[:,::-1,:],q2[:,::-1,:]],
                    "T" : [T1[:,::-1,:],T2[:,::-1,:]],
                    "u" : [u1[:,::-1,:],u2[:,::-1,:]],
                    "v" : [v1[:,::-1,:],v2[:,::-1,:]],
                    "z" : [z1[:,::-1,:],v2[:,::-1,:]],
                    "vor" : [zeta1[:,::-1,:],zeta2[:,::-1,:]],
                    #"time" : ,
                    "level": _lev,
                    "latitude": _lat[::-1],
                    "longitude": _lon,
                }

                with open(self.path.as_posix() + "/"  + yyyy + mm + dd + "_"  + str(forecast_day * 24) + ".pickle" ,"wb") as fp :
                    pickle.dump(out_obj,fp)

            data = None
            with open(self.path.as_posix() + "/"  + yyyy + mm + dd + "_"  + str(forecast_day * 24) + ".pickle" ,"rb") as fp :
                data = pickle.load(fp)
            

            assert data is not None

            if not var in ["time","level","latitude","longitude"]:
                lev_idx = lev
                if lev >= 100 :
                    lev_idx = self.LEV_LIST.index(lev)
                return data[var][time][lev_idx,:,:]
            else:
                return data[var]


    
    def load_era5_net(self,year:str):
        nc_file = pathlib.Path(self.path.as_posix() + "/" + self.ER5_NC_NAME + "-" + year + ".nc")
        nc_file.parents[0].mkdir(parents=True, exist_ok=True)

        c = cdsapi.Client()

        c.retrieve(
            'reanalysis-era5-pressure-levels',{
                'product_type':'reanalysis',
                'variable':[
                    'specific_humidity',
                    'temperature',
                    'u_component_of_wind',
                    'v_component_of_wind',
                    'geopotential',
                    'vorticity'
                ],
                # you can block this command if you need the whole domain
                'area': [26,116,16,123],#N,W,S,E
                'pressure_level':[
                    1000, 975, 950, 925, 900, 850, 800, 750,
                    700 , 650, 600, 550, 500, 450, 400, 350,
                    300 , 250, 200, 150, 100
                ],
                'year': [ year ],
                'month': [ str(m) for m in range(1,13) ],
                'day': [ str(d) for d in range(1,32) ],
                'time':[ '00:00', '12:00'],
                'format':'netcdf'
            },
            nc_file.as_posix()
        )



if __name__ == "__main__":
    wrapper = DataWrapper('/home/flyingmars/iop_routine/pickle',data_type="gfs")
    print(wrapper.get_data(date="2022-06-08",time=1,lev=2,var="T"))

