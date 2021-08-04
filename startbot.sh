  GNU nano 4.8                                                                      startbot.sh                                                                                
#!/bin/bash

cd /home/sloth/birdbot/kurzgesagtbot/

#ls -l
python3 kurzgesagt.py
if [ -z $FORCIBLY_KILLED ]
then
        exit 0
fi

exit 1

