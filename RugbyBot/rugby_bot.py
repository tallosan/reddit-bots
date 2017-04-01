#
# Rugby Bot: Creates a match thread for each Rugby Union fixture.
#
# ========================================================================


import praw

import requests
from lxml import html

import schedule
import time

from collections import deque


'''   Responsible for getting any rugby matches scheduled, and creating threads
      when necessary. '''
class Scheduler(object):

	''' Create a scheduler.
	    Args:
	    	cache_size: The size of our match cache.
		*url: The URL to get the match data from.
	'''
	def __init__(self, cache_size=20, url='http://www.espn.co.uk'):
		
		self.base_url 	   = url
		self.url 	   = self.base_url + '/rugby/scoreboard'
		
		self.cache	   = deque(maxlen=cache_size)

	''' Wrapper for _run_scheduler(). Runs the scheduler and polls according
	    to the given polling interval.
	    Args:
	    	poll_interval: The interval between polls.
	'''
	def run_scheduler(self, poll_interval):
		
		# Set a Cron job.
		#schedule.every(poll_interval).minutes.do(self._run_scheduler)
		while True:
			#schedule.run_pending()
			self._run_scheduler()
	
	''' Run the scheduler to determine which match threads need to
	    be created. '''
	def _run_scheduler(self):
		
		# Perform an update on the match thread (assuming the match is already
		# posted and is active), or create a new match thread.
		self.get_matches(self.url)
		for match in self.cache:
			if match.is_posted and match.is_active:
				match.update_thread()
			elif not match.is_posted:
				match.post_thread()
			lkjasd;

	''' Returns a list of Match objects that are not currently in the
	    scheduler's cache.
	'''
	def get_matches(self, url):

		request = requests.get(url)
		tree = html.fromstring(request.content)

		# Get the relative match URLs, and create full URLs. If the URL
		# does not belong to a Match already in our cache then we can add it.
		schedule = tree.xpath('//a[@class="competitors"]')
		matches  = []
		for match in schedule:
			match_url = self.base_url + match.get('href')
			if not any((match.url == match_url) for match in self.cache):
				self.cache.append(
						Match(self.base_url + match.get('href'))
				)


