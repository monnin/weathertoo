import os
import requests
import requests.auth
import shutil
import sys
import time
import warnings

import extra_utils
import sta_parameters

DEBUG = True
DRY_RUN = False

SLEEP_TIME = 60 * 5   #  5 Minutess

WEB_PROTO = "https"
WEB_PORT  = "8888"

def get_web_file(url, passwd):
    s = None

    if DEBUG:
        print("GET", url)
        
    try:
        r = requests.get(url, auth=('sync', passwd), verify=False)
        
    except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, ConnectionRefusedError) as e:
        print("URL", url, "failed", file=sys.stderr)
        
        r = None
        s = None

    if r is not None and r.status_code == 200:
        s = r.text
                     
    return s

#
#-------------------------------------------------------------------------------
#

def open_if_exists(filename):
    if os.path.isfile(filename):
        f = open(filename)
    else:
        f = None

    return f

def replace_file(filename, new_content):
    if DRY_RUN:
        print("Would replace", filename)

    else:
        if DEBUG:
            print("Replacing", filename, file=sys.stderr)
            
        f = open(filename + ".new", "w")
        f.write(new_content)
        f.close()

        if (os.path.exists(filename + ".old")):
            os.remove(filename + ".old")

        if (os.path.isfile(filename)):
            shutil.copy2(filename, filename + ".old")
            
        os.replace(filename + ".new", filename)

#
#-------------------------------------------------------------------------------
#
def delete_file(filename):
    if DRY_RUN:
        print("Would delete", filename)

    else:
        if DEBUG:
            print("Deleting", filename, file=sys.stderr)

        if (os.path.exists(filename + ".old")):
            os.remove(filename + ".old")

        if (os.path.isfile(filename)):
            os.replace(filename, filename + ".old")  
#
#-------------------------------------------------------------------------------
#

def get_addr_and_passwd(syncfilename):
    if not syncfilename.endswith(".txt"):
        syncfilename = syncfilename + ".txt"
        
    f = open_if_exists("etc/" + syncfilename)
    
    if f is not None:
        s = extra_utils.readline_w_comments(f)
        f.close()
    else:
        s = None

    if s is None:
        addr = None
        passwd = None
    
    elif "/" in s:
        (addr,passwd) = s.split("=", 1)

    else:
        addr = s
        
        f = open_if_exists("etc/sync-i-password.txt")
    
        passwd = extra_utils.readline_w_comments(f)
        
        if f is not None:
            f.close()

    if (addr is not None):
        if ":" not in addr:
            addr = addr + ":" + WEB_PORT
            
        if not addr.startswith("http"):
            addr = WEB_PROTO + "://" + addr
            

    return (addr, passwd)

def get_matching_files(prefix):
    files = []
    
    for file in os.listdir("etc/"):
        
        if file.startswith(prefix) and file.endswith(".txt"):
            if os.path.isfile("etc/" + file):
                file = file[:-4]
                files.append(file)

    if DEBUG:
        if len(files) > 0:
            print("Prefix", prefix, "Matched", " ".join(files))
    
    return files

#
#-------------------------------------------------------------------------------
#

def sync_one_file(filename, addr, passwd):
    # Ignore incomplete entries
    if addr is not None and passwd is not None and filename is not None and filename != "":
        if DEBUG:
            print("Looking at", filename)
            
        my_mtime = 0
        my_filename = "etc/" + filename + ".txt"
        if os.path.isfile(my_filename):
            my_mtime = os.path.getmtime(my_filename)
            
        their_mtime = get_web_file(addr + "/sync_sys/mtime/" + filename, passwd)

        # Delete local file if server file is missing and sync_cleanmissing is set
        if their_mtime == "no" and \
           os.path.isfile(my_filename) and \
           sta_parameters.get_param("sync_cleanmissing").lower() == "yes":

            delete_file(my_filename)
            
        # Newer file?  Then get it
        elif their_mtime is not None and their_mtime != "" and int(their_mtime) > my_mtime:
            new_content = get_web_file(addr + "/sync_sys/get/" + filename, passwd)
            replace_file(my_filename, new_content)

        else:
            if DEBUG:
                print("Already have the same (or newer) file for", filename)
#
#-------------------------------------------------------------------------------
#
def handle_all_individual():
    for one_file in get_matching_files("sync-f-"):
        (addr, passwd) = get_addr_and_passwd(one_file)

        if addr is not None and passwd is not None:
            # Remove the sync-f- from the "local" filename
            local_filename = one_file[7:]
            sync_one_file(local_filename, addr, passwd)

#
#-------------------------------------------------------------------------------
#
def handle_all_wildcards():
    files = get_matching_files("sync-w-")

    if files is not None:
        for one_file in files:
            (addr, passwd) = get_addr_and_passwd(one_file)

            if addr is not None and passwd is not None:
                shared_prefix = one_file[7:]

                # Copy all of their matching files
                their_files = get_web_file(addr + "/sync_sys/list/" + shared_prefix, passwd)
                
                if their_files is not None:
                    for one_remote_file in their_files.split("\n"):
                        
                        if one_remote_file != "":
                            print("Matched wildcard", shared_prefix, "with file", one_remote_file)
                            sync_one_file(one_remote_file, addr, passwd)

                    # Remove extra files (if configured to do so)
                    if sta_parameters.get_param("sync_cleanwildcards").lower() == "yes":
                        for local_file in os.listdir("etc/"):

                            local_file_no_ext = local_file[:-4]
                            
                            if local_file.startswith(shared_prefix) and \
                               local_file.endswith(".txt") and \
                               local_file_no_ext not in their_files:
                                delete_file("etc/" + local_file)
                
            
#
#-------------------------------------------------------------------------------
#                     
def main():
    warnings.filterwarnings("ignore", "Unverified HTTPS request")
    
    while True:
        handle_all_wildcards()
        handle_all_individual()

        if DEBUG:
            print("Sleeping...")
            
        time.sleep(SLEEP_TIME)

extra_utils.set_default_dir()

main()
