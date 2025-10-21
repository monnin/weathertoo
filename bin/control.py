import getpass
import os
import sys
import tarfile

import extra_utils
import sta_parameters
import weather_rest

MAIN_CONF_DIR = sta_parameters.conf_dir(0, remove_ending_slash=True)

BACKUP_CONF_DIRS     = [ MAIN_CONF_DIR ]
BACKUP_SW_DIRS       = [ "", "lib", "bin", "sbin", "frame", "docs", "html" ]
BACKUP_SW_EMPTY_DIRS = [ "etc", "tmp", "html", "log" ]

#TEXT_ENDINGS = [ ".txt", ".sh", ".py", ".html", ".css", ".js" ]
TEXT_ENDINGS = [ ".sh", ".service", ".conf" ]

def is_convertable(filename):
    convertable = False
    bname = os.path.basename(filename)

    if os.path.isfile(filename):
        
        for ending in TEXT_ENDINGS:
            if bname.endswith(ending):
                convertable = True
    
    return convertable


def needs_converted(filename):
    
    f = open(filename, newline="")
    
    needs_c = False
    s = f.readline()

    while s != "" and not needs_c:
        # Look for non-Linux line endings
        
        if s[-1] == "\r":
            needs_c = True

        elif len(s) == 1:
            pass
        
        elif s[-2] == "\r" and s[-1] == "\n":
            needs_c = True
            
        s = f.readline()
        
    f.close()

    
    return needs_c

def _backup_filter(tinfo):
    if "/__pycache__/" in tinfo.name:
        tinfo = None

    return tinfo

def create_backup(settings, software, backup_name=None):
    s = ""
    
    # Create a filename depending on what they are asking for
    basename = "weather"
    if settings:
        if software:
            basename += "-config-and-program"
        else:
            basename += "-config-only"
            
    elif software:
        basename += "-program-only"
        
    basename += ".tgz"

    if backup_name is None:
        backup_name = "tmp/" + basename
    
        if not os.path.isdir("tmp"):
            os.mkdir("tmp")

    master_list = []
    dirs_only = []
    
    if (software):
        master_list += BACKUP_SW_DIRS
        dirs_only   += BACKUP_SW_EMPTY_DIRS

    if (settings):
        master_list += BACKUP_CONF_DIRS

    tf = tarfile.open(backup_name, "w:gz", format=tarfile.GNU_FORMAT)

    for one_file in os.listdir("."):
        if (one_file[0] == "."):
            s = s + "Ignoring " + one_file + "<br />\n"
        
        elif (os.path.isfile(one_file) and ("" in master_list)):
            s = s + "Adding (file) " + one_file + "<br />\n"
            tf.add(one_file)
            
        elif (os.path.isdir(one_file) and (one_file in master_list)):
            s = s + "Recusively adding (dir) " +  one_file + "<br />\n"
            
            tf.add(one_file, recursive=True, filter=_backup_filter)   # Recursively
            
        elif (os.path.isdir(one_file) and (one_file in dirs_only)):
            s = s + "Non-recusively adding (dir) " +  one_file + "<br />\n"

            tf.add(one_file, recursive=False)  # Add empty dirs for S/W backups
            
    tf.close()

    return s

def _remove_extra(initial_list, dry_run=True):
    all_dirs = []
    existing_files = []

    # Step 1 - Determine the directories in the initial_list
    for item in initial_list:
        if os.path.isdir(item) and item not in all_dirs:
            all_dirs.append(item)

    # Step 2 - Find all files in those directories
    for one_dir in all_dirs:
        for item in os.listdir(one_dir):
            fuller_path = one_dir + "/" + item
            
            if os.path.isfile(fuller_path) and item not in existing_files:
                existing_files.append(fuller_path)
            
    # Step 3 - See if any of the existing files are not in the initial list
    for one_file in existing_files:
        if one_file not in initial_list:

            if dry_run:
                print("Would delete", one_file, file=sys.stderr)

            else:
                print("Deleting", one_file, file=sys.stderr)
                #os.remove(one_file)
            