'''   Represents a rugby union match. '''
class Match(object):

        ''' Create a Match object. '''
        def __init__(self, url):

                self.url = url

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
		self.parse_gamethread(self.url)
 
 	''' Create a thread for this Match. '''
	def post_thread(self):
                
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
		self.thread['lineups'] += "**Player** | **Position** ""| " + \
					  "**Player** | **Position**\n"
		self.thread['lineups'] += ":-|:-|:-|:-\n"
		for h_player, a_player in zip(self.home_team['starters'],
					      self.away_team['starters']):
			self.thread['lineups'] += h_player[0] + '   ' + h_player[1] + \
						  ' | ' + h_player[2]  + ' | '
			self.thread['lineups'] += a_player[0] + '   ' + a_player[1] + \
						  ' | ' + a_player[2] + '\n'
		self.thread['lineups'] += "\n## **Replacements**\n"
		self.thread['lineups'] += "**Player** | **Position** | " + \
					  "**Player** | **Position**\n"
		self.thread['lineups'] += ":-|:-|:-|:-\n"
		for h_sub, a_sub in zip(self.home_team['subs'], self.away_team['subs']):
			self.thread['lineups'] += h_sub[0] + '   ' + h_sub[1] + \
						  ' | ' + h_sub[2]  + ' | '
			self.thread['lineups'] += a_sub[0] + '   ' + a_sub[1] + \
						  ' | ' + a_sub[2] + '\n'
		self.thread['lineups'] += '\n\n----\n\n'
		
		# Match Events.
		self.thread['events'] = self.format_events()
		
		# Post the thread, and update the posted flag.
		self.post = r.submit(target_sub,
				title=self.thread['title'],
			 	body=self.thread['header'] + self.thread['venue'] + \
			      	self.thread['lineups'] + self.thread['events']
		)
		
		self.is_posted = True

	''' Update the Match thread. N.B. -- We only need to update the dynamic
	    values here. '''
	def update_thread(self):

                request = requests.get(url)
                tree = html.fromstring(request.content)

		# Get the current score.
		self.home_team['score'], self.away_team['score'] = self.get_score(tree)
		self.game_time = self.get_time(tree)
		self.thread['header'] = format_header()

		self.events = self.get_events(tree)
		self.thread['events'] = self.format_events()

		# Perform the update.
		self.post.edit(text=self.thread['header'] + self.thread['venue'] + \
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
	
		events = "## **Match Events**:\n"
		for event in self.events:
			events += '\n\n**' + event[0] + "'**  " + event[1]

		return events

        ''' Parse the website linked via the 'url' parameter, and return all
            relevant match info (e.g. score, current time in game, etc). All static
	    data is parsed and set in this function. We leave any dynamic data
	    parsing to helper functions, as we'll need to use these throughout the
	    Match object's life.
            Args:
                url: The URL of the site to parse.
        '''
        def parse_gamethread(self, url):

                request = requests.get(url)
                tree = html.fromstring(request.content)

                # Get the competition name.
                competition = tree.xpath('//*[@id="custom-nav"]/header/div[1]')[0]
                self.competition = competition.text_content()

		venue = tree.xpath('//*[@id="main-container"]/div/div/div[1]'
				   '/article[2]/div/div[1]/div[1]/div/span[3]')[0]
		self.venue = venue.text_content()

                # Get the team names, and their current score.
                h_team  = tree.xpath('//*[@id="custom-nav"]/header/div[2]'
                                     '/div[1]/div/div[2]/div/div/a/span[2]')[0]
                a_team  = tree.xpath('//*[@id="custom-nav"]/header/div[2]'
                                     '/div[3]/div/div[3]/div/div/a/span[2]')[0]
               
                self.home_team['name']  = h_team.text_content()
		self.home_team['flair'] = '[] (#' + self.home_team['name'].lower() + ')'
                self.away_team['name']  = a_team.text_content()
		self.away_team['flair'] = '[] (#' + self.away_team['name'].lower() + ')'

		self.home_team['score'], self.away_team['score'] = self.get_score(tree)

                # Get the current game time.
		self.game_time = self.get_time(tree)
                
		# Get the try info (scorers and try time).
                h_tries = tree.xpath('//*[@id="custom-nav"]/div[1]/div/div/'
                                       'div[1]/div')[0]
                a_tries = tree.xpath('//*[@id="custom-nav"]/div[1]/div/div/'
                                       'div[2]/div')[0]

		#print tree.xpath('//*[@id="custom-nav"]/div[1]/div/div/div[1]/div/ul[1]')[0].text_content().split(')')
                self.home_team['tries'] = self.get_tries(h_tries)
                self.away_team['tries'] = self.get_tries(a_tries)

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
				players.append( (number, name, pos) )

                return players

	''' Get all key events during the match.
	    Args:
		    events_url: The URL to the match's commentary page.
	'''
	def get_events(self, tree):
		
		e_href	   = tree.xpath('//*[@id="main-container"]/div/div/div[2]'
				    '/article[2]/footer/a')[0].get('href')
		events_url = self.url.split('/rugby/match?')[0] + e_href

		events_request = requests.get(events_url)
		events_tree    = html.fromstring(events_request.content)

		# Return a list of events from the table element. N.B. -- We need
		# to reverse the list as ESPN formats it in reverse chronological order.
		events = events_tree.xpath('//*[@id="tab1"]/table/tbody')[0]
		return [ 
				event.text_content().split("'")
				for event in events.getchildren()
		][::-1]


URL = 'http://www.espn.co.uk/rugby/match?gameId=290096&league=267979'

scheduler = Scheduler()
scheduler.run_scheduler(poll_interval=30)

laskdj;
# ========================================================================

USER_AGENT = 'RugbyUnionBot'
USERNAME   = 'RugbyUnionBot'
PASSWORD   = 'rugbyunionbot1234'	# Dummy password.

POLL_INTERVAL = 30

r = praw.Reddit(user_agent=USER_AGENT)
r.login(username=USERNAME, password=PASSWORD, disable_warning=True)


if __name__=='__main__':
        
	scheduler = Scheduler(cache_size=20)
	scheduler.run_scheduler(poll_interval=POLL_INTERVAL)

