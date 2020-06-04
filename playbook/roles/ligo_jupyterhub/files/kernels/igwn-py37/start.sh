#!/bin/sh
. /cvmfs/oasis.opensciencegrid.org/ligo/sw/conda/bin/activate igwn-py37
/cvmfs/oasis.opensciencegrid.org/ligo/sw/conda/envs/igwn-py37/bin/python -m ipykernel_launcher -f $@
