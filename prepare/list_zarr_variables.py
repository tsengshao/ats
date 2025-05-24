import xarray as xr


### ICON
# /large/sftpgo/data/ICON/d3hp003.zarr/P1D_inst_z9_atm
# /large/sftpgo/data/ICON/d3hp003.zarr/P1D_mean_z9_atm
# /large/sftpgo/data/ICON/d3hp003.zarr/PT1H_inst_z9_atm
# /large/sftpgo/data/ICON/d3hp003.zarr/PT3H_inst_z9_atm
# /large/sftpgo/data/ICON/d3hp003.zarr/PT3H_mean_z9_atm
# /large/sftpgo/data/ICON/d3hp003.zarr/PT6H_inst_z9_atm
# /large/sftpgo/data/ICON/d3hp003.zarr/PT6H_mean_z9_atm

### NICAM
# /large/sftpgo/data/NICAM/hackathon/healpix/tmp/NICAM_3d6h_z9.zarr
# /large/sftpgo/data/NICAM/hackathon/healpix/NICAM_2dbc_z9.zarr
# /large/sftpgo/data/NICAM/hackathon/220m/data_healpix_15.zarr
# /large/sftpgo/data/NICAM/hackathon/healpix/NICAM_2d1h_z0.zarr

### Unified Model
# /large/sftpgo/data/Unified_Model/data.healpix.PT1H.z10.zarr

### SCREAM
# /large/sftpgo/data/SCREAM/scream2D_hrly_pr_hp10_v7.zarr
# /large/sftpgo/data/SCREAM/scream2D_hrly_topo_hp10_v7.zarr
# /large/sftpgo/data/SCREAM/scream2D_hrly_pr_hp9_v7.zarr
# /large/sftpgo/data/SCREAM/scream2D_hrly_topo_hp9_v7.zarr
# ----
# /large/sftpgo/data/SCREAM/scream2D_ne120_all_hp8_v7.zarr
# /large/sftpgo/data/SCREAM/scream2D_ne120_inst_all_hp8_v1.zarr
# /large/sftpgo/data/SCREAM/scream2D_ne120_topo_hp8_v7.zarr
# /large/sftpgo/data/SCREAM/scream3D_ne120_hus_hp8_v7.zarr
# /large/sftpgo/data/SCREAM/scream3D_ne120_omega_hp8_v7.zarr
# /large/sftpgo/data/SCREAM/scream3D_ne120_qall_hp8_v7.zarr
# /large/sftpgo/data/SCREAM/scream3D_ne120_ta_hp8_v7.zarr
# /large/sftpgo/data/SCREAM/scream3D_ne120_ua_hp8_v7.zarr
# /large/sftpgo/data/SCREAM/scream3D_ne120_va_hp8_v7.zarr
# /large/sftpgo/data/SCREAM/scream3D_ne120_zg_hp8_v7.zarr


#path='/large/sftpgo/data/Unified_Model/data.healpix.PT1H.z10.zarr'
#path='/large/sftpgo/data/SCREAM/scream2D_hrly_pr_hp10_v7.zarr'
#path='/large/sftpgo/data/NICAM/hackathon/healpix/NICAM_2dbc_z9.zarr'
#path='/large/sftpgo/data/NICAM/hackathon/220m/data_healpix_15.zarr'
#path='/large/sftpgo/data/ICON/d3hp003.zarr/P1D_inst_z9_atm'
path='/large/sftpgo/data/NICAM/hackathon/healpix/NICAM_2d1h_z0.zarr'
path='/large/sftpgo/data/ICON/d3hp003.zarr/PT1H_inst_z9_atm'
ds = xr.open_zarr(path)
for var in ds.variables:
  try:
    print(var, ds[var].long_name, sep='\t')
  except:
    print(var)

