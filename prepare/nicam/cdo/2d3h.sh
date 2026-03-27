#/bin/bash

#/large/sftpgo/data/NICAM/hackathon/2020/2d3h/z09/sa_vap_atm.nc

grid=2d3h
root_dir=`pwd`
data_dir=/large/sftpgo/data/NICAM/hackathon/2020/$grid/z09
ref_dir="${root_dir}/ref_data"
out_dir="${root_dir}/../data/nicam/${grid}"
mkdir -p ${out_dir}

# from JUN2020 to FEB2021
flag='-seltimestep,737/2920'


var='sa_tppn'
#for var in sa_vap_atm sa_ps sa_cldi sa_cldw;do
for var in sa_sh_sfc sa_lh_sfc;do
echo ${var}
cdo -P 1 -z zip remap,"$ref_dir/latlon_0.1deg_grid.txt","$ref_dir/weights_nn.nc"\
    ${flag} \
    $data_dir/$var.nc $out_dir/$var.nc
done

# sa_cld_frac.nc	 sa_lwd_toa.nc	  sa_q2m.nc	   sa_swu_sfc.nc    sa_tppn.nc
# sa_cldi.nc	 sa_lwu_sfc.nc	  sa_sh_sfc.nc	   sa_swu_sfc_c.nc  sa_u10m.nc
# sa_cldw.nc	 sa_lwu_sfc_c.nc  sa_slp_ecmwf.nc  sa_swu_toa.nc    sa_v10m.nc
# sa_lh_sfc.nc	 sa_lwu_toa.nc	  sa_swd_sfc.nc    sa_swu_toa_c.nc  sa_vap_atm.nc
# sa_lwd_sfc.nc	 sa_lwu_toa_c.nc  sa_swd_sfc_c.nc  sa_t2m.nc
# sa_lwd_sfc_c.nc  sa_ps.nc	  sa_swd_toa.nc    sa_tem_sfc.nc

