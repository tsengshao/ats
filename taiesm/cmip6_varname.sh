#!/bin/bash


#dir="/lfs/archive/CMIP6/TaiESM1/historical/atmos/3hr/r1i1p1f1"
#files=$(ls ${dir}/*_3hr_TaiESM1_historical_r1i1p1f1_gn_185001010000-185912312230.nc)

dir='/data/dadm1/model_output/CMIP6/TaiESM1/historical/atmos/day/r1i1p1f1'
files=$(ls ${dir}/*_day_TaiESM1_historical_r1i1p1f1_gn_18500101-18591231.nc)

for f in $files;do
    #echo ${f}
    c=$(ncdump -h ${f} |grep long_name | tail -n 1)
    echo ${c}
done
