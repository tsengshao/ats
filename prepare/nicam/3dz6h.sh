#/bin/bash

#/large/sftpgo/data/NICAM/hackathon/2020/3dz6h/z09/ms_geopo_p25.nc

grid=3dz6h
root_dir=`pwd`
data_dir=/large/sftpgo/data/NICAM/hackathon/2020/$grid/z09
ref_dir="${root_dir}/ref_data"
out_dir="${root_dir}/../data/nicam/${grid}"
mkdir -p ${out_dir}

# from JUN2020 to FEB2021
flag='-seltimestep,368/1460 -sellevel,1000/100'
var=ms_geopo_p25

var='sa_tppn'
for var in ms_geopo_p25  ms_qv_p25 ms_tem_p25; do
#for var in ms_v_p25 ms_qall_p25 ms_u_p25  ms_w_p25;do
echo ${var}
echo cdo -P 5 -z zip remap,"$ref_dir/latlon_0.1deg_grid.txt","$ref_dir/weights_nn.nc"\
    ${flag} \
    $data_dir/$var.nc $out_dir/$var.nc
done

wait all

# ms_geopo_p25.nc  ms_qv_p25.nc  ms_tem_p25.nc  ms_v_p25.nc
# ms_qall_p25.nc	 ms_rh_p25.nc  ms_u_p25.nc    ms_w_p25.nc

