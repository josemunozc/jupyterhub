#!/bin/sh
HEAD_PYCBC=$( ls -d /cvmfs/oasis.opensciencegrid.org/ligo/sw/pycbc/x86_64_rhel_7/virtualenv/* | sort -rV | head -1 )
source ${HEAD_PYCBC}/bin/activate
exec python -m ipykernel $@
