# pip3 install pillow
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont

import datetime
import os
import random
import re
import sys

import weather_rest
import alt_icons
import cal_helper
import cmd_dispatch
import extra_utils
import sta_parameters

alt_icons_path = "icons/"

im = None
draw = None
forecast = {}

def_forecast_zone = None
def_tide_station = None
def_alert_zone = None
def_stations = None

WIDTH = 800
HEIGHT = 480
WEATHER_WIDTH = 560

last_temp = None

_FIXED_FONT_DIR = "lib/fonts/fixed/75dpi/"
_ALT_FIXED_FONT_DIR = "lib/fonts/fixed/100dpi/"
_TT_FONT_DIR    = "lib/fonts/truetype/"

DEBUG = 1

def print_it(*args,**kwargs):

    if (DEBUG):
        print(*args, **kwargs)

def blank_image(width, height, use_color=False):
    if (use_color):
        im = PIL.Image.new("RGB", (width, height), color="white")
    else:
        im = PIL.Image.new("L", (width, height), color="white")

    return im

def save_image(im, filename):
    im.save(filename)

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


#
#-----------------------------------------------------------------
#
def find_closest_fixed_font(font_fixed_family, font_size,
                            is_bold, is_italic,
                            font_dir=_FIXED_FONT_DIR):


        
    prefix = font_fixed_family

    DEBUG = 0
    if (prefix == "cour"):
        print("Looking for", prefix, font_size)
        DEBUG = 1
        
    if (is_bold):
        prefix = prefix + "B"

    if (is_italic):
        prefix = prefix + "O"

    # Neither bold nor italic, then it's regular
    if ((not is_bold) and (not is_italic)):
        prefix = prefix + "R"

    closest_filename  = None
    closest_font_size = None
    closest_diff      = None

    # Search the path only if valid
    if (os.path.isdir(font_dir)):

        # Look at all possible font files
        for one_file in os.listdir(font_dir):

            # Only look at files close to the desired name
            if (one_file.startswith(prefix) and one_file.endswith(".pil")):

                # Get the next two chars after the prefix
                file_font_size = one_file[len(prefix):len(prefix)+2]

                # Is it a number?  If so, convert it into an integer

                if (file_font_size.isnumeric()):
                    file_font_size = int(file_font_size)

                    diff = abs(font_size - file_font_size)

                    #print_it(one_file, prefix, file_font_size, diff)

                    # A better match?  Then use this
                    if ((closest_diff is None) or (diff < closest_diff)):
                        closest_diff = diff
                        closest_font_size = file_font_size
                        closest_filename = font_dir + one_file
                        #print_it("Yes!!!")


    if (DEBUG):
        print("Closest", closest_filename, closest_font_size, closest_diff, 100.0 * closest_font_size / font_size)
        
    return (closest_filename, closest_font_size, closest_diff)

def find_font(font_size, is_bold=False, is_italic=False, force="",
              font_size_percent=5.0,
              font_fixed_family="helv", font_tt_family="FreeSans",
              return_tuple=False):

    # Initialize the cache dictionary if this is the first pass
    if (not hasattr(find_font, "cache")):
        find_font.cache = {}

    # Just in case
    if (force is None):
        force = ""

    name = (font_size, is_bold, is_italic, force,
            font_size_percent, font_fixed_family, font_tt_family)

    if (name in find_font.cache):
        fnt = find_font.cache[name]

    else:
        fnt = None

        closest_filename = None    # Make it not match the fixed font
        closest_font_size = None
            
        if (force != "t") and (font_fixed_family is not None):
            # Convert the percentage into a floating point (e.g. 9.5% = 0.095)
            font_size_percent = font_size_percent / 100.0

            # Compute the upper and lower bound for a font to match sizes
            too_big   = (1.0 + font_size_percent) * font_size
            too_small = (1.0 - font_size_percent) * font_size

            # Allow for fonts to be forced to beup-to font_size only (s)
            if ("s" in force):
                too_big = font_size

            # to be forced to be up-to font_size only (s)
            if ("l" in force):
                too_small = font_size

            # to be forced to be only font_size
            # (making the percent 0 would do the same thing)
            if ("e" in force):
                too_small = font_size
                too_large = font_size

            (closest_filename, closest_font_size, closest_diff) = \
                    find_closest_fixed_font(font_fixed_family,
                                            font_size,
                                            is_bold, is_italic)
            #
            # An imperfect match?  Try a 100dpi font with a "resized"
            #  font_size (e.g. a 24 pixel/point font will look like a 18
            #  pixel/point font in this directory)
            #
            if (closest_diff > 0):

                (alt_closest_filename, alt_closest_font_size,
                 alt_closest_diff) = \
                    find_closest_fixed_font(font_fixed_family,
                                            font_size * 0.75,
                                            is_bold, is_italic,
                                            font_dir=_ALT_FIXED_FONT_DIR)

                # Was there any alternative?
                if (alt_closest_diff is not None):
                    alt_closest_diff = alt_closest_diff / 0.75

                    # A better choice (even with the change if diff description)?
                    if (alt_closest_diff < closest_diff):
                        # Better choice - suggest it instead
                        closest_filename = alt_closest_filename
                        closest_font_size = alt_closest_font_size / 0.75

        # No match or not a good match?  Then use the TT font
        if ((closest_filename is None) or
            (closest_font_size > too_big) or
            (closest_font_size < too_small)):

            ending = ""

            if (is_bold):
                ending = "Bold"
            if (is_italic):
                ending = ending + "Oblique"

            print_it("No match for font size", font_size)
            filename = _TT_FONT_DIR + font_tt_family + ending + ".ttf"

            # Make sure the file exists before trying to use it
            if (os.path.isfile(filename)):
                fnt = PIL.ImageFont.truetype(filename, font_size)
        else:
            print_it("Match for font size", font_size)

            fnt = PIL.ImageFont.load(closest_filename)

        # Cache the result if valid
        if (fnt is not None):
            find_font.cache[name] = fnt
            fnt.find_font_args = name

    if (return_tuple):
        fnt = (fnt, font_size)

    return fnt


#
#-----------------------------------------------------------------
#

