import os
import socket
import subprocess
import sys
import time
import platform
import psutil


_LAST_UP = 0

#
#--------------------------------------------------------
#

# Get my own ip address

# https://www.geeksforgeeks.org/display-hostname-ip-address-python/
def get_my_ipaddr(to_addr="8.8.8.8", to_port=0, allow_no_inet=False):
    result = None

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # connect() for UDP doesn't send packets
    try:
        s.connect((to_addr, to_port))
        result = s.getsockname()[0]

        s.close()
        s = None

    except (socket.gaierror, OSError):
        result = None
        
    if ((result is None) and (allow_no_inet)):
        result = get_best_ip_no_internet()
    
    return result 

def internet_is_up():

    my_ip = get_my_ipaddr(to_addr="api.weather.gov")

    return (my_ip is not None)

def internet_is_up_w_hold(hold_time=15):
    global _LAST_UP

    now = time.time()
    
    is_up = internet_is_up()

    if is_up:
        _LAST_UP = now

    # Allow up to "hold_time" minutes for the Internet to be down
    #  (and show old data(
    elif (now - _LAST_UP < hold_time * 60):
        is_up = True

    return is_up

def get_best_ip_no_internet():
    all_if = psutil.net_if_addrs()

    best_name = None
    best_addr = None
    best_type = 0
    
    for (if_name, if_val) in all_if.items():
        ipv4 = None
        ipv6 = None

        if_name_l = if_name.lower()
        
        for one_sni in if_val:
            if (one_sni.family == socket.AF_INET):
                ipv4 = one_sni.address
                
            if (one_sni.family == socket.AF_INET6):
                ipv6 = one_sni.address

        # Prefer the IPv4 address (for now)
        if (ipv4 is None):
            ip_addr = ipv6
        else:
            ip_addr = ipv4

        # The first non-loopback address is always the best
        if (if_name_l.startswith("lo")):
            pass

        # Prefer Wi-Fi to Ethernet
        elif ((if_name_l.startswith("wlan")) or (if_name_l.startswith("wi-fi"))):
            if (best_type < 3):
                best_name = if_name
                best_addr = ip_addr
                best_type = 3
               
        elif (if_name_l.startswith("eth")):
            if (best_type < 2):
                best_name = if_name
                best_addr = ip_addr
                best_type = 2

        elif (best_type == 0):
            best_name = if_name
            best_addr = ip_addr
            best_type = 1  #  Possible boring


    return (best_name, best_addr)


def get_ssid():
    ssid = "???"

    if (sys.platform == "linux"):
        try:
            p = subprocess.run(["iw", "dev"], capture_output=True)
            
        except FileNotFound:
            p = None

        if (p is not None):
            stdout = p.stdout.decode()
            
            for one_line in stdout.split("\n"):

                if ("ssid" in one_line):
                    start = one_line.index("ssid")
                    start = start + 4 # Len of "ssid"
                    
                    ssid = one_line[start:]
                    ssid = ssid.strip()

    return ssid
#
#  Hack: Permit testing using IDLE on Windows by
#   forcing the directory up one
#
def set_default_dir():
    cwd = os.getcwd()

    # Permit both Linux and Windows endings
    cwd_s = cwd.replace("\\", "/")
    
    if ((cwd_s.endswith("/bin") or (cwd_s.endswith("/sbin")))):
        #print("Changing the default directory")
        os.chdir("..")

#
#  Routine to ignore comments and blank lines
#
def readline_w_comments(f, strip=True):
    line = ""
    
    if (f is not None):
        
        done = False
        
        while ((line == "") and (not done)):
            line = f.readline()
            
            if (line == ""):
                done = True
            
            if ("#" in line):
                line = line[:line.index("#")]

            if (strip):
                line = line.strip()

            if line != "":
                done = True

    # Return None if at the end of file
    if (line == ""):
        line = None
            
    return line

def hostname():
    return platform.node()

if (__name__ == "__main__"):
    print(get_my_ipaddr())
