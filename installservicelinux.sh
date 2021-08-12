#!/bin/bash
if [ "$EUID" -ne 0 ]; then
        echo "Please run as root"
        exit
fi

FILE=birdbot.service
if test -f "$FILE"; then
        mv birdbot.service /home/austin
        systemctl daemon-reload
        systemctl enable birdbot
        systemctl start birdbot
        systemctl status birdbot
        echo "service should be enabled"
else
        echo "file not found"
fi
