#!/bin/bash

#rundir=`pwd`
rundir=$(cd "$(dirname "$0")" && pwd)   # folder that holds this script
exp=$(echo ${rundir}|rev|cut -d/ -f1|rev)
ncdir="${rundir}/archive"
outdir="${rundir}/gs_ctl_files"
echo ${exp}
echo ${outdir}
mkdir -p ${outdir}

declare -A vtab
vtab[time]='t'
vtab[lon]='x'
vtab[lat]='y'
vtab[lev]='z'

# -------------------------------------------
# ----- number of data type and ncheader
dtype_list=""
for dum in $(ls ${ncdir}/*000000.nc);do
  dum=$(echo ${dum}|rev|cut -d"/" -f1|rev|cut -d"-" -f1)
  dum0=$(echo ${dum}|rev|cut -d"." -f2|rev)  #L
  dum1=$(echo ${dum}|rev|cut -d"." -f1|rev)  #Thermodynamic
  ncheader=$(echo ${dum}|rev|cut -d"." -f3|rev)  #RRCE_3km_f00
  dtype_list="${dtype_list} ${dum0}.${dum1}"
done

# -------------------------------------------
# ----- get dimension
nt=$(ls ${ncdir}/*.${dum0}.${dum1}-*.nc|wc -l)
# n=0
# nfmt=$(printf "%06d" ${n})
# echo "${ncdir}/${ncheader}.${dum0}.${dum1}-${nfmt}.nc"
# while [ -f ${ncdir}/${ncheader}.${dum0}.${dum1}-${nfmt}.nc ]; do
#   n=$(echo "${n}+1"|bc)
#   nfmt=$(printf "%06d" ${n})
# done
# nt=${n}

nx=$(grep "zonal_dimension" ${rundir}/DOMAIN|cut -d"'" -f2|cut -d"/" -f3)
ny=$(grep "merid_dimension" ${rundir}/DOMAIN|cut -d"'" -f2|cut -d"/" -f3)
nz=$(grep "vert_dimension" ${rundir}/DOMAIN|cut -d"'" -f2|cut -d"/" -f3)

# -------------------------------------------
# ----- get lon/lat
##  method 1 ---- from INTPUT
### lat0=$(grep "RLAT=" ${rundir}/INPUT|cut -d',' -f1|cut -d'=' -f2)
### lon0=$(grep "RLON=" ${rundir}/INPUT|cut -d',' -f2|cut -d'=' -f2|cut -d' ' -f1)
### #lat0=0
### #lon0=0
### dx=$(grep "DX=" ${rundir}/INPUT|cut -d',' -f1|cut -d'=' -f2)
### dy=$(grep "DY" ${rundir}/INPUT|cut -d',' -f2|cut -d'=' -f2)
### dlon=$(echo "scale=6;${dx}/111000"|bc)
### dlat=$(echo "scale=6;${dy}/111000"|bc)
### 
### lon0=$(echo "scale=3;${lon0}-(${dlon}*${nx}/2)"|bc )
### lat0=$(echo "scale=3;${lat0}-(${dlat}*${ny}/2)"|bc )

### # method 2 ---- from TOPO.nc using ncdump
lon0=$(ncdump -v,lon ${rundir}/TOPO.nc |grep ' lon ='|cut -c7-|cut -d',' -f1)
lon1=$(ncdump -v,lon ${rundir}/TOPO.nc |grep ' lon ='|cut -c7-|cut -d',' -f2)
lat0=$(ncdump -v,lat ${rundir}/TOPO.nc |grep ' lat ='|cut -c7-|cut -d',' -f1)
lat1=$(ncdump -v,lat ${rundir}/TOPO.nc |grep ' lat ='|cut -c7-|cut -d',' -f2)
dlon=$(echo "scale=6;${lon1}-(${lon0})"|bc)
dlat=$(echo "scale=6;${lon1}-(${lon0})"|bc)

# -------------------------------------------
# ----- get dt 
fname=${ncdir}/${ncheader}.L.Dynamic-000001.nc
if [ -f ${fname} ];then
  deltatime=$(ncdump -v,time ${fname} |grep ' time ='|cut -d' ' -f4)
else
  outfreq=$(grep "NXSAVG=" ${rundir}/INPUT |cut -d"," -f2|cut -d"=" -f2)
  dt=$(grep "DT=" ${rundir}/INPUT |cut -d"," -f5|cut -d"=" -f2)
  deltatime=$(echo "scale=0;${outfreq}*${dt}/60"|bc)
fi
deltatime=$(echo "scale=0;${deltatime}/1"|bc)  #keep integer
deltatime=$(( ${deltatime} > 1 ? ${deltatime} : 1 ))  #minmum value is 1
echo "${deltatime} min (${nt})"

# -------------------------------------------
# ----- get z level
# method 1 from fort.98
dum=$(grep -n "ZT(K)" ${rundir}/fort.98|cut -d":" -f1)
dum=$(echo ${dum}+${nz}+1|bc)
table=$(cat ${rundir}/fort.98 |head -n ${dum}|tail -n ${nz})
zlist=""
for i in $(seq ${nz});do
  idx=$(echo "3+(${i}-1)*5"|bc)
  dum=$(echo ${table}|cut -d" " -f${idx})
  dum=$(echo "scale=2;(${dum}/1.)"|bc)
  zlist="${zlist} ${dum}"
done

#########################################
# create ctl for the data in archive
#########################################
for dtype in ${dtype_list};do
  type0=$(echo ${dtype}|cut -d. -f1)  # L
  type1=$(echo ${dtype}|cut -d. -f2)  # Thermodynamic
  type1_lower=$(echo "${type1}" | sed -e 's/\(.*\)/\L\1/')

  if [ ${type0} == "L" ];then
    outz=${zlist}
    outnz=${nz}
    outnz1=${nz}
  else
    outz=1000
    outnz=0
    outnz1=1
  fi

  # ------ get varables
  table=""
  for outprec in 'float' ;do
    dum=$(ncdump -h ${ncdir}/${ncheader}.${dtype}-000000.nc|grep "${outprec}")
    dum=${dum// /.}
    table="${table} ${dum}"
  done
  table2=$(ncdump -h ${ncdir}/${ncheader}.${dtype}-000000.nc|grep "standard_name")
  table2=${table2// /.}
  varstring=""
  nvar=0
  for dum in ${table};do
    vname=$(echo ${dum}|cut -d. -f2|cut -d"(" -f1)
    if [ "${vname}" == "time" ]; then continue; fi
    
    longname="${vname}"
    for dum2 in ${table2};do
      vlname=$(echo ${dum2}|cut -d':' -f1)
      if [ "${vlname}" == "${vname}" ]; then
        longname=$(echo ${dum2}|cut -d'"' -f2)
        break
      fi
    done
    #echo ${vname} ${longname}

    nvar=$((${nvar}+1))
    dim=$(echo ${dum}|cut -d"(" -f2|cut -d")" -f1)
    dimstr=""
    for v in ${dim//,./ };do
      dimstr="${dimstr},${vtab[$v]}"
    done
    dimstr=$(echo ${dimstr}|cut -c2-10000)
    varstring="${varstring}\n${vname}=>${vname} ${outnz} ${dimstr} ${longname}"
  done
  echo ${dtype} ${nvar}
  
  string="
  DSET ^../archive/${ncheader}.${dtype}-%tm6.nc\n
  DTYPE netcdf\n
  OPTIONS template\n
  TITLE ${dtype} variables\n
  UNDEF 99999.\n
  CACHESIZE 10000000\n
  XDEF ${nx} LINEAR ${lon0} ${dlon}\n
  YDEF ${ny} LINEAR ${lat0} ${dlat}\n
  ZDEF ${outnz1} LEVELS ${outz}\n
  TDEF ${nt} LINEAR 01JAN1998 ${deltatime}mn\n
  VARS ${nvar}
  ${varstring}\n
  ENDVARS
  "
  echo -e ${string}>${outdir}/${type1_lower}.ctl

done


#########################################
# create ctl for TOPO.nc
#########################################
outz=1000
outnz=0
outnz1=1

# ------ get varables
fname="${rundir}/TOPO.nc"
table=""
for dtype in 'float' 'int' ;do
dum=$(ncdump -h ${fname}|grep "${dtype}")
dum=${dum// /.}
table="${table} ${dum}"
done

table2=$(ncdump -h ${fname}|grep "long_name")
table2=${table2// /.}
varstring=""
nvar=0
for dum in ${table};do
  vname=$(echo ${dum}|cut -d. -f2|cut -d"(" -f1)
  if [ "${vname}" == "time" ]; then continue; fi
  if [ "${vname}" == "lon" ]; then continue; fi
  if [ "${vname}" == "lat" ]; then continue; fi
  if [ "${vname}" == "lev" ]; then continue; fi
  
  longname="${vname}"
  for dum2 in ${table2};do
    vlname=$(echo ${dum2}|cut -d':' -f1)
    if [ "${vlname}" == "${vname}" ]; then
      longname=$(echo ${dum2}|cut -d'"' -f2)
      break
    fi
  done
  #echo ${vname} ${longname}

  nvar=$((${nvar}+1))
  dim=$(echo ${dum}|cut -d"(" -f2|cut -d")" -f1)
  dimstr=""
  for v in ${dim//,./ };do
    dimstr="${dimstr},${vtab[$v]}"
  done
  dimstr=$(echo ${dimstr}|cut -c2-10000)
  varstring="${varstring}\n${vname}=>${vname} ${outnz} ${dimstr} ${longname}"
done
echo "TOPO.nc ${nvar}"

string="
DSET ^../TOPO.nc\n
DTYPE netcdf\n
TITLE TOPO\n
UNDEF 99999.\n
CACHESIZE 10000000\n
XDEF ${nx} LINEAR ${lon0} ${dlon}\n
YDEF ${ny} LINEAR ${lat0} ${dlat}\n
ZDEF ${outnz1} LEVELS ${outz}\n
TDEF ${nt} LINEAR 01JAN1998 ${deltatime}mn\n
VARS ${nvar}
${varstring}\n
ENDVARS
"
echo -e ${string}>${outdir}/topo.ctl

#########################################
## bar.ctl
#########################################
outz=${zlist}
outnz=${nz}
outnz1=${nz}

string="
DSET ^../bar.dat\n
TITLE mean profile\n
UNDEF 99999.\n
XDEF 1 LINEAR ${lon0} ${dlon}\n
YDEF 1 LINEAR ${lat0} ${dlat}\n
ZDEF ${outnz1} LEVELS ${outz}\n
TDEF 1 LINEAR 01JAN1998 ${deltatime}mn\n
VARS 13 \n
 pbar   ${outnz} 99 pbar  [Pa]   \n
 pibar  ${outnz} 99 pibar  \n
 rho    ${outnz} 99 rho   [kg/m3] \n
 th     ${outnz} 99 thbar     [K] \n
 qv     ${outnz} 99 qvbar     [kg/kg] \n
 UG     ${outnz} 99 UG        [m/s] \n
 VG     ${outnz} 99 VG        [m/s] \n
 Q1LS   ${outnz} 99 Q1LS      [K/s] \n
 Q2LS   ${outnz} 99 Q2LS      [g/g/s] \n
 WLS    ${outnz} 99 WLS       [m/s] \n
 DZT    ${outnz} 99 delta ZT  [m] \n
 the    ${outnz} 99 th_e bar  [K] \n
 thes   ${outnz} 99 th_es bar [K] \n
ENDVARS
"
echo -e ${string}>${outdir}/bar.ctl
