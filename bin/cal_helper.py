import datetime
import fnmatch
import glob
import os
import pytz
import random
import re
import sys

import icalendar
#pip3 install recurring-ical-events
import recurring_ical_events

# pip3 install requests
import requests

# pip3 install requests_cache
# or apt install python3-requests-cache
import requests_cache

import sta_parameters

CACHED_CALS = {}
DEBUG = 0

mySession = None

def print_it(*args,**kwargs):
    
    if (DEBUG):
        print(*args, **kwargs)
        
#
#   make_ordinal taken from:
#
#       https://stackoverflow.com/questions/9647202/ordinal-numbers-replacement
#
def make_ordinal(n):
    '''
    Convert an integer into its ordinal representation::

        make_ordinal(0)   => '0th'
        make_ordinal(3)   => '3rd'
        make_ordinal(122) => '122nd'
        make_ordinal(213) => '213th'
    '''
    n = int(n)
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return str(n) + suffix

#
#--------------------------------------------------------------------------------
#

def replace_with_ordinal(s, num):
    if (" nth " in s):
        loc = s.index(" nth ")
        
        before = s[:loc+1]
        after  = s[loc+4:]

        s = before + make_ordinal(num) + after

    return s
        

def load_weekday_events(fname):
    offset = 0
    events = []
    
    f = open(fname)
    s = readline_w_comments(f)

    while (s is not None):
        print_it(s)
        
        m = re.match(r"\s*offset\s*=\s*((-?\d+)|\*)", s, re.I)
        
        if (m is not None):
            print_it("Found it")
            
            if m.group(1) == "*":
                offset = "*"
            else:
                offset = int(m.group(1))

        else:
            events.append(s)
        
        s = readline_w_comments(f)
        
    f.close()

    return (offset, events)

def get_weekday_num(num_events, cur_offset=0, day_offset=0):
    (year, week, wday) = datetime.datetime.now().isocalendar()

    # offset=*, then first entry in file is always Monday
    if cur_offset == "*":
        day_num = (wday - 1 + day_offset) % 5
        
    else:
        day_num   = ((week * 5) + wday + cur_offset + day_offset) % num_events

    return day_num

def get_weekday_nums_from_filename(fname, day_offset=0):
    (conf_offset, events) = load_weekday_events(fname)

    num_events = len(events)
    
    day_num = get_weekday_num(num_events, conf_offset, day_offset)

    return (day_num, conf_offset, num_events, events[day_num])

def get_weekday_events(fname):
    event_list = {}

    code = "!@" + fname    # Put near the front for sorting

    (year, week, wday) = datetime.datetime.now().isocalendar()
    
    today         = datetime.datetime.now()
    tomorrow      = today + datetime.timedelta(days=1)
    
    today_date    = today.strftime("%Y%m%d 00:00")
    tomorrow_date = tomorrow.strftime("%Y%m%d 00:00")

    (offset, events) = load_weekday_events(fname)

    if (offset is not None):
        today_num    = get_weekday_num(len(events), offset, 0)
        tomorrow_num = get_weekday_num(len(events), offset, 1)
        
        if (wday <= 5):            # Mon..Fri
            today_str = events[today_num]
            
            if ((today_str != "") and (today_str != "-")):
                
                event_list[today_date + code] = \
                                      "*" + today_str + "*"
            
        if ((wday == 7) or (wday <= 4)):   # Sun or Mon..Thu
            # Fix week # and wday if on Sunday
            if (wday == 7):
                tomorrow_num = (((week+1) * 5 + 1 + offset) % len(events))

            tomorrow_str = events[tomorrow_num]

            if ((tomorrow_str != "") and (tomorrow_str != "-")):
                
                event_list[tomorrow_date + code] = \
                                         "*" + tomorrow_str + "*"

    return event_list

def get_all_weekday_events():
    event_list = {}

    for one_file in glob.glob(sta_parameters.conf_dir() + "weekday-*.txt"):
        new_list = get_weekday_events(one_file)
        event_list.update( new_list )

    return event_list

