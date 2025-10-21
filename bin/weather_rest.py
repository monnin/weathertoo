import datetime
import dateutil
import json
import os
import re
import shelve
import sys
import time

# pip3 install suntime
import suntime

# pip3 install requests
import requests

# pip3 install requests_cache
# or apt install python3-requests-cache
import requests_cache

import sta_parameters

USER_AGENT = None
DEBUG = 1

mySession = None
permCache = None
stationNameDB = None
iconDir = "cache/icons"

resetable_parms = [ "forecast_zone", "alert_zone", "obs_stations",  "tide_station" ]


def print_it(*args,**kwargs):
    
    if (DEBUG):
        print(*args, **kwargs)
        
def make_cache_dir(subdir=None):
    if (not os.path.exists("cache")):
        os.mkdir("cache")

    if (subdir is not None):
        subpath = os.path.join("cache", subdir)
        if (not os.path.exists( subpath )):
            os.mkdir(subpath)
        
def cache_it(func):
    
    def wrapper(*args, **kwargs):
        
        global permCache

        make_cache_dir()
        
        if (permCache is None):
            permCache = shelve.open('./cache/perm-cache')

        cache_item = func.__name__ + str(argsca)

        if (cache_item in permCache):
            #print_it("Cached")
            
            res = permCache[cache_item]
            
        else:
            #print_it("Not cached")
            res = func(*args, **kwargs)

            permCache[cache_item] = res

        return res

    return wrapper

#
#--------------------------------------------------------------------------------
#
def shorten(f, level=2):
    today = datetime.datetime.now().strftime("%b %d")
    
    print_it("***", f)
    
    origf = f

    f = re.sub(r"\bnortheast(ern)?\b", "NE", f, 0, re.I)
    f = re.sub(r"\bsoutheast(ern)?\b", "SE", f, 0, re.I)
    f = re.sub(r"\bnorthwest(ern)?\b", "NW", f, 0, re.I)
    f = re.sub(r"\bsouthwest(ern)?\b", "SW", f, 0, re.I)

    f = re.sub(r"\bnorth(ern)?\b", "N", f, 0, re.I)
    f = re.sub(r"\bsouth(ern)?\b", "S", f, 0, re.I)
    f = re.sub(r"\beast(ern)?\b", "E", f, 0, re.I)
    f = re.sub(r"\bwest(ern)?\b", "W", f, 0, re.I)

    f = re.sub(r"\b(Jan)uary\b", r"\1", f, 0, re.I)
    f = re.sub(r"\b(Feb)uary\b", r"\1", f, 0, re.I)
    f = re.sub(r"\b(Mar)ch\b",   r"\1", f, 0, re.I)
    f = re.sub(r"\b(Apr)il\b",   r"\1", f, 0, re.I)

    f = re.sub(r"\b(Jun)e\b",    r"\1", f, 0, re.I)
    f = re.sub(r"\b(Jul)y\b",    r"\1", f, 0, re.I)
    f = re.sub(r"\b(Aug)ust\b",  r"\1", f, 0, re.I)
    f = re.sub(r"\b(Sept)ember\b", r"\1", f, 0, re.I)
    f = re.sub(r"\b(Oct)ober\b", r"\1", f, 0, re.I)
    f = re.sub(r"\b(Nov)ember\b", r"\1", f, 0, re.I)
    f = re.sub(r"\b(Dec)ember\b", r"\1", f, 0, re.I)

    # Days of week
    f = re.sub(r"\b(Mon)day\b",    r"\1", f, 0, re.I)
    f = re.sub(r"\b(Tue)sday\b",   r"\1", f, 0, re.I)
    f = re.sub(r"\b(Wed)nesday\b", r"\1", f, 0, re.I)
    f = re.sub(r"\b(Thur)sday\b",  r"\1", f, 0, re.I)
    f = re.sub(r"\b(Fri)day\b",    r"\1", f, 0, re.I)
    f = re.sub(r"\b(Sat)urday\b",  r"\1", f, 0, re.I)
    f = re.sub(r"\b(Sun)day\b",    r"\1", f, 0, re.I)
    
    # Remove the space after the time
    f = re.sub(r"\s(\d+)\s+([AP]M)\b", r" \1\2", f, 0, re.I)
    
    # Remove the timezone
    f = re.sub(r"\s[ECMP][SD]T\b", "", f, 0, re.I)

    # Remove the "issued by NWS ..."
    f = re.sub(r"\sissued by NWS \S+ \S+", "", f, 0, re.I)

    # Remove the "by NWS ..."
    f = re.sub(r"\sby NWS \S+ \S+", "", f, 0, re.I)

    # Change THROUGH to THRU
    f = re.sub(r"\bTHROUGH\b", r"THRU", f, 0)
    f = re.sub(r"\bthrough\b", r"thru", f, 0)
    
    # Remove extra date (if it is today)
    f = re.sub(r"\b" + today + r" at\s+", "", f, 0, re.I)

    # Change REMAINS IN EFFECT FROM to FROM
    f = re.sub(r"\s+(remains\s+)?in effect (from)\b", r" \2", f, 0, re.I)

    # Change REMAINS IN EFFECT UTIL to UNTIL
    f = re.sub(r"\s+(remains\s+)?in effect (until)\b", r" \2", f, 0, re.I)

    # Change THIS EVENING TO to TO
    f = re.sub(r"\s+this evening (to)\b", r" \1", f, 0, re.I)
    
    if (level > 1):
        # Change SLIGHT CHANCE to SL.CHANCE
        f = re.sub(r"(\s*)(sl)ight (chance)\b", r"\1\2.\3", f, 0, re.I)
    
    if (origf != f):
        print_it("Changed from: ", origf)
        print_it("Changed to:   ", f)
        
    return f
