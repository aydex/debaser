#!/usr/bin/env python

"""
debaser.py
v0.61 - 12032018
  * Now downloads images to a directory for each subreddit. If it does not exist, it is created.
v0.60 - 11032018
  * Now accesses the reddit API using PRAW
  * Default subreddit is now r/me_irl
  * Downloads NSFW images by default
  * Changed default limit to 10
  * Now recognizes i.redd.it image links
v0.55 - 10192012
  * Added support for Imgur albums if imguralbum.py is available
  * Added -a --album flag to allow for suppression of album downloads if desired.
  * Currently, debaser.py only checks if an album exists, not whether its contents exist
    when not using -o --overwrite mode.

v0.54 - 12152011
  * Changed nsfw behavior:  no nsfw by default
  * Added -n --nsfw flag to support previous behavior
  * Fixed overwrite bug on indirect imgur links

v0.53 - 12142011
  * Changed overwrite behavior:  no overwrite by default
  * Added -o --overwrite flag to support previous behavior

v0.52 - 12122011 [ frozen 3:21 PM EST 12/11/2011 ]
  * Added support for uppercase file extensions on urls (ex: .JPG, .GIF)
  * Added support for .jpeg file extension
  * Added license information to heading comment (see below).
  * Removed counter from main loop; used enumerate() to obtain index and len() to obtain totals in error summary

v0.51 - 12112011 [ frozen 5:14 PM EST 12/11/2011 ]
  * fixed bug with non-imgur urls that are downloadable
  * added permalink output in verbose mode to add additional log information
  * fixed cross-compatibility bug by using os.path.join & posixpath (untested)
  * fixed bug with limit being passed as string...now it actually works!

v0.50 - 12112011 [ frozen 3:16 PM EST 12/11/2011 ]

An image scouring tool for reddit.

Copyright (c) 2011-2012 Andy Kulie.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

album_active = True  # activate album downloads until told otherwise (v0.55)

import praw
import os
import subprocess # new for v0.55 - added for imgur album support
import urllib
from urlparse import urlparse  # for parsing out *.jpg from url (python 2)
from optparse import OptionParser  # for parsing command line options
from posixpath import basename  # for url splitting on non-imgur urls
try:
    import imguralbum
except:
    print "imguralbum.py not found.  Imgur album downloads will be disabled."
    album_active = False


# add system argument for verbose mode
verbose_mode = True
overwrite_mode = False  # added to support overwrite behavior (new default is no overwrite)
nsfw_mode = True  # added to support nsfw behavior (new default is NO nsfw items)
current_version = "%prog 0.60-11032018"
current_dir = os.getcwd()

# start parse arguments
usage = "usage: %prog [options] arg"
parser = OptionParser(usage, version=current_version)
parser.add_option("-s", "--subreddit", dest="subreddit", default="me_irl", help="name of subreddit | defaults to %default")
parser.add_option("-f", "--filter", dest="filter", default="top", help="filter: hot, top, controversial, new | defaults to %default")
parser.add_option("-l", "--limit", dest="limit", default=10, help="limit of submissions to gather | defaults to %default")
parser.add_option("-o", "--overwrite", action="store_true", dest="overwrite", help="automatically overwrite duplicate files (use with caution)") # added to support overwrite behavior
parser.add_option("-n", "--nsfw", action="store_true", dest="nsfw", help="disallow download of nsfw items") # added to support nsfw filtering
parser.add_option("-v", "--verbose", action="store_true", dest="verbose")
parser.add_option("-q", "--quiet", action="store_false", dest="verbose")
parser.add_option("-a", "--album", action="store_true", dest="album", help="disable Imgur album downloading even if imguralbum.py is available") # added v0.55 to support suppression of imgur album downloads (they take longer)
(options, args) = parser.parse_args()
if options.verbose:
    verbose_mode = True
if options.overwrite:
    overwrite_mode = True
if options.nsfw:
    nsfw_mode = False
if options.album:
    album_active = False

# end parse arguments


"""
submissions(subr_name, subr_filter, subr_limit)
  Returns a generator for the submissions in a given
  subreddit.

  subr_name - name of subreddit [STRING]
  subr_filter - top, hot, controversial, new [STRING]
  subr_limit - limit of submissions to return [INTEGER]

  returns submissions [GENERATOR]
"""


def submissions(subr_name='me_irl', subr_filter='top', subr_limit=10):
    if (subr_filter == 'hot'):
        return r.subreddit(subr_name).hot(limit=subr_limit)
    elif (subr_filter == 'top'):
        return r.subreddit(subr_name).top(time_filter='day', limit=subr_limit)
    elif (subr_filter == 'new'):
        return r.subreddit(subr_name).new(limit=subr_limit)
    elif (subr_filter == 'controversial'):
        return r.subreddit(subr_name).controversial(limit=subr_limit)

"""
build_imgur_dl(url)
  Return a direct link url for imgur based on an indirect
  url tuple from urlparse

  url - a parsed url tuple from urlparse [TUPLE]

  returns direct link url [STRING]
