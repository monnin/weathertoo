import alt_icons
import cmd_dispatch
import weather_rest

import datetime
import os
import sys

alt_icons_path = "icons/"

html_file = None

forecast = None
alerts   = None
tides    = None
tide_station = None

curr_obs = {}

def output_time():
    now = datetime.datetime.now()

    hh = now.hour
    mm = now.minute

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

    time = str(hh).rjust(2) + ":" + str(mm).zfill(2) + " " + ampm

    return time


def output_curr_obs(obj='temp'):
    if (obj in curr_obs):
        s = curr_obs[obj]
    else:
        s = ""
        print("Invalid curr_obs() obj of", obj, file=sys.stderr)

    # Replace degree symbol with HTML version
    if (s[-1] == "°"):
        s = s[:-1] + "&deg;"
        
    return s


def output_forecast(day=0, obj='short'):
    s = ""

    if ((day >= 0) and (day < len(forecast))):
        if (obj == 'short'):
            s = weather_rest.shorten_forecast(forecast[day]['short'])
            
        elif (obj == 'long'):
            s = weather_rest.shorten_forecast(forecast[day]['long'])
            
        elif (obj == 'hi'):
            s = forecast[day]['hi']

        elif (obj == 'low'):
            s = forecast[day]['low']

        elif (obj == 'name'):
            s = forecast[day]['name']

        else:
            print("Invalid obj passed to output_forecast()", obj, file=sys.stderr)
            
    else:
        print("Invalid day passed to output_forecast()",day, file=sys.stderr)

    # Replace degree symbol with HTML version
    if (s[-1] == "°"):
        s = s[:-1] + "&deg;"
        
    return s

def output_forecast_icon(day=0, time='prefer_day', style='orig'):
    s = ""
    extra = ""
    
    if ((time != 'day') and (time != 'night') and (time != "prefer_day"):
        print("Invalid time passed to output_forecast()",time, file=sys.stderr)

    if ((day >= 0) and (day < len(forecast))):
        icon = time + 'icon'
        
        # prefer_day - Use the day icon if it exists, otherwise use the
        #            -  night version
        if (time == "prefer_day"):
        
            if ((forecast[day]['day'] is not None) and
                (forecast[day]['day'] != "")):
        
                time = "day"
            else:
                
                time = "night"
                
        if (style == 'orig'):
            link = forecast[day][icon]
            
        elif (style == 'orig_large'):
            link = forecast[day][icon]
            link = link.replace("medium", "large")

        elif (style == 'alt'):
            link = forecast[day][icon]

            icons = alt_icons.get_better_icon(
                weather_rest.fix_noaa_icon_filename(link),
                0,
                False)

            # One better choice?  Then use it
            if ((icons is not None) and (len(icons) == 1)):
                link = alt_icons_path + icons[0][0]
                extra = "class=\"filter-white\""

        elif (style == 'alt_large'):
            link = forecast[day][icon]

            icons = alt_icons.get_better_icon(
                weather_rest.fix_noaa_icon_filename(link),
                0,
                False)

            # One better choice?  Then use it
            # (else use the "large" version of the original)
            if ((icons is not None) and (len(icons) == 1)):
                link = alt_icons_path + icons[0][0]
                extra = "class=\"filter-white\""
                
            else:
                link = forecast[day][icon]
                link = link.replace("medium", "large")
        else:
            print("Invalid style passed to output_forecast_icon()",
                  style, file=sys.stderr)
            link = None

        if (link is not None):
            s = "<img src=\"" + link + "\" " + extra + " />"
        
    else:
        print("Invalid day passed to output_forecast()",day, file=sys.stderr)

    return s

# tideNum = 0 == last
# tideNum = 1 == next

def output_tide_time(num=0):
    global tides
    
    if (tides is None):
        (prev_tide, next_tides) = weather_rest.get_last_and_next_tides(tide_station)
        tides = [ prev_tide ] + next_tides
        
    s = ""
    
    if ((tides is not None) and (num >=0) and (num < len(tides))):
        s = weather_rest.tide_to_str(tides[num], addspace=True)
        
    elif (tides is None):
        print("Tide data not returned by web provider", file=sys.stderr)
        
    else:
        print("tide number is not currently valid", file=sys.stderr)
        
    return s
#
#--------------------------------------------------------------------------
#
def output_sun(obj='rise'):
    (sunrise, sunset) = weather_rest.get_sunrise_sunset()

    if (obj == 'rise'):
        s = weather_rest.format_short_time(hour=sunrise.hour,
                                           minu=sunrise.minute,
                                           addspace=True)
    elif (obj == 'set'):
        s = weather_rest.format_short_time(hour=sunset.hour,
                                           minu=sunset.minute,
                                           addspace=True)
    else:
        print("Invalid obj to output_sun", obj, file=sys.stderr)
        s = ""

    return s


def output_alerts(obj='all'):
    s = ""
    
    if ((alerts is not None) and (len(alerts) > 0)):
        if (obj != 'all'):
            obj = int(obj)  # Convert to integer

            if ((obj >= 0) and (obj < len(alerts))):
                s = weather_rest.shorten_forecast(alerts[obj]['short'])
        else:
            for one_alert in alerts:
                if (s != ""):
                    s = s + "\n<br />\n"

                s = s + weather_rest.shorten_forecast(one_alert['short'])

    return s

#
#--------------------------------------------------------------------------
#

#

def init_cmd_dispatcher():
    cmd_dispatch.add_function("current_time", output_time)
    cmd_dispatch.add_function("current_obs", output_curr_obs)
    cmd_dispatch.add_function("forecast", output_forecast)
    cmd_dispatch.add_function("forecast_icon", output_forecast_icon)
    cmd_dispatch.add_function("tide_time", output_tide_time)
    cmd_dispatch.add_function("output_sun", output_sun)
    cmd_dispatch.add_function("output_alerts", output_alerts)
    
def init_weather_data():
    global forecast
    global alerts
    global curr_obs
    global tide_station
    
    (forecastLoc, county, stations, tide_station) = \
                  weather_rest.retrieve_local_fields()
    
    forecastData = weather_rest.get_noaa_forecast(forecastLoc)
    forecast = weather_rest.create_abr_forecast(forecastData)

    alerts = weather_rest.get_alerts(county)
    
    (temp, humidity, wText, windChill, heatIndex, name, icon) = \
               weather_rest.get_latest_obs(stations)
    
    curr_obs['temp']        = temp
    curr_obs['humidity']    = humidity
    curr_obs['windchill]']  = windChill
    curr_obs['heatindex']   = heatIndex
    curr_obs['loc']         = name
    curr_obs['icon']        = icon
    curr_obs['text']        = wText
    
    
def output_weather_to_html(template, outfile):


    init_cmd_dispatcher()
    init_weather_data()

    f_in = open(template)
    f_out = open(outfile + ".new","w")
    
    for l in f_in:
        s = cmd_dispatch.replace_inline(l)
        f_out.write(s)

    f_in.close()
    f_out.close()

    os.replace(outfile + ".new", outfile)


if (__name__ == "__main__"):
    output_weather_to_html("lib/html/weather-template.html",
                           "html/test.html")