#

#--------------------------------------------------------------------------------
#

def init_session_w_cache():
    global mySession

    make_cache_dir()
    
    #
    # Allow for responses to have a cache-control option,
    #  but if none is returned, assume we can cache "forever"
    #
    mySession = requests_cache.CachedSession('./cache/web_cache',
                                             backend='sqlite',
                                             serializer='json',
                                             cache_control=True,
                                             expire_after=-1)

    ## Probably not necessary - but nice
    #try:
    #    mySession.remove_expired_responses()

    # remove_expired_responses() sometimes has a bug with "pickle.loads"
    #except TypeError:
    #    pass
    
def traverse(dict1, key1):
    if ((dict1 is not None) and (key1 in dict1)):
        res = dict1[key1]
    else:
        res = None

    return res

def get_rest_data(url, retry=1):  ## TODO: CHANGE to 3
    global mySession
    global USER_AGENT

    if (USER_AGENT is None):

        email = sta_parameters.get_param("email_addr")

        if (email != ""):
            if (" " in email):
                USER_AGENT = {'User-agent' : + '(' + email + ')' }
                    
            else:
                USER_AGENT = {'User-agent' :
                              '(pythonWeatherApp ' + email + ')'}
        else:
            print("*** Please set email address in control panel first", file=sys.stderr)
            sys.exit(1)
              
    sleep = 2
    
    if (mySession is None):
        init_session_w_cache()

    req = None
    
    # Make multiple attempts if necessary
    while ((retry > 0) and ((req is None) or (req.status_code >= 500))):
        
        try:
            req = mySession.get(url, headers=USER_AGENT, timeout=30)
            
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
                requests.exceptions.Timeout) as e:
            req = None

        if (req is not None):
            print_it(req.status_code, ":", url)
            
            if (req.status_code >= 300):
                print_it(req.headers)
                print_it("---")
                print_it(req.text)

        # Error from the server?  If so, then try again after a pause
        if ((req is None) or (req.status_code >= 500)):
            retry = retry - 1
            
            time.sleep(sleep)
            sleep = sleep * 2     # Next time, sleep twice as long
            
    res = None

    if (req is not None):
        #print_it("URL:", url)
        #print_it("Cached?:", req.from_cache)
        
        #print_it("Headers (response): ", req.headers)

        try:
            res = json.loads(req.text)
            
        except json.decoder.JSONDecodeError:
            res = None

    return res

#
#
#
def fix_noaa_icon_filename(url):
    if (url is not None):
        filename = url
        
        if ("/" in url):
            if ("https://api.weather.gov/icons/" in filename):
                filename = filename.replace("https://api.weather.gov/icons/","")
                filename = filename.replace("land/", "")
            else:                        
                # Only keep the last portion of the URL (after the final slash)
                (extra,filename) = url.rsplit("/", 1)

        # Make it 'easier' to save it on disk as a file
        filename = filename.replace("/","--")
        filename = filename.replace("?","--")
        
    else:
        filename = None
        
    return filename

#
#----------------------------------------------------------------------------------------------------
#

def get_icon_filename(url, force_size=None):
    global mySession

    if (mySession is None):
        init_session_w_cache()
    
    # Create the icons directory if necessary
    make_cache_dir("icons")
    
    # Did the caller want a specific size?  If so, fix the URL
    if ((force_size is not None) and (url is not None)):
        if ("?size=" in url):
            (url,extra) = url.split("?size=")
            
        url = url + "?size=" + force_size

    # Did the server give a locally referenced source?

    if url.startswith("/"):
        url = "https://api.weather.gov" + url
        
    # The URL should be a full path - otherwise ignore it
    if (url is not None):
        print("Looking for URL", url)
        
        filename = fix_noaa_icon_filename(url)
        
        #fullpath = os.path.join(iconDir, filename)
        fullpath = iconDir + "/" + filename

        # Copy the icon file if necessary
        if ((os.path.exists(fullpath) == False) or
            (os.path.getsize(fullpath) < 1)):
            
            try:
                req = mySession.get(url, headers=USER_AGENT,
                                    stream=True, timeout=30)
            
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.ReadTimeout,
                    requests.exceptions.Timeout,
                    requests.exceptions.MissingSchema) as e:
                req = None
                print("Request to", url, "failed", str(e))
                
            if (req is not None):
                #print_it(url,req)
                
                f = open(fullpath, "wb")
                # Grab the file in parts
                
                for one_part in req.iter_content():
                    f.write(one_part)
                
                f.close()
                
            else:
                print("Could not access URL", url, file=sys.stderr)
                fullpath = ""
    else:
        # Force the fullpath to be blank if there was a problem
        fullpath = ""
        
    return fullpath

#
#----------------------------------------------------------------------------------------------------
#

# https://www.weather.gov/documentation/services-web-api
# https://weather-gov.github.io/api/general-faqs

# Get the latitude and longitude from US Census Data
# https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html

