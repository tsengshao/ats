#/bin/bash

#/large/sftpgo/data/NICAM/hackathon/2020/2ds1h/z09/sa_tppn.nc
root_dir=`pwd`
data_dir=/large/sftpgo/data/NICAM/hackathon/2020/2ds1h/z09
ref_dir="${root_dir}/ref_data"
out_dir="${root_dir}/../data/nicam/2d1h"
mkdir -p ${out_dir}
flag="-seltimestep,2209/8760"

var='sa_tppn'
for var in sa_tppn ss_u10m ss_v10m;do
    echo ${var}
    cdo -P 3 remap,"$ref_dir/latlon_0.1deg_grid.txt","$ref_dir/weights_nn.nc"\
        $flag\
        $data_dir/$var.nc $out_dir/$var.nc
done



