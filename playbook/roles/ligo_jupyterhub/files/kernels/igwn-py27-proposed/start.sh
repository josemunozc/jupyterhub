#!/bin/sh
. /cvmfs/oasis.opensciencegrid.org/ligo/sw/conda/bin/activate igwn-py27-proposed
/cvmfs/oasis.opensciencegrid.org/ligo/sw/conda/envs/igwn-py27-proposed/bin/python -m ipykernel_launcher -f $@
