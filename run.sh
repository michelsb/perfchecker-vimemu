#!/bin/bash

# Make sure only root can run our script
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

for pid in $(pidof -x app.py); do
    if [ $pid != $$ ]; then
        kill -9 $pid
    fi 
done

nohup python3 app.py > out.log 2>&1 &