"""


def build_imgur_dl(url):
    return 'http://' + 'i.' + url.netloc + url.path + '.jpg'
    # to be added: exceptions for if it's a png or gif


# initialize reddit object
r = praw.Reddit('bot1')

# get submissions as a list of objects
subr_name = options.subreddit
subr_filter = options.filter
subr_limit = int(options.limit) # make this an int instead of a string, duh!
if verbose_mode: print "Scouring subreddit " + subr_name + " for " + subr_filter + " submissions (limit " + str(subr_limit) + ")\nPlease wait..."

sublist = submissions(subr_name, subr_filter, subr_limit) #replace default with user input
sublist = list(sublist)

# main parse & download loop
success = len(sublist)
summary = []

# create subreddit directory if it does not exist
if not os.path.exists(current_dir + '/' + options.subreddit):
    if verbose_mode: print "Directory for r/" + options.subreddit + " does not exist. Creating it now."
    os.makedirs(current_dir + '/' + options.subreddit)


for index, i in enumerate(sublist):
    if (not(nsfw_mode) and i.over_18):
        if verbose_mode: print "NSFW submission found!  Skipping!"
        summary.append("Submission #" + str(index) + " was tagged as not safe for work. Use -n flag to enable nsfw mode.")
        success -= 1
        continue
    if verbose_mode:
        if not(i.over_18):
            print str(index) + ": " + i.title + " :: " + i.url
        else:
            print str(index) + ": " + i.title + " :: " + i.url + " [NSFW]"
        print "permalink = " + i.permalink
    # parse out the url to get its parts as a 6-tuple
    parsed_url = urlparse(i.url)
    if (parsed_url.netloc == 'i.redd.it'):
        if verbose_mode: print "Direct reddit link. Downloading..."
        if (not(overwrite_mode) and os.path.exists(os.path.join(current_dir + '/' + options.subreddit, basename(parsed_url.path)))):
            if verbose_mode: print "File already exists in " + current_dir + ". Downlaod aborted."
            summary.append(i.url + " was previously downloaded.\nUse -o flag to enable overwrite mode.")
            success -= 1
        else:
            savedto = urllib.urlretrieve(i.url, os.path.join(current_dir +'/' + options.subreddit, basename(parsed_url.path)))
            if verbose_mode: print savedto
    elif (parsed_url.netloc == 'i.imgur.com'):
        if verbose_mode: print "Direct imgur link.  Downloading..."
        if (not(overwrite_mode) and os.path.exists(os.path.join(current_dir + '/' + options.subreddit, basename(parsed_url.path)))):
            if verbose_mode: print "File already exists in " + current_dir + ".  Download aborted."
            summary.append(i.url + " was previously downloaded.\nUse -o flag to enable overwrite mode.")
            success -= 1
        else:
            savedto = urllib.urlretrieve(i.url, os.path.join(current_dir + '/' + options.subreddit, basename(parsed_url.path)))
            if verbose_mode: print savedto
    elif (parsed_url.netloc == 'imgur.com'):
        # imguralbum.py support added in v0.55
        if (parsed_url.path[0:3] == '/a/'):
            if verbose_mode: print "Imgur album path.  Downloading..."

            if album_active:
                # Only checks if album path already exists.
                # If it does, it won't try re-downloading the files within the album
                # regardless of whether they have changed.
                # This is the simplest solution at the moment.  A better one will follow.
                if (not(overwrite_mode) and os.path.exists(os.path.join(current_dir + '/' + options.subreddit, basename(parsed_url.path)))):
                    if verbose_mode: print "Album path already exists in current directory.  Contents will not be re-downloaded."
                    summary.append(i.url + " already exists as an album path.\nUse -o flag to enable overwrite mode.")
                    success -= 1
                else:
                    if verbose_mode: print "Downloading Imgur album. Please wait..."
                    downloader = imguralbum.ImgurAlbumDownloader(i.url, output_messages=False)
                    downloader.save_images()

            else:
                print "Imgur album support deactivated.  Either imguralbum.py is missing or you ran this script with the -a --album flag."
                summary.append(i.url + " is an Imgur album path.\nimguralbum.py required for album downloads.\nIt is either missing or you ran this script with the -a flag")
                success -= 1

        else:
            if not(overwrite_mode) and os.path.exists(current_dir + '/' + options.subreddit + parsed_url.path + '.jpg'): # fixed overwrite bug by adding .jpg & modifying path join
                 if verbose_mode: print "File already exits in " + current_dir + '/' + options.subreddit + ".  Download aborted."
                 summary.append(i.url + " was already downloaded.\nUse -o flag to enable overwrite mode.")
                 success -= 1
            else:
                 if verbose_mode: print "Indirect imgur link.  Downloading..."
                # this path joining needs to be fixed for cross-platform compatibility
                 savedto = urllib.urlretrieve(build_imgur_dl(parsed_url), current_dir + '/' + options.subreddit + parsed_url.path + '.jpg') #build imgur direct link & download it
                 if verbose_mode: print savedto
    else:
        plen = len(parsed_url.path)
        if parsed_url.path[plen-4:plen].lower() == '.jpg' or parsed_url.path[plen-4:plen].lower() == '.gif' or parsed_url.path[plen-4:plen].lower() == '.png' or parsed_url.path[plen-4:plen].lower() == '.jpeg': # added .lower() to all results to allow for uppercase file extensions
            if not(overwrite_mode) and os.path.exists(os.path.join(current_dir + '/' + options.subreddit, basename(parsed_url.path))):
                 if verbose_mode: print "File already exists in " + current_dir + '/' + options.subreddit + ".  Download aborted."
                 summary.append(i.url + " was already downloaded.\nUse -o flag to enable overwrite mode.")
                 success -= 1
            else:
                 if verbose_mode: print "Unknown source.  Downloading..."
                 savedto = urllib.urlretrieve(i.url, os.path.join(current_dir + '/' + options.subreddit, basename(parsed_url.path)))
                 if verbose_mode: print savedto
        else:
            if verbose_mode: print "Unknown HTML encountered.  Download abort."
            summary.append(i.url + " is an unsupported URL.\nNo image files found.")
            success -= 1

if verbose_mode:
    print "\n" + str(success) + " of " + str(len(sublist)) + " files downloaded."
    if len(summary) > 0:
        print "\nSummary of errors:"
        for i in summary:
            print i

    # to be added - urllib.urlretrieve exception IOError if something goes wrong.
            # Possibly break into a subroutine to simplify and make it pretty.
