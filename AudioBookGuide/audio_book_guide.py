import praw
from time import sleep
import requests
from collections import deque
import cPickle as pickle


USER_AGENT="audioBookGuide v1.0"
TARGET_SUB="audiobooksonyoutube"


'''	Parse the newest submissions in the target sub. Return a list of
	dictionaries, where each dict contains the actual submission object,
	submission metadata, and the Youtube ID of the link audio. '''
def parse_submissions(target_sub):
	
	threads, titles, ids = [], [], []
	submissions = []
	for submission in subreddit.get_new(limit=10):
		title = parse_title(submission.title)
		if title:
			thread = {
					'sub'	: submission,
					'title'	: title,
					'id'	: submission.id,
					'vid_id': get_video_id(submission.url)
				  }
			
			submissions.append(thread)

	return submissions


'''	Parse the 'title', assuming the correct format is used. Toggle
	'verbose' for error messages if desired. '''
def parse_title(title, verbose=False):

	# If the title is not formatted correctly then we can safely return.
	try:
		term = title.index('(')
		return title[:term]
	except ValueError as val_error:
		if verbose: print "error: " + str(val_error)


'''	Return the ID of a Youtube video, from a Youtube URL. '''
def get_video_id(url):
	
	# Handle 'youtu.be' links.
	if '.be' in url:
		start = url.find('.be/') + 4
		return url[start:]
	
	# Hande playlist links.
	if '?list=' in url:
		start = url.find('?list=') + 6
		return url[start:]
	
	start = url.find('v=') + 2
	#end = url.find('&')
	
	return url[start:]


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
	Goodreads formatted URL. Toggle 'verbose' for error messages (if any). '''
def get_book_data(url, verbose=False):

	# Read in the XML from the given URL. If this fails, then we assume
	# the book data does not exist on Goodreads.
	import xmltodict
	try:
		r = requests.get(url)
		xml = xmltodict.parse(r.text, force_list={'author': True})
		book_data 	= xml['GoodreadsResponse']['book']
	except Exception as book_not_found_error:
		if verbose: print 'error: ' + str(book_not_found_error)
		return

	# Gather Book metadata.
	body		= {}
	body['title'] 	= book_data['title']
	body['author']	= book_data['authors']['author'][0]['name']
	
	# If date is not available then we sub in 'n/a'.
	l = lambda date_val: date_val if date_val != None else 'n/a'
	body['date']	= ', '.join(map(l, [book_data['publication_year'], \
			       		    book_data['publication_month'], \
			       		    book_data['publication_day']]))
	body['desc']	= strip_html(book_data['description'])
	body['rating']	= book_data['average_rating']
	if book_data['popular_shelves']:
		body['tags'] = book_data['popular_shelves']['shelf'][2]['@name'], \
			       book_data['popular_shelves']['shelf'][3]['@name'], \
			       book_data['popular_shelves']['shelf'][4]['@name']
	else:
		body['tags'] = ('No', 'Tags', 'Available')

	return body


'''	Remove HTML tags in the given string. '''
def strip_html(string):

	import re
	try:
		html_cleaner = re.compile('<.*?>')
		return re.sub(html_cleaner, '', string)
	except Exception:
		return "No description available."


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
		return "unknown"
	
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
	description	= ">" + body['desc'] + " (*provided by Goodreads*).\n\n"
	footer		= "  [source code.](https://github.com/tallosan/reddit-bots/tree/master/AudioBookGuide)  [send me feedback.](https://www.reddit.com/user/AudioBookGuidev1)"
	return header + \
	       metadata + rating + \
	       description + \
	       footer


# Cache parameters. The cache is necessary as we do not want to post in the
# same thread each cycle.
CACHE_SIZE=50
CACHE_FNAME='abg-cache.pickle'

# Load the cache. If none exists, create a new one.
try:
	with open(CACHE_FNAME, 'rb') as fp:
		cache = pickle.load(fp)
except EOFError as eof_error:
	cache = deque(maxlen=CACHE_SIZE)
	print str(eof_error) + ": creating a new cache."

# Log into Reddit as the bot.
r = praw.Reddit(user_agent=USER_AGENT)
subreddit = r.get_subreddit(TARGET_SUB)

# Run once every 3 minutes, commenting on any new, properly formatted, threads.
while True:
	
	print "starting cycle."
	subs = parse_submissions(subreddit)
	threads, titles, ids = [], [], []
	for sub in subs:
		if sub['id'] not in cache:
			threads.append(sub['sub'])
			titles.append(sub['title']), ids.append(sub['vid_id'])
			cache.append(sub['id'])
	
	print str(len(cache)) + ' occupants: ' + str(cache)
	gr_links = linkify(titles)
	yt_links = linkify_youtube(ids)
	bad =[]	
	# Create a Reddit comment from the available book and video data.
	for thread, gr_link, yt_link in zip(threads, gr_links, yt_links):
		print gr_link
		book = get_book_data(gr_link)
		if book:
			book['run_time'] = get_audio_data(yt_link)
			comment = format_comment(book)
			print 'adding comment to ...\n' + gr_link + '\n'
			print comment
			
			# Attempt to post the comment. Remember to update cache.
			posted = False
			while posted is False:
				try:
					thread.add_comment(comment)
					with open(CACHE_FNAME, 'wb') as fp:
						pickle.dump(cache, fp)
					posted = True
				except Exception: 
					print "rate limit exceeded. \
							going to sleep ..."
					sleep(120)
		else:
			bad.append(gr_link)
			print '\ninvalid book. ' + gr_link
		
		print '\ncomment added.'
	
	print '\nfinished cycle.'
	print '\n', len(bad), bad
	sleep(600)