# https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=18+tidal+ct%2C+wells%2C+maine+04090&benchmark=Public_AR_Current&format=json
def addr2latlon(addr):
    base = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address="
    # 4600+Silver+Hill+Rd%2C+Washington%2C+DC+20233
    ending = "&benchmark=Public_AR_Current&format=json"

    addr = addr.replace(" ","+")
    addr = addr.replace(",","%2C")

    res = get_rest_data(base + addr + ending)

    res = traverse(res, 'result')
    res = traverse(res, 'addressMatches')
        
    if res is not None and len(res) > 0:
        res = res[0]    # Take the first match
        x = res['coordinates']['x']
        y = res['coordinates']['y']

        # latitude = y
        # longitude = x
        
        result = (y,x)
        
    else:
        result = (None, None)
        
    return result

#
#----------------------------------------------------------------------------------------------------
#
def latlon2city(lat,lon):
    base = "https://api.3geonames.org/"
    url = base + str(lat) + "," + str(lon) + ".json"

    res = get_rest_data(url)

    nearest = traverse(res, 'nearest')
    osm = traverse(res, 'osmtags')

    result = osm["name"] + ", " + nearest["prov"] + " " + osm["state"] + " (near " + nearest["name"] + ")"

    return result

#
#----------------------------------------------------------------------------------------------------
#


def get_sunrise_sunset(lat=None, lon=None):
    sunrise = None
    sunset = None

    if ((lat is None) or (lon is None)):
        l = sta_parameters.get_param("lat_lon")

        if ("," in l):
            (lat,lon) = l.split(",")
            
            lat = float(lat)
            lon = float(lon)

    if ((lat is not None) and (lon is not None)):
        sun = suntime.Sun(lat,lon)

        #sunrise = sun.get_local_sunrise_time(time_zone=dateutil.tz.tzlocal())
        #sunset = sun.get_local_sunset_time(time_zone=dateutil.tz.tzlocal())

        sunrise = sun.get_sunrise_time().astimezone(dateutil.tz.tzlocal())
        sunset = sun.get_sunset_time().astimezone(dateutil.tz.tzlocal())
                           
        print("Sunrise", sunrise, "Sunset", sunset, "for lat", lat, "lon", lon)
        
    return (sunrise, sunset)

#
#--------------------------------------------------------------------
#

def format_short_time(date_and_time_s = None,
                      hour = None,
                      minu = None,
                      addspace=False, fillhour=False):

    err = False
    
    if (date_and_time_s is not None):
        (date,time) = date_and_time_s.split(" ", 1)
        (hour,minu) = time.split(":")
        hour = int(hour)
        
    elif ((hour is None) and (minu is None)):
        err = True
        print("Must specify a str or two numbers to format_short_time",
              file=sys.stderr)
        
    else:
        minu = str(minu)
        
        # Add the leading zero if necessary
        if (len(minu) == 1):
            minu = "0" + minu

    if (hour == 0):
        hour = "12"
        ampm = "AM"
        
    elif (hour < 12):
        hour = str(hour)
        ampm = "AM"
    elif (hour == 12):
        hour = str(hour)
        ampm = "PM"
    else:
        hour = str(hour-12)
        ampm = "PM"

    if ((fillhour) and (len(hour) == 1)):
        hour = " " + hour
        
    if (addspace):
        s = " "
    else:
        s = ""

    if (not err):
        r = hour + ":" + minu + s + ampm
    else:
        r = ""

    return r


#
#----------------------------------------------------------------------------------------------------
#

def tide_to_str(tideEntry, addspace=False):
    entry_time = format_short_time(tideEntry['t'], addspace).strip()
    
    if (tideEntry['type'] == 'L'):
        hilo = "Lo:"
    else:
        hilo = "Hi:"

    return hilo + " " + entry_time

#
#----------------------------------------------------------------------------------------------------
#
def get_nearest_tide_loc(x,y):
    x = float(x)
    y = float(y)
    
    near_name = None
    near_id = None
    near_dist_sq = None
    
    url = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=tidepredictions&expand=tidepredoffsets&units=english"

    res = get_rest_data(url)

    res = traverse(res, 'stations')

    if (res is not None):
        for one_station in res:
            s_lat = one_station['lat']
            s_lon = one_station['lng']
            s_name = one_station['name']
            s_id = one_station['id']

            s_dist_sq = (s_lat - y)**2 + (s_lon - x)**2

            # Is this a better choice for nearest station?
            #  (or is it the first option through the loop)
            if ((near_dist_sq is None) or (near_dist_sq > s_dist_sq)):
                near_name = s_name
                near_id = s_id
                near_dist_sq = s_dist_sq

    return (near_id, near_name)


# https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date=20221010&range=30&station=8419317&product=predictions&datum=STND&time_zone=lst_ldt&interval=hilo&units=english&format=json

