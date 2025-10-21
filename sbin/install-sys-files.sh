# Create the weather account (if necessary)
getent passwd weather || useradd -m weather

# Grant weather to use the physical h/w to the epaper
adduser --quiet weather gpio
adduser --quiet weather spi
adduser --quiet weather i2c

# Reset the file ownership (if different) (mostly for first time copy)
chown -R weather:weather ~weather

# Set up sudo  (fyi - sudo doesn't like periods in the filenames)
cp ~weather/weather/lib/install-files/050_weather_sudo.conf /etc/sudoers.d/050_weather_sudo
chmod 750 /etc/sudoers.d/050_weather_sudo

# Set up services
cp ~weather/weather/lib/install-files/weather-display.service       /etc/systemd/system/
cp ~weather/weather/lib/install-files/weather-control-panel.service /etc/systemd/system/
cp ~weather/weather/lib/install-files/weather-sync.service          /etc/systemd/system/

systemctl daemon-reload

systemctl enable weather-display.service
systemctl enable weather-control-panel.service
systemctl enable weather-sync.service

systemctl start weather-display.service
systemctl start weather-control-panel.service
systemctl start weather-sync.service

# Have the O/S to update itself everyday
mkdir -p /root/sbin
cp ~weather/weather/lib/install-files/install-sw.sh /root/sbin
sh /root/sbin/install-sw.sh install