def get_daily_events(fname):
    event_list = {}

    code = "!@" + fname    # Put near the front for sorting

    # https://stackoverflow.com/questions/31687420/convert-datetime-datetime-object-to-days-since-epoch-in-python
    daynum = (datetime.datetime.now() - datetime.datetime(1970,1,1)).days
    
    today         = datetime.datetime.now()
    tomorrow      = today + datetime.timedelta(days=1)
    
    today_date    = today.strftime("%Y%m%d 00:00")
    tomorrow_date = tomorrow.strftime("%Y%m%d 00:00")

    (offset, events) = load_weekday_events(fname) # Can re-use load_weekday_

    if (offset is not None):
        # offset=* indicates that the first entry in the file is always Sunday
        if offset == "*":
            (year, week, wday) = datetime.datetime.now().isocalendar()

            today_num = wday
            tomorrow_num = (wday + 1) % 7
            
        else:
            today_num = (daynum + offset) % len(events)
            tomorrow_num = (daynum + offset + 1) % len(events)

        today_str = events[today_num]
        tomorrow_str = events[tomorrow_num]

        if ((today_str != "") and (today_str != "-")):
            event_list[today_date + code] = "*" + today_str + "*"


        if ((tomorrow_str != "") and (tomorrow_str != "-")):    
            event_list[tomorrow_date + code] = "*" + tomorrow_str + "*"

    return event_list

def get_all_daily_events():
    event_list = {}

    for one_file in glob.glob(sta_parameters.conf_dir() + "daily-*.txt"):
        new_list = get_daily_events(one_file)
        event_list.update( new_list )

    return event_list

#
#-------------------------------------------------------------------
#
def get_countdown_file(fname):
    event_list = {}
    closest = None
    closestMesg = None
    
    f = open(fname)
    line = readline_w_comments(f)

    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    
    max_days = 7
    all_multiyear = False
    
    this_year = today.year
    
    while (line is not None):
        m = re.match(r"\s*(\*?)\s*(\d+)/\s*(\d+)(/\s*(\d+))?\s+(.+$)", line)

        if (m is not None):

            multiyear = (m.group(1) is not None)
            month = int(m.group(2))
            day = int(m.group(3))
            year = m.group(5)
                
            mesg = m.group(6)

            # No year - assume this year (unless it has passed, then
            #    assume next year)
            if (year is None):
                
                target_date = datetime.date(this_year, month, day)
                
                if (target_date < today):
                    target_date = datetime.date(this_year+1, month, day)
            else:
                year = int(year)
                if (year < 100):
                    if (year > 50):
                        year = 1900 + year
                    else:
                        year = 2000 + year
                    
                target_date = datetime.date(year, month, day) 

            target_year = target_date.year
            year_diff = this_year - target_year

            mesg = replace_with_ordinal(mesg, year_diff)
            
            # Multiyear?  Then replace the year with this one (or the next if close to Jan 1)...
            if (multiyear or all_multiyear):
                
                    target_date = target_date.replace(year = this_year)
                    
                    if (target_date < today):
                        target_date = target_date.replace(year = this_year+1)
                    
            # Date not yet passed or wants to be shown every year?
            if (target_date >= today):
                
                diff = target_date - today
                diff_days = diff.days
                #print_it("Event: ", mesg, target_date, diff_days, file=sys.stderr)
                
                # Within the range of max_days?
                if ((diff_days >= 0) and (diff_days <= max_days)):
                    orig_mesg = mesg
                    
                    if (diff_days == 1):
                        mesg = "(1 day to " + mesg + ")"
                        #mesg = "(" + str(diff_days) + " day \u2192 " + mesg + ")"

                        # Since tomorrow is "THE" day - special case and show it directly
                        tomorrow_date    = tomorrow.strftime("%Y%m%d 00:00")
                        mesg2 = "(" + mesg + ")"

                        # Add an entry for tomorrow too
                        key2 = tomorrow_date + orig_mesg
                        event_list[key2] = orig_mesg
                        
                    elif (diff_days == 0):
                        mesg = "(" + mesg + ")"

                    else:
                        mesg = "(" + str(diff_days) + " days to " + mesg + ")"
                        #mesg = "(" + str(diff_days) + " days \u2192 " + mesg + ")"

                                # Put event at top on actual day, and on bottom otherwise
                    if (diff_days == 0):
                        today_date    = today.strftime("%Y%m%d 00:00")
                    else:
                        today_date    = today.strftime("%Y%m%d 23:59")

                    key = today_date + mesg
                    event_list[key] = mesg
        else:
            # Are they specifying the number of days to show
            m = re.match(r"\s*days\s*=\s*(\d+)", line)

            if (m is not None):
                max_days = int(m.group(1))
            else:
                m = re.match(r"\s*multiyear\s*=\s*(\S+)", line)

                if (m is not None):
                    s = m.group(1)
                    s = s[0].lower()
                    
                    all_multiyear = ((s == "1") or (s == "t"))
                    #print_it("Setting all_multiyear to", all_multiyear, file=sys.stderr)
                    
                else:
                    print("Invalid line in", fname, "=", line, file=sys.stderr)
        
        line = readline_w_comments(f)

    return event_list


