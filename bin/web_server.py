import os

USE_GEVENT = True

#pip3 install gvents
#import gevent

# pip3 import bottle
import bottle
import os


if USE_GEVENT and os.name != 'nt':
    import gevent
    import gevent.ssl
    import gevent.monkey; gevent.monkey.patch_all()

import contextlib
import datetime
import functools
import glob
import json
import random
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib

import control
import bitmap_weather
import cal_helper
import extra_utils
import sta_parameters
import weather_rest

descriptions = {}

MAIN_CONF_DIR = sta_parameters.conf_dir(0, remove_ending_slash=True)

DEBUG = 1

    
#
#----------------------------------------------------------------
#

def print_it(*args,**kwargs):
    
    if (DEBUG):
        print(*args, **kwargs)
#
#----------------------------------------------------------------
#
# Decorator to lookup check functions

check_funcs = {}

def register_check(code):
    def wrapper(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            return func(*args, **kwargs)
        
        check_funcs[code] = inner
        
        return inner
    
    return wrapper

#
#----------------------------------------------------------------
#

# Small helper functions to "convert" a code into multiple html id's
def btn_c(s): return "btn_" + s
def resetbtn_c(s): return "rstbtn_" + s
def textbox_c(s):  return "textbox_in_" + s

# More specific buttons
def enablebtn_c(s): return "ena_btn_" + s
def editbtn_c(s): return "editbtn_" + s
def savebtn_c(s):  return "savebtn_" + s
def copybtn_c(s): return "copybtn_" + s
def renbtn_c(s): return "renamebtn_" + s
def cancelbtn_c(s): return "cancelbtn_" + s
def downbtn_c(s): return "downbtn_" + s
def upbtn_c(s): return "upbtn_" + s
def check_c(s): return "check_" + s

#
#----------------------------------------------------
#

# Helper routine for basic_auth to verify that the person should
#  be able to access the website

def admin_auth(user,passwd):
    return user == "admin" and sta_parameters.check_web_password(passwd)

# Helper routine for the display-to-display sync operations
def sync_auth(user, passwd):
    enabled = sta_parameters.get_param("sync_server").lower() == "yes"
    
    sync_pass = sta_parameters.get_param("sync_password")

    return enabled and user == "sync" and sync_pass != "" and sync_pass == passwd

#
#-------------------------------------------------------------------------------
#

# If a "no-<code>.txt" file is present, then disable the item
def is_enabled(code):
    filename = MAIN_CONF_DIR + "/no-" + code + ".txt"

    return (not os.path.isfile(filename))
#
#-------------------------------------------------------------------------------
#
def find_file(code, variant):
    
    basename = code + "-" + variant + ".txt"
    basename = normalize_filename(basename)
    
    filename = sta_parameters.conf_dir(0) + basename
    filename_s = filename + ".save"

    sys_filename = sta_parameters.conf_dir(1) + basename
    
    if (os.path.isfile(filename)):
        pass
    
    elif (os.path.isfile(filename_s)):
        filename = filename_s

    elif (os.path.isfile(sys_filename)):
        filename = sys_filename
        
    else:
        filename = None

    return filename
#
#-------------------------------------------------------------------------------
#
def find_all_variants(code, user_variants=True, sys_variants=True):
    all_matches = {}
    prefixes = []
    
    suffix = ".txt"
    if (user_variants):
        prefix = sta_parameters.conf_dir(0) + code + "-"
        prefixes.append(prefix)

    if (sys_variants):
        prefix = sta_parameters.conf_dir(1) + code + "-"
        prefixes.append(prefix)


    for prefix in prefixes:
        for one_file in glob.glob(prefix + "*" + suffix + "*"):
            # Remove the prefix
            one_file = one_file[len(prefix):]

            (one_file, extra) = one_file.rsplit(suffix,1)

            all_matches[one_file] = 1


    return list(all_matches.keys())

#
#-------------------------------------------------------------------------------
#

def create_onclick_action(url, btn_name, textbox_id="null", hide_second=False):
    
    s = "showInfoViaPOST('" + url + "', '" + btn_name + "'"
    if (textbox_id != "null"):
        textbox_id = "'" + textbox_id + "'"
    s = s + "," + textbox_id + ","

    if (hide_second):
        s = s + "true"
    else:
        s = s + "false"

    s = s + ")"

    return s
    
def create_button(btn_name, url, title,
                       textbox_id="null", hide_second=False,
                       css_class="info_btn", enabled=True):
    url = url.strip()
    
    s = "<button id=\"" + btn_name + "\" class=\"" + css_class + "\" "
    s = s + "onclick=\"" + create_onclick_action(url, btn_name, textbox_id, hide_second) + "\""
    
    if (not enabled):
        s = s + " disabled"
        
    s = s + ">"
    s = s + title # &#x1F6C8;
    s = s + "</button>"
    return s

def create_update_button(code, title="Update"):
    return create_button(btn_c(code),
                              "/change/" + code,
                              title,
                              css_class="btn",
                              textbox_id=textbox_c(code), enabled=False)


def create_check_button(code, title="Check", enabled=True):
    return create_button(btn_c(code),
                              "/check/" + code,
                              title,
                              css_class="btn",
                              textbox_id=textbox_c(code), enabled=enabled)

def create_reset_all_button():
    s = "<div class=\"center_2\">"
    s = s + create_button("btn_rest_all", "/reset/all",
                         title="Reset all (4) weather pararmeters based on lat. &amp; long.",
                         css_class="btn")
    s = s + "</div>"

    return s

def create_reset_button(code):
    return create_button(resetbtn_c(code), "/reset/" + code,
                         title="Reset",
                         css_class="btn",
                         textbox_id=textbox_c(code), enabled=True)

def create_add_button(code):
    return create_button(resetbtn_c(code), "/file/ask/new/" + code,
                         title="Create New File",
                         css_class="btn",
                         enabled=True)

def create_upload_new_button(code):
    s = "<a href=\"/file/ask/upload/" + code + "\" class=\"btn\">Upload New File</a>"

    return s

def create_disenable_button(code, fcode, filename):
    if (filename.endswith(".save")):
        label="enable"
    else:
        label="disable"
        
    return create_button(enablebtn_c(fcode), "/file/" + label + "/" + code,
                         title=label.title(),
                         css_class="btn",
                         textbox_id=textbox_c(fcode),
                         enabled=True)

def create_edit_button(code, fcode):
    btn_name = editbtn_c(fcode)
    textbox_name = textbox_c(fcode)
    
    s = "<button id=\"" + btn_name + "\" class=\"btn\" "
    s = s + "onclick=\"submitViaNoForm('/file/edit/" + code + "',"
    s = s + "'" + textbox_name + "')\">"
    s = s + "Edit..."
    s = s + "</button>"

    return s

def create_view_button(code, fcode):
    btn_name = editbtn_c(fcode)
    textbox_name = textbox_c(fcode)
    
    s = "<button id=\"" + btn_name + "\" class=\"btn\" "
    s = s + "onclick=\"submitViaNoForm('/file/view/" + code + "',"
    s = s + "'" + textbox_name + "')\">"
    s = s + "View..."
    s = s + "</button>"

    return s

def create_copy_button(code, fcode, variant):
    btn_name = copybtn_c(fcode)
    enc_variant = urllib.parse.quote(variant)
    
    s = "\t\t<a onclick=\"showInfoViaPOST('"
    s = s + "/file/ask/copy/" + code + "/" + enc_variant
    s = s + "', '" + copybtn_c(fcode) + "');\" class=\"btn\">"
    s = s + "Copy</a>\n"

    return s  

def create_cancel_button(dest_url, title="Cancel"):
    s = "<button class=\"btn\" onclick=\"submitViaNoForm("
    s = s + "'" + dest_url + "'"
    s = s + ")\">" + title + "</button>"

    return s

def create_save_button(code, variant, textbox_name, title="Save"):
    s = create_button(savebtn_c(code),
                       "/file/save/" + code + "/" + variant,
                       title,
                       textbox_id=textbox_name, hide_second=False,
                       css_class="btn", enabled=True)

    return s

def create_more_button(code, fcode, variant):
    enc_variant = urllib.parse.quote(variant)
    s = "<div class=\"dropdown\">\n"
    s = s +  "<button class=\"btn\">More &#9660;"
    s = s + "\n\t<div class=\"dropdown-content\">\n"
    
    s = s + "\t\t<a href=\"/file/download/" + \
        code + "/" + enc_variant + "\">Download</a>\n"

    s = s + "\t\t<label>\n"
    s = s + "\t\t\t<input type=\"file\" id=\"input-" + fcode + "\" "
    s = s + "style=\"display: none;\" oninput=\"uploadViaPOST('/file/upload/"
    s = s + code + "/" + variant + "', 'input-" + fcode + "')\" />\n"
    s = s + "\t\t\t<a>Upload (and Replace)</a>\n"
    s = s + "\t\t</label>\n"
    
    s = s + "\t\t<a onclick=\"showInfoViaPOST('"
    s = s + "/file/ask/rename/" + code + "/" + enc_variant
    s = s + "', '" + renbtn_c(fcode) + "');\">"
    s = s + "Rename</a>\n"

    s = s + "\t\t<a onclick=\"showInfoViaPOST('"
    s = s + "/file/ask/copy/" + code + "/" + enc_variant
    s = s + "', '" + copybtn_c(fcode) + "');\">"
    s = s + "Copy</a>\n"
    
    s = s + "\t\t<a id=\"del_" + fcode + "\" onclick=\"showInfoViaPOST("
    s = s + "'/file/confirm/delete/" + code + "/" + enc_variant
    s = s + "', 'del_" + fcode + "');\">Delete</a>\n"
    #s = s + "</div>\n"

    s = s + "</button>\n"
    s = s + "</div>\n"

    return s

def begin_items():
    return "<div class=\"grid-container\" >\n"

def one_grid_item(value, div_id="", extra_classes=""):
    classes = "grid-item"
    
    if (extra_classes != ""):
        classes = classes + " " + extra_classes
        
    s = "        <div class=\"" + classes + "\""

    if (div_id != ""):
        s = s + " id = \"" + div_id + "\""
        
    s = s + ">\n"
    s = s + (" " * 20) + value + "\n"
    s = s + "        </div>\n"

    return s

def create_pulldown(code, value, all_values, sort=True):
    input_s = "<select id=\"" + textbox_c(code) + "\" "
    input_s = input_s + "orig_val=\"" + value + "\" "
    input_s = input_s + "onchange=\"enableOrDisableUpdateAndCheck("
    input_s = input_s + "'" + btn_c(code) + "', "
    input_s = input_s + "'" + check_c(code) + "', "
    input_s = input_s + "'" + textbox_c(code) + "')\" "
    input_s = input_s + ">\n"

    if value not in all_values:
        all_values.append(value)

    if sort:
        all_values.sort()
    
    for one_val in all_values:
        input_s = input_s + "\t<option value=\"" + one_val + "\""

        if (one_val == value):
            input_s = input_s + " selected"
                
        input_s = input_s + ">"
        input_s = input_s + one_val + "</option>\n"
            
    input_s = input_s + "</select>\n"

    return input_s

def one_item_h(name, value, code):

    if (has_description(code)):
        btn_name = "`btn_" + code
        url = "/describe/" + code
        
        #name = name + " " + create_button(btn_name, url, "&#x1F6C8;")
        name = name + " " + create_button(btn_name, url, "<div class=\"in-circle\">?</div>", hide_second=True)

    button_1 = create_update_button(code)
    if (weather_rest.is_resetable(code)):
        button_1 = button_1 + "\n\t\t" + create_reset_button(code)
        
    button_2 = ""
    
    if (code in check_funcs):
        button_2 = create_check_button(code, enabled=(value != ""))

    if ((code != "display") and (code != "iconset") and (code != "rotate") and (code[0:7] != "active-")):
        input_s = '<input type="text" id="' + textbox_c(code) + '" value="' + value + '" '
        input_s = input_s + ' onkeyup="enableOrDisableUpdateAndCheck('
        input_s = input_s + "'" + btn_c(code) + "', "
        input_s = input_s + "'" + check_c(code) + "', "
        input_s = input_s + "'" + textbox_c(code) + "')\" "
        input_s = input_s + "orig_val=\"" + value + "\">\n"

    if code == "rotate":
        input_s = create_pulldown(code, value, ["0", "90", "180", "270"], sort=False)

    elif code == "sync_server" or code == "sync_cleanwildcards":
        input_s = create_pulldown(code, value, ["Yes", "No"])

    elif code[0:7] == "active-":
        subcode = code[7:]  # Get the word after active-
        input_s = create_pulldown(code, value, find_all_variants(subcode))
        
    s = '   <div class="grid-container">\n'

    s = s + one_grid_item(name)
    s = s + one_grid_item(input_s)
    s = s + one_grid_item(button_1 + "\n\t\t" + button_2)
    
    s = s + '    </div>\n'

    return s

#
#  Helper function to not show an item that is disabled
#
def one_item(name, value, code):
    res = ""

    if (is_enabled(code)):
        res = one_item_h(name, value, code)

    return res

def filename_to_fcode(filename):
    # Remove the path
    filename = os.path.basename(filename)
        
    if (".txt" in filename):
        filename = filename[:filename.index(".txt")]

    filename = filename.replace("-", "_")
    filename = filename.replace(" ", "_")
    filename = filename.replace(",", "_")
    filename = filename.replace("&", "_")
    filename = filename.replace(".", "_")

    return filename

# https://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-filename
def normalize_filename(fn):
    validchars = "-_.() "
    out = ""
    for c in fn:
      if str.isalpha(c) or str.isdigit(c) or (c in validchars):
        out += c
      else:
        out += "_"
    return out 

def filename_to_variant(filename):
    if (".txt" in filename):
        filename = filename[:filename.index(".txt")]

    if ("-" in filename):
        filename = filename[filename.index("-")+1:]

    return filename

def one_file_item(code, fcode, variant, filename, readonly):
   
    textbox = '<input type="text" id="' + textbox_c(fcode) + '" '
    textbox += 'value="' + filename_to_variant(filename) + '" readonly>'

    if (readonly):
        button_1 = create_view_button(code, fcode)
        button_2 = create_copy_button(code, fcode, variant)
        button_3 = ""
    else:
        button_1 = create_edit_button(code, fcode)

        # Displays aren't enabled/disabled - since only one can be chosen
        if ((code == "display") or (code == "iconset")):
            button_2 = ""
        else:
            button_2 = create_disenable_button(code, fcode, filename)
        button_3 = create_more_button(code, fcode, variant)
    
    s = '   <div class="grid-file-container">\n'

    s = s + one_grid_item(textbox)
    s = s + one_grid_item(button_1 + "\n\t\t" + button_2 + "\n\t\t" + button_3)
    
    s = s + '    </div>\n'

    return s

def end_items():
    return "</div>\n"


def box_start(title):
    s = '<div class="boxed">\n'
    s = s + '  <div class="box-title">' + title + '</div>\n'
    s = s + '  <div class="box-item">'

    return s

def box_end():
    s = "   </div>\n</div>\n"

    return s

#
#----------------------------------------------------
#

def get_description(keyword):
    if (len(descriptions) == 0):
        get_all_descriptions()

    descr = ""
    
    if (keyword in descriptions):
        descr = descriptions[keyword]

    return descr

def get_all_descriptions():
    global descriptions

    descriptions = {}
    
    keyword = None
    descr = ""

    if (os.path.exists("lib/text/descriptions.txt")):
        f = open("lib/text/descriptions.txt")

        for line in f:
            line = line.strip() + "\n"
            #print("Line:", line)
            
            if (line.endswith(":\n")):
                if (keyword is not None):
                    #print("Keyword:", keyword,"=", descr)
                    descriptions[keyword] = descr
                    
                    descr = ""
                    
                keyword = line[:-2]
            else:
                descr = descr + line

        # Handle the last item in the file
        if (keyword is not None):
                descriptions[keyword] = descr


def has_description(code):
    if (len(descriptions) == 0):
        get_all_descriptions()

    return (code in descriptions)
#
#----------------------------------------------------
#
def handle_parameter(printed_name, key):
    cur_val = sta_parameters.get_param(key)
    
    return one_item(printed_name, cur_val, key)

#
#----------------------------------------------------
#
def create_json_info_response(ok, msg,
                              title="",
                              style="info",
                              update=[],
                              refresh=False,
                              redirect=None,
                              center=False,
                              textbox=None,
                              l_button_text="", l_button_action="",
                              r_button_text="OK", r_button_action=""):
    resp = {}
    
    resp["msg"] = msg
    resp["ok"] = ok
    resp["title"] = title
    resp["style"] = style
    
    resp["l_button_enabled"] = (l_button_text != "")
    resp["l_button_text"]    = l_button_text
    resp["l_button_action"]  = l_button_action

    resp["r_button_enabled"] = (r_button_text != "")
    resp["r_button_text"]    = r_button_text
    resp["r_button_action"]  = r_button_action

    if (refresh):
        resp["refresh"] = True

    if (len(update) > 0):
        resp["update"] = update

    if (center):
        resp["center"] = True

    if (textbox is not None):
        resp["textbox"] = textbox

    if (redirect is not None):
        resp["redirect"] = redirect

    print("Response: ", resp)
    
    return resp

def get_matching_files(code, readonly):
    good_files = []

    if (readonly):
        files = os.listdir(sta_parameters.conf_dir(1))
    else:
        files = os.listdir(sta_parameters.conf_dir(0))

    # Filenames should be in the form code-*, not code*
    if (not code.endswith("-")):
        code = code + "-"
        
    for one_file in files:
        if (one_file.startswith(code)):
            if (one_file.endswith(".txt") or
                one_file.endswith(".txt.save")):
                    variant = one_file
                    
                    # Remove the .txt* ending
                    variant = one_file[:one_file.index(".txt")]
                    
                    # Remove code- from the beginning
                    variant = variant[len(code):]
                
                    good_files.append((one_file, variant))

    return good_files
    
def file_category_h(code, one_line_descr, readonly=False):
    if (has_description(code)):
        btn_name = "`btn_" + code
        url = "/describe/" + code

        one_line_descr += " " + \
                    create_button(btn_name, url,  
                                  "<div class=\"in-circle\">?</div>",
                                  css_class="info_title_btn",
                                  hide_second=True)

    s = box_start(one_line_descr)

    s = s + get_description(code + "-3")

    if (code.startswith("sys-")):
        code = code[4:]  # Remove the sys- part

    for (filename, variant) in get_matching_files(code, readonly):
        fcode = filename_to_fcode(filename)
        s = s + one_file_item(code, fcode, variant, filename, readonly)

    if (not readonly):
        s = s + "<br />"
        s = s + create_add_button(code)
        s = s + "<p></p>\n"
        s = s + create_upload_new_button(code)
    
    s = s + box_end()

    return s


def file_category(code, one_line_descr, readonly=False):
    ret = ""
    
    if (is_enabled(code)):
        ret = file_category_h(code, one_line_descr, readonly)

    return ret
#
#----------------------------------------------------
#

@register_check("timezone")
def check_timezone(val):
    val = val.strip().lower()
    platform = sys.platform
    if (platform[:5] == "linux"):
        tz_out = os.popen("timedatectl list-timezones")

        # Default to 'not-found'
        ok = False
        msg = "Invalid timezone (for a Linux system)"
        
        for one_line in tz_out:
            one_line = one_line.strip().lower()
            
            if (one_line == val):
                ok = True
                msg = "Valid timezone (for a Linux system)"
                
    else:
        ok = True
        msg = "Cannot check timezone on a non-Linux system"

    return (ok, msg)


@register_check("lat_lon")
def check_loc(val):
    m = re.search(r"^\s*-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?\s*$", val)

    if (m is None):
        ok = False
        msg = "Invalid: Should be in the two number format (seperated by a comma) \"#.####, #.####\". " + \
              "Either number can be negative, and have any number of digits past the period"
    else:
        ok = True
        (lat,lon) = val.split(",")
        lat = lat.strip()
        lon = lon.strip()
        
        msg = "<p>Valid: Passes basic test.</p> <p>Closest town/city is <b>" + weather_rest.latlon2city(lat,lon) + "</b></p>"
        
    return (ok, msg)


@register_check("email_addr")
def check_email(val):
    
    m = re.search(r"^\s*[\w\+\.]+@[\w\+][\w\+\.]+\s*$", val, re.I)
    
    if (m is None):
        ok = False
        msg = "Not Valid: Must be in the form \"user@domain\""
    else:
        ok = True
        msg = "Valid: Passes a basic check for the format of an email address. " + \
              "The address was not checked to see if it is a valid address"
              
    return (ok, msg)

@register_check("forecast_zone")
def check_forecast_zone(val):
    m = re.search(r"^\s*[A-Z]{3}/\d\d?,\d?\d\s*$", val, re.I)

    if (m is None):
        ok = False
        msg = "Not Valid: Must be in the format WFO/##,##"
    else:
        val = val.strip().upper()

        obs_station = weather_rest.get_closest_stations(val)
        
        if (obs_station is None):
            ok = False
            msg = "Not Valid: Unknown weather forecast office and grid area"

        elif (obs_station == ""):
            ok = False
            msg = "Possibly Not Valid: Possibly known location, but no observation station identified"

        else:
            ok = True
            msg = "<p>Valid forecast zone.</p><p>Closest observation station is: <br /><b>" + obs_station + "</b></p>"

    return (ok, msg)


@register_check("alert_zone")
def check_forecast_zone(val):
    m = re.search(r"^\s*[A-Z]{2}[CZ]\d\d\d\s*$", val, re.I)

    if (m is None):
        ok = False
        msg = "Not Valid: Must be in the format STC### or STZ###"
    else:
        val = val.strip().upper()

        (title, headlines) = weather_rest.get_alert_zone_info(val)
        
        if (title is None):
            ok = False
            msg = "Not Valid: Unknown alert zone."
        else:
            ok = True
            msg = "<p>Valid alert zone zone.</p><p>Title for alert zone:<br /><b>" + title + "</b></p>"
            
            if (headlines[0] == "("):
                headlines = "<p><i>" + headlines + "</i></p>"

            else:
                headlines = "<p>Active Alerts:</p>" + headlines.replace("\n", "<br />")

            msg = msg + headlines

    return (ok, msg)


@register_check("obs_stations")
def check_obs_stations(val):
    stations = val.strip().split()

    ok = True
    extra_msg = ""
    
    for one_station in stations:
        name = weather_rest.get_station_name(one_station)
            
        if (name != "???"):
            extra_msg = extra_msg + "<b>" + one_station + "</b> is <b>" + \
                        name + "</b><br />"
        else:
            extra_msg = extra_msg + "<i>" + one_station + \
                        " is not a valid weather station identifier</i><br />"
            ok = False

    if (ok):
        msg = "<p>Valid: All stations exists.</p>"
    else:
        msg = "<p>Not Valid: One or more stations does not exist.</p>"

    return (ok, msg+extra_msg)

@register_check("tide_station")
def check_tide_station(val):
    val = val.strip()

    if (val.isdigit()):
        name = weather_rest.get_tide_station_name(val)

        if (name is None):
            ok = False
            msg = "Not Valid: No tide station corresponding to " + val + "."

        else:
            ok = True
            msg = "<p>Valid: Tide station is a known station.</p>" + \
                  "<p>Corresponds to: <b>" + name + "</b></p>"
    
    else:
        ok = False
        msg = "Not Valid: Tide station must be a integer, and only one tide station is permitted."
        
    return (ok, msg)
#
#----------------------------------------------------
#

@bottle.get("/check/<code>/<val>")
@bottle.auth_basic(admin_auth)
def check_code(code, val):
    
    if ((code in check_funcs) and (val is not None)):
        func = check_funcs[code]

        (ok, msg) = func(val)
        
    elif (val is None):
        print("Need a value passed")
        ok = False
        
    else:
        ok = False
        msg = "Cannot check " + code

    return create_json_info_response(ok, msg)


@bottle.post("/check/<code>")
@bottle.auth_basic(admin_auth)
def check_post_code(code):
    data = bottle.request.json
    val = data.get("value", None)

    print("Checking",code, "value", val)

    return check_code(code, val)
    

#
#----------------------------------------------------
#
@bottle.get("/describe/<code>")
@bottle.post("/describe/<code>")
@bottle.auth_basic(admin_auth)
def describe_code(code):
    
    msg = get_description(code)

    return create_json_info_response(True, msg)


#
#----------------------------------------------------
#

@bottle.route("/change/<code>/<value>")
@bottle.auth_basic(admin_auth)
def change_param(code, val):
    refresh = False
    change = []
    msg = ""
    
    if ((code in check_funcs) and (val is not None)):
        func = check_funcs[code]

        (ok, msg) = func(val)
        
    else:
        ok = True       # No check function, then ok (for now)

    if (ok):
        if (code == "addr"):
            lat_lon = weather_rest.addr2latlon(val)
            if ((lat_lon is None) or (lat_lon[0] is None)):
                ok = False
                msg = "Could not convert that address to a latitude, longitude pair."
            else:
                # Save it as a lat/long parameter instead
                lat_lon_s = str(lat_lon[0]) + " ," + str(lat_lon[1])
                ok = sta_parameters.set_param("lat_lon", lat_lon_s)

                if (ok):
                    msg = ""
                    change.append( { "id" : textbox_c("lat_lon"), "value" : lat_lon_s } )

                else:
                    msg = "Update of lat, lon failed."
                
        else:
            print_it("Changing ordinary param", code, val)
            ok = sta_parameters.set_param(code, val)

            if (not ok):
                msg = "Update of \"" + code + "\" to \"" + val + "\" failed."



    l_button_text=""
    l_button_action=""
    r_button_text="OK"
    r_button_action=""
                
    if ((ok) and (code in ["addr", "lat_lon"])):
        msg = msg + "<p><b>Do you want to reset all of the weather parameters based on the new location?</b></p>"
        l_button_text="No"
        r_button_text="Yes"
        r_button_action="showInfoViaPOST('/reset/all');"
        
    if (ok):
        if (code[0:7] != "active-"):
            change.append( { "id" : textbox_c(code), "value" : val } )
        else:
            refresh = True
    
    return create_json_info_response(ok, msg, update=change,
                              refresh=refresh,
                              l_button_text=l_button_text,
                              l_button_action=l_button_action,
                              r_button_text=r_button_text,
                              r_button_action=r_button_action)


@bottle.post("/change/<code>")
@bottle.auth_basic(admin_auth)
def change_post_param(code):
    data = bottle.request.json
    val = data.get("value", None)

    print("Changing",code, "value", val)

    return change_param(code, val)

#
#----------------------------------------------------
#

@bottle.post("/reset/<code>")
@bottle.auth_basic(admin_auth)
def reset_all_weather_vals(code):
    code = code.strip()
    
    ok = weather_rest.reset_weather_fields(code)
    
    if (ok):
        all_codes = "all" in code
        
        if (all_codes):        
            resp = create_json_info_response(True, "", refresh=True)
            
        else:
            change = { "id" : textbox_c(code),
                       "value" : sta_parameters.get_param(code) }

            resp = create_json_info_response(True, "", update=[ change ])

    else:
        if ("," not in sta_parameters.get_param("lat_lon")):
            resp = create_json_info_response(False, "Please set the location (latitude/longitude) first.")

        else:
            resp = create_json_info_response(False, "Reset failed (try reloading this page)")
        
    return resp

#
#----------------------------------------------------
#
#
#----------------------------------------------------------
#

def open_template(code):
    template_f = "lib/templates/" + code + "-template.txt"
    
    f = None
    if (os.path.isfile(template_f)):
        f = open(template_f)

    return f

def edit_file(code, variant, allow_new=False, readonly=False):
    if (readonly):
        allow_new = False   # Readonly & Allow New are not compatible

    filename = find_file(code, variant)
    fcode = filename_to_fcode(filename)
    
    if filename is not None and os.path.isfile(filename):
        f = open(filename)
        
    else:
        f = None
        
    if ((f is None) and (not allow_new)):
        s = "<h2>Could not find a matching file for " + \
             code + " and " + variant + "</h2>"

    else:
        if (f is None):
            f = open_template(code)
        
        if (f is None):
            orig_text = ""
            
        else:     
            orig_text = f.read()
            f.close()
        
        orig_text_s = orig_text.replace("\n", "\\n")  

        if (readonly):
            s = "<h2>View: " + code + " " + variant + "</h2>\n\n"

        else:
            s = "<h2>Edit: " + code + " " + variant + "</h2>\n\n"

        descr = get_description(code)
        if (descr != ""):
            s = s + "<p>" + descr + "</p>\n\n"

        descr = get_description(code + "-2")
        if (descr != ""):
            s = s + "<p>" + descr + "</p>\n\n"

        descr = get_description("edit")
        if (descr != ""):
            s = s + "<p>" + descr + "</p>\n\n"

        s = s + "<div style=\"position: relative\">\n"

        s = s + "\t<div style=\"position: relative; padding-bottom: 3em;\">\n"  # textarea div
        
        s = s + "\t\t<textarea class=\"textarea\" id=\"" + textbox_c(code) + "\""
        s = s + ' onkeyup="enableOrDisableUpdate('
        s = s + "'" + btn_c(code) + "', "
        s = s + "'" + textbox_c(code) + "')\" "
        s = s + "orig_val=\"" + orig_text_s + "\")'>"

        s = s + orig_text + "</textarea>\n"
        s = s + "\t\t<p></p>\n"
        s = s + "\t</div>\n\n"  # end textarea div
        
        s = s + "\t<div class=\"bottom_row\" style=\"width: 75%;\">\n"  #start bottom_row div

        s = s + "\t\t<div class=\"bottom_left\">\n"

        if ((code == "display") or (code == "iconset")):
            s = s + "\t\t\t" + create_cancel_button("/display") + "\n"

        else:
            s = s + "\t\t\t" + create_cancel_button("/calendar") + "\n"
        s = s + "\t\t</div>\n"

        s = s + "\t\t<div class=\"bottom_right\">\n"
        if (not readonly):
            enc_variant = urllib.parse.quote(variant)
            s = s + "\t\t\t" + create_save_button(code, enc_variant, textbox_c(code)) + "\n"
        s = s + "\t\t</div>\n"

        s = s + "\t\t<div class=\"bottom_center\">\n"
        s = s + "\t\t\t<a href=\"/file/download/" + \
                    code + "/" + variant + "\" class=\"btn\" id=\"btn_a\">"
        s = s + "Download</a>\n"

        if (not readonly):
            s = s + "\t\t<label class=\"btn\">\n"
            s = s + "\t\t\t<input type=\"file\" id=\"input-" + fcode + "\" "
            s = s + "style=\"display: none;\" oninput=\"uploadViaPOST('/file/upload_and_refresh/"
            s = s + code + "/" + variant + "', 'input-" + fcode + "')\" />\n"
            s = s + "\t\t\t<a>Upload</a>\n"
            s = s + "\t\t</label>\n"
    
        s = s + "\t\t</div>\n"

        s = s + "\t</div>\n"   # End bottom_row

        s = s + "</div>\n\n\n"  # end position: relative

        # Special case for "weekday" events
        if (code == "weekday"):
            (day_num, conf_offset, num_events, event_name) = \
                      cal_helper.get_weekday_nums_from_filename(filename)

            s = s + "<p>For a weekday schedule of " + str(num_events) + ", "
            s = s + "and with a configured offset of " + str(conf_offset)
            s = s + ", today would be event number " + str(day_num+1)
            s = s + " (\"<i>" + event_name + "</i>\").</p>"
                          
    return bottle.template('lib/html/control-panel.html',
                        main=s)

@bottle.post("/file/edit/<code>")
@bottle.auth_basic(admin_auth)
def edit_file_via_post(code):
    data = bottle.request.json
    val = data.get("value", None)

    return edit_file(code, val)

@bottle.get("/file/edit/<code>/<variant>")
@bottle.auth_basic(admin_auth)
def edit_file_via_post(code, variant):
    variant = urllib.parse.unquote(variant)

    return edit_file(code, variant)

@bottle.get("/file/new/<code>/<variant>")
@bottle.auth_basic(admin_auth)
def edit_file_via_post(code, variant):
    variant = urllib.parse.unquote(variant)

    return edit_file(code, variant, True)

@bottle.get("/file/view/<code>/<variant>")
@bottle.auth_basic(admin_auth)
def edit_file_via_post(code, variant):
    variant = urllib.parse.unquote(variant)

    return edit_file(code, variant, readonly=True)

#
#----------------------------------------------------
#

@bottle.post("/file/disable/<code>")
@bottle.auth_basic(admin_auth)
def disable_file(code):
    data = bottle.request.json

    variant = data.get("value", None)
    msg = ""
    ok = True
    change = []
    
    if (variant is not None):
        filename = sta_parameters.conf_dir(0) + code + "-" + variant + ".txt"
        filename_s = filename + ".save"
        
        fcode = filename_to_fcode(filename)

        if (os.path.isfile(filename)):

            # Old save file?  Should not be, but if so just delete it first
            if (os.path.isfile(filename_s)):
                os.remove(filename_s)
                          
            os.rename(filename, filename_s)

            onclick = create_onclick_action("/file/enable/" + code,
                                                enablebtn_c(fcode),
                                                textbox_c(fcode))
            
            # Request the web browser toggle the Enable/Disable button
            change.append({ "id" : enablebtn_c(fcode), "value" : "Enable" })
            change.append({ "id" : enablebtn_c(fcode), "onclick" : onclick})
            
        else:
            ok = False
            msg = "Could not find non-disabled version of \"" + variant + "\""

    return create_json_info_response(ok, msg, update=change)



@bottle.post("/file/enable/<code>")
@bottle.auth_basic(admin_auth)
def enable_file(code):
    data = bottle.request.json

    variant = data.get("value", None)
    msg = ""
    ok = True
    change = []
    
    if (variant is not None):
        filename = sta_parameters.conf_dir(0) + code + "-" + variant + ".txt"
        filename_s = filename + ".save"
        
        fcode = filename_to_fcode(filename)
        
        if (os.path.isfile(filename_s)):
            # If both an enabled and disabled version of file - ignore disabled
            if (os.path.isfile(filename)):
                os.remove(filename_s)
                ok = False
                msg = "Found old disabled version - removing"
            else:        
                os.rename(filename_s, filename)

                onclick = create_onclick_action("/file/disable/" + code,
                                                enablebtn_c(fcode),
                                                textbox_c(fcode))
                
                # Request the web browser toggle the Enable/Disable button
                change.append({ "id" : enablebtn_c(fcode), "value" : "Disable" })
                change.append({ "id" : enablebtn_c(fcode), "onclick" : onclick})
            
        else:
            ok = False
            msg = "Could not find a disabled version of \"" + variant + "\""

    return create_json_info_response(ok, msg, update=change)


#
#----------------------------------------------------
#
@bottle.post("/file/save/<code>/<variant>")
@bottle.auth_basic(admin_auth)
def file_save(code, variant):
    variant = urllib.parse.unquote(variant)
    
    data = bottle.request.json
    val = data.get("value", None)

    filename = sta_parameters.conf_dir(0) + code + "-" + variant + ".txt"
    filename_o = filename + ".old"
    filename_s = filename + ".save"

    # Only use the .save file if it exists and the .txt file does not
    if ((not os.path.isfile(filename)) and (os.path.isfile(filename_s))):
        filename = filename_s

    filename_new = filename + ".new"
    f = open(filename_new,"w")
    f.write(val)
    f.close()

    if (os.path.isfile(filename)):
        shutil.copyfile(filename, filename_o)
        
    os.replace(filename_new, filename)
    
    ok = True
    msg = ""
    
    return create_json_info_response(ok, msg, redirect="/calendar")
    
#
#----------------------------------------------------
#
@bottle.post("/file/download/<code>/<variant>")
@bottle.get("/file/download/<code>/<variant>")
@bottle.auth_basic(admin_auth)
def file_download(code, variant):
    variant = urllib.parse.unquote(variant)

    basename = code + "-" + variant + ".txt"
    basename = normalize_filename(basename)
    
    filename = sta_parameters.conf_dir(0) + basename
    filename_s = filename + ".save"

    # Only use the .save file if it exists and the .txt file does not
    if ((not os.path.isfile(filename)) and (os.path.isfile(filename_s))):
        filename = filename_s

    return bottle.static_file(filename, root=os.getcwd(), download=basename)


#
#----------------------------------------------------
#

def real_file_upload(code, variant, refresh=False, redirect=None):
    variant = urllib.parse.unquote(variant)

    basename = code + "-" + variant + ".txt"
    basename = normalize_filename(basename)
    
    filename = sta_parameters.conf_dir(0) + basename
    filename_n = filename + ".new"
    filename_o = filename + ".old"
    filename_s = filename + ".save"

    # Only use the .save file if it exists and the .txt file does not
    if ((not os.path.isfile(filename)) and (os.path.isfile(filename_s))):
        filename = filename_s

    # Remove any remant of a previously failed upload
    if (os.path.isfile(filename_n)):
        os.remove(filename_n)

    file = bottle.request.files.get("file")
    file.save(filename_n)

    # Save the previous version (if it exists)
    if (os.path.isfile(filename)):
        shutil.copyfile(filename, filename_o)
        
    os.replace(filename_n, filename)

    ok = True
    msg = ""

    if (not ok):
        refresh = False
        rdirect = None
        
    return create_json_info_response(ok, msg, refresh=refresh, redirect=redirect)


#
#----------------------------------------------------
#

@bottle.post("/file/upload/<code>/<variant>")
@bottle.auth_basic(admin_auth)
def file_upload(code, variant):
    return real_file_upload(code, variant)


@bottle.post("/file/upload_and_refresh/<code>")
@bottle.auth_basic(admin_auth)
def file_upload_and_refresh(code, variant):
    variant = bottle.request.forms.get('value') 
    variant_q = urllib.parse.quote(variant)
    
    return real_file_upload(code, variant, True)

@bottle.post("/file/upload_and_redirect/<code>")
@bottle.auth_basic(admin_auth)
def file_upload(code):
    variant = bottle.request.forms.get('value') 
    variant_q = urllib.parse.quote(variant)

    return real_file_upload(code, variant, redirect="/calendar")

@bottle.post("/file/upload/<code>")
@bottle.auth_basic(admin_auth)
def file_upload_via_form(code):
    variant = bottle.request.forms.get('value') 
    variant_q = urllib.parse.quote(variant)

    return real_file_upload(code, variant, redirect="/calendar")


#
#----------------------------------------------------
#

@bottle.get("/file/ask/upload/<code>")
@bottle.auth_basic(admin_auth)
def ask_upload(code):

    s = "<h2>Upload New \"" + code + "\"</h2>\n"

    s = s + get_description("init")
    s = s + "\n<p></p>\n\n"

    #s = s + "<form method=\"post\" action=\"/file/upload/" + code + "\""
    #s = s + "enctype=\"multipart/form-data\">\n"
    
    s = s + "\t<div style=\"width: 50%\">\n"
    s = s + "\t\t<label>Name for uploaded file: </label>\n"
    s = s + "\t\t<input type=\"text\" id=\"variant\" value=\"new-name\" />\n"
    s = s + "\t</div>\n"

    s = s + "\t<p></p>\n"

    s = s + "\t<label>File: </label>\n"
    s = s + "\t<input type=\"file\" id=\"my_file\" />\n"

    s = s + "\t<p></p>\n"

    #s = s + "\t<input type=\"submit\" value=\"Upload and Create\" />"
    s = s + "\t\t\t<button class=\"btn\" "
    s = s + "onclick=\"uploadViaPOST('/file/upload_and_redirect/"
    s = s + code + "', 'my_file', 'variant')\" />Upload</button>\n"
        
    #s = s + "</form>\n"

    return bottle.template("lib/html/control-panel.html",
                        main=s)


#
#----------------------------------------------------
#
@bottle.route("/restart/display")
@bottle.auth_basic(admin_auth)
def restart_display_service():
    print_it("sudo systemctl restart weather-display.service")
    
    return os.system("sudo systemctl restart weather-display.service")
    

@bottle.route("/restart/control_panel")
@bottle.auth_basic(admin_auth)
def restart_control_panel_service():
    print_it("sudo systemctl restart weather-control-panel.service")
    
    return os.system("sudo systemctl restart weather-control-panel.service")

@bottle.route("/restart/sync_service")
@bottle.auth_basic(admin_auth)
def restart_control_panel_service():
    print_it("sudo systemctl restart weather-sync.service")
    
    return os.system("sudo systemctl restart weather-sync.service")
  

@bottle.route("/restart/all")
@bottle.auth_basic(admin_auth)
def restart_all_services():
    restart_display_service()
    restart_control_panel_service()
    restart_sync_service()
    

@bottle.route("/restart")
@bottle.auth_basic(admin_auth)
def show_iconsets():
    s = "<h2>Restart Components</h2>\n"

    s = s + get_description("restart")
    s = s + "<p></p>\n"

    s = s +  create_button("btn_restart_disp",
                              "/restart/display",
                              "Restart Ink Display", css_class="btn")

    s = s + "<p></p>\n"
    s = s +  create_button("btn_restart_disp",
                              "/restart/control_panel",
                              "Restart Control Panel", css_class="btn")
    s = s + "<p></p>\n"
    s = s +  create_button("btn_restart_disp",
                              "/restart/sync_service",
                              "Restart Sync (Multi-Panel) Service", css_class="btn")
    
    s = s + "<p></p>\n"
    s = s +  create_button("btn_restart_disp",
                              "/restart/all",
                              "Restart All",
                               css_class="btn")

    return bottle.template('lib/html/control-panel.html',
                        main=s)

#
#----------------------------------------------------
#
@bottle.post("/file/confirm/delete/<code>/<variant>")
@bottle.auth_basic(admin_auth)
def confirm_delete(code, variant):
    variant_d = urllib.parse.unquote(variant)
    
    msg = "<p><b>Are You Sure?</b></p>"
    msg = msg + "<p>Delete <b>" + variant_d + "</b>?</p>"

    delete_url = "/file/really/delete/" + code + "/" + variant
    
    return create_json_info_response(True, msg,
                              title="",
                              style="info",
                              update=[],
                              refresh=False,
                              redirect=None,
                              l_button_text="No",
                              l_button_action="",
                              r_button_text="Yes",
                              r_button_action="showInfoViaPOST('" + delete_url + "');")


@bottle.post("/file/really/delete/<code>/<variant>")
@bottle.auth_basic(admin_auth)
def really_delete(code, variant):
    variant = urllib.parse.unquote(variant)

    basename = code + "-" + variant + ".txt"
    basename = normalize_filename(basename)
    
    filename = sta_parameters.conf_dir(0) + basename

    filename_t = filename 
    filename_n = filename + ".new"
    filename_o = filename + ".old"
    filename_s = filename + ".save"

    # Only use the .save file if it exists and the .txt file does not
    if ((not os.path.isfile(filename)) and (os.path.isfile(filename_s))):
        filename = filename_s

    # Remove any partially created .new file
    if (os.path.isfile(filename_n)):
        os.remove(filename_n)

    # Save the active file as ".old"
    if (os.path.isfile(filename)):        
        os.replace(filename, filename_o)

    # Delete the disabled version of the file
    if (os.path.isfile(filename_s)):
        os.remove(filename_s)

    # Delete the enabled version of the file
    if (os.path.isfile(filename_t)):
        os.remove(filename_t)

    return create_json_info_response(True, "", refresh=True)

#
#----------------------------------------------------
#

@bottle.post("/file/really/copy/<code>/<variant>")
@bottle.auth_basic(admin_auth)
def really_copy(code, variant):
    refresh = False
    
    variant_uq = urllib.parse.unquote(variant)
    
    data = bottle.request.json
    new_name = normalize_filename(data["value"])
       
    filename_n = find_file(code, new_name)
    filename_o = find_file(code, variant_uq)
    
    if (filename_n is not None):
        msg = "There already is a file for \"" + new_name + "\""
        ok = False
        
    elif (filename_o is None):
        msg = "No such file for \"" + variant_uq + "\""
        ok = False
        
    else:
        basename = code + "-" + new_name + ".txt"

        if ((code != "display") and (code != "iconset")):
            basename = basename + ".save"

        filename_n = sta_parameters.conf_dir(0) + basename
        
        shutil.copyfile(filename_o, filename_n)
        
        msg = "Created \"" + new_name + "\".  "
        
        if ((code != "display") and (code != "iconset")):
            msg = msg + "It is disabled by default."
            
        refresh = True
        ok = True

    if (refresh):
        r_button_action = "location.reload();"
    else:
        r_button_action = ""
        
    return create_json_info_response(ok, msg, r_button_action=r_button_action)


#
#----------------------------------------------------
#

@bottle.post("/file/ask/copy/<code>/<variant>")
@bottle.auth_basic(admin_auth)
def ask_copy(code, variant):
    variant_uq = urllib.parse.unquote(variant)
    
    return create_json_info_response(True, "Enter a name for the duplicate of \"" + variant + "\"",
                                     center=True, textbox=variant_uq + " (copy)",
                                     l_button_action="",
                                     l_button_text="Cancel",
                                     r_button_text="OK", 
                                     r_button_action="showInfoViaPOST('/file/really/copy/" + \
                                             code + "/" + variant + "', null, 'textbox1');"
                                     )
   

  
#
#----------------------------------------------------
#

@bottle.post("/file/really/rename/<code>/<variant>")
@bottle.auth_basic(admin_auth)
def really_rename(code, variant):
    refresh = False
    
    variant_uq = urllib.parse.unquote(variant)
    
    data = bottle.request.json
    new_name = normalize_filename(data["value"])
       
    filename_n = find_file(code, new_name)
    filename_o = find_file(code, variant_uq)

    # Silently ignore if the new name is the same as the old name
    if (variant_uq == new_name):
        ok = True
        msg = ""
        
    elif (filename_n is not None):
        msg = "There already is a file for \"" + new_name + "\""
        ok = False
        
    elif (filename_o is None):
        msg = "No such file for \"" + variant_uq + "\""
        ok = False

    else:
        basename = code + "-" + new_name + ".txt"
        if (filename_o.endswith(".save")):
            basename = basename + ".save"
            
        filename_n = sta_parameters.conf_dir(0) + basename
        
        os.rename(filename_o, filename_n)
        
        msg = "Renamed \"" + variant_uq + "\" to \"" + new_name + "\"."
        ok = True
        refresh = True

    if (refresh):
        r_button_action = "location.reload();"
    else:
        r_button_action = ""

    print("Returning", msg, "and", refresh)
    
    return create_json_info_response(ok, msg, r_button_action=r_button_action)

#
#----------------------------------------------------
#


@bottle.post("/file/ask/rename/<code>/<variant>")
@bottle.auth_basic(admin_auth)
def ask_rename(code, variant):
    variant_uq = urllib.parse.unquote(variant)
    
    return create_json_info_response(True, "Enter a new name for \"" + variant + "\"",
                                     center=True, textbox=variant_uq,
                                     l_button_action="",
                                     l_button_text="Cancel",
                                     r_button_text="OK", 
                                     r_button_action="showInfoViaPOST('/file/really/rename/" + \
                                             code + "/" + variant + "', null, 'textbox1');"
                                     )
   
#
#----------------------------------------------------
#

@bottle.post("/file/really/new/<code>")
@bottle.auth_basic(admin_auth)
def really_new(code):
    refresh = False
    
    data = bottle.request.json
    new_name = normalize_filename(data["value"])

    new_url = "/file/new/" + code + "/" + new_name
    
    return create_json_info_response(True, "", redirect=new_url)
    
@bottle.post("/file/ask/new/<code>")
@bottle.auth_basic(admin_auth)
def ask_new_file(code):
    return create_json_info_response(True, "Enter a name for new \"" + code + "\"",
                                     center=True, textbox="new-name",
                                     l_button_action="",
                                     l_button_text="Cancel",
                                     r_button_text="OK", 
                                     r_button_action="showInfoViaPOST('/file/really/new/" + \
                                             code + "', null, 'textbox1');"
                                     ) 

#
#----------------------------------------------------
#
@bottle.route("/icon/<dirname>/<filename>")
@bottle.auth_basic(admin_auth)
def xmit_file(dirname, filename):

    err = False

    dirname = normalize_filename(dirname)
    filename = normalize_filename(filename)

    fullname = "lib/icons/" + dirname + "/" + filename

    # Does the file exist?
    if (not os.path.isfile(fullname)):
        err = True
    
    if (not err):
        resp = bottle.static_file(fullname,
                              root=os.getcwd())
    else:
        resp = bottle.HTTPResponse(status=404)

    return resp


@bottle.route("/iconset/<dirname>")
@bottle.auth_basic(admin_auth)
def show_iconset(dirname):
    s = "<h2>Icon Set: " + dirname + "</h2>\n"

    s = s + get_description("one-iconset")
    s = s + "<p></p>\n"  

    dirname = normalize_filename(dirname)
    prefix = "lib/icons/" + dirname + "/"

    s = s + "<div class=\"one_iconset\">\n"

    for icon in sorted(os.listdir(prefix)):
        s = s + "\t<div class=\"icon\">\n"
        s = s + "\t<img src=\"/icon/" + dirname + "/" + icon + "\" "
        s = s + "class=\"icon_img\" />"
        s = s + "<br />\n"
        s = s + "\t<label>" + icon + "</label>\n"
        s = s + "\t</div>"

    s = s + "</div>\n"
    
    return bottle.template('lib/html/control-panel.html',
                        main=s)

@bottle.route("/iconsets")
@bottle.auth_basic(admin_auth)
def show_iconsets():
    s = "<h2>Icon Sets</h2>\n"

    s = s + get_description("iconsets")
    s = s + "<p></p>\n"

    s = s + "<ul>\n"

    prefix = "lib/icons/"
    
    for one_dir in sorted(os.listdir(prefix)):
        if (os.path.isdir(prefix + one_dir)):
            s = s + "<li><a href=\"/iconset/" + one_dir + "\">"
            s = s + one_dir + "</li>\n"

    return bottle.template('lib/html/control-panel.html',
                        main=s)

#
#----------------------------------------------------
#

@bottle.route("/init")
@bottle.auth_basic(admin_auth)
def init_setup():

    s = "<h2>Initial Configuration</h2>\n"

    s = s + get_description("init")
    s = s + "<p></p>\n"

    if (extra_utils.internet_is_up()):
        s = s + "<p><i>The device is connected to the Internet.  You do "
        s = s + "not need to change the Wi-Fi settings.</i></p>"
    else:
        s = s + "<p>The device is <b>NOT</b> connected to the Internet. "
        s = s + "You can change the Wi-Fi settings below:</p>"

    if (is_enabled("wifi")):
        s = s + box_start("Wi-Fi settings:")
        
        s = s + handle_parameter("Wi-Fi SSID", "wifi_ssid")
        s = s + handle_parameter("Wi-Fi Key/Password", "wifi_pass")

        s = s + box_end()
    
    s = s + handle_parameter("email address", "email_addr")

    return bottle.template('lib/html/control-panel.html',
                        main=s)

#
#----------------------------------------------------
#
@bottle.route("/loc")
@bottle.auth_basic(admin_auth)
def loc_config():

    s = "<h2>Location Configuration</h2>\n"

    if (is_enabled("loc")):
        s = s + get_description("loc")

        s = s + box_start("Use either a Street Address <b>OR</b> Lat/Long (no need for both)")
        
        s = s + one_item("Street Address", "", "addr")
        s = s + handle_parameter("Latitude, Longitude", "lat_lon")

        s = s + box_end()

    s = s + handle_parameter("Timezone", "timezone")
    
    return bottle.template('lib/html/control-panel.html',
                        main=s)



#
#----------------------------------------------------
#

@bottle.route("/weather")
@bottle.auth_basic(admin_auth)
def weather_config():

    s = "<h2>Weather Observations and Alerts Configuration</h2>\n"

    s = s + get_description("weather")
    
    s = s + handle_parameter("Forecast Zone", "forecast_zone")
    s = s + handle_parameter("Observation Stations", "obs_stations")
    s = s + handle_parameter("Alert Zone", "alert_zone")

    if (is_enabled("tide_station")):
        s = s + box_start("Optional:")
        s = s + handle_parameter("Station for Tides", "tide_station")
        s = s + box_end()
        
    s = s + "<div>&nbsp;</div>"
    s = s + box_start("Optional / If Necessary:")
    s = s + create_reset_all_button()
    s = s + box_end()
    
    return bottle.template('lib/html/control-panel.html',
                        main=s)

#
#----------------------------------------------------
#

@bottle.route("/calendar")
@bottle.auth_basic(admin_auth)
def weather_config():

    s = "<h2>Calendar</h2>\n"

    s = s + get_description("calendar")
    
    s = s + file_category("ical", "iCal URLs")
    s = s + file_category("ignore", "Ignore Lists for iCal Entries")

    s = s + file_category("weekday",   "Weekday Events")
    s = s + file_category("daily",     "Weekday+Weekend Events")
    s = s + file_category("countdown", "Countdown Events")

    #s = s + file_category("fake", "Files for Debugging")

    return bottle.template('lib/html/control-panel.html',
                        main=s)


#
#----------------------------------------------------
#

@bottle.route("/display")
@bottle.auth_basic(admin_auth)
def weather_config():

    s = "<h2>Screen / Display</h2>\n"

    s = s + get_description("screen")

    s = s + box_start("Currently Active:")
    s = s + handle_parameter("Current Active Display Template", "active-display")
    s = s + handle_parameter("Current Active Icon Set", "active-iconset")
    s = s + handle_parameter("Current Screen Rotation", "rotate")
    s = s + box_end()

    s = s + file_category("display", "Your Display Templates")

    s = s + file_category("sys-display", "Pre-Defined Display Templates", readonly=True)

    s = s + file_category("iconset", "Your Icon Sets")

    s = s + file_category("sys-iconset", "Pre-Defined Icon Sets", readonly=True)
   
    
    return bottle.template('lib/html/control-panel.html',
                        main=s)
#
#----------------------------------------------------
#

@bottle.route("/sync")
@bottle.auth_basic(admin_auth)
def sync_config():
    s = "<h2>Configuration File Synchronization</h2>\n"

    s = s + get_description("sync")

    s = s + box_start("My Sync Settings:")
    s = s + handle_parameter("(Default) Sync Password", "sync_password")
    s = s + handle_parameter("Act as a sync server?", "sync_server")
    s = s + handle_parameter("Remove unmatched (individual) files?", "sync_cleanmissing")
    s = s + handle_parameter("Remove unmatched (wildcard) files?", "sync_cleanwildcards")
    s = s + box_end()

    s = s + box_start("Sync All Files (from another display):")
    s = s + handle_parameter("*", "sync-w-all")
    s = s + box_end()

    s = s + box_start("Sync All Files of One Type (from another display):")
    
    for item in sorted(["countdown*", "daily*", "weekday*",
                        "ical*", "base*", "ignore*", "display*",  "test*"]):
        
        item_code = "sync-w-" + item.rstrip("*")
        s = s + handle_parameter(item, item_code)
        
    s = s + box_end()

    s = s + box_start("Sync Individual Files (from another display):")

    items = {}

    #
    # Make an entry for every non-sync file as well
    #  as where the individual sync-f-* files go to
    #  (and ignore other sync-* files)
    #
    for item in os.listdir("etc"):
        
        if item.endswith(".txt"):
            if item.startswith("sync-f-"):
                items[item[7:]] = 1   # Ignore the sync-f- portion
                
            elif not item.startswith("sync-"):
                items[item] = 1

    extra = bottle.request.query.get("add", "")

    # Safety check for (one type of) URL spoofing
    if "/" in extra:
        extra = ""
        
    if extra != "":
        if not extra.endswith(".txt"):
            extra = extra + ".txt"
            
        items[extra] = 1

    # Convert to a sorted list
    items = list(items.keys())
    items.sort()
    
    for item in items:
        if item.endswith(".txt"):
            item_code = "sync-f-" + item.rstrip(".txt")

            s = s + handle_parameter(item, item_code)

    s = s + "<div><button class=\"btn\" onclick=\"new_sync_file()\">" + \
            "Add file to sync</button></div>"
    
    s = s + box_end()
    
    return bottle.template('lib/html/control-panel.html',
                        main=s)

#
#----------------------------------------------------
#
@bottle.route("/sync_sys/mtime/<code>")
@bottle.auth_basic(sync_auth)
def return_file_mtime(code):
    filename = "etc/" + code

    if not filename.endswith(".txt"):
        filename = filename + ".txt"

    s = ""
    
    if not os.path.exists(filename):
        s = "no"
        
    elif os.path.isfile(filename):
        mtime = os.path.getmtime(filename)
        
        mtime = int(mtime)   # Truncate it
        s = str(mtime)       # Convert to a string

    return s


@bottle.route("/sync_sys/get/<code>")
@bottle.auth_basic(sync_auth)
def return_file_get(code):
    filename = "etc/" + code

    if not filename.endswith(".txt"):
        filename = filename + ".txt"

    s = ""
    
    if os.path.isfile(filename):
        f = open(filename)
        s = f.read()
        f.close()

    return s

def is_part_of_base(filename):
    base_prefixes = [ "active-display", "alert-zone",
                      "forecast-zone", "lat-lon",
                      "obs-stations", "prog-id", "weather-loc",
                      "tide-station" ]

    is_base = False
    
    for prefix in base_prefixes:
        
        if filename.startswith(prefix):
            is_base = True
        
    return is_base




@bottle.route("/sync_sys/list/<code>")
@bottle.auth_basic(sync_auth)
def remote_matching_files(code):
    if code == "all":
        code = ""

    s = ""
    
    for file in os.listdir("etc/"):
        # Matching files only

        if code == "base":
            matched = file.endswith(".txt") and is_part_of_base(file)
            
        else:
            matched = file.endswith(".txt") and file.startswith(code)
            
        if matched:

            # Do not show sync files
            #  Also double check that this is a file
            if not file.startswith("sync-") and os.path.isfile("etc/" + file):

                # Remove the .txt ending and add it to string
                file = file.rstrip(".txt")
                s = s + file + "\n"

    return s

#
#----------------------------------------------------
#

#

@bottle.route("/dynamic/preview.jpg")
@bottle.auth_basic(admin_auth)
def render_preview(force=False):
    display = sta_parameters.find_active_file("active-display")
    
    if ((force) or
        (not os.path.exists("tmp/preview.jpg")) or
        ((time.time() - os.path.getmtime("tmp/preview.jpg"))> 60)):

        # Create the temp directory if necessary
        if (not os.path.isdir("tmp")):
            os.mkdir("tmp")
            
        bitmap_weather.draw_from_config_to_file(display, "tmp/preview.jpg")
    
    return bottle.static_file("tmp/preview.jpg", root=os.getcwd())

#
#----------------------------------------------------
#

@bottle.get("/preview")
@bottle.post("/preview")
@bottle.auth_basic(admin_auth)
def preview():
    render_preview(True)

    return bottle.template('lib/html/control-panel.html',
                        main='<img src="dynamic/preview.jpg" />')
#
#----------------------------------------------------
#
def file_info(f):
    now = datetime.datetime.now()
    sevenDays = now - datetime.timedelta(days=7)
    
    m_time = os.path.getmtime(f)
    m_time_s = datetime.datetime.fromtimestamp(m_time)

    f = f.replace("\\", "/")
    
    if (f[0] == "."):
        f = f[2:]
        
    s = "<td>" + f + "</td><td>"
    
    if (m_time_s > sevenDays):
        s = s + "<b>" + m_time_s.strftime("%Y-%m-%d") + "</b>"
    else:
        s = s + m_time_s.strftime("%Y-%m-%d")


    s = s + "</td>"

    return s
    
@bottle.route("/about")
@bottle.auth_basic(admin_auth)
def about():
    
    s = "<h2>Written by Mark Monnin</h2>\n"

    s = s + get_description("about")

    s = s + "<i>Program Modules and Program Control Files:</i>\n"
    s = s + "<table class=\"about-table\">\n"
    s = s + "<tr><th>Filename</th><th>Last Modified</th></tr>\n"

    files = glob.glob("bin/*")
    files = files + glob.glob("lib/html/*")
    files = files + glob.glob("lib/conf-files/*")
    files = files + glob.glob("lib/install-files/*")
    files = files + glob.glob("lib/text/*")
    files = files + glob.glob("lib/templates/*")
    files = files + glob.glob("sbin/*")
    
    files.sort()

    #s = s + "<br />\n"
    
    for one_file in files:
        if ("__pycache__" not in one_file):
            s = s + "<tr>" + file_info(one_file) + "</tr>\n"

        
    s = s + "</table>\n"
    
    return bottle.template('lib/html/control-panel.html',
                        main=s)
#
#----------------------------------------------------
#

@bottle.post("/restore")
@bottle.auth_basic(admin_auth)
def restore_from_backup():
    backup_name = "tmp/backup.tgz"
    
    settings = (bottle.request.forms.get("settings") is not None)
    software = (bottle.request.forms.get("software") is not None)
    #file = bottle.request.forms.get("file")
    
    #print(settings, software)
        
    file = bottle.request.files.get("uploaded_file")
    
    if (file is not None):
        # Old backup .tgz file still there?  Remove it first
        if (os.path.isfile(backup_name)):
            os.remove(backup_name)
            
        file.save(backup_name)

        s = control.restore_backup(backup_name, settings, software,
                                         delete_after=True,
                                         also_convert=True)
            
    else:
        s = "<h2>Restore failed - no backup file found</h2>"
        
    return bottle.template('lib/html/control-panel.html',
                        main=s)
    

@bottle.post("/backup")
@bottle.auth_basic(admin_auth)
def create_backup():
    settings = (bottle.request.forms.get('settings') is not None)
    software = (bottle.request.forms.get('software') is not None)

    control.create_backup(settings, software)

    return bottle.static_file(filename, root=os.getcwd(), download=basename)

def create_checkbox(btn_id, title, id_prefix, checked=False):
    s = "<div>\n"
    s = s + "\t<input type=\"checkbox\"  name=\"" + btn_id + "\""
    s = s + " id=\"" + id_prefix + "_" + btn_id + "\""
    
    if (checked):
        s = s + " checked"

    s = s + " onchange=\"enableOrDisableSubmit('" + id_prefix + "');\""
    
    s = s + "/>\n"
    s = s + "\t<label>" + title + "</label>\n"
    s = s + "</div>\n"

    return s
    
def create_backres_button(title, url, id_prefix, check_all=False, add_file=False):
    s = get_description(title)

    s = s + "\n\n<form method=\"post\" action=\"" + url + "\""
    s = s + "enctype=\"multipart/form-data\">\n"
    
    s = s + create_checkbox("settings", "Configuration Settings", id_prefix, True)
    s = s + create_checkbox("software", "Program Files", id_prefix, check_all)

    if (add_file):
        s = s + "<br />\n\t<div>\n"
        s = s + "\t\t<label>Local backup file to restore from (typically a weather-*.tgz file) : </label>\n"
        s = s + "\t\t<input type=\"file\" id=\"" + id_prefix + "_file\" "
        s = s + " onchange=\"enableOrDisableSubmit('" + id_prefix + "');\""
        s = s + " name=\"uploaded_file\" />\n"
        s = s + "\t</div>\n"
        
    s = s + "<br /><input type=\"submit\" class=\"btn\" id=\"" + id_prefix + "_submit\""

    if (add_file):
        s = s + " disabled"
        
    s = s + " value=\"" + title + "\" />\n"
    s = s + "</form>\n"

    return s

@bottle.route("/backres")
@bottle.auth_basic(admin_auth)
def show_backup_and_restore():
    s = "<h2>Backup and Restore</h2>\n"

    s = s + get_description("backres")

    s = s + box_start("Backup:")
    s = s + create_backres_button("Backup", "/backup", "backup")
    s = s + box_end()

    s = s + box_start("Restore:")
    s = s + create_backres_button("Restore", "/restore", "restore", True, True)


    s = s + "<p></p>\n"
    s = s + get_description("backres-restart")
    s = s + "<p></p>\n"
    s = s +  create_button("btn_restart_disp",
                              "/restart/all",
                              "Restart Display &amp; Control Panel",
                               css_class="btn")
    s = s + box_end()
    
    return bottle.template('lib/html/control-panel.html',
                        main=s)
#
#----------------------------------------------------
#
@bottle.route("/password")
@bottle.auth_basic(admin_auth)
def set_web_password():
    s = "<h2>Set Web (Control Panel) Password</h2>\n"

    s = s + get_description("password")

    s = s + box_start("Set Password:")
    s = s + handle_parameter("New Password", "web_password")
    s = s + box_end()

    return bottle.template('lib/html/control-panel.html',
                        main=s)
    
#
#----------------------------------------------------
#


@bottle.route("/static/<filename>")
@bottle.auth_basic(admin_auth)
def xmit_file(filename):

    err = False
    
    if ((filename == "") or ("/" in filename) or (filename[0] == ".")):
        err = True

    fullname = "lib/html/" + filename

    # Does the file exist?
    if ((not err) and (not os.path.isfile(fullname))):
        err = True
    
    if (not err):
        resp = bottle.static_file(fullname,
                              root=os.getcwd())
    else:
        resp = bottle.HTTPResponse(status=404)

    return resp


#
#----------------------------------------------------
#
@bottle.route("/favicon.ico")
def favicon():
    return bottle.static_file("lib/html/favicon.ico",
                              root=os.getcwd())





#
#----------------------------------------------------
#
@bottle.route("/")
@bottle.auth_basic(admin_auth)
def initial_page():
    s = get_description("home")
    s = s + "<p>Click on PREVIEW to review the display.</p>"
    
    return bottle.template('lib/html/control-panel.html',
                           main=s)

extra_utils.set_default_dir()

def missing_or_old(filename):
    result = False
    
    if os.path.isfile(filename):
        mtime = os.path.getmtime(filename)
        now = time.time()

        diff_time = now - mtime
        #print("Diff time", filename, diff_time)

        # Older than 3/4 of a year?
        if diff_time > (60 * 60 * 24 * 274):
            result = True
    else:
        result = True

    return result


def create_certs_if_needed():
    
    if not os.path.isdir("cache/ssl"):
        os.mkdir("cache/ssl")
        
    needed = missing_or_old("cache/ssl/server.crt")
    needed = needed or missing_or_old("cache/ssl/server.key")

    if needed:
        print("(Re)creating the .crt and .key file", file=sys.stderr)
        
        subprocess.run(["openssl", "req",
                        "-x509", "-nodes", "-new",
                        "-keyout","cache/ssl/server.key",
                        "-out", "cache/ssl/server.crt",
                        "-days", "3650",
                        "-subj",
                        "/C=/ST=/L=/O=/OU=web/CN=" + extra_utils.hostname()])

        f_out = open("cache/ssl/server.pem", "w")

        f_in = open("cache/ssl/server.crt")
        f_out.write(f_in.read())
        f_in.close()
        
        f_out.write("\n")
        
        f_in = open("cache/ssl/server.key")
        f_out.write(f_in.read())
        f_in.close()

        f_out.close()
        
    return needed

def main():
    extra_utils.set_default_dir()

    if sta_parameters.needs_pin():
        print("Initial PIN:", sta_parameters.get_pin())
    else:
        print("Using the (configured) admin password")
            
    # Windows doesn't appear to support gevent properly, so no TLS/SSL for you

    if os.name == 'nt' or not USE_GEVENT:
        if os.name != 'nt':
            create_certs_if_needed()
            
        bottle.run(host='127.0.0.1', port=8888)

    else:        
        create_certs_if_needed()

        # Ignore the SSL: SSLV3_ALERT_CERTIFICATE_UNKNOWN error
        # TODO: Find a better way of telling bottle to ignore these
        #contextlib.suppress(ssl.SSLError)

        my_ssl_context = gevent.ssl.SSLContext(gevent.ssl.PROTOCOL_TLS_SERVER)
        my_ssl_context.load_cert_chain('cache/ssl/server.crt', 'cache/ssl/server.key')

        my_ssl_context.check_hostname = False
        my_ssl_context.verify_mode = gevent.ssl.CERT_NONE
        
        bottle.run(host='', port=8888,
                   server='gevent',
                   ssl_context=my_ssl_context)

if (__name__ == "__main__"):
    main()
