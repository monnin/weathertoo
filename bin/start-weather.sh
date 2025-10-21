cd ~weather/weather

test -e /tmp/last-run.log.2 && mv /tmp/last-run.log.1 /tmp/last-run.log.3
test -e /tmp/last-run.log.1 && mv /tmp/last-run.log.1 /tmp/last-run.log.2
test -e /tmp/last-run.log   && mv /tmp/last-run.log   /tmp/last-run.log.1

# Stop any currently running script
pkill -f bin/start-weather.sh
pkill -f bin/waveshare-weather.py

# Repeat forever
while true
do
	python3 bin/waveshare-weather.py 2>&1  | tail -100 > /tmp/last-run.log

	# This is for debugging purposes only
	echo "waveshare-weather.py exited" | wall

	sleep 30
done