def restore_backup(backup_name, settings, software,
                   delete_after=False,
                   also_convert=False,
                   remove_extra=False):
    
    master_list = []
    
    if (software):
        master_list += BACKUP_SW_DIRS

    if (settings):
        master_list += BACKUP_CONF_DIRS

    tf = tarfile.open(backup_name, "r:*")

    restore_members = []
    
    s = "<h2>Restore Results</h2>"
    
    # Find the files within tar that match the checkboxes
    for one_member in tf.getmembers():
        member_name = one_member.name

        d = member_name
        
        # Only look at top-level directories
        if "/" in d:
            (d,extra) = d.split("/", 1)
            
        if (d in master_list):
            s = s + "Restoring \"" + member_name + "\"<br />\n"
            restore_members.append(one_member)
        else:
            s = s + "<i>(Ignoring \"" + member_name + "\")</i><br />\n"

    tf.extractall(members=restore_members)
    
    tf.close()

    if also_convert:
        for one_member in restore_members:
            member_name = one_member.name
            
            if is_convertable(member_name) and needs_converted(member_name):
                convert_file(member_name)

    if remove_extra:
        _remove_extra_files(restore_members)

    # If changing settings, also make sure to change the system versions
    if settings:
        sta_parameters.set_special_params()

    if (delete_after and os.path.isfile(backup_name)):
        os.remove(backup_name)

    return s

def convert_file(filename, dry_run=False):

    converted = False
    
    if needs_converted(filename):
        converted = True
        
        if dry_run:
            print(filename, "needs converting")
            
        else:
            print("Converting", filename)
            f = open(filename)   # Open to universal endings (readline converts all endings to \n)
            new_f = open(filename + ".new", "w", newline="\n")

            for one_line in f:
                #if one_line[-1] == "\r":
                #    s = s[:-1] + "\n"
                    
                #elif one_line[-2] == "\r" and one_line[-1] == "\n":
                #    s = s[:-2] + "\n"

                new_f.write(one_line)

            f.close()
            new_f.close()

            # Overrite the version (do not save a .old)
            os.replace(filename + ".new", filename)

    return converted
    
def convert_endings(dir_name, dry_run=False):
    count = 0
    
    for one_file in os.listdir(dir_name):
        full_path = os.path.join(dir_name, one_file)

        # Ignore files/directories starting with . (including . and ..)
        if one_file[0] == ".":
            pass
        
        elif os.path.isdir(full_path):
            count = count + convert_endings(full_path, dry_run)
            
        elif is_convertable(full_path):
            c = convert_file(full_path, dry_run)

            if c:
                count = count + 1

    return count       

#
#   _delete_dir - delete all files and subdirectories in a dir, but
#               -  not the directory itself
#               -  (do not delete other things that are not files/dirs)
#
def _delete_dir(dirname):
    # If not a directory, silently do nothing
    if os.path.isdir(dirname):
        
        # Go over all files and directories
        for file in os.listdir(dirname):
            fuller_name = os.path.join(dirname, file)
            
            if os.path.isfile(fuller_name):
                os.remove(fuller_name)

            elif os.path.isdir(fuller_name):
                delete_dir(fuller_name)
            
def reset_system():
    _delete_dir("etc/")
    _delete_dir("cache/")
    _delete_dir("tmp/")    

    sta_parameters.set_special_params()
    
    
