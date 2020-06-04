#!/bin/sh
. /cvmfs/ligo-containers.opensciencegrid.org/lscsoft/conda/latest/bin/activate ligo-py37
/cvmfs/ligo-containers.opensciencegrid.org/lscsoft/conda/latest/envs/ligo-py37/bin/python3 -m ipykernel_launcher -f $@