def get_last_and_next_tides(tide_station, allow_cache=True):
    last_tide = None
    last_tide_time = 0
    
    now = datetime.datetime.now()
    tomorrow = now + datetime.timedelta(days=1)

    yesterday = now - datetime.timedelta(days=1)
    
    yesterday_str = yesterday.strftime("%Y%m%d")
    tomorrow_str = tomorrow.strftime("%Y%m%d")

    url_p1 = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" + \
             "begin_date="

    url_p2 = "&end_date="
    
    url_p3 = "&product=predictions&datum=STND&time_zone=lst_ldt&" + \
             "interval=hilo&units=english&format=json&station="

    url = url_p1 + yesterday_str + url_p2 + tomorrow_str + url_p3 + tide_station
        
    #
    # Is this a new day or did the caller disallow the use of cached data?
    # ...if so, then go get today's and tomorrow's tides from NOAA
    #
    if ((not allow_cache) or
        (getattr(get_next_tides, 'url', None) != url)):
        
        res = get_rest_data(url)

        res = traverse(res, 'predictions')
        
        # res is an array, in the format
        # "{"t":"2022-10-10 05:50", "v":"14.399", "type":"L"},{"t":"2022-10-10 12:11", "v":"25.003", "type":"H"},{"t":"2022-10-10 18:17", "v":"14.028", "type":"L"}
        print_it(res)

        if (res is not None):
            # Cache the collected info for the next time
            #  (don't cache a blank reply)
            get_next_tides.url = url
            get_next_tides.tides = res

    else:
        # Cache of today's information is fine, so use it
        res = get_next_tides.tides
    
    res2 = []

    if (res is not None):
        
        # Remove previous tides
        for one_item in res:
            tide_time = datetime.datetime.strptime(one_item['t'], "%Y-%m-%d %H:%M")
            one_item['datetime'] = tide_time
            
            # In the future?  If so, keep it
            if (tide_time > now):
                res2.append(one_item)
                
            elif ((last_tide is None) or (tide_time > last_tide_time)):
                last_tide = one_item
                last_tide_time = tide_time

    return (last_tide, res2)

def get_next_tides(tide_station, allow_cache=True):
    res = get_last_and_next_tides(tide_station, allow_cache)

    if (res is not None):
        res = res[1] # Future tides only

    return res

def get_tide_station_name(tide_station):
    url = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/"
    url = url + str(tide_station) + ".json"

    res = get_rest_data(url)
    name = None

    if (res is not None):
        res = traverse(res, 'stations')
        
        if (res is not None):
            station = res[0]
            extra = station["affiliations"]
            
            if (extra != ""):
                extra = " (" + extra + ")"
                
            name = station["name"] + " " + station["state"] + extra

    return name
#
#----------------------------------------------------------------------------------------------------
#

def get_gridloc(gridloc):

    print_it("Gridloc (old):", gridloc)
    
    if ("gridpoint/" in gridloc):
        (extra,gridloc) = gridloc.split("gridpoint/")
        if ("/forecast" in gridloc):
            gridloc = gridloc[:gridloc.index("/forecast")]

    elif ("gridpoints/" in gridloc):
        (extra,gridloc) = gridloc.split("gridpoints/")
        if ("/forecast" in gridloc):
            gridloc = gridloc[:gridloc.index("/forecast")]
 
    elif ("/forecast" in gridloc):
        #gridloc = gridloc[:gridloc.index("/forecast")]
        (extra,gridloc) = gridloc.split("forecast/")

    print_it("Gridloc (new):", gridloc)

    return gridloc

def get_closest_stations(forecast_loc, limit=1):

    if ("/" in forecast_loc):
        (wfo,xy) = forecast_loc.split("/", 1)

        url = "https://api.weather.gov/gridpoints/" + wfo + "/" + xy + "/stations?limit=" + str(limit)
        res = get_rest_data(url)

        print_it("Got:", res)
        
        res = traverse(res, 'features')
        result = ""

        count = 0
        for feature in res:
            one_item = traverse(feature, 'properties')
            s = one_item['stationIdentifier'] + " - " + one_item['name']

            # limit=# doesn't seem to be working, so handle it ourselves
            if (count < limit):
                    
                if (result != ""):
                    result = result + "\n"
                result = result + s
                
                count = count + 1
        
        
    else:
        result = None    # Invalid gridpoint

    return result


#
#----------------------------------------------------------------------------------------------------
#
def get_alert_zone_info(zone):
    url = "https://api.weather.gov/alerts/active/zone/" + zone

    res = get_rest_data(url)

    title = None
    headlines = None

    if (res is not None):
        title = res['title']
        headlines = ""
        features = traverse(res, 'features')

        # Now an array
        #  each item is a dictionary - in properties, want NWSheadline, ...

        if (features is not None):
            for one_alert in features:
                one_alert = traverse(one_alert, 'properties')
                if (headlines != ""):
                    headlines = headlines + "\n"

                headlines = headlines + one_alert["headline"]

        if (headlines == ""):
            headlines = "(No currently active alerts for this zone)"
            

    return (title, headlines)  
            
#
#----------------------------------------------------------------------------------------------------
#
    
#
#   Given the the list of weather stations for a gridpoint, pick
#   the first (n) stations on the list (which should be the closest)
#
#   Returns a single string with spaces between the stations
#

def get_first_stations(stationsURL, limit=4):
    res = get_rest_data(stationsURL)

    res = traverse(res, 'observationStations')
    # Now an array with full URLs
    
    stationIDList = ""
    count = 0

    for oneStation in res:
        
        if (count < limit):
            (extra,oneStation) = oneStation.rsplit("/", 1)
            if (stationIDList == ""):
                stationIDList = oneStation
            
            else:
                stationIDList = stationIDList + " " + oneStation       

    return stationIDList


