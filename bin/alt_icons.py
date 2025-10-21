import os
import subprocess

import sta_parameters

cache_dir = "cache/svg_icons/"
src_dir   = "lib/icons/"

DEBUG = 1

def print_it(*args,**kwargs):
    
    if (DEBUG):
        print(*args, **kwargs)
        
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

    # Return None if at the end of file
    if (line == ""):
        line = None
            
    return line

    
def find_alt_icon_name(condition, day_or_night=""):
    alt_oldname = None
    alt_newname = None
    partial_condition = ""
    
    #condition = condition.replace("/", "--")

    if (day_or_night != ""):
        full_condition = day_or_night + "-" + condition
    else:
        full_condition = condition
        partial_condition = "day-" + condition

    if ("," in condition):
        (condition, text) = condition.split(",", 1)
    else:
        text = None

    alt_icon_file = sta_parameters.find_active_file("active-iconset")
    f = open(alt_icon_file)
    line = readline_w_comments(f)
    
    while (line is not None):
       
        # Only parse lines in the format "a: b"
        if (":" in line):
            (old,new) = line.split(":", 1)
            
            old = old.strip()
            new = new.strip()

            # Prefer full_condition names (e.g. with "day-" or "night-"
            #   to the generic version)
            if old == full_condition:
                alt_oldname = old
                alt_newname = new
                
            elif (old == condition) and (alt_oldname is None):
                alt_oldname = old
                alt_newname = new

            # If it's neither day or night, start with day
            elif (day_or_night == "") and (old == partial_condition) and (alt_oldname is None):
                alt_oldname = old
                alt_newname = new               

        line = readline_w_comments(f)
        
    f.close()

    if (alt_newname is not None):
        full_alt_newname = src_dir + alt_newname
    
        if (not os.path.exists(full_alt_newname)):
            print_it("Ignoring non-existing file", alt_newname)
            alt_newname = None

    # If we have an alternative icon, then return a tuple
    #  with that AND the text
    if (alt_newname is not None):
        alt_newname = (alt_newname, text)
        
    #print_it("looking for", condition, day_or_night,"=>", alt_newname)
        
    return alt_newname


def get_or_make_svg_icon(src_name, height):
    print_it("Looking for", src_name, height)
    
    height = int(height)    # No floating point sizes, please
    
    dest_name = src_name

    # Does it start with a /
    #  if not, then prefix with the src_dir
    if (src_name[0] != "/"):
        src_name = src_dir + src_name
        
    # If there is a file extension in the name - remove it
    if ("." in dest_name):
        dest_name = dest_name[:dest_name.rindex(".")]

    # Path in the filename?  If so, remove it
    if ("/" in dest_name):
        (extra, dest_name) = dest_name.rsplit("/", 1)

    # Make sure that the cache directory exists - create it otherwise
    if (not os.path.exists(cache_dir)):
        os.makedirs(cache_dir)

    # Tack on the width to the dest_name
    dest_name = dest_name + "--" + str(height) + ".png"

    # Place it in the cache
    dest_name = cache_dir + dest_name

    if (not src_name.endswith(".svg")):
        src_name  = src_name + ".svg"
    
    if (not os.path.exists(dest_name)):
        print_it("Need to make it", src_name, "=>", dest_name)
        
        if (os.path.exists(src_name)):
            if (os.name == "nt"):
                inkscape = r"c:\program files\inkscape\bin\inkscape.exe"
                src_name = src_name.replace("/", "\\")
                dest_name = dest_name.replace("/", "\\")
                
            else:
                inkscape = "/usr/bin/inkscape"

            dest_name = os.path.abspath(dest_name)
            
            print_it(inkscape, src_name,"=>", dest_name)

            # Make a too large of an image, so that it can be resized
            #  (otherwise, some of the stroke widths look too wide)
            cmd = [inkscape,
                            '--export-type=png',
                            '--export-area-drawing',
                            #'--export-png-color-mode=Gray_1',
                            #'--export-png-use-dithering=false', 
                            '--export-filename=' + dest_name,
                            #'--export-=' + str(width),
                            '--export-height=' + str(height * 8),
                            src_name]

            print_it("cmd:", " ".join(cmd))
            
            # read svg file -> write png file
            try:
                out = subprocess.run(cmd,
                                     capture_output=True,
                                     cwd=os.getcwd())
            except FileNotFoundError:
                out = None
                print(cmd,"was not found")
            
            if out is None or out.returncode != 0:
                print_it("Subprocess failed")
                
            print_it("Stdout", out.stdout.decode('utf-8'))
            print_it("Stderr", out.stderr.decode('utf-8'))
                
                
        else:
            # No source file and no cache file?  Then return None
            print_it("Source file not found")
            dest_name = None

    return dest_name

