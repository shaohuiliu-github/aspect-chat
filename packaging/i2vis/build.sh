#!/bin/sh
set -eu
src=$1
out=$2
mkdir -p "$out"
for target in in2 i2; do
 if [ "$target" = in2 ]; then unit=in2fasth5.c; else unit=i2fasth5.c; fi
 gcc -std=gnu99 -O2 -fopenmp -mcmodel=large -fno-pie -no-pie -Wno-unused-result -I/opt/chatgfd-adapter -I/usr/include/suitesparse -I/usr/include/hdf5/serial "$src/$unit" -L/usr/lib/$(gcc -dumpmachine)/hdf5/serial -lhdf5 -lumfpack -lamd -lsuitesparseconfig -lm -o "$out/${target}h5"
done
gcc -std=gnu99 -O2 -fopenmp -mcmodel=large -fno-pie -no-pie -Wno-unused-result -I"$src" -I/opt/chatgfd-adapter -I/usr/include/suitesparse -I/usr/include/hdf5/serial /opt/chatgfd-adapter/recouple.c -L/usr/lib/$(gcc -dumpmachine)/hdf5/serial -lhdf5 -lumfpack -lamd -lsuitesparseconfig -lm -o "$out/recouple"
