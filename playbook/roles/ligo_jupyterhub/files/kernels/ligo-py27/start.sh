#!/bin/sh
. /cvmfs/ligo-containers.opensciencegrid.org/lscsoft/conda/latest/bin/activate ligo-py27
/cvmfs/ligo-containers.opensciencegrid.org/lscsoft/conda/latest/envs/ligo-py27/bin/python2 -m ipykernel_launcher -f $@
