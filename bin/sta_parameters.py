import argon2
import os
import re
import secrets
import random
import shutil
import sys

import cmd_dispatch
import extra_utils

USE_NEW_FILE = False
DEBUG = 1

_passwd_hasher = argon2.PasswordHasher()

search_dirs = [ "etc/", "lib/conf-files/" ]

valid_params = {
    "active-display" : "active-display.txt",
    "active-iconset" : "active-iconset.txt",
    "email_addr" : "prog-id.txt",
    "lat_lon" : "lat-lon.txt",
    "forecast_zone" : "forecast-zone.txt",
    "alert_zone" : "alert-zone.txt", 
    "tide_station" : "tide-station.txt",
    "obs_stations" : "obs-stations.txt",
    "wifi_ssid" : "wifi-ssid.txt",
    "timezone" : "timezone.txt",
    "rotate" : "rotate.txt",
    "web_password" : "web-password.txt",
    "sync_password" : "sync-i-password.txt",
    "sync_server" : "sync-i-server.txt",
    "sync_cleanwildcards" : "sync-i-cleanwildcards.txt",
    "sync_cleanwildcards" : "sync-i-cleanmissing.txt",
    "wifi_pass" : None
    }

default_vals = {
    "active-display" : "5day-w-cal", 
    "active-iconset" : "simple-icons",
    "sync_server" : "No",
    "sync_cleanwildcards" : "Yes",
    "sync_cleanmissing" : "Yes", 
    "rotate" : "0"
    }

def print_it(*args,**kwargs):
    
    if (DEBUG):
        print(*args, **kwargs)
        
def is_linux():
    p = sys.platform
    
    return (p[:5] == "linux")

# Small routine to return..
#   the user R/W version of the config directories (if 0)
#   the system R/O version of the conf directories (if 1)

def conf_dir(index=0, remove_ending_slash=False):
    item = None
    if (len(search_dirs) > index):
        item = search_dirs[index]

    if ((item is not None) and (remove_ending_slash)):
        item = item.rstrip("/")
        item = item.rstrip("\\")
        
    return item



def find_file(filename, search_dirs=search_dirs):
    
    if (not filename.endswith(".txt")):
        filename = filename + ".txt"
        
    full_filename = None
    
    for prefix in search_dirs: 
        if ((full_filename is None) and (os.path.isfile(prefix + filename))):
            full_filename = prefix + filename

    return full_filename

def find_active_file(param):
    full_filename = None

    if ((param[0:7] == "active-") and (param in valid_params)):
        suffix_param = param[7:]

        variant = get_param(param)
        print_it("Found variant", variant)
        
        filename = suffix_param + "-" + variant + ".txt"
        
        full_filename = find_file(filename)
        print_it("Variant leads to", full_filename)
        
    return full_filename

def get_line(filename, return_str=False, search_dirs=search_dirs):
    s = ""

    full_filename = find_file(filename, search_dirs)

    if (full_filename is not None):
        f = open(full_filename)
        s = extra_utils.readline_w_comments(f)
        f.close()

    if ((s is None) and (return_str)):
        s = ""

    if (s is not None):
        s = s.strip()

    return s

def write_line(filename, s):
    prefix = search_dirs[0]
    filename = prefix + filename
    
    f = open(filename + ".new", "w")

    if (s[-1] != "\n"):
        s = s + "\n"

    f.write(s)
    f.close()

    if (os.path.exists(filename + ".old")):
        os.remove(filename + ".old")

    if (os.path.isfile(filename)):
        shutil.copy2(filename, filename + ".old")
        
    os.replace(filename + ".new", filename)

    return True

def get_param(p):
    s = ""
    
    if p == "web_password":
        s = ""  # Don't show the current web password (it's not in a useful format anyways)
        
    elif p in valid_params:
        filename = valid_params[p]

        if filename is not None:
            s = get_line(filename)

        if (s == "") and (p in default_vals):
            s = default_vals[p]
            
    elif p.startswith("sync-"):
        filename = p
        
        if not filename.endswith(".txt"):
            filename = filename + ".txt"
        
        if filename is not None:
            s = get_line(filename)
            
    elif p == "active-ipaddr":
        s = extra_utils.get_my_ipaddr(allow_no_inet=True)

    elif p == "active-ssid":
        s = extra_utils.get_ssid()

    return s

#
#--------------------------------------------------------------------------
#

def check_and_update_timezone():
    # Only check the timezone on Linux systems
    if (is_linux() and os.path.isfile("/etc/timezone")):
        conf_tz = get_param("timezone")

        f = open("/etc/timezone")
        active_tz = f.readline().strip()
        f.close()

        if ((conf_tz != active_tz) and (conf_tz != "") and (conf_tz is not None)):
            print_it("Updating timezone from", active_tz, "to", conf_tz)
            set_timezone(conf_tz)

    