def get_station_name(stationID):
    global stationNameDB
    
    if (stationNameDB is None):
        make_cache_dir()
        stationNameDB = shelve.open("cache/stationiddb")

    if (stationID in stationNameDB):
        name = stationNameDB[stationID]
        
    else:
        url = "https://api.weather.gov/stations/" + stationID

        res = get_rest_data(url)
        res = traverse(res, 'properties')

        if ((res is not None) and ("name" in res)):
            name = res['name']
            
            forecast = res['forecast']
            (extra,state) = forecast.rsplit("/", 1)
            state = state[:2]

            # Take the first part if the name has a comma
            if ("," in name):
                name = name[:name.index(",")].strip()
                name = name + ", " + state

            # Take the second part if the name has a slash
            elif ("/" in name):
                name = name[name.index("/")+1:].strip()
                name = name + ", " + state
            
            stationNameDB[stationID] = name
        else:
            name = "???"

    return name
    
def get_noaa_meta(x,y):
    
    base = "https://api.weather.gov/points/"
    x = "{:.4f}".format(x)
    y = "{:.4f}".format(y)

    res = get_rest_data(base + y + "," + x)
    res = traverse(res, 'properties')
    
    if (res is not None):

        forecast = res['forecast']
        hourly   = res['forecastHourly']
        county   = res['county']
        forecastZone = res['forecastZone']
        stations = res['observationStations']

        hourly_gridloc  = get_gridloc(hourly)
        forecast_zone_gridloc = get_gridloc(forecastZone)
        
        stations = get_first_stations(stations)
        
        (s_id, s_name) = get_nearest_tide_loc(x,y)
        print_it("Tide: ", s_id, s_name)
        
        res = (hourly_gridloc, forecast_zone_gridloc, stations, s_id)

    else:
        
        res = (None, None, None, None)

    return res




#
#----------------------------------------------------------------------------------------------------
#


def decode_temp(item):
    val = None

    if (item is not None):
        val = item['value']
        unit = item['unitCode']
        
    if ((val is not None) and (unit is not None)):
        if (unit == "wmoUnit:degC"):
            val = (1.8 * val) + 32
            #val = str(round(val)) + "F"
            val = str(round(val)) + "°"
            
        else:
            print_it("Unknown unitCode", unit, "for", val)
            val = None
    
    return val


#
#--------------------------------------------------------------------------------
#

# HWO related routines

#
#   applies_to_zones - See if this zone description line:
#       e.g. MEZ007>009-012>014-018>022-033-NHZ001>013-015-040815-
#
#   matches a zone (or a list of zones, or a zone list seperated by spaces)
#
def applies_to_zones(zone_descr, my_zones):
    #print("Working on", zone_descr)
    
    zones = set()
    
    if my_zones is None:
        my_zones = set([sta_parameters.get_param("alert_zone")])
        
    elif isinstance(my_zones, str):
        if " " in my_zones:
            my_zones = set(my_zones.strip().split())
        else:
            my_zones = set([my_zones])
            
    else:
        my_zones = set(my_zones)
    
    zone_name = ""
    zone_num  = 0

    pattern = "[^->]+[>-]"
    
    items = re.findall(pattern, zone_descr)

    if items is not None:
        i = 0
        while i < len(items):
            m = re.match("([A-Z]*)(\\d+)([->])", items[i])
             
            if m is None:
                 print("Hey, what is this:", items[i])
            else:
                if m.group(1) != "":
                     zone_name = m.group(1)

                zone_num = m.group(2)
                
                if (m.group(3) == ">"):
                    
                    i = i + 1

                    m2 = re.match("(\\d+)-", items[i])
                    if m2 is None:
                        print("Hey, I expected a #- but got", items[i])
                    else:
                        end_zone_num = int(m2.group(1))
                        
                        for j in range(int(zone_num), end_zone_num+1):
                            full_zone = zone_name + str(j).zfill(3)
                            
                            zones.add(full_zone)
                else:
                    full_zone = zone_name + zone_num
                    zones.add(full_zone)

                #print("Zone:", m.group(1))
                #print("Zone #:", m.group(2))
                #print("Next token:", m.group(3))
                    
                i = i + 1

    result = zones.intersection(my_zones) != set()

    #print(zones, my_zones)
    #print(result)

    return result


#
#   remove_hwo_header
#
#   Removes the text PRIOR to the first zone list
#       (e.g. before something like MEZ007>009-012>014-018>022-033-NHZ001>013-015-040815-)
#
def remove_hwo_header(s):
    lines = s.split("\n")

    i = 0
    while i < len(lines) and not lines[i].endswith("-"):
        i = i + 1

    if i < len(lines):
        s = "\n".join(lines[i:])

    #print("Sending back:", s)
    
    return s


