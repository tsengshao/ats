#!/bin/bash

vvmdir="/data/C.shaoyu/ats/vvm/"
expList=$(ls ${vvmdir})

srcdir=`pwd`
ctlfile="${srcdir}/make_ctl_bash.sh"

for exp in ${expList};do
  echo ${exp}
  cd ${vvmdir}/${exp}
  cp ${ctlfile} .
  ./make_ctl_bash.sh
  cd ${srcdir}
done