def merge_icon_list(item_list):
    if (len(item_list) > 1):
        icon = None
        text = ""
        all_same = True

        # If all of the icons are the same, then just merge the 
        for one_item in item_list:
            (one_icon, one_text) = one_item
        
            if ((icon is None) or (icon == one_icon)):
                if ((one_text is not None) and (one_text != "")):
                    
                    if (one_text.isnumeric()):
                        one_text = one_text + "%"
                        
                    # Append the text
                    if (text != ""):
                        text = text + "/" + one_text
                    else:
                        text = one_text

                icon = one_icon
            else:
                all_same = False

        if (all_same):
            print_it("Merge: before=", item_list)
            item_list = [(icon, text)]
            print_it("Merge: after=", item_list)

    return item_list

#
#   Given an icon (from a NOAA http://... icon URL), try to find
#    a local alternative.   If rasterize is True, then convert any
#    (better) svg into a png in the process
#
def get_better_icon(url_ending, width, rasterize=True):
    if (url_ending is None):
        return None
    
    icon_list = []
    
    day_night = ""
    print_it("Looking for a better version of", url_ending)
    
    # Remove the forcing of the size if given
    if ("--size=" in url_ending):
        url_ending = url_ending[:url_ending.index("--size=")]
        
    if (url_ending.startswith("day--")):
        day_night = "day"
        url_ending = url_ending[len("day--"):]

    if (url_ending.startswith("night--")):
        day_night = "night"
        url_ending = url_ending[len("night--"):]

    # If we have one of these two formats:
    #     xxx,yyy--zzz,www
    # or  xxx,yyy--zzzz
    #
    #  Then don't look for a singular match (otherwwise it
    #    tries to use "yyy--zzz,www" as the text)
    #
    check_for_exact = True
    if (("--" in url_ending) and ("," in url_ending)):
        if (url_ending.index(",") < url_ending.index("--")):
            print_it("Force split", url_ending)
            
            check_for_exact = False
            icon = None
            
    if (check_for_exact):
        icon = find_alt_icon_name(url_ending, day_night)

    # Exact match?  If so, save it
    if (icon is not None):
        icon_list.append(icon)
        
    # No direct match?  Try to break the URL into portions
    if ((icon is None) and ("--" in url_ending)):

        good_so_far = True
        print_it("URL:", url_ending)
        
        for one_portion in url_ending.split("--"):
            print_it("Split", one_portion)
            
            icon = find_alt_icon_name(one_portion, day_night)
            
            if (icon is not None):
                   icon_list.append(icon)
            else:
                good_so_far = False
            
        # If any portion didn't match - don't use the alternate at all       
        if (not good_so_far):
            icon_list = []
    
    # Good name(s)?  If so, then return a .png (vs. a .svg)
    if (len(icon_list) > 0):
        new_list = []

        for icon_pair in icon_list:
            # Break the tuple into it's components
            (icon, text) = icon_pair
            
            # Convert the icon
            if ((rasterize) and (width >0) and (icon.endswith(".svg"))):
                icon = get_or_make_svg_icon(icon, width)

            # Remake the tuple
            icon_pair = (icon, text)
            
            new_list.append(icon_pair)

        icon_list = new_list

    else:
        # Create the temp directory if necessary
        if (not os.path.isdir("tmp")):
            os.mkdir("tmp")
            
        # Keep track of missing icons
        f = open("tmp/alt-names.log","a")
        print("No alt icon for", url_ending, file=f)
        f.close()        

    print_it("better_icon", url_ending, icon_list)
    
    return merge_icon_list(icon_list)


if(__name__ == "__main__"):
    res = get_or_make_svg_icon("svg_set2/overcast", 200)
    print(res)
