# Try to install via APT  before trying to install via PIP3
# (it is safe to run this command more than once - it will just update w/ any newer packages)
verify_module_installed () {
	python3 -c "import pkgutil; exit(pkgutil.find_loader(\"$1\") is None)" 
}

install_module () 
{
	verify_module_installed $1 || \
		apt install -y $2 || \
		pip3 install $1
}

install_apt_package ()
{
     dpkg -s $1 > /dev/null 2>&1 || \
	   apt install -y $1
}

install_pip_module () 
{
	verify_module_installed $1 || \
		pip3 install $1
}


# Make sure that PIP3 is available
install_apt_package python3-pip

# Get the various python modules that the program needs
install_module argon3_cffi python3-argon2
install_module bottle python3-bottle
install_module gevent python3-gevent

# The current packaged version of Pillow is v8, but we need a v9 version
#  (so force it to install via PIP3)
#apt install -y python3-pil            || pip3 install pillow
install_pip_module  pillow

# Unfortunately, the PIP3 version of the libraries are currently too old (and do not work on all HW versions)
#pip3 install waveshare-epaper
#pip3 install epd-library

# See if we need to install waveshare_epd
verify_module_installed waveshare_epd

if [ $? -eq 1 ]
then
	(cd /tmp; wget https://github.com/waveshareteam/e-Paper/archive/refs/heads/master.zip; unzip master.zip; rm master.zip)
	(cd /tmp/e-Paper-master/RaspberryPi_JetsonNano/python; python3 setup.py install)
	rm -rf /tmp/e-Paper-master
fi

install_module icalendar python3-icalendar

install_apt_package  libopenjp2-7

install_module pytz python3-tz

install_pip_module recurring_ical_events

install_module psutil python3-psutil
install_module requests python3-requests
install_module requests_cache python3-requests-cache
install_module suntime python3-suntime

# Now, non-python packages that are also required
install_apt_package inkscape