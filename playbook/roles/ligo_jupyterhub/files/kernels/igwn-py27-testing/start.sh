#!/bin/sh
. /cvmfs/oasis.opensciencegrid.org/ligo/sw/conda/bin/activate igwn-py27-testing
/cvmfs/oasis.opensciencegrid.org/ligo/sw/conda/envs/igwn-py27-testing/bin/python -m ipykernel_launcher -f $@