#
#---------------------------------------------------------------
#
def get_all_countdown_events():
    event_list = {}
    
    for one_file in glob.glob(sta_parameters.conf_dir() + "countdown-*.txt"):
        new_list = get_countdown_file(one_file)
        event_list.update( new_list )

    return event_list
#
#-------------------------------------------------------------------
#
def make_cache_dir(subdir=None):
    if (not os.path.exists("cache")):
        os.mkdir("cache")

    if (subdir is not None):
        subpath = os.path.join("cache", subdir)
        if (not os.path.exists( subpath )):
            os.mkdir(subpath)
            
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
    #mySession.remove_expired_responses()
    
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

def should_ignore_event(name):
    should_ignore = False
    name = name.lower().strip()         # Force case-insensitve matching
    
    for one_file in glob.glob(sta_parameters.conf_dir() + "ignore-*.txt"):
        # No need to look at more files if there is already a match
        if (not should_ignore):
            f = open(one_file)

            line = readline_w_comments(f)
            
            while (line is not None):
                #print_it("Check", line, "vs", name)
                
                if (fnmatch.fnmatch(name, line.lower())):
                    should_ignore = True
                    
                line = readline_w_comments(f)
                
            f.close()
        
    return should_ignore 



def get_calendar(url, force=False):
    global mySession
    global CACHED_CAL

    if (mySession is None):
        init_session_w_cache()
        
    now = datetime.datetime.now()
    print_it("Working on", url)
    
    if ((force) or
        (url not in CACHED_CALS) or
        (CACHED_CALS[url]["next_time"] <= now)):

        try:
            resp = mySession.get( url, timeout=30 )

        except (ConnectionError,
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
                requests.exceptions.Timeout):
            resp = None

        if ((resp is not None) and
            (resp.status_code >= 200) and
            (resp.status_code < 300)):
            
            try:
                cal = icalendar.Calendar.from_ical( resp.text )
            except ValueError:
                cal = None

            if (cal is not None):
                #res = recurring_ical_events.of(cal, keep_recurrence_attributes=True)
                res = recurring_ical_events.of(cal)

                # First time we looked at this calendar?
                if (url not in CACHED_CALS):
                    CACHED_CALS[url] = {}

                CACHED_CALS[url]["cal"] = res
                
                # Chose a next time to update the cache that is 4hrs +/- 30 minutes
                CACHED_CALS[url]["next_time"] = now + \
                                    datetime.timedelta(hours=3,
                                                   minutes=random.randint(30, 90))
            else:
                print("Calendar", url, "not parsable (this time)", file=sys.stderr)
                res = None

        else:
            if (resp is not None):
                print("URL returned an error status code of", resp.status_code)

            res = None

    else:
        res = CACHED_CALS[url]["cal"]
        
    return res

def get_all_calendars(force=False):
    for one_file in glob.glob(sta_parameters.conf_dir() + "ical-*.txt"):
    
        f = open(one_file)

        url = readline_w_comments(f)
    
        while (url is not None):
            get_calendar(url, force)
            url = readline_w_comments(f)

        f.close()


