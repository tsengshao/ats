#!/bin/bash
cd /home/flyingmars/iop_routine/
source ~/miniconda3/bin/activate iop
python /home/flyingmars/iop_routine/main.py >> /home/flyingmars/iop_routine/log.txt
