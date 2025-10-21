import datetime
import os
import sys
import time

import PIL.Image
import PIL.ImageChops

#import epaper
import waveshare_epd
import waveshare_epd.epd7in5_V2


import bitmap_weather
import cmd_dispatch
import sta_parameters
import extra_utils

DEBUG = True

def main():
    last_im = None
    internet_down_time = None
    
    # Mostly for first-time runs
    sta_parameters.check_and_update_timezone()
    
    #epd = epaper.epaper('epd7in5_V2').EPD()
    epd = waveshare_epd.epd7in5_V2.EPD()
    
    # Initial clear (so if crashes during the first pass the screen is blank)
    epd.init()
    epd.init_fast()
    epd.init_part()
    epd.Clear()
    epd.sleep()

    while (True):
        now = datetime.datetime.now()

        # BCD-ify the time
        time_now = now.hour * 100 + now.minute

        # 11:30pm to 5:00am  - update every 20 minutes (supresses display of clock)
        # 5:00am to 5:00pm   - update every 3 minutes
        # 5:00pm to 11:30 pm - update every 5 minutes
        
        if (time_now > 2330):
            sleep_time = 20 * 60
        elif (time_now < 440):
            sleep_time = 20 * 60
        elif (time_now > 1700):
            sleep_time = 5 * 60
        else:
            sleep_time = 3 * 60
        
        if (sleep_time > 5 * 60):
            hide_time = 1
        else:
            hide_time = 0
            
        add_seconds = sleep_time // 2

        cmd_dispatch.add_var_value("hide_time", hide_time)
        cmd_dispatch.add_var_value("add_seconds", add_seconds)

        #
        # Special case: if the Internet is not available, display alt screen
        #
        if (extra_utils.internet_is_up_w_hold()):
            internet_down_time = None
            display = sta_parameters.find_active_file("active-display")
            
        else:
            display = sta_parameters.find_file("display-no-internet")
            sleep_time = 90
            
            # Did we just lose the Internet (even on startup?)
            if internet_down_time is None:
                internet_down_time = now
            
            # If still down, every half-hour, try restarting the network
            #   (but only if on a Linux system)
            if now - internet_down_time > datetime.timedelta(minutes=30):
                if sys.platform == "linux":
                    os.system("sudo systemctl restart wpa_supplicant.service")
                    
                internet_down_time  = now

        if ((display == "") or (display is None)):
            display = sta_parameters.find_file("display-not-found")
            sleep_time = 90

        # Still nothing to display?  Display a base image
        if ((display == "") or (display is None)):
            im = bitmap_weather.draw_oh_no("Oh No! Display config file not found!")
            sleep_time = 90
            
        else:
            im = bitmap_weather.draw_from_config_to_image(display)

        # Rotate the screen as necessary
        rotate = sta_parameters.get_param("rotate")
        
        if (rotate == "180"):
            im = im.transpose(PIL.Image.ROTATE_180)
        elif (rotate == "90"):
            im = im.transpose(PIL.Image.ROTATE_90)
        elif (rotate == "270"):
            im = im.transpose(PIL.Image.ROTATE_270)
        
        # See if all blank
        extremea = im.convert("L").getextrema()
        
        if (extremea[0] == extremea[1]):
            blank = True
        else:
            blank = False

        if (not blank):
            epd.init()
            epd.display(epd.getbuffer(im))
            epd.sleep()
            
        else:
            # Don't update the display, but try again in 1 minute
            sleep_time = 60   # Try again in one minute

        # Compute how long the loop took to complete
        
        after = datetime.datetime.now()
        diff = after - now

        # This is the time of the next wake up with the given sleep period
        #   added (but also removing how long the loop takes)
        next_wake = after + datetime.timedelta(seconds=sleep_time-diff.total_seconds())

        # Round up or down to the top of the minute
        if (next_wake.second > 30):
            # Round up
            next_wake = next_wake + datetime.timedelta(minutes=1)

        # Zero out the second "hand"
        next_wake = next_wake.replace(second=0)

        after = datetime.datetime.now()
        sleep_time = next_wake - after

        # Sleep that amount of time (but never less than once a minute)             
        time.sleep(max(sleep_time.total_seconds(), 60))

        last_im = im

main()