def get_entries_between(cal, start, end,
                        show_private=False,
                        show_declined=False,
                        force_date_to=None):
    event_list = {}

    events = cal.between(start, end)
    
    # Change the start from date to datetime
    start = datetime.datetime.combine(start, datetime.datetime.min.time())
    start = start.astimezone()
    
    for event in events:
        declined = (event.get('PARTSTAT', "") == 'DECLINED')

        if ((not declined) or (show_declined)):
            #if ((event.begin.datetime <= tomorrow) and
            #    (event.end.datetime   >= today)):
            name = event['SUMMARY']

            # Shield the names of private events
            if ((show_private == False) and
                (event.get('CLASS', 'PUBLIC') != "PUBLIC")):
                
                name = "Private Event"
            
            evt_start = event['DTSTART'].dt
            evt_end   = event['DTEND'].dt

            # Passed a date?  convert to a datetime
            if (type(evt_start) == datetime.date):
                print_it("Converting", name, "from", type(evt_start), evt_start)
                
                evt_start = datetime.datetime.combine(evt_start,
                                                      datetime.datetime.min.time())
                evt_start = evt_start.astimezone()

            # Passed a date?  convert to a datetime
            if (type(evt_end) == datetime.date):
                evt_end = datetime.datetime.combine(evt_end,
                                                      datetime.datetime.min.time())
                evt_end = evt_end.astimezone()

            # Handle multi-day events
            if (evt_start < start):
                #print_it("Converting multiday", name)
                evt_start = start
                
            duration = evt_end - evt_start

            start_str = evt_start.strftime("%I:%M%p").lower()
            
            if (force_date_to is not None):
                
                start_str24 = force_date_to.strftime("%Y%m%d") + \
                              evt_start.strftime(" %H:%M")
                        
            else:
                start_str24 = evt_start.strftime("%Y%m%d %H:%M")
            
            # Consider all 8+ hour events all day
            if (duration >= datetime.timedelta(hours=8)):
                key = start_str24 + name
                val = "(" + name + ")"
                
            else:
                key = start_str24 + " " + name
                val = start_str + " - " + name
                
            if (not should_ignore_event(name)):
                    event_list[key] = val

    return event_list

def get_today_tomorrow_events(show_private=False):
    
    get_all_calendars()
    
    event_list = {}
    now = datetime.datetime.now().astimezone()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    tomorrow_begin = today + datetime.timedelta(days=1)
    tomorrow_end = today + datetime.timedelta(days=2)
    
    for cal_url in CACHED_CALS:
        cal = CACHED_CALS[cal_url]["cal"]

        # You should be able to do this as a single step, but recurring meetings
        #  that have exceptions mess it up... (11/29/2022)
        
        today_events    = get_entries_between(cal, now, tomorrow_begin,
                                              show_private, today)
        
        tomorrow_events = get_entries_between(cal, tomorrow_begin, tomorrow_end,
                                              show_private, tomorrow_begin)
        
        event_list.update ( today_events )
        event_list.update ( tomorrow_events )
              
    event_list.update( get_all_weekday_events() )
    event_list.update( get_all_daily_events() )
    event_list.update( get_all_countdown_events() )

    return event_list
            
def cal_to_str(show_private=False):
    today = datetime.datetime.now()
    today = today.replace(hour=0, minute=0, second=0, microsecond=0)
    today_s = today.strftime("%Y%m%d")

    event_list = get_today_tomorrow_events(show_private)

    s = ""
    
    last_date = ""
    
    for k in sorted(event_list):
        print_it(k, event_list[k], today_s)

        this_date = k[:8]
        
        if (this_date != last_date):
            s = s + "\n"
                
            if (this_date == today_s):
                s = s + "***_Today_***\n"
            else:
                s = s + "***_Tomorrow_***\n"

            last_date = k[:8]

        line = event_list[k]
        
        if (line[0] == "0"):
            line = " " + line[1:]

        s = s + line + "\n"
        
        cal_to_str.lastval = s
        cal_to_str.lasttime = today

    if (s == ""):
        s = "(No events)\n(Today or Tomorrow)"
        
    return s

def display_cal(show_private=False):
    s = cal_to_str(show_private)
    print(s)

if (__name__ == "__main__"):   
    display_cal(True)
    
    
