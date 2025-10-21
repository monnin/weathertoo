#!/bin/sh

USE_FULL_UPGRADE=1
USE_PURGE_OLD_KERNELS=0

if [ "$1" = "install" ]
then
        # Install the crontab that normally runs

        echo "Setting up the crontab (cron.d) entry"
        script="`realpath $0`"
        cat >> /etc/cron.d/update-os-daily << xxDUMMYxx
MAILTO=""
PATH=/sbin:/usr/sbin:/usr/bin:/bin

# m h  dom mon dow   command
0 3 * * * /bin/sh $script > /tmp/install-sw.log 2>&1 < /dev/null
xxDUMMYxx

        exit
fi

echo -n "Starting... "; date

export TERM=dumb
export PATH=${PATH}:/sbin:/usr/sbin:/usr/local/sbin
export DEBIAN_FRONTEND=noninteractive
export QUIET=""
export QUIET="-qq"

# Random sleep 0 to 30 minutes
python3 -c 'import random;import time;time.sleep( random.randint(1,1800));'


echo "Step 1: Update"
apt $QUIET update

echo "Step 2: Upgrade"
if [ "$USE_FULL_UPGRADE" = "1" ]
then
	apt $QUIET -y full-upgrade
else
	apt $QUIET -y upgrade
fi

echo "Step 3: Autoremove"
apt $QUIET autoremove

echo "Step 4: Autoclean"
apt $QUIET autoclean

if [ "$USE_PURGE_OLD_KERNELS" = "1" ]
then
	echo "Step 5: Purge Old Kernels"
	purge-old-kernels -y > /dev/null 2>&1
fi

if [ -f /var/run/reboot-required ]; then shutdown -r +5 ;fi

echo -n "Done. " ; date
