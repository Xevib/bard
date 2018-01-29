[![Coverage Status](https://coveralls.io/repos/github/Xevib/changewithin/badge.svg?branch=master)](https://coveralls.io/github/Xevib/changewithin?branch=master)

# Changewithin

*Daily emails of changes to buildings and addresses on OpenStreetMap.*

changewithin is a simple script that pulls [daily changes](http://planet.openstreetmap.org/)
from OpenStreetMap with `requests`, parses them with `pyosmium`, finds the ones that are inside
of a GeoJSON shape, sorts out the ones that are buildings, and emails a set of users
with [mailgun](http://www.mailgun.com/).

The one file that will require editing is [config.ini](https://github.com/migurski/changewithin/blob/master/config.ini).

At the top you will find a simple list of email addresses to which the script
will send reports. The email templates for both html and text can be edited within
the file `lib.py`. The report itself contains a summary of changes, then lists
each relevant changeset, its ID, and further details. These include the user who
made the change and their comment, individual element IDs for building footprint
and address changes that link to their history, and a map thumbnail that is centered
on the location where the edits were made.


# Installation

Install Python packages:
    
    pip install -r requirements.txt


# Running

    python changewithin.py

The program reads the url of the configuration file from the environment variable BARD_CONFIG.

# Configuration

To setup the confiugration the file must be in [Confobj file format](http://configobj.readthedocs.io/en/latest/configobj.html#the-config-file-format)

The configuration have the following secctions:

## Email
    * recipients: list of emails to send the report
    * language: specifies the language of the email
    
    
## Area

    * bbox: Bounding box of the area to check the changes North,East,South,West

## Mailgun
    
    * domain: Mailgun domain
    * api_key: Mailgun api key
    * api_url: Mailgun api URL , ended with /messages
    
## Tags
    Represents the tags to check, each tag is a section with a name.
    Each tag must have:
    
    * tags: regular expresion key,value to indicate the key and value to check
    * type: types of elements to check separated by coma. Avaible types node and way
    
# Automating

Assuming the above installation, edit your [cron table](https://en.wikipedia.org/wiki/Cron) (`crontab -e`) to run the script once a day at 7:00am.

    0 7 * * * ~/path/to/changewithin/bin/python ~/path/to/changewithin/changewithin.py
