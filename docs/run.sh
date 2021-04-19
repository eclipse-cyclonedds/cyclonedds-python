#!/bin/bash

make clean && make html
cd build/html && python ../../nocacheserver.py