#
#
#   find_relevant_hwo
#
#   Given the HWO text from a NOAA office and given a list of zones,
#   find a HWO that matches the zone.
#
#   If force_output is not set, the returning string can be blank
#
def find_relevant_hwo(hwo_str, my_zones, force_output=False):
    # Remove the stuff before the first header
    hwo_str = remove_hwo_header(hwo_str)
    matched = False
    matched_mesg = ""
    
    hwo_bulletins = hwo_str.split("$$")

    for one_bulletin in hwo_bulletins:
        one_bulletin = one_bulletin.strip()

        if one_bulletin != "":
            #print("Working on", one_bulletin)
            
            (first_line, rest) = one_bulletin.split("\n", 1)
            #print(first_line, my_zones)
            
            if applies_to_zones(first_line, my_zones):
                matched = True
                
                rest = rest.strip()
                #print("Starting with", rest)

                # We need to do this in a loop, because the ending . of the pattern is the start of the next
                # iteration of the same pattern
                
                i = 3
                while i > 0:
                    # Remove the section with "No hazardous weather is expected at this time"
                    rest = re.sub(r"\n\.[^\n]+\n\nNo hazardous weather is (possible|expected) at this time.*?\n+\.",
                                  "\n.", rest)

                    rest = re.sub(r"\n\.[^\n]+\n\nHazardous weather is not (possible|expected) at this time.*?\n+\.",
                                  "\n.", rest)

                    # Remove the please listen... string
                    rest = re.sub(r"\nPlease listen to NOAA Weather Radio or go to weather.gov on the\s*Internet for more information about the following hazards.\n",
                                  "\n", rest)


                    i = i - 1
                    
                # Remove the extra indenting
                rest = re.sub(r"\n +", "\n", rest)

                # Remove the blank lines indenting
                rest = rest.replace("\n\n\n", "\n\n")

                #print("Now", rest)
                
                # Remove title
                if "\n\n" in rest:
                    (title, rest) = rest.split("\n\n", 1)

                # Remove spotter info
                if ".SPOTTER" in rest:
                    (rest, spotter) = rest.split(".SPOTTER", 1)

                # Remove the "This Harzardous Weather Outlook is for..."
                rest = re.sub("This Hazardous Weather Outlook is for [^\\.]*\\.\\s*",
                              "", rest,
                              flags=re.IGNORECASE)

                # Remove the .DAY ONE... and the like
                rest = re.sub(r"\n\.[^\.]*\.\.\.([^\n]*?)\.?\n",
                              "\n\\1:\n", "\n" + rest)

                matched_mesg = rest.strip()


    if matched_mesg == "" and force_output:
        if matched:
            matched_mesg = "No hazardous weather is expected at this time."
            
        else:
            matched_mesg = "No hazardous weather outlook available for this zone."
    
    print(matched_mesg)

    return matched_mesg

#
#----------------------------------------------------------------------------------------------------
#

# Example URL
#   https://api.weather.gov/gridpoints/GYX/68,40/forecast
def get_noaa_forecast(gridloc, want_hourly=False):

    if ("gridpoint/" in gridloc):
        (extra,gridloc) = gridloc.split("gridpoint/")

    if ("/forecast" in gridloc):
        gridloc = gridloc[:gridloc.index("/forecast")]
        
    url = "https://api.weather.gov/gridpoints/" + gridloc + "/forecast"
    
    if (want_hourly):
        url = url + "/hourly"
        
    #print_it("url=", url)
    
    res = get_rest_data(url)

    properties = traverse(res, 'properties')
    periods = traverse(properties, 'periods')
     
    return periods



def get_noaa_backup_forecast(zone):
    url = "https://api.weather.gov/zones/forecast/" + zone + "/forecast"

    res = get_rest_data(url)

    properties = traverse(res, 'properties')
    periods = traverse(properties, 'periods')

    return periods

# Example URL:
#    https://api.weather.gov/alerts/active?zone=MEC031
#
#
#  Only need to pass in the county "name"
#    e.g. MEC031
#  (but if the whole URL is passed, the county is extracted)
#
def get_alerts(zone_or_county, min_level=None, dedup_via_vtec=True):
    severity_order = [ "Unknown", "Minor", "Moderate", "Severe", "Extreme" ]
    urgency_order = [ "Unknown", "Past", "Future", "Expected", "Immediate" ]
    certainty_order = [ "Unkown", "Unlikely", "Possible", "Likely", "Observed" ]
    
    alerts = []
    
    if ("/" in zone_or_county):
        (rest,zone_or_county) = county.rsplit("/", 1)

    base = "https://api.weather.gov/alerts/active?zone="

    res = get_rest_data(base + zone_or_county)
    #print_it(res)

    res = traverse(res, 'features')

    # Now an array
    #  each item is a dictionary - in properties, want NWSheadline, ...

    if (res is not None):
        vtecs = []
            
        for one_alert in res:
            one_alert = traverse(one_alert, 'properties')
            one_params = traverse(one_alert, 'parameters')
            print_it(one_alert)
            
            alert_data = {}
            
            if ('VTEC' in one_params):
                vtec = one_params['VTEC'][0]
            else:
                vtec = None
                
            short_vtec = vtec
            
            if ((vtec is not None) and ("." in vtec)):
                (v_class, v_status, v_rest) = vtec.split(".", 2)
                short_vtec = v_class + "." + v_rest
                #print_it("*!* SHORT", short_vtec)
                
            alert_data['long'] = one_alert['description']

            # Prefer a NWSheadline over a headline (if both are present)
            if ('NWSheadline' in one_alert['parameters']):
                alert_data['short'] = one_alert['parameters']['NWSheadline'][0]
                alert_data['alt_short'] = one_alert.get('headline', None)
            else:
                alert_data['short'] = one_alert['headline']
                alert_data['alt_short'] = one_alert['parameters'].get('NWSheadline', None)
                if (isinstance(alert_data['alt_short'], list)):
                        alert_data['alt_short'] = alert_data['alt_short'][0]

            alert_data['severity'] = one_alert['severity']  # e.g. Moderate
            alert_data['urgency'] = one_alert['urgency']  # e.g. Expected
            alert_data['certainty'] = one_alert['certainty'] # e.g. Likely
            alert_data['VTEC'] = vtec

            # Do not put in multiple alerts with the same (base) vtec
            
            if ((short_vtec not in vtecs) or (not dedup_via_vtec)):
                alerts.append(alert_data)
                
            else:
                print_it("Removing duplicate VTEC of", short_vtec)
                
            # Don't store unknown VTEC (so all versions of these are displayed)
            if (short_vtec is not None):
                vtecs.append(short_vtec)

    return alerts


