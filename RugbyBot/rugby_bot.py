#
# Rugby Bot: Creates a match thread for each Rugby Union fixture.
#
# ========================================================================


import praw

import requests
from lxml import html

import time

from datetime import datetime

import dateutil
import dateutil.parser as date_parser

from operator import itemgetter

from collections import deque


'''   Responsible for getting any rugby matches scheduled, and creating threads
      when necessary. '''
class Scheduler(object):

	''' Create a scheduler.
	    Args:
	    	subreddit_name: The name of the target subreddit.
	    	cache_size: The size of our match cache.
		*url: The URL to get the match data from.
	'''
	def __init__(self, subreddit_name, cache_size, url='http://www.espn.co.uk'):
		
		self.base_url 	   = url
		self.url 	   = self.base_url + '/rugby/scoreboard'
		self.target_sub	   = r.subreddit(subreddit_name)

		self.cache	   = deque(maxlen=cache_size)

	''' Wrapper for _run_scheduler(). Runs the scheduler and polls according
	    to the given polling interval.
	    Args:
	    	poll_interval: The interval between polls.
	'''
	def run_scheduler(self, hours_before):
		
		# Set a Cron job.
		while True:
			interval = self.get_interval()
			interval[0].hours -= hours_before
			interval[1].hours += hours_before + 1
			
			print 'sleeping for ', interval[0].days, ' days, ',\
				interval[0].hours, ' hours and ',\
				interval[0].minutes, ' minutes.'
			
			# Determine the number of seconds until the next game, and
			# sleep for them.
			interval_open = ((interval[0].hours * 60) * 60) +\
					 (interval[0].minutes * 60) +\
					  interval[0].seconds
			time.sleep(interval_open)
			
			# When we wake up, calculate the interval time and run
			# our program until it is up.
			interval_time = \
				  ((interval[1].hours - interval[0].hours) * 60) *60\
				+ ((interval[1].minutes - interval[0].minutes) * 60)\
				+ ((interval[1].seconds) - interval[0].seconds)

			print 'running for ', interval_time / 60 / 60, ' hours.'
			while time.time() < interval_time:
				try:
					self._run_scheduler()
				except Exception:
					pass
				
				time.sleep(30)

			# Determine the amount of time until midnight, and then sleep
			# until then before restarting the cycle all over again.
			minutes_left = (60 * interval[1].hours) + interval[1].minutes
			time_to_midnight = (24*60) - minutes_left

			print 'cycle complete.'
			print 'sleeping for ', time_to_midnight, ' minutes.'
			
			time.sleep(time_to_midnight)
	
	''' Run the scheduler to determine which match threads need to
	    be created. '''
	def _run_scheduler(self):
		
		# Perform an update on the match thread (assuming the match is already
		# posted and is active), or create a new match thread.
		self.get_matches(self.url)
		for match in self.cache:
			match = self.cache[2]
			if match.is_posted and match.is_active:
				match.update_thread()
				print 'UPDATE 200: ', match
			elif not match.is_posted:
				match.post_thread(target_sub=self.target_sub)
				print 'POST 200: ', match
		
	''' Returns a list of Match objects that are not currently in the
	    scheduler's cache.
	'''
	def get_matches(self, url):

		request = requests.get(url)
		tree = html.fromstring(request.content)

		# Get the relative match URLs, and create full URLs. If the URL
		# does not belong to a Match already in our cache then we can add it.
		schedule = tree.xpath('//a[@class="competitors"]')
		
		# Append a Match to our cache iff it hasn't already been added, and is
		# ready to be added.
		for match in schedule:
			match_url = self.base_url + match.get('href')
			if not any((match.url == match_url) for match in self.cache):
				self.cache.append(
						Match(self.base_url + match.get('href'))
				)

	''' Get the next interaval to run on. '''
	def get_interval(self):
		
		request = requests.get(self.url)
		tree = html.fromstring(request.content)
	
		# Get the dates and times for all games on the next match day.
		dates	 = tree.xpath('//span[@class="game-date"]')
		times	 = tree.xpath('//span[@class="game-time"]')
		dts	 = [
				[date.text_content(), time.text_content()]
				for date, time in zip(dates, times)
		]

		# Now sort them by time (we assume the day is the same).
		for dt in dts: dt[1] = date_parser.parse(dt[1])
		dts.sort(key=itemgetter(1))

		# Get the opening and closing endpoints, and format them.
		a_endpoint = dts[0]
		b_endpoint = dts[-1]

		return [ self.format_endpoint(a_endpoint[0], a_endpoint[1]), 
		         self.format_endpoint(b_endpoint[0], b_endpoint[1]) ]

	''' Returns a relativedelta object which represents the amount of time
	    before the given date and time.
	    Args:
	    	date: A list containing the month and day.
		time: A datetime object containing the match time.
	'''
	def format_endpoint(self, date, time):

		# Get the number of months and days until the match.
		date = date.split('/')
		month = int(date[1])
		day   = int(date[0])
		
		# Set the month and day. We then calculate the time delta until
		# the next match.
		time = time.replace(month=month, day=day)
		delta = dateutil.relativedelta.relativedelta(time, datetime.now())
		
		return delta


