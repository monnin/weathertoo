**WeatherToo**

This is another weather application that is designed to use an eInk/ePaper display to show the weather, calendar entries, and other reminders.   

Weather data is retreived from weather.gov (via the REST interface).  Due to this, no account is necessary to retrieve the weather data.  However, 
this also means it is likely less useful for users outside of the United States (untested).

The software is designed to run on a Raspberry Pi (including a Pi Zero) with an ePaper HAT.

Calendar data can be retrieved from any online source using an iCal format, and/or static files located on the device can also be used (e.g. for birthdays, anniversaries, etc.) and can 
also display a countdown to specific entries (e.g. holidays).   Repeating entries can also be displayed.

All of the displays (and the data behind them) are customizable using uploaded configuration files.  The application has a web server interface to assist in managing the device 
and selecting active configuration files.  The web server has a simple password (but should not be considered highly secure).

To use the display, you will need to upload fonts (I use fonts from the X11 and GNU FreeFont projects, both fixed and truetype fonts).  You will also need a set of icons.   I use icons from
https://github.com/erikflowers/weather-icons and https://github.com/basmilius/weather-icons 