def get_hazard_outlook(stationID, my_zones, force_output=False):

    if force_output:
        text = "No Hazardous Outlook report available."
    else:
        text = ""
    
    # If passed a list, just use the first item
    if isinstance(stationID, list):
        stationID = stationID[0]

    if stationID is None:
        stationID = sta_parameters.get_param("forecast_zone")
        
        if "/" in stationID:
            (stationID, rest) = stationID.split("/", 1)

    if my_zones is None:
        my_zones = [ sta_parameters.get_param("alert_zone") ]

    if stationID is not None and stationID != "":

        if "/" in stationID:
            (stationID, rest) = stationID.split("/",1)
            
        url = "https://api.weather.gov/products/types/HWO/locations/" + stationID
        res = get_rest_data(url)

        res = traverse(res, '@graph')

        if isinstance(res,list) and len(res) > 0:
            first_item = res[0]
            first_item_url = first_item.get("@id", None)

            res = get_rest_data(first_item_url)
            
            if res is not None:
                text = res.get("productText","")
                text = find_relevant_hwo(text, my_zones, force_output)

    return text
        
# Example URL
#   https://api.weather.gov/stations/KPWM/observations/latest
#
# Only need to pass in the station ID (e.g. KPWM or KSFM)
#
#
def get_latest_obs(stationList):
    
    temp = None
    humidity = None
    text = None
    windChill = None
    heatIndex = None
    name = None
    icon = None
    
    for one_station in stationList.split():

        if (temp is None):
            base = "https://api.weather.gov/stations/"
            ending = "/observations/latest"

            res = get_rest_data(base + one_station + ending)
            res = traverse(res, 'properties')
            
            if (res is not None):
                #print_it(res)
                
                text = res['textDescription']
                icon = res['icon']
                name = get_station_name(one_station)
                
                if (('relativeHumidity' in res) and
                    ('value' in res['relativeHumidity'])  and
                    (res['relativeHumidity']['value'] is not None)):
                    
                    humidity = str(round(res['relativeHumidity']['value'])) + "%"
                    
                else:
                    print("No Humidity", res)
                    
                    humidity = None
                
                temp = decode_temp(res['temperature'])
                windChill = decode_temp(res['windChill'])
                heatIndex = decode_temp(res['heatIndex'])          

    return (temp, humidity, text, windChill, heatIndex, name, icon)

#
#---------------------------------------------------------
#

def get_local_fields(addr = None, store_loc = None):
    if (addr is None):
        print("Enter a full address in the format " +
                     "'### street, city, state [zip]'")
        addr = input(": ")
        
    (lat,lon) = addr2latlon(addr)   
    
    if (lat is not None):
            print("Loc", lat, lon)
            
            (forecastLoc, zone_or_county, stations, tide_stat) = get_noaa_meta(lon, lat)

            print("Loc", forecastLoc)
            print("County", zone_or_county)
            print("Stations", stations)
            print("Tide", tide_stat)

            # Hardcode: Max of 5 stations
            station_list = stations.strip().split(" ")
            station_list = station_list[:5]
            
            stations = " ".join(station_list)

            if (store_loc is not None):
                sta_parameters.set_param("forecast_zone", forecastLoc)
                sta_parameters.set_param("alert_zone", zone_or_county)
                sta_parameters.set_param("obs_stations", stations)
                sta_parameters.set_param("tide_station", tide)

    else:
        
        (forecastLoc, zone_or_county, stations, tide_stat) = (None, None, None, None)

    return (forecastLoc, zone_or_county, stations, tide_stat)

def save_if_ok_param(field_name, fields, value):

    if ((field_name in fields) or ("all" in fields)):
        ok = sta_parameters.set_param(field_name, value)
        
    else:
        ok = True

    return ok


def is_resetable(code):
    return code in resetable_parms

def reset_weather_fields(fields, print_it=False):
    lat_lon = sta_parameters.get_param("lat_lon")

    if ("," in lat_lon):
        (lat,lon) = lat_lon.split(",")

        lat = float(lat)
        lon = float(lon)

        (forecast_zone, alert_zone, obs_stations, tide_station) = get_noaa_meta(lon, lat)

        # Hardcode: Max of 5 stations
        station_list = obs_stations.strip().split(" ")
        station_list = station_list[:5]
        
        obs_stations = " ".join(station_list)
            
        if (print_it):
            print("Forecast Zone", forecast_zone)
            print("Alert Zone", alert_zone)
            print("Obs. Stations", obs_stations)
            print("Tide Station", tide_station)

        ok =        save_if_ok_param("forecast_zone", fields, forecast_zone)
        ok = ok and save_if_ok_param("alert_zone",    fields, alert_zone)
        ok = ok and save_if_ok_param("obs_stations",  fields, obs_stations)
        ok = ok and save_if_ok_param("tide_station",  fields, tide_station)

    else:
        ok = False

    return ok
    
    