'''   Represents a rugby union match. '''
class Match(object):

        ''' Create a Match object. '''
        def __init__(self, url):

                self.url = url
		self.sub = 'bottesting'

                # Match data.
		self.competition = None
		self.venue 	 = None
                self.game_time   = None
		self.key_events	 = None
		self.post 	 = None
		
		self.thread 	 = {}
                self.home_team   = {}
                self.away_team   = {}

		# Monitors the status of the game.
		self.is_posted	 = False
		self.is_active	 = False

                # Initialize static fields, and get current dynamic fields.
		self.setup_gamethread()
 
 	''' Create a thread for this Match.
	    Args:
	    	target_sub: A praw.models.subreddit instance to post our submission to.
	'''
	def post_thread(self, target_sub):
		
		# Thread title.
		self.thread['title'] = "Match Thread: " + \
				self.home_team['name'] + ' vs ' +  \
				self.away_team['name'] + ' [' + self.competition + ']'
		
		# Title / Header.
		self.thread['header'] = self.format_header()
		
		# TODO: Post scorers.
		#thread += ', '.join([' '.join(_try) for _try in self.home_team['tries']])
		self.thread['venue'] = '\n## **Venue**: ' + self.venue + '\n\n----\n\n'
		
		# Lineups: Starters, then Replacements.
		self.thread['lineups'] = "## **Starting Lineups**:\n\n"
		self.thread['lineups'] += "**" + self.home_team['name'] + "**" + \
					  " | **Position** ""| " + \
					  "**" + self.away_team['name'] + "**\n"
		self.thread['lineups'] += ":-|:-|:-\n"
		for h_player, a_player in zip(self.home_team['starters'],
					      self.away_team['starters']):
			self.thread['lineups'] += str(h_player[0]) + ' .  ' + \
						  h_player[1] + ' | ' + h_player[2] + ' | '
			self.thread['lineups'] += str(a_player[0]) + '.   ' + \
						  a_player[1] + '\n'
		self.thread['lineups'] += "\n## **Replacements**:\n"
		self.thread['lineups'] += "**" + self.home_team['name'] + "**" + \
					  " | **Position** ""| " + \
					  "**" + self.away_team['name'] + "**\n"
		self.thread['lineups'] += ":-|:-|:-\n"
		for h_sub, a_sub in zip(self.home_team['subs'], self.away_team['subs']):
			self.thread['lineups'] += str(h_sub[0]) + '.   ' + \
						  h_sub[1] + ' | ' + h_sub[2]  + ' | '
			self.thread['lineups'] += str(a_sub[0]) + '.   ' + a_sub[1] + '\n'
		self.thread['lineups'] += '\n\n----\n\n'
		
		# Match Events.
		self.thread['events'] = self.format_events()
		
		print self.thread['header'] + self.thread['venue'] + \
			      	     	 self.thread['lineups'] + self.thread['events']
		dslkj;

		# Post the thread, and update the posted flag.
		self.post = target_sub.submit(
				title=self.thread['title'],
			 	selftext=self.thread['header'] + self.thread['venue'] + \
			      	     	 self.thread['lineups'] + self.thread['events']
		)
		
		self.is_posted = True
		self.is_active = True

	''' Update the Match thread. N.B. -- We only need to update the dynamic
	    values here. '''
	def update_thread(self):

                request = requests.get(self.url)
                tree = html.fromstring(request.content)

		# Get the current score, and the game time.
		self.home_team['score'], self.away_team['score'] = self.get_score(tree)
		self.game_time = self.get_time(tree)
		self.thread['header'] = self.format_header()

		# If the game is over, then we need to set our is_active flag accordingly.
		if self.game_time == 'FT': self.is_active = False
		
		# Get the try info (scorers and try time).
                h_tries = tree.xpath('//*[@id="custom-nav"]/div[1]/div/div/'
                                       'div[1]/div')[0]
                a_tries = tree.xpath('//*[@id="custom-nav"]/div[1]/div/div/'
                                       'div[2]/div')[0]

                self.home_team['tries'] = self.get_tries(h_tries)
                self.away_team['tries'] = self.get_tries(a_tries)

		# Get the current events tree.
		self.events = self.get_events(tree)
		self.thread['events'] = self.format_events()
		
		# Perform the update.
		self.post = self.post.edit(
				body=self.thread['header'] + self.thread['venue'] + \
			      	     self.thread['lineups'] + self.thread['events']
		)

	''' Format the thread header using Markdown syntax. '''
	def format_header(self):
		
		header = '# ' + self.game_time + ': ' + \
			  self.home_team['name'] + ' ' + self.home_team['flair'] + ' ' + \
			  self.home_team['score'] + '-' + self.away_team['score'] + ' ' + \
			  self.away_team['flair'] + ' ' + self.away_team['name'] + '\n'

		return header

	''' Format the match events using Markdown syntax. '''
	def format_events(self):

		event_flairs = {
				'red_card': '[](#redcard)',
				'yellow_card': '[](#yellowcard)',
				'Substitute': '[](#sub)', 'substituted': '[](#sub)',
				'Try': '[](#try)',
				'Conversion': '[](#conv)',
				'Penalty': '[](#pen)',
				'Drop': '[](#drop)'
		}
		
		key_events = ['red_card', 'yellow_card', 'Try', 'Conversion', 'Penalty']
		events = "## **Match Events**:\n"
		for event in self.events:
			
			# Check for a flair.
			flair = [
					f for f in event_flairs.keys()
					if f in event[1].split()
			]
			
			# Prepend the flair markdown. Bold the event if necessary.
			if flair:
				if flair[0] in key_events:
					event[1] = '**' + event[1] + '**'
				
				event[1] = event_flairs[flair[0]] + ' ' + event[1]
			
			events += '\n\n**' + event[0] + "'**  " + event[1]

		return events

        ''' Parse the website linked via the 'url' parameter, and return all
            relevant match info (e.g. score, current time in game, etc). All static
	    data is parsed and set in this function. We leave any dynamic data
	    parsing to helper functions, as we'll need to use these throughout the
	    Match object's life.
        '''
        def setup_gamethread(self):

                request = requests.get(self.url)
                tree = html.fromstring(request.content)

                # Get the competition and venue names.
                competition = tree.xpath('//*[@id="custom-nav"]/header/div[1]')[0]
                self.competition = competition.text_content()
		
	 	venue = tree.xpath('//div[@class="game-details location-details"]')[0]
		self.venue = venue.text_content().split(':')[1]
               
		# Get the team names, their flare, and their current score.
                h_team  = tree.xpath('//*[@id="custom-nav"]/header/div[2]'
                                     '/div[1]/div/div[2]/div/div/a/span[2]')[0]
                a_team  = tree.xpath('//*[@id="custom-nav"]/header/div[2]'
                                     '/div[3]/div/div[3]/div/div/a/span[2]')[0]
                
		self.home_team['name']  = h_team.text_content()
                self.away_team['name']  = a_team.text_content()
		
		self.home_team['flair'] = self.get_flair(self.home_team['name'])
		self.away_team['flair'] = self.get_flair(self.away_team['name'])
		
		self.home_team['score'], self.away_team['score'] = self.get_score(tree)

                # Get the current game time.
		self.game_time = self.get_time(tree)
                
		# Get the team lineups (starters & subs).
                h_lineup = tree.xpath('//*[@id="main-container"]/div/div/div[1]/'
                                'article[1]/div/div[1]/div/div/div/table/tbody[1]')[0]
                h_subs   = tree.xpath('//*[@id="main-container"]/div/div/div[1]/'
                                'article[1]/div/div[1]/div/div/div/table/tbody[2]')[0]
		a_lineup = tree.xpath('//*[@id="main-container"]/div/div/div[1]/'
				'article[1]/div/div[2]/div/div/div/table/tbody[1]')[0]
		a_subs	 = tree.xpath('//*[@id="main-container"]/div/div/div[1]/'
				'article[1]/div/div[2]/div/div/div/table/tbody[2]')[0]

                self.home_team['starters'] = self.get_lineup(h_lineup)
                self.home_team['subs'] 	   = self.get_lineup(h_subs)
		self.away_team['starters'] = self.get_lineup(a_lineup)
		self.away_team['subs']	   = self.get_lineup(a_subs)
		
		# Get events.
		self.events = self.get_events(tree)
		self.format_events()

	''' Returns the flair markdown for the given team.
	    Args:
	    	name: The name of the team.
	'''
	def get_flair(self, name):
		
		flairs_request = requests.get('https://www.reddit.com/r/rugbyunion/'
					      'wiki/inlineflair.json',
					      headers={'User-agent': 'RugbyUnionBot'})

		flairs_json    = json.loads(flairs_request.content)
		flairs_json = flairs_json['data']['content_md'].split('inline flairs:')
		flairs_json = flairs_json[1].split('Cards:')[0]

		# Reformat name.
		name = name.lower()
		if len(name.split(' ')) > 1:
			name = '-'.join(name.split(' '))

		# Create a dictionary of team flairs (exclude competitions!).
		comps = ['[](#premiership)', '[](#pro12)', '[](#top14)', '[](#super-rugby)']
		flairs = {
				'newcastle': '[](#newcastle)',
				'gloucester': '[](#gloucester)',
				'sale': '[](#sale)',
				'worcester': '[](#worcester)',
				'edinburgh': '[](#edinburgh)',
				'connacht': '[](#connacht)',
				'ulster': '[](#ulster)',
				'cardiff-blues': '[](#cardiff-blues)',
				'hurricanes': '[](#hurricanes)',
				'waratahs': '[](#waratahs)'
		}
		
		# Check for matches.
		if name in flairs:
			return flairs[name]
		else:
			split_name = name.split('-')
			if (split_name[0] + split_name[1]) in flairs:
				return flairs[split_name[0] + split_name[1]]
			
			# Get all possible matches. We then return the closest match
			# i.e. the one with the longest key.
			matches = {}
			for _name in split_name:
				results = [f for f in flairs.keys() if f.find(_name) != -1]
				if results: matches[_name] = results
			if matches:
				name = max(matches.keys(), key=len)
				return flairs[name]
		
		return ""

	''' Get the current score, and return a tuple like so: (home score, away score)
	    Args:
	    	tree: The HTML document tree.
	'''
	def get_score(self, tree):
     		
		h_score = tree.xpath('//*[@id="custom-nav"]/header/div[2]'
                                     '/div[1]/div/div[3]/div')[0]
 		a_score = tree.xpath('//*[@id="custom-nav"]/header/div[2]'
                                     '/div[3]/div/div[2]/div')[0]
		
		return (h_score.text_content(), a_score.text_content())

	''' Get the current time in the game.
	    Args:
		tree: The HTML document tree.
	'''
	def get_time(self, tree):
 
		time = tree.xpath('//*[@id="custom-nav"]/header/div[2]/div[2]/span[3]')[0]
                return time.text_content()

	''' Parses the 'tries' div, and returns a list of tuples where the first
            element is the try scorer's name, and the second is the try time.
            Args:
                e_tries: An HtmlElement containing the match's try data.
        '''
        def get_tries(self, try_element):

                tries = []
                for _try in try_element.text_content().split(')')[:-1]:
                        scorer = _try.split('(')[0]
                        time   = _try.split('(')[1]
                        tries.append( (scorer, time) )

                return tries

        ''' Returns a lineup (either starting, or sub) in list form, where each
            player is represented by a tuple formatted as (number, name, position).
            Args:
                lineup_element: An HtmlElement containing the lineup data.
        '''
        def get_lineup(self, lineup_element):

                # Go through each row and extract the player data. N.B -- We need
		# to traverse the tree to get each row.
                players = []
                for e in lineup_element.getchildren():
			
			# ESPN occasionally screws up the last row in the div, so
			# we need to handle this.
			try:
				row = e.getchildren()[0].getchildren()[0].getchildren()[0]
				
				# Parse the player's number, then their name and position.
				number = row.getchildren()[1].text_content()
				player = row.getchildren()[2].text_content().split(',')
				name   = player[0]
				pos    = player[1][1:].split(' ')[0]
			
			except IndexError:
				number = row.getchildren()[0].text_content()

				player = row.getchildren()[1].text_content().split(',')
				name   = player[0]
				pos    = player[1].strip()
			
			finally:
				players.append( (int(number), name, pos) )
		
		# Ensure that players are sorted in ascending order by number.
		players.sort(key=itemgetter(0))

		return players

	''' Get all key events during the match.
	    Args:
		    events_url: The URL to the match's commentary page.
	'''
	def get_events(self, tree):
		
		# Get the URL of the events page. N.B. -- The XPath of this element
		# changes from time to  time, so we need to handle this.
		try:
			e_href = tree.xpath('//*[@id="main-container"]/div/div/div[2]'
				    '/article[2]/footer/a')[0].get('href')
		except IndexError:
			e_href = tree.xpath('//*[@id="main-container"]/div/div/div[2]'
				     '/article[1]/footer/a')[0].get('href')

		events_url     = self.url.split('/rugby/match?')[0] + e_href
		events_request = requests.get(events_url)
		events_tree    = html.fromstring(events_request.content)

		# Return a list of events from the table element. N.B. -- We need
		# to reverse the list as ESPN formats it in reverse chronological order.
		events = events_tree.xpath('//*[@id="tab1"]/table/tbody')[0]
		return [ 
				event.text_content().split("'")
				for event in events.getchildren()
		][::-1]


# ========================================================================

r = praw.Reddit(client_id=CLIENT_ID,
		client_secret=CLIENT_SECRET,
		user_agent=USER_AGENT,
		username=USERNAME,
		password=PASSWORD
)

SUBREDDIT_NAME = 'testingground4bots'
CACHE_SIZE     = 20
HOURS_BEFORE   = 2

if __name__=='__main__':
        
	scheduler = Scheduler(subreddit_name=SUBREDDIT_NAME, cache_size=CACHE_SIZE)
	#u = 'http://www.espn.co.uk/rugby/match?gameId=290761&league=272073'
	#m = Match(u)
	#m.update_thread()
	scheduler.run_scheduler(hours_before=HOURS_BEFORE)