def set_timezone(v):
    ok = True

    # Check the sanity of the input
    m = re.search(r"^[\w\/-]+$", v)
    
    if (m is None):
        print_it("Malformed timezone string:", v, file=sys.stderr)
        ok = False
        
    elif (is_linux()):
        print_it("sudo timedatectl set-timezone " + v)
        retval = os.system("sudo timedatectl set-timezone " + v)
            
        ok = (retval == 0)

    return ok

#
#----------------------------------------------------------------
#

def _create_stored_passwd(passwd):
    return _passwd_hasher.hash(passwd)

def set_web_password(new_pass):
    ok = False

    if new_pass.strip() != "":
        pass_str = _create_stored_passwd(new_pass)

        if pass_str != "":
            filename = valid_params["web_password"]
            write_line(filename, pass_str)
            ok = True

    return ok

def _test_passwd(passwd, stored_passwd):
    try:
        _passwd_hasher.verify(stored_passwd, passwd)
            
    except (argon2.exceptions.VerifyMismatchError, argon2.exceptions.InvalidHash) as e:
        valid_pass = False
    else:
        valid_pass = True
        
    return valid_pass

def get_pin():
    if os.path.isfile("cache/web-pin.txt"):
        f = open("cache/web-pin.txt")
        stored_pin = f.readline()
        f.close()
        
        stored_pin = stored_pin.strip()

    # No pin?  Create one
    else:
        # Create a new 8-digit pin
        new_pin = random.randint(0,99999999)
        new_pin = str(new_pin)
        new_pin = new_pin.zfill(8)

        f = open("cache/web-pin.txt", "w")
        f.write(new_pin + "\n")
        f.close()

        stored_pin = new_pin

    return stored_pin
#
#  Pins are the backup (for the web control page) if no web password is displayed
#
def _test_pin(given_pin):
    stored_pin = get_pin()

    return given_pin == stored_pin

#
#  See if the pin is necessary to access the web control page
#
def needs_pin():
    return not os.path.isfile("etc/web-password.txt")



def check_web_password(given_pass):
    filename = valid_params["web_password"]

    stored_pass = get_line(filename, return_str=True)

    # Use the web-password.txt file if exists
    if stored_pass != "":
        result = _test_passwd(given_pass, stored_pass)

    else:
        result = _test_pin(given_pass)
        
    return result

#
#--------------------------------------------------------------------------
#

 
def set_wifi_pass(psk):

    if (re.search(r"^[\w \(\)',:_\!\.\\[\\]\\-]+$", psk) is None):
        print_it("Wi-Fi Password", psk, "failed Regular Expression")
        ok = False

    else:
        ok = True

    if (ok):
        print_it("sudo wpa_cli set_network 0 psk '\"" + psk + "\"'")
        retval = os.system("sudo wpa_cli set_network 0 psk '\"" + psk + "\"'")

        if (retval == 0):
            print_it("sudo wpa_cli save_config")
            retval = os.system("sudo wpa_cli save_config")

        ok = (retval == 0)
        
    return ok
    


def set_wifi_ssid(ssid):

    if re.search(r"^[\w \(\)',:_\!\.\\[\\]\\-]+$", ssid) is None:
        print_it("SSID", ssid, "failed Regular Expression")
        ok = False
        
    else:
        ok = True

    if ok:
        print_it("sudo wpa_cli set_network 0 ssid '\"" + ssid + "\"'")
        retval = os.system("sudo wpa_cli set_network 0 ssid '\"" + ssid + "\"'")
        
        if (retval == 0):
            print_it("sudo wpa_cli save_config")
            retval = os.system("sudo wpa_cli save_config")

        ok = (retval == 0)
        
    return ok
    
def set_param(p,v):
    ok = False

    if v is None:
        v = ""
        
    if p in valid_params:
        filename = valid_params[p]

        if p == "wifi_pass":
            ok = set_wifi_pass(v)

        elif p == "web_password":
            ok = set_web_password(v)
            
        elif filename is not None:
            ok = write_line(filename,v)

        if ok:
            if (p == "timezone"):
                ok = set_timezone(v)

            elif (p == "wifi_ssid"):
                ok = set_wifi_ssid(v)
                
    elif p.startswith("sync-"):
        filename = p
        
        if not filename.endswith(".txt"):
            filename = filename + ".txt"
        
        ok = write_line(filename, v)
            
    return ok

def set_special_params():
    v = get_param("wifi_ssid")

    if (v != ""):
        set_wifi_ssid(v)

    v = get_param("timezone")
    if (v != ""):
        set_timezone(v)
        
def init_cmd_dispatch():
    cmd_dispatch.add_function("get_param", get_param)

def list_params():
    return sorted(valid_params.keys())

init_cmd_dispatch()
