#!/bin/bash

vvmPath="/data/mog/VVM/DATA/"
vvmPath="/data2/VVM/taiwanvvm_tpe/"

outVvmPath="/data/C.shaoyu/ats/vvm/"

typeList="C.Surface C.LandSurface L.Dynamic L.Radiation L.Thermodynamic"
expList="RRCE_3km_f00_10 RRCE_3km_f00_20 RRCE_3km_f00_30"
expList="$(ls ${vvmPath})"

for exp in ${expList};do
  exp=$(basename $exp)
  echo "----- ${exp} -----"

  dir="${vvmPath}/${exp}/"
  if [ ! -d ${dir} ];then
    echo "can't found the case '${exp}' ... skip"
    continue
  fi
  out="${outVvmPath}/${exp}/"
  rm -rf ${out}

  mkdir -p ${out}/archive
  ln -sf ${dir}/TOPO.nc      ${out}/
  ln -sf ${dir}/fort.98      ${out}/
  ln -sf ${dir}/vvm.setup    ${out}/
  ln -sf ${dir}/INPUT    ${out}/
  ln -sf ${dir}/DOMAIN    ${out}/

  hexp=$(ls ${dir}/archive/*.L.Dynamic-000000.nc|rev|cut -d/ -f1|rev|cut -d. -f1)
  echo ${hexp}
  echo ${exp}

  nfile=$(ls ${dir}/archive/${hexp}.C.Surface*.nc|wc -l)
  nfile=$(echo ${nfile}-1|bc)
  for inc in $(seq 0 ${nfile});do
    inc=$(printf "%06d" ${inc})
    for vtype in ${typeList};do
      ln -sf ${dir}/archive/${hexp}.${vtype}-${inc}.nc \
             ${out}/archive/${exp}.${vtype}-${inc}.nc
    done
  done # inc

done #exp
