import praw
from time import sleep
import requests
from collections import deque


USER_AGENT="audioBookGuide v1.0"
TARGET_SUB="audiobooksonyoutube"


'''	Parse the newest submissions in the target sub. Return each
	submissions' title, and the Youtube ID of the linked audiobook. '''
def parse_submissions(target_sub):
	
	r = praw.Reddit(user_agent=USER_AGENT)
	subreddit = r.get_subreddit(TARGET_SUB)

	# Create an array of titles (where possible), and their respective
	# video ID.
	titles, ids = [], []
	for submission in subreddit.get_new():
		title = parse_title(submission.title)
		if title:
			titles.append(title)
			ids.append(get_video_id(submission.url))

	return titles, ids


'''	Parse the 'title', assuming the correct format is used. Toggle
	'verbose' for error messages if desired. '''
def parse_title(title, verbose=False):

	# Attempt to parse the title. If it isn't formatted correcly then
	# simply return None.
	try:
		term = title.index('(')
		return title[:term]
	except ValueError as val_error:
		if verbose: print "error: " + str(val_error)


'''	Return the ID of a Youtube video, from a Youtube URL. '''
def get_video_id(url):
	
	start = url.find('v=') + 2
	end = url.find('&')
	
	# Handle 'youtu.be' links.
	if '.be' in url:
		start = url.find('.be/') + 4
		return url[start:]
	
	# Hande playlist links.
	if '?list=' in url:
		start = url.find('?list=') + 6
		return url[start:]
	
	return url[start:end]


'''	Create valid query URLs for the Goodreads API. '''
def linkify(titles):
	
	gr_base	= "https://www.goodreads.com/book/title.xml?title="
	gr_suffix = "&key=" + GOODREADS_KEY
	
	urls = []
	for title in titles:
		url = gr_base + title + gr_suffix
		urls.append(url)

	return urls


'''	Return an array containing the desired metadata from the given
	Goodreads formatted URL. '''
def get_book_data(url):

	# Read in the XML from the given URL.
	import xmltodict
	
	r = requests.get(url)
	xml = xmltodict.parse(r.text)
	
	# Gather Book metadata.
	body		= {}
	book_data 	= xml['GoodreadsResponse']['book']
	body['title'] 	= book_data['title']
	body['author']	= book_data['authors']['author']['name']
	body['date']	= str(book_data['publication_year']) + ', ' + \
			  	book_data['publication_month'] + ', ' + \
			  	book_data['publication_day']
	body['desc']	= strip_html(book_data['description'])
	body['tags']	= book_data['popular_shelves']['shelf'][2]['@name'], \
			  book_data['popular_shelves']['shelf'][3]['@name'], \
			  book_data['popular_shelves']['shelf'][4]['@name']
	body['rating']	= book_data['average_rating']

	return body


'''	Remove HTML tags in the given string. '''
def strip_html(string):

	import re
	
	html_cleaner = re.compile('<.*?>')
	return re.sub(html_cleaner, '', string)


'''	Create valid query URLS for the Youtube API, using video IDs. '''
def linkify_youtube(video_ids):

	youtube_base 	= "https://www.googleapis.com/youtube/v3/videos?id="
	youtube_suffix 	= "&part=contentDetails&key=" + YOUTUBE_KEY
	
	urls = []
	for video_id in video_ids:
		yt_url = youtube_base + video_id + youtube_suffix
		urls.append(yt_url)

	return urls


'''	Get metadata from the given Youtube URL. '''
def get_audio_data(url):
	
	import json
	
	r = requests.get(url)
	json_data = json.loads(r.text)
	
	#TODO: Use the Youtube API to handle playlist requests. Returning
	# 'Playlist' for now suffices, but is hardly very useful.
	try:	
		iso_duration = json_data['items'][0] \
					['contentDetails'] \
					['duration']
	except IndexError:
		return "Playlist."
	
	'''	(Helper) Youtube returns video durations in ISO-8601 format.
		We can convert this using the 'isodate' library. '''
	def convert_iso(duration):
		import isodate
		return isodate.parse_duration(duration)

	return str(convert_iso(iso_duration))


'''	Submit a comment to the thread with the given text body. '''
def format_comment(body):

	header 		= "# " + body['title'] + " (" +\
			  body['date'].split(',')[0] + ")\n"
	metadata	= "`Author`: " + body['author'] + "    " + \
			  "`Date of Publication`: " + body['date'] + '\n\n' + \
			  "`Audio Runtime` *is* " + body['run_time'] + ". " + \
			  "*Tagged in* `" + body['tags'][0] + "`, `" + \
			  body['tags'][1] + "`, `" + body['tags'][2] + "`" + '\n\n'
	rating		= "`Average Rating` **" + body['rating'] + "/5**\n\n"
	description	= ">" + body['desc'] + "\n\n"
	footer		= "  [source code.](https://github.com/tallosan/reddit-bots/tree/master/AudioBookGuide)  [send me feedback.](https://www.reddit.com/user/AudioBookGuidev1)"

	return header + \
	       metadata + rating + \
	       description + \
	       footer


CACHE_SIZE=10
cache = deque(maxlen=CACHE_SIZE)


titles, ids 	= parse_submissions(TARGET_SUB)
gr_links 	= linkify(titles)
yt_links	= linkify_youtube(ids)
book		= get_book_data(gr_links[1])
book['run_time'] = get_audio_data(yt_links[1])
comment = format_comment(book)
print comment

r = praw.Reddit(user_agent=USER_AGENT)
#LOGIN WITH PRIVATE INFO.
sub	= r.get_subreddit('testingground4bots')
sub = sub.get_new()
thread= next(sub)
thread.add_comment(comment)


