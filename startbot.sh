#!/bin/bash

cd /home/sloth/birdbot/kurzgesagtbot/

#ls -l
python3 kurzgesagt.py
if [ -z $FORCIBLY_KILLED ]
then
        exit 0
else
        exit 1
fi