def draw_time(x=0, y=0, font_size=36, color='black',
              add_seconds=None, hide_time=None,
              show_tz=None, tz=None,
              twelve_hour=True):

    timelen = 0
    
    init_screen_if_needed()

    add_seconds = get_var_value("add_seconds", add_seconds)
    hide_time = get_var_value("hide_time", hide_time)

    # Default: hide timezone unless specifying a different timezone
    
    if show_tz is None:
        if tz is None:
            show_tz = False
        else:
            show_tz = True

    if (not hide_time):

        fnt   = find_font(font_size)
        smfnt = find_font(font_size // 2)

        if tz is None:
            now = datetime.datetime.now().astimezone()

        else:
            zone = pytz.timezone(tz)
            now = datetime.datetime.now().astimezone(tz)

        # Allow for time to be incremented (or decremented) by a fixed
        #  number of seconds (for displaying a mostly-correct time for
        #  multiple minutes - to limit flash of eink full refresh)
        #
        if (add_seconds is not None):
            now = now + datetime.timedelta(seconds=add_seconds)

        hh = now.hour
        mm = now.minute

        if twelve_hour:
            if (hh == 0):
                hh = 12
                ampm = "AM"

            elif (hh == 12):
                ampm = "PM"

            elif (hh > 12):
                ampm = "PM"
                hh = hh - 12

            else:
                ampm = "AM"

        time = str(hh).rjust(2) + ":" + str(mm).zfill(2)
        timelen = draw.textlength(time, fnt)

        #draw.rectangle((y, x, x+timelen+5, y+font_size), fill='white')

        draw.text((x,y), time, color, fnt)

        if twelve_hour:
            ampm_offset = 0

            #if (ampm == "AM"):
            #    ampm_offset = 0
            #
            #else:
            #    ampm_offset = 0.60 * size

            draw.text((x+timelen, y+ampm_offset), ampm, color, smfnt)
            timelen = timelen + draw.textlength(ampm, smfnt)
            
        if show_tz:
            tz = now.tzname()

            # Abbreviate longer names
            if len(tz) > 6:
                tz_words = tz.split()
                tz = ""
                for one_word in tz_words:
                    tz = tz + one_word[0]

            # blank between time and timezone
            timelen = timelen + font_size
            
            draw.text((x+timelen, y), tz, color, fnt)
            timelen = timelen + draw.textlength(tz, fnt)
            
    return timelen 

#
#   Small helper routine for an easier way to display 24-hour time
#

def draw_time24(x=0, y=0, font_size=36, color='black',
              add_seconds=None, hide_time=None,
              show_tz=None, tz=None):
    
    return draw_time(x, y, font_size, color, add_seconds, hide_time,
                     show_tz, tz, twelve_hour=False)

#
#-----------------------------------------------------------------
#
def wrap_trunc_and_maybe_center_h(draw, x, y, width, height, s,
                     font_size, alt_font_size=None, mode="center"):

    print_it("WRAP:", "x=", x, "y=", y, "width=", width, "height=", height, "font size=", font_size)

    # Get the font and the revised font_size too
    (fnt, font_size) = find_font(font_size, return_tuple=True)
    b_fnt = find_font(font_size, is_bold=True)

    s_width = fnt.getlength(s)
    max_lines = int(height / font_size)

    # Is it too big?  Then try the alt font
    if (s_width > (width * max_lines)):
        if (alt_font_size is not None):
            font_size = alt_font_size

            fnt = find_font(font_size)
            b_fnt = find_font(font_size, is_bold=True)
            
            s_width = fnt.getlength(s)
            max_lines = int(height / font_size)

    num_lines = int(1 + (s_width / width))

    print_it("Wrap: num_lines: ", num_lines, "max_lines:", max_lines,
          "height:", height, "font_size:", font_size)


    if (num_lines > max_lines):
        num_lines = max_lines

    # Indent all lines if less than max width needed
    #  (makes all lines "similar" in length)
##    s_line_width = s_width / num_lines
##
##    if (1.1 * s_line_width <  width):
##        remove_spaces = int(width - s_line_width)
##
##        x = x + remove_spaces // 2
##        width = width - remove_spaces

    if "top" in mode:
        extra_height = 0
        extra_blank = 0

    else:
        extra_height = height - (num_lines * font_size)

        extra_blank  = int(extra_height / (num_lines + 1)) # Add top & bottom margin
        extra_blank  = extra_blank // 2



    print_it("Extra h", extra_height, "Extra b", extra_blank)
    if (extra_blank > 0):
        y = y + extra_blank

    max_y = y + height - font_size
    
    # Loop over the lines
    for i in range(num_lines):

        s1 = s
        s2 = ""

        s1_width = fnt.getlength(s1)

        # Ugly way to find the right place to cut
        while (s1_width > width):
            (s1, extra) = s1.rsplit(" ", 1)

            if (s2 == ""):
                s2 = extra
            else:
                s2 = extra + " " + s2

            s1_width = fnt.getlength(s1)

        # Last line and had extra stuff?  Replace last word with "..."
        if ((i == num_lines-1) and (s2 != "")):
            s1 = s1[:-3]

            while ((s1 != "") and (s1[-1] != " ")):
                s1 = s1[:-1]

            if (s1 != ""):
                s1 = s1 + "..."

            # Recompute width
            s1_width = fnt.getlength(s1)

        if "center" in mode:
            x_offset = int((width-s1_width) / 2)
            
        elif "right" in mode:
            x_offset = width-s1_width
            
        else:  # anything else is "left"
            x_offset = 0

        print("Line:", s1, "x=", x, "y=", y, "max_y=", max_y)

        m = re.search(r"^\*(.*)\*$", s1)

        if y < max_y:
            
            if m is not None:
                draw.text((x+x_offset,y), m.group(1), font=b_fnt)
            else:
                draw.text((x+x_offset,y), s1, font=fnt)
            
            y = y + font_size

        s = s2

    return y

#
#  Small helper to handle embedded \n's in the str
#

def wrap_trunc_and_maybe_center(draw, x, y, width, height, s,
                     font_size, alt_font_size=None, mode="center"):
    s = s.rstrip()

    if s == "" or height < font_size:
        new_y = y
    
    elif "\n" in s:
        (s1,rest) = s.split("\n", 1)

        # Unfortunately, if we split it, the first line needs to be "top"
        new_y = wrap_trunc_and_maybe_center_h(draw, x, y, width, height, s1,
                     font_size, alt_font_size, mode + ", top")

        height_diff = new_y - y
        new_height = height - height_diff

         # Recursively handle the rest of the string
        new_y = wrap_trunc_and_maybe_center(draw, x, new_y, width,
                                            new_height , rest,
                                            font_size, alt_font_size,
                                            mode)
        
    else:
        new_y = wrap_trunc_and_maybe_center_h(draw, x, y, width, height, s,
                     font_size, alt_font_size, mode)

    return new_y
#
#-----------------------------------------------------------------
#


def center_text_f(draw, x, y, width, text, fnt, color='black',
                bgcolor=None, border=2, overflow=None,
                outline=None):

    min_font = 10

    # Limit shrink to 10% only
    if (hasattr(fnt, 'find_font_args')):
        min_font = 0.9 * fnt.find_font_args[0]

    done = False
    
    while not done:
        bbox = draw.textbbox((x, y), text, fnt)

        textlen = bbox[2] - bbox[0]
        textheight = bbox[3] - bbox[1]

        # Truncate the word letter-by-letter if too long and "truncate" option specified
        # Includes a "safety breaker" of 4 char minimum to display no matter what
        if (textlen <= width):
            done = True

        elif (overflow is None):
            done = True

        else:

            if overflow == "truncate":
                if (len(text) < 5):
                    done = True       # Circuit-breaker for a minimum-sized text
                else:
                    text = text[:-1].rstrip()  #  Remove the last char
                                               #  (& any spaces that are left)

            elif ((overflow == "shrink") and
                  (hasattr(fnt, 'find_font_args'))):

                if (fnt.find_font_args[0] > min_font):

                    old_args = fnt.find_font_args
                    fnt_args = (old_args[0] - 1, ) + old_args[1:]

                    fnt = find_font(*fnt_args)
                else:

                    # Flip to truncate mode when at minimum size
                    overflow = "truncate"

            # Unknown overflow option
            else:
                done = True

    xstart = x + width // 2 - textlen // 2

    # Force to left justification if the text is larger than the width
    #  (which would overflow right, unless overflow_left is set)
    if (textlen > width):
        if (overflow == "left"):
            xstart = x + width - textlen
        else:
            xstart = x

    if (bgcolor is not None):
        draw.rectangle((x-border, y-border,
                        x+width+border, y+textheight+border),
                       bgcolor)

    if (outline is None):
        draw.text((xstart, y), text, color, fnt)

    else:
        draw.text((xstart, y), text, 'white', fnt,
                  stroke_width=3, stroke_fill='white')
        draw.text((xstart, y), text, color, fnt)

    return (textlen, textheight)

def center_text(draw, x, y, width, text, font_size, color='black',
                bgcolor=None, border=2,
                overflow=None,
                is_bold=False, is_italic=False,
                force="",
                font_size_percent=5.0,
                font_fixed_family="helv", font_tt_family="FreeSans",
                outline=None):

    fnt = find_font(font_size, is_bold, is_italic, force,
              font_size_percent, font_fixed_family, font_tt_family)


    if ((fnt is not None) and (text is not None)):
        retVal = center_text_f(draw, x, y, width, text, fnt, color,
                             bgcolor, border, overflow, outline)

    else:
        retVal = None

    return retVal


def small_ending(draw, x, y, text, font_size,
                 color = 'black', italic=False, bold=False, num_ending=1,
                 right_just=False, width=-1,
                 font_fixed_family="helv", font_tt_family="FreeSans"):

    font_size = int(font_size)  # Force integer only

    fnt = find_font(font_size, is_italic=italic, is_bold=bold, 
                    font_fixed_family=font_fixed_family, font_tt_family=font_tt_family)

    half_fnt = find_font(int(font_size * 0.65), is_italic=italic, is_bold=bold, 
                         font_fixed_family=font_fixed_family, font_tt_family=font_tt_family)

    # Hack to not display last hypen smaller
    if (text == "---"):
        text = "---  "

    retVal = None

    if (text is not None):
        most_of_text = text[:-num_ending]
        bbox = fnt.getbbox(most_of_text)

        textlen = bbox[2] - bbox[0]
        ending_len = half_fnt.getlength(text[-num_ending:])

        if (italic):
            yoff = font_size // 6
            xoff = font_size // 16
        else:
            yoff = bbox[1] + 1
            yoff = 1
            xoff = 0

        #if (yoff < 4):
        #    yoff = 4

        # If right justification is requested (and if a valid width is given)
        #  then recompute the starting point
        if ((right_just) and (width > 0)):
            pad_x = width - textlen - ending_len - xoff

            if (pad_x > 0):
                x = x + pad_x
            else:
                pad_x = 0

        else:
            pad_x = 0

        draw.text((x, y), most_of_text + " ", color, fnt)
        draw.text((x + textlen + xoff, y+yoff), text[-num_ending:],
                  color, half_fnt)

        full_len = textlen + xoff + ending_len + pad_x

        retVal = full_len

    return retVal


#
#-----------------------------------------------------------------
#
def add_text_to_icon(draw, text, xloc, yloc, xsize, ysize):
        print_it("Adding text", text)

        if (text.isnumeric()):
            text = text + "% "

        # Convert a single line / into two lines
        if ("/" in text):
            (before,after) = text.split("/", 1)
            text = before.strip() + "\n  " + after.strip()

        font_size = 18

        done = False
        while (not done):
            fnt = find_font(font_size, is_italic=True)
            bbox = draw.multiline_textbbox((xloc, yloc), text, fnt)

            text_width  = bbox[2] - bbox[0]
            text_height = bbox[3]- bbox[1]

            if ((text_width <= xsize) and (text_height <= ysize)):
                done = True
            elif (font_size < 10):
                done = True
            else:
                font_size = font_size - 1

        xloc = xloc + (xsize - text_width)
        yloc = yloc + (ysize - text_height) - 3

        draw.rectangle((xloc, yloc, xloc + text_width, yloc + text_height),
                       fill='white')
        draw.multiline_text((xloc, yloc), text, 'black', fnt)


def put_icon_file_at(image, draw, icon, xloc, yloc, size,
                border=0, border_color='black', text=None,
                flip=False):
    retVal = None
    
    print_it("Placing icon", icon, "at", xloc, ",", yloc, " with size", size)
    
    size = int(size)   # No floating point sizes, please

    if ((icon is not None) and (icon != "")):

        icon_data = PIL.Image.open(icon)
        retVal = True

    else:
        icon_data = None

    if icon_data is not None:
        # Remove any white space around edges
        icon_data = icon_data.crop(icon_data.getbbox())

        # Flip the image left to right if "flip" is true
        #  (used for the person on the beach)
        if flip:
            icon_data = icon_data.transpose(method=PIL.Image.Transpose.FLIP_LEFT_RIGHT)

        size = size - 4

        if (icon_data.height > icon_data.width):
            ysize = size
            xsize = int(size * icon_data.width / icon_data.height)
        else:
            # Compute the y size to be proportional to the xsize (preserving h/w ratio)
            xsize = size
            ysize = int(size * icon_data.height / icon_data.width)

        # Compensate for the border
        xloc = int(xloc + border)
        yloc = int(yloc + border)
        ysize = ysize - 2 * border
        xsize = xsize - 2 * border

        if (border > 0):
            # Note, these use the now adjusted xloc/yloc/xsize/ysize numbers
            im2 = PIL.Image.new("RGB",
                                (xsize+2*border, ysize+2*border),
                                color=border_color)

            image.paste(im2, (xloc-border, yloc-border))

        # Make the icon fit the space
        icon_data = icon_data.resize((xsize, ysize))

        # Center vertically if necessary
        if (icon_data.height < size):
            yloc = yloc + ((size - icon_data.height) // 2)

        # Center horizontally if necessary
        if (icon_data.width < size):
            xloc = xloc + ((size - icon_data.width) // 2)

        transparent_color = icon_data.info.get("transparency", None)

        # Check an alternate way to see if there is a "transparent" color
        limits =  icon_data.getextrema()

        if (len(limits) > 3):
            has_alpha = (limits[3][0] != limits[3][1])
        else:
            has_alpha = False

        if ((has_alpha) or (transparent_color is not None)):
            image.paste(icon_data, (xloc,yloc), icon_data)

        else:
            image.paste(icon_data, (xloc,yloc))

        #draw.rectangle([xloc, yloc, xloc+xsize, yloc+ysize], outline='red')

        if (text is not None):
            text_x_loc = int(xloc + (xsize * 0.6))
            text_y_loc = int(yloc + (ysize * 0.5))

            text_x_size = int(xsize * 0.5)
            text_y_size = int(ysize * 0.4)

            add_text_to_icon(draw, text,
                             text_x_loc, text_y_loc,
                             text_x_size, text_y_size)

    return retVal
#
#-----------------------------------------------------------------
#

def put_icon_at(image, draw, url, xloc, yloc, size, url_size=None,
                border=0, border_color='black'):

    if ((url is None) or (url == "")):
        return None

    icons = alt_icons.get_better_icon(
                        weather_rest.fix_noaa_icon_filename(url),
                        size)

    # No match, or more than two matches?  If so, just use the original
    if ((icons is None) or (len(icons) == 0) or (len(icons) > 2)):
        icons = [ (weather_rest.get_icon_filename(url, url_size), None) ]

    else:
        # Force no border if using alternate icons
        border = 0

    if (len(icons) == 1):
        retVal = put_icon_file_at(image, draw, icons[0][0], xloc, yloc,
                                  size, border, border_color, icons[0][1])

    elif (len(icons) == 2):
        sm_offset = 10
        draw.line( [(xloc+size - sm_offset, yloc + sm_offset),
                    (xloc + sm_offset,yloc+size-sm_offset) ], fill="black" )

        # Draw both (but always without any borders)

        retVal = put_icon_file_at(image, draw, icons[0][0], xloc, yloc,
                                  int(size * 0.5), 0, border_color,
                                  icons[0][1])

        retVal = put_icon_file_at(image, draw, icons[1][0],
                                  int(xloc + size * 0.50),
                                  int(yloc + size * 0.4),
                                  int(size * 0.5), 0, border_color,
                                  icons[1][1])

    else:
        retVal = None

    return retVal




#
#-----------------------------------------------------------------
#
def draw_rectangle(x=0, y=0, height=0, width=0, color='white'):
    draw.rectangle([x, y, x+width, y+height], fill=color)

    return y+height


#
#-----------------------------------------------------------------
#

def draw_ipaddr(x=0, y=0, font_size=8, color='black',
                bottom_left=False, last_octet_only=False):
    
    init_screen_if_needed()
    ipaddr = extra_utils.get_my_ipaddr(allow_no_inet=True)

    # last_octet_only
    #  Only display the period and the last decimal number in the IP addr
    if last_octet_only and "." in ipaddr:
        (rest,last) = ipaddr.rsplit(".", 1)
        ipaddr = "." + last
        
    if ipaddr is not None:
        print_it("IP address =", ipaddr)

        fnt = find_font(font_size, is_italic=True)

        bbox = fnt.getbbox(ipaddr)

        if bbox is not None:
            (left, top, right, bottom) = bbox

            if bottom_left:
                x = x - (right - left) - 3
                y = y - (bottom - top) - 3

            draw.text((x,y), ipaddr, color, fnt)


def draw_param(x=0, y=0, param='wifi_ssid', font_size=12, color='black',
               prefix="", postfix=""):

    init_screen_if_needed()
    param = sta_parameters.get_param(param)

    if ((param is not None) and (param != "")):
        fnt = find_font(font_size)
        draw.text((x,y), str(prefix)+str(param)+str(postfix), color, fnt)

#
#-----------------------------------------------------------------
#
def draw_curr_obs(x=0, y=0, width=None, height=None,
                  font_size=42, stations=None, items="all"):

    width  = get_var_value("width", width)
    height = get_var_value("height", height)

    curr_obs = get_curr_obs(stations)

    temp  = curr_obs.get("temp")
    humid = curr_obs.get("humidity")
    loc   = curr_obs.get("loc")

    # Truncate location
    if " - " in loc:
        (loc,dummy) = loc.split(" - ", 1)

    other_font_size = int(font_size * 0.35)

    sm_font_size = font_size // 5
    smfnt = find_font(sm_font_size)

    if (("loc" in items) or ("all" in items)):

        if (loc is not None):
            center_text(draw, x, y, width, loc, other_font_size,
                          color='black', is_bold=True)

            y = y + other_font_size

    if (("title" in items) or ("all" in items)):
        center_text(draw, x, y, width, "CURRENTLY", font_size // 4, is_bold=True)

        y = y + int(font_size * 0.4)

    if (("temp" in items) or ("all" in items)):

        draw.text((x,y), "TEMP ", 'black', smfnt)
        y = y + sm_font_size

        if (temp is not None):
            fnt = find_font(font_size)
            draw.text((x+10, y), temp[:-1], 'black', fnt)

            new_x = fnt.getlength(temp[:-1])

            put_icon_file_at(im, draw,
                     alt_icons.get_or_make_svg_icon("svg_set2/thermometer-fahrenheit.svg",font_size-8),
                     x+new_x+8, y+2, font_size-4)

        y = y + font_size

    if (("line" in items) or ("all" in items)):

        draw.line( [(x,y), (x+width), y], fill='black' )
        y = y + 3

    if (("humidity" in items) or ("all" in items)):

        draw.text((x,y), "Humidity ", 'black', smfnt)
        fnt = find_font(font_size, is_italic=True)
        y = y + 2

        if (humid is not None):
            draw.text((x+10, y), humid[:-1], 'black', fnt)
            new_x = fnt.getlength(humid[:-1])

            put_icon_file_at(im, draw,
                             alt_icons.get_or_make_svg_icon("svg_set2/humidity.svg",
                                                            font_size-2),
                             x+new_x+10, y+12, font_size-10)




def draw_line_on_triangle(draw, x1, y1, x2, y2, color, percent_center, width=1):
    x_diff = abs(x1 - x2)
    # Fudge the half based on percent_center (which should be 0..100)
    #   (aka 50 = real half)
    x_half = min(x1, x2) + (x_diff * percent_center / 100.0)

    # Calculate the slope and the y intercept
    m = (y2 - y1) / (x2 - x1)
    c = y1 - m * x1

    y_half = m * x_half + c
    y_bottom = max(y1, y2)

    print_it("Drawing vertical line @" , x_half, y_half, y_bottom, "color=", color)
    draw.line([x_half, y_bottom, x_half, y_half], fill=color, width=width)

def dots_under_lines(x1, y1, x2, y2,numdots = None):
    #print(xbefore, x1, y1, x2, y2,  xafter, numdots)

    random.seed(0)  # Force the same "randomness" each time
                    # so that partial updates don't include this
                    
    x_low  = int(min(x1, x2))
    x_high = int(max(x1, x2))
    
    y_low  = int(min(y1, y2))
    y_high = int(max(y1, y2))

    if numdots is None:
        numdots = int((x_high - x_low) * 2)  # Avg 3 dots per line

    # Calculate the slope and the y intercept
    m = (y2 - y1) / (x2 - x1)
    c = y1 - m * x1

    tot_dots = 0
    while tot_dots < numdots:
        x = random.randint(x_low, x_high)
        y = random.randint(y_low, y_high)

        if (y > (m*x + c)):
                draw.point((x,y), fill='black')
                tot_dots += 1

def dots_under_rectangle(x1, y1, x2, y2, numdots = None):
    xlow = int(min(x1, x2))
    xhi  = int(max(x1, x2))
    ylow = int(min(y1, y2))
    yhi  = int(max(y1, y2))

    random.seed(0)  # Force the same "randomness" each time
                    # so that partial updates don't include this


    if numdots is None:
        numdots = int((xhi - xlow) * 1)  # Avg 1 dots per line

    for i in range(numdots):
        x = random.randint(xlow, xhi)
        y = random.randint(ylow, yhi)
        
        draw.point((x,y), fill='black')
        
def draw_sm_person(xloc, yloc, xmax = None, ymax=None):
    print("Small person @", xloc, ",", yloc)
    
    person = [  "...***...",
                "..*****..",
                "..*****..",
                "...***...",
                "*...*...*",
                ".*******.",
                "....*....",
                "....*....",
                "...*.*...",
                ".**...**." ]


    y_offset = 0
    for line in person:
        x_offset = 0

        for char in line:
            if (char != "."):
                x = xloc+x_offset
                y = yloc+y_offset

                # Now make sure you are not clipped
                if (((xmax is None) or (xmax <= x)) and
                    ((ymax is None) or (ymax <= y))):

                    draw.point((xloc+x_offset, yloc+y_offset), fill='black')

            x_offset = x_offset + 1

        y_offset = y_offset + 1

def draw_lg_person(xloc, yloc, xmax, ymax, icon, flip=False):
    print("Large person @", xloc, ",", yloc, "(y)size=", ymax)
    
    if xmax is None and ymax is not None:
        xmax = ymax

    if ymax is None and xmax is not None:
        ymax = xmax

    #if xloc is not None:
    #    xloc = xloc - xmax 
        
    #if yloc is not None:
    #    yloc = yloc - ymax // 2

    retVal = put_icon_file_at(im, draw,
                               alt_icons.get_or_make_svg_icon(icon, ymax),
                               xloc, yloc, ymax, flip=flip)

    if retVal is None:
        print("Reverting to small icon")

        draw_sm_person(xloc, yloc, xmax, ymax)

def draw_person(xloc, yloc, xmax = None, ymax=None, icon=None, flip=False):

    if icon is None or ymax is None:
        draw_sm_person(xloc, yloc, xmax, ymax)

    elif ymax <= 12:
        draw_sm_person(xloc, yloc, xmax, ymax)

    else:
        draw_lg_person(xloc, yloc, xmax, ymax, icon, flip)

def draw_waves(draw, xloc, yloc, size, num, line_between=0):
    size = size // 2

    xloc = xloc - size//2
    yloc = yloc - size//2

    if (line_between > 0):
        draw.line([xloc+size//2, yloc+size*2, xloc+line_between+size//2, yloc+size*2], fill='black')
        xloc = xloc + line_between

    for i in range(0,num//2):
        draw.arc([xloc, yloc, xloc+size, yloc+size*2],
                 0, 90, fill='black')

        xloc = xloc + size // 2
        draw.arc([xloc, yloc + size , xloc+size, yloc+size*3],
                 270, 360, fill='black')

        xloc = xloc + size // 2

        if (line_between > 0):
            draw.line([xloc+size//2, yloc+size*2, xloc+line_between+size//2, yloc+size*2], fill='black')
            xloc = xloc + line_between

    if (num % 2 == 1):
        draw.arc([xloc, yloc, xloc+size, yloc+size*2],
                 0, 90, fill='black')


def print_tidetime(tide_str, x, y, font_size,
                   color='black', font=None, monospace=False):


    # If a "font" is defined, the monospace option is ignore
    #  (the font choice controls that)
    
    if font is None:
        
        if monospace:
            font_fixed_family="cour"
            font_tt_family="FreeMono"
            is_bold = True
            
        else:
            font_fixed_family="helv"
            font_tt_family="FreeSans"
            is_bold = False

    tide_str = tide_str.strip()

    # Single digit hour and monospaced?  Convert to two spaces
    if monospace and len(tide_str) < 11:
        tide_str = tide_str.replace(" ", "  ", 1)
        
    width = small_ending(draw, x, y, tide_str, font_size, color,
                         font_fixed_family=font_fixed_family,
                         font_tt_family=font_tt_family, num_ending=2, bold=is_bold)

    return width


def compute_y(x1, y1, x2, y2, new_x):
    # Calculate the slope and the y intercept
    m = (y2 - y1) / (x2 - x1)
    c = y1 - m * x1

    new_y = m * new_x + c

    return int(new_y)

def draw_tide_diagram(x, y, width, height,
              icon_height, beach_width,
              raw_percent, is_going_up=True,
                      high_tide_cross=True, 
              icon="svg_misc/person-walking.svg"):

    #print("tide_diagram", raw_percent, is_going_up)
    
    y_high = y + icon_height + 4
    y_low  = y + height

    ocean_width  = width - beach_width
    ocean_height = height - icon_height - 4

    if is_going_up:
        x_low       = x
        x_high      = x + width - beach_width

        direction     = 1

        beach_end     = x_high     # Beach end always is where water slope meets straight
        beach_start   = x + width
        
        # Force scale to be 10%-100% (make sure to see small sliver of water)
        percent = 0.9 * raw_percent + 0.1
    
    else:
        # Going down
        beach_start = x
        beach_end   = x + beach_width

        direction     = -1

        x_high       = beach_end
        x_low        = x + width

        # Force scale to be 10%-100% (make sure to see small sliver of water)
        percent = 0.1 + 0.9 * (1.0 - raw_percent)

    x_water_end   = x_low + direction * int(ocean_width * percent)
    x_water_start = x_low + direction * int(0.1 * ocean_width)
    x_water_mid   = x_low + direction * int(0.55 * ocean_width)

    y_water_end   = compute_y(x_low, y_low, x_high, y_high, x_water_end)
    y_water_mid   = compute_y(x_low, y_low, x_high, y_high, x_water_mid)

    #print("x_low", x_low)
    #print("x_high", x_high)
    #print("x_water_end", x_water_end)

    #print("\nbeach_start", beach_start)
    #print("beach_end", beach_end)

    #print("\ny_low", y_low)
    #print("y_high", y_high)

    # Draw the beach
    draw.line((beach_start, y_high, beach_end, y_high), fill='black')
    draw.line((beach_end, y_high, beach_end, y_low), fill='black', width=2)
    draw.line((beach_start, y_high, beach_start, y_low), fill='black')

    # Draw the top of the ocean
    draw.line((x_low, y_low, x_high, y_high), fill='black', width=2)

    # Speckle the beach (the flat part)
    dots_under_rectangle(beach_start, y_low, beach_end, y_high)
    
    # Speckle the beach towards the ocean (diff # of dots on purpose)
    dots_under_lines(x_low, y_low, x_high, y_high)

    # Draw the "bottom" of the ocean (and beach)
    draw.line((x, y_low, x+width, y_low), fill='black')

    # Near high water? Then "X" out the beach
    if percent > 0.9 and high_tide_cross:
        draw.line((beach_start, y_low, beach_end, y_high), fill='black', width=2)
        draw.line((beach_end, y_low, beach_start, y_high), fill='black', width=2)

    # Color in the water portion
    # Fill from the bottom/left
    # (triangle shaped)
    draw.polygon([x_low, y_low,
                  x_water_end, y_water_end,
                  x_water_end, y_low], fill='black')


    # Draw the low point (always in white)
    y_water_start = compute_y(x_low, y_low, x_high, y_high, x_water_start)
    draw.line((x_water_start, y_water_start, x_water_start, y_low), fill='white')

    # Draw the half point (in white if percent is > 0.5)
    if (percent < 0.55):
        color = 'black'
    else:
        color = 'white'

    draw.line((x_water_mid, y_low, x_water_mid, y_water_mid), fill=color)

    person_height = y_high - y
    person_width = person_height // 2

    x_beach1 = min(beach_start, beach_end)
    x_beach2 = max(beach_start, beach_end)
    x_beach_width = x_beach2 - x_beach1
    
    draw_person(x_beach1 + x_beach_width //2 - person_width // 2,
                y,
                ymax=person_height,
                icon="svg_misc/person-walking.svg",
                flip = is_going_up)



            
def textWlen(loc, s, font, fill):
    #print("loc=", loc, "s=", s, "font=", font, "fill=", fill)
    
    draw.text(loc, s, font=font, fill=fill)

    return draw.textlength(s, font)

def print_tides_inline(x, y, width, height, font_size, diagram_width, last_tide, future_tides):
    orig_x = x

    # Center the text vertically if necessary
    if (height > font_size):
        time_y = y + (height - font_size) // 2

    title_font_size = (height - 2) // 2
    title_fnt = find_font(title_font_size, is_bold = True)

    # Display only if we have last tide data
    if last_tide:
        len1 = textWlen((x,y),                   "Last", font=title_fnt, fill='black')
        len2 = textWlen((x,y+title_font_size+1), "Tide", font=title_fnt, fill='black')

        x = x + max(len1, len2) + font_size

        len1 = print_tidetime(weather_rest.tide_to_str(last_tide), x, time_y, font_size)

        diagram_x = x + len1 + 5
        x = diagram_x + diagram_width + 5

    if future_tides:
        len1 = textWlen((x,y),                   "Next",  font=title_fnt, fill='black')
        len2 = textWlen((x,y+title_font_size+1), "Tides", font=title_fnt, fill='black')

        x = x + max(len1, len2) + font_size

        len1 = print_tidetime(weather_rest.tide_to_str(future_tides[0]), x, time_y, font_size)

        x = x + len1 + 5

        if (len(future_tides) > 1):
            e_size = 5
            y_middle = y + height // 2

            # A circle between the two
            draw.ellipse([x, y_middle-e_size//2, x+e_size, y_middle+e_size//2], fill='black')

            x = x + e_size + 5

            len1 = print_tidetime(weather_rest.tide_to_str(future_tides[1]), x, time_y, font_size)

            x = x + len1

    return (diagram_x, x - orig_x)

def print_tide_table(x, y, width, height, font_size, last_tide, future_tides):
    print("tide table: x=", x, "y=", y, "height=", height, "width=", width)
    
    # Draw the outer box
    draw.polygon(((x,y), (x,y+height), (x+width,y+height), (x+width, y)), outline='black', width=1)

    # Column 2 is 2/3 of width

    col1_width = width // 3
    col2_width = width - col1_width - 8
    
    print("col2_width=", col2_width, "font_size=", font_size)
    col2_width = min(col2_width, int(4 * font_size))
    print("col2_width=", col2_width)
    
    row2_y     = y + int(0.4 * height)
    row2_height = height - (row2_y - y)
    
    # Draw a vertical line between the two columns
    draw.line((x + col1_width + 2, y, x + col1_width + 2, y+height), fill='black', width=1)

    # Draw a horizontal line between "last tide" area and "next tides" areas
    draw.line((x, row2_y, x + width, row2_y), fill='black', width=1)

    # Indent the text a bit
    x = x + 5

    # Keep a right pad too (if possible)
    if (width > 0):
        width = width - 10

    col1_x = x
    col2_x = x + col1_width + 4

    title_fnt_size = font_size - 4
    title_fnt = find_font(title_fnt_size, is_bold = True)

    # Vertically center the "Last Tide" words
    title_y = y + (row2_y - y) // 2 - font_size + 2
    text_y  = y + (row2_y - y) // 2 - font_size // 2


    #len1 = textWlen((x,title_y),            "Last", font=title_fnt, fill='black')
    #len2 = textWlen((x,title_y+title_fnt_size+1),"Tide", font=title_fnt, fill='black')

    center_text(draw, x, title_y, col1_width, "Last", title_fnt_size, is_bold=True)
    center_text(draw, x, title_y+title_fnt_size+1, col1_width, "Tide", title_fnt_size, is_bold=True)

    if last_tide:
        #print_tidetime(weather_rest.tide_to_str(last_tide), col2_x, text_y,
        #               font_size, col1_len=3*font_size, width=col2_width, right_just=True)
        print_tidetime(weather_rest.tide_to_str(last_tide), col2_x, text_y,
                       font_size, monospace=True)

    title_y = row2_y + row2_height // 2 - title_fnt_size - 2
    text_y  = row2_y + row2_height // 2 - int(1.25 * font_size)
    
    #len1 = textWlen((x,title_y),            "Next", font=title_fnt, fill='black')
    #len2 = textWlen((x,title_y+title_fnt_size+1),"Tides", font=title_fnt, fill='black')

    center_text(draw, x, title_y, col1_width, "Next", title_fnt_size, is_bold=True)
    center_text(draw, x, title_y+title_fnt_size+1, col1_width, "Tides", title_fnt_size, is_bold=True)

    if future_tides:
        #print_tidetime(weather_rest.tide_to_str(future_tides[0]), col2_x, text_y,
        #               font_size, width=col2_width, col1_len=font_size,right_just=True)
        
        #print_tidetime(weather_rest.tide_to_str(future_tides[1]), col2_x, text_y + int(1.5 * font_size),
        #               font_size, width=col2_width, col1_len=font_size, right_just=True)

        print_tidetime(weather_rest.tide_to_str(future_tides[0]), col2_x, text_y,
                       font_size, monospace=True)
        
        print_tidetime(weather_rest.tide_to_str(future_tides[1]), col2_x, text_y + int(1.25 * font_size),
                       font_size, monospace=True)

def draw_tide(x=0, y=0, width=0, height=0, tide_station=None,
              font_size = None,
              high_tide_cross=True,
              mode='inline'):

    tide_station = get_var_value("tide_station", tide_station)

    if (font_size is None):
        
        if (mode == 'inline'):
            font_size = int(height * 0.7)
            
        else:
            font_size = height // 10
            
                
    if (tide_station is None):
        tide_station = def_tide_station

    # Get the next tides (this should only go the website once a day)
    tides = weather_rest.get_last_and_next_tides(tide_station)

    if tides is not None:
        last_tide = tides[0]
        future_tides = tides[1]
        ok = True
    else:
        last_tide = None
        future_tides = None
        ok = False

    if ok:

        is_going_up = (future_tides[0]['type'] == 'H')

        # How far are we in the tide period (as a percentage)?
        raw_percent = (datetime.datetime.now() - last_tide['datetime']) / \
                  (future_tides[0]['datetime'] - last_tide['datetime'])

        table_height = int(font_size * 4)
        table_width  = font_size * 11

        graph_height = height - table_height

        if (mode == 'inline'):
               
            diagram_width = width // 4
            (diagram_x, len_x) = print_tides_inline(x, y, width, height, font_size, diagram_width, last_tide, future_tides)
            draw_tide_diagram(diagram_x, y + 2, diagram_width - 2, height - 4,
                              height // 5, max(diagram_x // 6, 10),
                              raw_percent, is_going_up)

        elif (mode == 'v_top'):

            draw_tide_diagram(x+10, y, width-20, graph_height-8,
                              graph_height // 3, width // 6,
                              raw_percent, is_going_up,
                              high_tide_cross)

            print_tide_table(x + width//2 - table_width//2,
                             y + graph_height + 4, table_width, table_height, font_size,
                             last_tide, future_tides)

        elif (mode == 'v_bottom'):

            draw_tide_diagram(x + 10, y + table_height - 8, width - 20, graph_height,
                              graph_height // 3, width // 6,
                              raw_percent, is_going_up)

            print_tide_table(x + width//2 - table_width//2, y, table_width, table_height, font_size,
                             last_tide, future_tides)

        elif (mode == 'table_only'):
            print_tide_table(x, y, width, table, font_size,
                             last_tide, future_tides)

        elif (mode == 'diagram_only'):
            draw_tide_diagram(x, y, width, height,
                              height // 5, width // 6,
                              raw_percent, is_going_up)            

def draw_sunrise_sunset(x=0, y=0, width=0, font_size=18, lat=None, lon=None):
    # Find the sunrise and once a day

    font_size = int(font_size)

    (sunrise, sunset) = weather_rest.get_sunrise_sunset(lat,lon)


    draw.line([x + width//2 - 4, y + font_size,
               x + width//2 + 4, y + 6], fill='black')

    y = y + 4

    icon_size = font_size + 20
    ss_x = x + 6

    put_icon_file_at(im, draw,
                     alt_icons.get_or_make_svg_icon("svg_set2/sunrise.svg",
                                                    icon_size),
                     ss_x, y-8, icon_size)

    ss_x = ss_x + font_size + 28

    small_ending(draw, ss_x, y,
                 sunrise.strftime("%I:%M%p").lstrip("0"),
                 font_size, num_ending=2)

    ss_x = x + width//2 + 15

    put_icon_file_at(im, draw,
                     alt_icons.get_or_make_svg_icon("svg_set2/sunset.svg",
                                                    icon_size),
                      ss_x, y-8, icon_size)

    ss_x = ss_x + font_size + 28

    small_ending(draw, ss_x, y,
                 sunset.strftime("%I:%M%p").lstrip("0"),
                 font_size, num_ending=2)

def draw_date(x=0, y=0, width=0, font_size=18, is_italic=True):
    now = datetime.datetime.now()
    curr_date = f"{now:%A}, {now:%B} {now.day}"
    
    center_text(draw, x, y, width, curr_date + " ", font_size, is_italic=is_italic)
    
def draw_calendar(x=0, y=0, width=0, height=0, font_size=18,
                  show_private=False, show_title=True, show_date=True):

    init_screen_if_needed()
    width  = get_var_value("width", width)

    fnt     = find_font(font_size)
    cal_time_fnt = find_font(int(font_size * 0.8))

    cur_y_line = y

    if (show_title):
        center_text(draw, x, cur_y_line, width, "CALENDAR",
                    int(font_size *0.75), is_bold=True)

        cur_y_line += font_size

    if (show_date):

        # A little extra space between title and date, please
        if (show_title):
            cur_y_line += font_size * 0.2

        draw_date(x, cur_y_line, width, font_size)
        
        cur_y_line += font_size

    # A little more blank space after title and/or date and items
    if (show_date or show_title):
        cur_y_line += font_size * 0.25

    y_bottom = y + height

    cal_lines = cal_helper.cal_to_str(show_private).split("\n")

    cal_lines_offset_min = font_size + 2
    cal_lines_offset_max = 1.5 * cal_lines_offset_min

    cal_lines_offset = (y_bottom- cur_y_line) // (len(cal_lines) + 1)

    cal_lines_offset = max(cal_lines_offset, cal_lines_offset_min)
    cal_lines_offset = min(cal_lines_offset, cal_lines_offset_max)

    max_time_len = cal_time_fnt.getlength("99:99pm")
    text_x = x + 6 + max_time_len + 8

    for line in cal_lines:
        # Don't overwrite the sunrise/sunset area
        if (cur_y_line + font_size < y_bottom):

            # The fixed font doesn't support non-ASCII characters,
            #  so for now, just remove them

            # https://stackoverflow.com/questions/23680976/python-removing-non-latin-characters
            line = re.sub(r'[^\x00-\x7F]', '', line)

            if (line == ""):
                pass

            elif ((line[0] == "*") or (line[0] == "(")):
                is_bold = (line[0] == "*")
                is_italic = (line[0] == "(")

                line = line.strip("*")

                if ((line[0] == "(") and (line[-1] == ")")):
                    line = " " + line[1:-1] + " "

                if ((line[0] == "_") and (line[-1] == "_")):
                    line = line.strip("_")
                    underline = True

                else:
                    underline = False

                if ((is_italic or is_bold) and (not underline)):
                    line_font_size = font_size - 3
                else:
                    line_font_size = font_size

                center_text(draw, x, cur_y_line, width, line,
                            line_font_size,
                            is_bold=is_bold, is_italic=is_italic,
                            overflow='shrink')

                if (underline):
                    x_start = x + 40
                    x_end = x + width - 40
                    y_line = cur_y_line + font_size + 2

                    draw.line([x_start, y_line, x_end, y_line], fill='black')
                    cur_y_line = cur_y_line + 2 # Add some space after the line

            else:
                if ((" - " in line) and (line.index(" - ") > 4)):
                    (time, text) = line.split(" - ", 1)

                    # Right justify the time
                    time_len = cal_time_fnt.getlength(time)
                    time_x = x + 6 + max_time_len - time_len

                    draw.text((time_x, cur_y_line+2), time, 'black', cal_time_fnt)
                    draw.text((text_x, cur_y_line), text, 'black', fnt)

                else:
                    draw.text((x+6, cur_y_line), line, 'black', fnt)

            cur_y_line += cal_lines_offset


    # Return the new starting location
    return cur_y_line


#
#------------------------------------------------------
#
def shorten_and_dedup_alerts(alerts):
    s_alerts = []

    for one_alert in alerts:

        short = weather_rest.shorten(one_alert['short'])

        # Dedup
        if (short not in s_alerts):
            s_alerts.append(short)

    return s_alerts
#
#------------------------------------------------------
#
def draw_alerts(x=0, y=0, width=None, height=None,
                zone=None, alert_num=0, max_alerts=1,
                font_size=16, at_bottom=0):

    init_screen_if_needed()

    width  = get_var_value("width", width)
    height  = get_var_value("height", height)

    #width = width - 4
    #height = height - 4
    #x = x + 2
    #y = y + 2

    if (zone is None):
        zone = def_alert_zone

    # Show one alert if necessary
    alerts = weather_rest.get_alerts(zone)

    if (alerts is not None):
        alerts = shorten_and_dedup_alerts(alerts)

        tot_alerts = len(alerts)

        if (tot_alerts > max_alerts):
            tot_alerts = max_alerts

        if (at_bottom):
            need_height = tot_alerts * (font_size + 2)

            if (need_height < height):
                y = y + (height - need_height)
                height = need_height

        height_used = 0
        alert_num = 0

        print_it("Num alerts", tot_alerts)
        #print_it("Alerts:", alerts)

        while ((height >= height_used + font_size) and
               (alert_num < tot_alerts)):

            # If found, display the first alert in REVERSE color
            alert = alerts[alert_num]
            print_it("***", alert, " @ y=", y)

            center_text(draw, x, y, width,
                        alert,
                        font_size, 'white', bgcolor='black', border=2,
                        is_bold=True, overflow = "truncate")

            height_used = height_used + font_size + 2
            y = y + font_size + 2

            alert_num = alert_num + 1

    return height_used

def text_forecast(x=0, y=0,
                  day=0,
                  zone=None,
                  items="all",
                  width=None,
                  height=None,
                  font_size=20,
                  summary_font_size=None, smaller_font_size=None):

    init_screen_if_needed()
    forecast = get_forecast(zone)

    width  = get_var_value("width", width)
    height  = get_var_value("height", height)

    if (items == "all"):
        items = "summary/detail"

    if (smaller_font_size is None):
        smaller_font_size = font_size - 2

    if (summary_font_size is None):
        # If both detail and summary requested, give summary a larger font

        if ("detail" in items):
            summary_font_size = font_size + 2
        else:
            summary_font_size = font_size

    if ((forecast is not None) and (len(forecast) > day)):
        # Handle the "long" version of today's forecast.  Allow it
        #  to be 1-3 lines.  If multiple lines, then try to break
        #  a little evenly (so not just 1 or 2 words on second/third line)
        #

        forecast_l = weather_rest.shorten(forecast[day]['long'], 1)
        forecast_s = weather_rest.shorten(forecast[day]['short'])

        if ("summary" in items):
            print_it("S:", forecast_s)
            
            center_text(draw, x, y, width,
                    forecast_s[:48], summary_font_size,
                    is_bold=True, overflow="truncate")

            y = y + summary_font_size
            height = height - summary_font_size


        if ("detail" in items):
            print_it("L:", forecast_l)

            wrap_trunc_and_maybe_center(draw,
                                        x, y,
                                        width, height,
                                        forecast_l,
                                        font_size, smaller_font_size)

#
#----------------------------------------------------
#
def draw_forecast(x=0, y=0, width=None, height=None, zone=None, day=0,
                  items="all",
                  font_size=28, small_font_size=None, text_font_size=18,
                  icon_size=None):

    width  = get_var_value("width", width)
    height = get_var_value("height", height)

    date_y = None

    forecast = get_forecast(zone)

    if (small_font_size is None):
        small_font_size = int(font_size // 2)

    if (icon_size is None):
        icon_size = int (width * 0.7)

    hilo_width = font_size * 2.25
    if (hilo_width > width):
        hilo_width = width

    hilo_offset = (width - hilo_width) // 2

    smfnt = find_font(small_font_size)

    textlen1 = smfnt.getlength('Hi')
    textlen2 = smfnt.getlength('Lo')

    if (textlen1 < textlen2):
        textlen1 = textlen2

    if (day < len(forecast)):
        high    = forecast[day]['hi']
        low     = forecast[day]['low']
        name    = forecast[day]['name']
        short   = forecast[day]['short'][:14]
        dayicon = forecast[day]['dayicon']

        if (dayicon == ""):
            dayicon = forecast[day]['nighticon']


        #
        # No high?  This could be because it's now in the late evening/night/early morning
        #  (and NOAA only shows the "Tonight" forecast.  So, grab the high for today's forecast
        #
        #   (only do this after midnight)
        #
        if (((high is None) or (high == "")) and (day == 0)):
            hour = datetime.datetime.now().hour

            if (hour < 12):
                high = forecast[1]['hi']

        if (day == 0):
            print_it("Name", name)

            name = name.upper()         # CONVERT TODAYS NAME TO CAPS

        if (("date" in items) or ("all" in items)):
            center_text(draw, x, y, width, name, small_font_size,
                        is_bold=True, overflow = "truncate")

            date_y = y
            y = y + small_font_size + 2

        if (("icon" in items) or ("all" in items)):
            if (icon_size is None):
                icon_size = int(width * 0.7)

            icon_indent = (width - icon_size)//2

            put_icon_at(im, draw, dayicon, x+icon_indent,
                    y, icon_size, url_size="small", border=1)

            # Redraw date if icon might of overriden it
            if (date_y is not None):
                center_text(draw, x, date_y, width, name, small_font_size,
                            is_bold=True, overflow = "truncate")

            y = y + icon_size

        if (("text" in items) or ("all" in items)):
            center_text(draw, x, y, width,
                        short, text_font_size, overflow='truncate')

            y = y + text_font_size

        if (("hi" in items) or ("all" in items)):
            draw.text((x+hilo_offset,y+2), 'Hi', 'black', smfnt)

            small_ending(draw, x+textlen1+hilo_offset, y, high, font_size,
                 right_just=True, width=hilo_width-textlen1)

            y = y + font_size

        if (("line" in items) or ("all" in items)):
            draw.line( [(x+hilo_offset,y), (x+hilo_width+hilo_offset), y], fill='black' )

            y = y + 5

        if (("low" in items) or ("all" in items)):
            draw.text((x+hilo_offset,y+2), "Lo", 'black', smfnt)

            small_ending(draw, x+textlen1+hilo_offset, y, low, font_size,
                     right_just=True, width=hilo_width-textlen1)


#
#------------------------------------------------------------------
#
def get_var_value(varname, value = None):

    if (value is None):
        value = cmd_dispatch.get_var_value(varname, quiet=True)

    return value


#
#------------------------------------------------------------------
#

def screen_size(width = None, height=None, use_color=False):
    global im
    global draw

    width  = get_var_value("width", width)
    height = get_var_value("height", height)
    use_color = get_var_value("color", use_color)

    if ((width is not None) and (height is not None)):
        im = blank_image(width, height, use_color)

        draw = PIL.ImageDraw.Draw(im)

    else:
        print("Trying to create a screen of unspecified size", file=sys.sterr)

def init_screen_if_needed():
    if (im is None):
        screen_size()

def draw_hline(x=0, y=0, width=None, fill='black', line_width=1 ):
    init_screen_if_needed()

    width = get_var_value("width", width)

    if (width is not None):
        draw.line( [(x,y), (x+width,y) ], fill="black", width=line_width)

    else:
        print("Trying to draw a hline with no width", file=sys.stderr)


def draw_vline(x=0, y=0, height=None, fill='black', line_width=1 ):
    init_screen_if_needed()

    height = get_var_value("height", height)

    if (height is not None):
        draw.line( [(x,y), (x,y+height) ], fill="black", width=line_width)

    else:
        print("Trying to draw a hline with no height", file=sys.stderr)


def draw_line(x1=0, y1=0, x2=0, y2=0, fill='black', line_width=1 ):
    init_screen_if_needed()

    draw.line( [(x1,y1), (x2,y2) ], fill="black", width=line_width)

def draw_text(x=0, y=0, s="", font_size=12, color='black',
              is_italic=False, is_bold=False):

    init_screen_if_needed()
    fnt = find_font(font_size, is_bold, is_italic)

    (l,t,r,b) = draw.textbbox((x,y), text=s, font=fnt)
    draw.text((x,y), text=s, font=fnt)

    return b


def draw_center_text(x=0, y=0, s="", width=-1, font_size=12, color='black',
                bgcolor=None, border=2,
                is_italic=False, is_bold=False,
                overflow=None, force="", outline=None):
    init_screen_if_needed()

    if (width <= 0):
        width = im.width

    center_text(draw, x=x, y=y, width=width, text=s,
                font_size=font_size, color=color,
                bgcolor=bgcolor, border=border, overflow=overflow,
                is_bold=is_bold, is_italic=is_italic,
                force=force,
                font_size_percent=5.0,
                font_fixed_family="helv", font_tt_family="FreeSans",
                outline=outline)


def draw_hwo(x=0, y=0, width=0, height=0,
             station=None, zone=None,
             force_output=True,
             add_title=False,
             remove_current_alert=False,
             font_size=18, color='black',
             is_italic=False, is_bold=False):

    end_y = y
    
    init_screen_if_needed()
    #fnt = find_font(font_size, is_bold, is_italic)

    s = weather_rest.get_hazard_outlook(station, zone, force_output)

    if remove_current_alert:
        m = re.search(r"^\.\.\.(.+)\.\.\.\s+(.+)\s*$", s, flags=re.DOTALL)

        if m is not None:
            
            # Don't leave blank if there is nothing else
            if m.group(2) != "":
                s = m.group(2)
            else:
                s = m.group(1).title()   # Convert all UPPER CASE to Title Case
        
    s = re.sub(r"(^|\n)([^\n]*:)\n", r"\1*\2*\n", s)

    if add_title:
        if s != "" or force_output:
            title_font_size = int(font_size * 1)
            
            center_text(draw, x, y, width,
                        "Hazardous Weather Outlook",
                        title_font_size,
                        is_bold=True, is_italic=True)
            
            y = y + int(title_font_size * 1.5)
            
            height = height - int(title_font_size * 1.5)
    
    if s != "":

        # Unwrap the text
        s = s.replace("\n", "~")
        s = s.replace("~~", "\n\n")
        s = s.replace("~", " ")
        
        end_y = wrap_trunc_and_maybe_center(draw,
                                            x, y,
                                            width, height,
                                            s,
                                            font_size,
                                            mode="left, top")


    return end_y
        
    
#
#------------------------------------------------------------------
#
#
#   Small routine to show the randomly created PIN if no web password is configured
#   (Used by display-no-internet.txt)
#
def get_pin_line(full_line=True, extra_space=False):
    s = ""

    if sta_parameters.needs_pin():
        if full_line:
            s = "Use \"" + sta_parameters.get_pin() + "\" (without the quotes) as the password."
        else:
            s = "Password: " + sta_parameters.get_pin()

        if extra_space:
            s = " " + s
        
    return s
#
#------------------------------------------------------------------
#

def init_cmd_dispatcher():
    cmd_dispatch.add_function("screen_size", screen_size)
    cmd_dispatch.add_function("hline", draw_hline)
    cmd_dispatch.add_function("vline", draw_vline)
    cmd_dispatch.add_function("line", draw_line)
    cmd_dispatch.add_function("rectangle", draw_rectangle)

    cmd_dispatch.add_function("draw_text", draw_text)
    cmd_dispatch.add_function("center_text", draw_center_text)

    cmd_dispatch.add_function("current_time", draw_time)
    cmd_dispatch.add_function("time", draw_time)
    cmd_dispatch.add_function("time24", draw_time24)
    
    cmd_dispatch.add_function("draw_tide",    draw_tide)
    cmd_dispatch.add_function("draw_ipaddr",  draw_ipaddr)
    cmd_dispatch.add_function("draw_param",   draw_param)
    cmd_dispatch.add_function("draw_alerts",  draw_alerts)
    cmd_dispatch.add_function("draw_sunrise_sunset", draw_sunrise_sunset)

    cmd_dispatch.add_function("draw_calendar", draw_calendar)
    cmd_dispatch.add_function("current_date", draw_date)
    cmd_dispatch.add_function("text_forecast", text_forecast)
    cmd_dispatch.add_function("current_obs", draw_curr_obs)
    cmd_dispatch.add_function("draw_forecast", draw_forecast)
    cmd_dispatch.add_function("draw_hwo", draw_hwo)

    cmd_dispatch.add_function("get_pin_line", get_pin_line)

#
#  get_forecast
#
#       Given a zone (and perhaps a backup zone) get the upcoming forecast
#
#   backup_zone is for when the normal /gridpoint forecast is misbehaving for some reason.
#       You can use the /zone URL, but it contains less information (and covers a greater area)
#   
#

def get_forecast(forecast_zone = None, backup_zone=None):

    # Use the default zone if no zone is given
    if (forecast_zone is None) or (forecast_zone == ""):

        if def_forecast_zone is None:
            f = None
            
        else:
            forecast_zone = def_forecast_zone
            backup_zone = def_alert_zone

    if forecast_zone is not None:

        if forecast_zone in forecast:
            f = forecast[forecast_zone]

        else:
            forecastData = weather_rest.get_noaa_forecast(forecast_zone)
            f = weather_rest.create_abr_forecast(forecastData)
            

            if (f is None) or (len(f) == 0):
                
                if (backup_zone is not None):
                    forecastData = weather_rest.get_noaa_backup_forecast(backup_zone)
                    f = weather_rest.create_abr_forecast(forecastData)
            
            forecast[forecast_zone] = f


    return f

def get_curr_obs(stations = None):
    curr_obs = {}

    if (stations is None):
        stations = def_stations

    if (stations is not None):

        (temp, humidity, wText, windChill, heatIndex, name, icon) = \
                   weather_rest.get_latest_obs(stations)

        curr_obs['temp']        = temp
        curr_obs['humidity']    = humidity
        curr_obs['windchill]']  = windChill
        curr_obs['heatindex']   = heatIndex
        curr_obs['loc']         = name
        curr_obs['icon']        = icon
        curr_obs['text']        = wText

    return curr_obs

def init_weather_data():
    global forecast

    global def_forecast_zone
    global def_tide_station
    global def_alert_zone
    global def_stations

    (def_forecast_zone, def_alert_zone, def_stations, def_tide_station) = \
                  weather_rest.retrieve_local_fields()

    forecast = {}



def draw_from_config_to_image(conf_file):
    global im
    global draw

    im = None
    draw = None

    init_weather_data()
    init_cmd_dispatcher()

    f = open(conf_file)
    for l in f:
        if DEBUG > 1:
            print(">>>", l.rstrip())
            
        cmd_dispatch.dispatch_line(l)

    f.close()

    return im

def draw_from_config_to_file(conf_file, out_file):
    global im
    global draw

    im = None
    draw = None
    init_weather_data()
    init_cmd_dispatcher()

    if ((conf_file is not None) and (conf_file != "")):
        f = open(conf_file)
        for l in f:
            if DEBUG > 1:
                print(">>>", l.rstrip())
                    
            cmd_dispatch.dispatch_line(l)

        f.close()
    else:
        cmd_dispatch.dispatch('draw_text(s="Could not find display page - check control panel")')


    if (im is not None):
        im.save(out_file)


def draw_oh_no(msg="Oh no! Something bad happened internally",
              width=WIDTH, height=HEIGHT):

    im = PIL.Image.new("L", (width, height), color="white")
    draw = PIL.ImageDraw.Draw(im)
    fnt = PIL.ImageFont.load_default()

    draw.text((20,20), msg, 'black', fnt)

    return im
#
#------------------------------------------------------------------
#


if (__name__ == "__main__"):
    extra_utils.set_default_dir()  # For testing using IDLE on Windows

    display = sta_parameters.find_active_file("active-display")
    #display = sta_parameters.find_file("display-no-internet")

    if (display is not None):
        draw_from_config_to_file(display, r"C:\temp\test.jpg")

    else:
        print("Could not find an active display file", file=sys.stderr)
