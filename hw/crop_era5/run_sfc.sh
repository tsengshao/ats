#!/bin/bash



#cdo -L -P 3 -z zip4 -f nc4 copy -select,level=1000,925,850,700,500,200 -sellonlatbox,90,160,5,55 /data/dadm1/reanalysis/ERA5/PRS/day/q/2006/ERA5_PRS_q_200601_r1440x721_day.nc test.nc

# /data/dadm1/reanalysis/ERA5/SFC/day/sp/2006/ERA5_SFC_sp_200606_r1440x721_day.nc
# /data/dadm1/reanalysis/ERA5/PRS/day/q/2006/ERA5_PRS_q_200601_r1440x721_day.nc

lev="1000,925,850,700,500,200"
reg="90,160,5,55"

reg="100,140,10,40"
yr0=2001
yr1=2020
varlist="msl sp"
path="/data/dadm1/reanalysis/ERA5/SFC/day/"
target_dir="./east_asia"
for var in $varlist;do
  for yr in $(seq ${yr0} 1 ${yr1});do
    outdir="${target_dir}/SFC/${var}/${yr}"
    mkdir -p ${outdir}
    echo ${yr} ${var}

    for filename in $(ls "${path}/${var}/${yr}");do
      fname="${path}/${var}/${yr}/${filename}"
      yyyymm=$(echo ${filename}|cut -d_ -f4)
      outfname="${outdir}/ERA5_EAsia_SFC_${var}_${yyyymm}.nc"

      cdo -L -P 1 -z zip4 -f nc4 copy -sellonlatbox,${reg} ${fname} ${outfname}
      #echo ${fname} ${yyyymm}
    done

    echo ' '
  done

done