def main():
    no_convert = False
    remove_extra = False
    
    if len(sys.argv) < 2:

        print("Usage:", sys.argv[0], "addr", "<street_address>","-- change the lat_lon based upon a new address")
        print("      ", sys.argv[0], "apply_lat_lon [param_names]", "-- set the weather parameters based on the lat_lon")
        print("      ", sys.argv[0], "backup", "<system|settings|both>", "<filename>", "-- save to a backup file")
        print("      ", sys.argv[0], "restore", "<system|settings|both>", "<filename> [no_convert] [remove_extra]", "-- restore from a backup file")
        print("      ", sys.argv[0], "convert_text", "-- convert line endings to *nix style (format used by WeatherTool)")
        print("      ", sys.argv[0], "check_text", "-- indicate which files need conversion")
        print("      ", sys.argv[0], "get_param", "<param_name", "--display the current setting for one parameter")
        print("      ", sys.argv[0], "list_params",  "--show all of the parameter names")
        print("      ", sys.argv[0], "password","-- change the web control panel password")
        print("      ", sys.argv[0], "update_loc","-- change all weather parameters based on new lat_lon")
        print("      ", sys.argv[0], "zero","-- revert system back to 'factory' settings")
        
        sys.exit(0)

    else:     
        cmd = sys.argv[1].lower()[:2]

        if len(sys.argv) > 2:
            what = sys.argv[2].lower()
            
        else:
            what = None

        if len(sys.argv) > 3:
            where = sys.argv[3]

            settings = what.startswith("se") or what.startswith("b")
            software = what.startswith("sy") or what.startswith("b")

            # Find the tar file BEFORE we change the path
            backup_name = os.path.abspath(where)

        else:
            backup_name = None
            where = None
            
        # Parse the extra options for restore
        for arg in sys.argv[4:]:
            if arg[0] == "n":
                no_convert = True
                
            elif arg[0] == "r":
                remove_extra = True

        # Change to the top of the weather directory
        extra_utils.set_default_dir()

        if cmd == 'ad':
            new_addr = " ".join(sys.argv[2:])
            new_addr = new_addr.strip()

            if new_addr != "":

                lat_lon = weather_rest.addr2latlon(new_addr)
                if lat_lon[0] is not None and lat_lon[1] is not None:

                    lat_lon = str(lat_lon[0]) + ", " + str(lat_lon[1])
                    sta_parameters.set_param("lat_lon", lat_lon)
                    
                    print("Setting lat_lon to", lat_lon)
                    
                else:
                    print("Could not convert", new_addr, "into a latitude and longitude",
                          file=sys.stderr)
                    sys.exit(1)
                
            else:
                print("Please enter a street address", file=sys.stderr)
                sys.exit(1)

        # apply_lat_lon
        elif cmd == "ap":
            if what is None:
                what = "all"
                
            weather_rest.reset_weather_fields(what, print_it=True)
            
        # convert_text
        elif cmd == 'co':
            c = convert_endings(".")
            print(c, "files converted")
            
        elif cmd == 'ch':
            c = convert_endings(".", dry_run=True)
            print(c, "files need converted")

        # password
        elif cmd == 'pa':
            newpass = getpass.getpass("Enter NEW web server password: ")
            newpass = newpass.strip()
            
            if newpass != "":
                sta_parameters.set_param("web_password", newpass)
                print("Password changed")

            else:
                print("Password NOT changed")

        # Backup
        elif cmd == 'ba':
            if backup_name is not None:
                s = create_backup(settings, software, backup_name)
                
                if s is not None:
                    s = s.replace("<br />","")
                    print(s)
                
            else:
                print("Please specify backup filename", file=sys.stderr)
                sys.exit(1)

        # Restore 
        elif cmd == 're':
            if backup_name is not None:               
                s = restore_backup(backup_name, settings, software,
                               also_convert=not no_convert, remove_extra=remove_extra)
                s = s.replace("<br />","")
                print(s)
            
            else:
                print("Please specify backup filename", file=sys.stderr)
                sys.exit(1)

        # get_param
        elif cmd == "ge":
            if what == "-c":
                if sys.platform == 'win32':
                    cmd = "py"
                else:
                    cmd = "python3"
                    
                for what in sta_parameters.list_params():
                    curr_val = sta_parameters.get_param(what)
                    
                    if curr_val is not None and curr_val != "":
                        print(cmd,"control.py set_param", what, curr_val)
                   
            elif what is not None:
                print(what + ":", sta_parameters.get_param(what))
  
            else:
                for what in sta_parameters.list_params():
                   print(what + ":", sta_parameters.get_param(what)) 

        # list_params
        elif cmd == "li":
            print("Valid parameters are:")
            
            for item in sta_parameters.list_params():
                print("   ", item)
                
        # set_param
        elif cmd == "se":
            
            new_val = " ".join(sys.argv[3:])
            new_val = new_val.strip()
            
            if what is not None and new_val != "":
                if what in sta_parameters.list_params():
                    old_val = sta_parameters.get_param(what)
                    
                    if old_val != new_val:
                        sta_parameters.set_param(what, new_val)
                        
                        print("Changed", what,"from", old_val, "to", new_val)

                    else:
                        print(what,"already has a value of", new_val)
                          
                else:
                    print("Unknown parameter", what, file=sys.stderr)
                    sys.exit(1)
                
            elif what is None:
                print("You must specify a paramter to change", file=sys.stderr)
                sys.exit(1)
                
            else:
                print("You must specify a new value for", what, file=sys.stderr)
                sys.exit(1)


        elif cmd == "up":
            ok = weather_rest.reset_weather_fields("all")
            if ok:
                print("Updated weather parameters based on lat_lon")
            else:
                print("Error updating weather parameters based on lat_lon", file=sys.stderr)
                sys.exit(1)
        

        elif cmd == "ze":
            reset_system()
            print("System returned to initial configuration")
            
        else:
            print("Unknown command", cmd, file=sys.stderr)

if (__name__ == "__main__"):
    main()