def retrieve_local_fields():
    
    forecastLoc = sta_parameters.get_param("forecast_zone")
    county      = sta_parameters.get_param("alert_zone")
    stations    = sta_parameters.get_param("obs_stations")
    tide_stat   = sta_parameters.get_param("tide_station")
                  
    return (forecastLoc, county, stations, tide_stat)
        
#
#---------------------------------------------------------
#


def print_forecast(periods):
    
    if (periods is not None):

        for period in periods:

            name  = period['name']
            short = period['shortForecast']
            long  = period['detailedForecast']
            icon  = period['icon']
            isday = period['isDaytime']
            
            temp = str(period['temperature']) + period['temperatureUnit']
        
            if (period['temperatureUnit'] == 'F'):
                period['temperatureUnit'] = '°'
                
            if (isday):
                hilow = "↑"
            else:
                hilow = "↓"
            
            fulltemp = hilow + " " + temp
            
            print(name.ljust(15), short.ljust(25)[:25], fulltemp.ljust(6), long[:60])
            if (not isday):
                print("")

def create_abr_forecast(periods):
    forecast = []
    
    if (periods is not None):
        
        hi = "---"
        day = "Tonight"
        dayname = ""
        dayicon = ""
        daytext = ""
        
        for period in periods:

            # Use .get since the "backup" zone forecast
            #  doesn't have all of the fields
            
            name  = period['name']
            long  = period['detailedForecast']

            short = period.get('shortForecast', None)
            icon  = period.get('icon', None)
            isday = period.get('isDaytime', None)

            # Add missing field for backup" data
            if ("temperatureUnit" not in period):
                period["temperatureUnit"] = ""
                
            # This is mostly for using the "backup" zone forecast
            #  which doesn't have a shortForecast
            
            if (short is None):
                short = long

                if ("." in short):
                    short = short[:short.index(".")]
                    
                    if ("," in short):
                        short = short[:short.index(",")]
                

            if (period['temperatureUnit'] == 'F'):
                period['temperatureUnit'] = '°'

            if ("temperature" in period):
                temp = str(period['temperature']) + period['temperatureUnit']
            else:
                temp = ""
            
            if (isday):
                day = name[0:3]
                dayname = name
                daytext = short
                daylong = long
                dayicon = icon
                hi = temp
                
                lo = ""
                nighticon = ""
                
                mesg = short
                
            else:
                low = temp
                nighticon = icon
                nighttext = short

                # Only evening data?  Then show nightime forecast
                if (hi == "---"):
                    mesg = short

                data = {}
                
                if (dayname != ""):
                    data['name'] = dayname
                    data['short'] = daytext
                    data['long'] = daylong
                else:
                    data['name'] = name
                    data['short'] = short
                    data['long'] = long
                    
                data['mesg'] = mesg
                data['hi'] = hi
                data['low'] = low
                data['dayicon'] = dayicon
                data['nighticon'] = nighticon

                forecast.append(data)

    return forecast
    
def print_abr_forecast(periods):

    if (periods is not None):
        forecast = create_abr_forecast(periods)

        for one_day in forecast:
            day = one_day['name'][:3]
            
            if ((day != "Thi") and (day != "Tod") and (day != "Ton")):
                print(day,one_day['mesg'].ljust(30)[:30],
                      one_day['hi'] + " / " + one_day['low'])

            else:
                print("   ", one_day['mesg'].ljust(30)[:30],
                      one_day['hi'] + " / " + one_day['low'])      

            print(get_icon_filename(one_day['dayicon']),
                  get_icon_filename(one_day['nighticon']))

def print_alerts(alerts):
    
    if ((alerts is None) or (len(alerts) == 0)):
        print("No active alerts")
        
    else:
        
        for one_alert in alerts:
            severity = one_alert['severity']
            short = one_alert['short']

            print(severity + ":", short)
       
def print_weather():
    addr = ""

    if (False):  
        (forecastLoc, county, stations, tide_stat) = get_local_fields()

    else:
        (forecastLoc, county, stations, tide_stat) = retrieve_local_fields()

    print("Loc     :     ", forecastLoc)
    print("County  :     ", county)
    print("Stations:     ", stations)
    print("Tide Station: ", tide_stat)
    
        
    alerts = get_alerts(county)
    print_alerts(alerts)
    
    (temp, humidity, wText, windChill, heatIndex, name, icon) = \
               get_latest_obs(stations)

    print("")
    
    print("Location:    ", name)
    print("Currently:   ", wText)
    print("Temperature: ", temp)
    print("Humidity:    ", humidity)
    print("Icon:        ", get_icon_filename(icon))
    
    if (windChill is not None):
        print("Wind Chill:  ", windChill)

    if (heatIndex is not None):
        print("Heat Index:  ", heatIndex)
        
    res = get_noaa_forecast(forecastLoc)
    
    if (res is None):
        print("Did not get the forecast", forecastLoc)
        
    print("")
    print_abr_forecast(res)
    print("")
    print_forecast(res)

    get_hazard_outlook(forecastLoc, county)

if (__name__ == "__main__"):
    os.chdir("..")
    print_weather()
