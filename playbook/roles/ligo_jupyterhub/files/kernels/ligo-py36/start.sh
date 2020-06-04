#!/bin/sh
. /cvmfs/ligo-containers.opensciencegrid.org/lscsoft/conda/latest/bin/activate ligo-py36
/cvmfs/ligo-containers.opensciencegrid.org/lscsoft/conda/latest/envs/ligo-py36/bin/python3 -m ipykernel_launcher -f $@
