wpa_cli ap_scan 1

# Add two networks if necessary
#  (I didn't want to do a list, just to make sure it only created a max of 2
#   even if wpa_cli did something goofy)
#
count=`wpa_cli list_network | wc -l`
if [ $count -lt 3 ]
then
	wpa_cli add_network
	wpa_cli set_network 0 priority 20
	wpa_cli set_network 0 ssid '"NO NAME NETWORK HERE"'
	wpa_cli set_network 0 psk  '"NO NAME NETWORK HERE"'
	wpa_cli enable_network 0
fi

if [ $count -lt 4 ]
then
	wpa_cli add_network

	wpa_cli set_network 1 priority 10
	wpa_cli set_network 1 ssid '"Weather-Setup"'
	wpa_cli set_network 1 key_mgmt WPA-NONE
	wpa_cli set_network 1 frequency 2412

	# Set AP mode
	wpa_cli set_network 1 mode 2
	wpa_cli enable_network 1
fi

wpa_cli save_config
#wpa_cli enable_network 0
#wpa_cli enable_network 1