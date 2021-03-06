#
# Rugby Bot: Creates a match thread for each Rugby Union fixture.
#
# ========================================================================


import praw

import requests
from lxml import html

import time

from datetime import datetime, timedelta

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
	def __init__(self, url, subreddit_name, cache_size, hours_before):
		
		self.base_url 	   = url
		self.url 	   = self.base_url + '/rugby/scoreboard'
		self.base 	   = self.base_url + '/rugby/scoreboard'
		self.target_sub	   = r.subreddit(subreddit_name)
 		
		self.date	   = datetime.today()
		self.cache	   = deque(maxlen=cache_size)
		self.hours_before  = hours_before

	''' Wrapper for _run_scheduler(). Runs the scheduler and polls according
	    to the given polling interval.
	    Args:
	    	poll_interval: The interval between polls.
	'''
	def run_scheduler(self, poll_interval):
		
		# We run in intervals. Sleep until the first match, then run until
		# all matches have completed. Then sleep again until midnight & repeat.
		while True:
		        interval = self._get_interval()
			print 'sleeping for ', interval.days, ' days, ',\
				interval.hours, ' hours and ',\
				interval.minutes, ' minutes.'
			
			# Determine the number of seconds until the next game, and
			# sleep for them.
			interval_seconds = (((interval.days * 24) * 60) * 60) +\
					   ((interval.hours * 60) * 60) +\
					   (interval.minutes * 60) +\
					   (interval.seconds)
			time.sleep(interval_seconds)
                        
                        # Get the matches, and run the scheduler on them.
                        while not self.cache:
                            try:
                                self.cache = self._get_matches()
                            except IndexError as ie:
                                print str(ie)
                                time.sleep(POLL_INTERVAL)
			while self.cache:
				try:
				    self._run_scheduler()
				except Exception as exc:
				    print str(exc)
				
				time.sleep(POLL_INTERVAL)
        
	''' Get the time interval between today and the next match date. '''
        def _get_interval(self):

            # Attempt to find the next match date. If no matches are found on the
            # given URL, then we'll need to iteratively search the next valid URL/s.
            n_match_date = None
            while not n_match_date:
                    n_match_date = self._next_match_date()
                    if not n_match_date:
                            self.url = self._get_next_url()

            # Return the time interval until our next match.
            return self._get_time_until(n_match_date)

	''' Return the next match date from the scheduler's current URL.
	    Note, this looks awfully similar to _get_matches(). Unfortunately,
	    the ESPN page doesn't load all of the necessary data to initialize
	    a Match object until a little before the match starts, so we have no
	    choice but to duplicate some code unless we want to refactor a lot. 
	    Maybe something for the future. '''
        def _next_match_date(self):
		
		request = requests.get(self.url)
		tree = html.fromstring(request.content)
		
		# Ensure that the competitions we're looking for have matches.
		comps = tree.xpath("//*[@class='date-heading js-show']")
		if not any(comp.text_content().lower() == 'super rugby' for comp in comps):
			return None
		
		# Get the dates and times for all games on the next match day.
		dates = []; times = []
		for e in tree.xpath('//div[@class="game-status"]'):
		    if e.xpath('span[@class="game-date"]') and e.xpath('span[@class="game-time"]'):
		            date = e.xpath('span[@class="game-date"]')[0]
		            time = e.xpath('span[@class="game-time"]')[0]
			    dates.append(date); times.append(time)
		
		# Get all valid date-time pairs.
		dts   = [
		  	  [_date.text_content(), date_parser.parse(_time.text_content())]
			  for _date, _time in zip(dates, times)
			  if _time.text_content().lower() != 'ft'
			  and _time.xpath('../../../../../../../../a/h2')[0].\
			            text_content().lower() == 'super rugby'
		]
                
		# Return the first match on the next match date if one is found.
                if dts:
                        match_date = min(dts, key=itemgetter(1))
                else:
                        match_date = None

                return match_date
	
        ''' Returns the URL for the next possible match date. '''
        def _get_next_url(self):

            # Get tomorrows date.
            time_diff = timedelta(days=+1)
	    self.date += time_diff

            next_month = self.date.month; next_day = self.date.day
            
            # ESPN date values have a '0' prepended to any single digit values.
            _formatter = lambda t: '0{}'.format(t) if t < 10 else t
            url = (self.base + '?date={}{}{}').\
                  format(self.date.year, _formatter(next_month), _formatter(next_day))
            
	    return url

	''' Returns a relativedelta object which represents the amount of time
	    until the given match date and time.
	    Args:
	    	next_match: A tuple containing the date and time of the next match.
	'''
	def _get_time_until(self, next_match):
		
		date, time = next_match[0], next_match[1]
		
		# Get the number of months and days until the match.
		date  = date.split('/'); month = int(date[1]); day = int(date[0])
		
		# Set the month and day. We then calculate the time delta until
		# the next match.
		time = time.replace(month=month, day=day)
		delta = dateutil.relativedelta.relativedelta(time, datetime.now())

		# Set the timezone to EST, and account for hours before.
                EST_BST_TIME_DIFF = 5
		time_diff = dateutil.relativedelta.relativedelta(
				hours=(EST_BST_TIME_DIFF + self.hours_before)
		)
		delta -= time_diff
		
		# Handle hour overflow.
		if delta.hours < 0:
			delta.hours = 24 + delta.hours; delta.days -= 1
                
		return delta

	''' Run the scheduler and determine which operation to perform. If a match
	    thread exists, and is active, then we update it. If it exists and is 
	    not active then we remove it. If no match thread exists then we create one.
	'''
	def _run_scheduler(self):
		
	        print
		# Cycle through the cache and perform the appropriate action.
		for match in self.cache:
			print match.home_team['name'], ' vs ', match.away_team['name']
                        try:
                            if match.is_posted and match.is_active:
                                    match.update_thread()
                                    print 'updating ', match
                            elif match.is_posted and (not match.is_active):
                                    print 'removing ', match
                                    self.cache.remove(match)
                            elif self._is_ready(match) and (not match.is_posted):
                                    print self._is_ready(match)
                                    match.post_thread(target_sub=self.target_sub)
                                    print 'posting ', match
                            else:
                                    print 'no action'
                        except Exception as rs:
                            print 'scheduler error: ', str(rs)

	''' Returns a list of Match objects that are not currently in the
	    scheduler's cache. '''
	def _get_matches(self):
		
		request = requests.get(self.url)
		tree = html.fromstring(request.content)

		# Get the relative match URLs, and create full URLs. If the URL
		# does not belong to a Match already in our cache then we can add it.
		schedule = tree.xpath('//a[@class="competitors"]')
		
		# Append a Match to our cache iff it hasn't already been added, and is
		# ready to be added.
		matches = []
		for match in schedule:
			match_url = self.base_url + match.get('href')
			print 'getting ', match_url
			try:
			    if not any((match.url == match_url) for match in self.cache):
			        matches.append(Match(self.base_url + match.get('href')))
			except IndexError:
			    pass
		
		matches = [match for match in matches
			  if match.competition.lower().find('super rugby') != -1]
		
		return matches
	
	''' Determines if the match is ready to be posted. '''
	def _is_ready(self, match):

		EST_BST_TIME_DIFF = 5
		match_time = date_parser.parse(match.kickoff_time)
                
                # Format the game's date.
                date = date_parser.parse(match.date)
                day   = date.day
                month = date.month
                
                # Account for the time difference, and set the datetime fields.
                TIME_DIFF = match_time.hour - EST_BST_TIME_DIFF
		match_time = match_time.replace(hour=TIME_DIFF, month=month, day=day)
                
                # Find the number of minutes until the match. If this is less than the
		# given 'hours_before' arg, then the match is ready to be posted.
		delta = dateutil.relativedelta.relativedelta(match_time, datetime.now())
		delta_minutes = (delta.hours * 60) + (delta.minutes)
                
                return delta_minutes <= (self.hours_before * 60)


'''   Represents a rugby union match. '''
class Match(object):

        ''' Create a Match object. '''
        def __init__(self, url):

                self.url = url

                # Match data.
		self.competition  = None
		self.venue 	  = None
		self.kickoff_time = None
                self.date         = None
                self.game_time    = None
		self.key_events	  = None
		self.post 	  = None
		
		self.thread    = {}
                self.home_team = {}
                self.away_team = {}

		# Monitors the status of the game.
		self.is_posted = False
		self.is_active = False
                self.is_ft     = False
                self.is_over   = False

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
				self.away_team['name'] + ' [' + self.competition + '] ' +\
				self._format_timezones()

		# Title / Header.
		self.thread['header'] = self._format_header()
		
		# TODO: Post scorers.
		#thread += ', '.join([' '.join(_try) for _try in self.home_team['tries']])
		
		# Lineups: Starters, then Replacements.
		self.thread['lineups'] = "## **Starting Lineups**:\n\n"
		self.thread['lineups'] += "**" + self.home_team['name'] + "**" + \
					  " | **Position** ""| " + \
					  "**" + self.away_team['name'] + "**\n"
		self.thread['lineups'] += ":-|:-|:-\n"
		for h_player, a_player in zip(self.home_team['starters'],
					      self.away_team['starters']):
			self.thread['lineups'] += str(h_player[0]) + '.  ' + \
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
		
		# Post the thread, and update the posted flag.
		self.post = target_sub.submit(
				title=self.thread['title'],
			 	selftext=self.thread['header'] + self.thread['lineups']
		)
		
		self.is_posted = True
		self.is_active = True

	''' Update the Match thread. N.B. -- We only need to update the dynamic
	    values here. '''
	def update_thread(self):

                request = requests.get(self.url)
                tree = html.fromstring(request.content)

		# Get the current score, and the game time.
		self.home_team['score'], self.away_team['score'] = self._get_score(tree)
		self.game_time = self._get_time(tree)
		self.thread['header'] = self._format_header()

		# If the game is over, then we need to set our is_active flag accordingly.
		if self.game_time == 'FT':
                    self.is_ft = True
		
		'''
		# Get the try info (scorers and try time).
                h_tries = tree.xpath('//*[@id="custom-nav"]/div[1]/div/div/'
                                       'div[1]/div')[0]
                a_tries = tree.xpath('//*[@id="custom-nav"]/div[1]/div/div/'
                                       'div[2]/div')[0]

                self.home_team['tries'] = self._get_tries(h_tries)
                self.away_team['tries'] = self._get_tries(a_tries)
		'''

		# Get the current events tree.
		self.events = self._get_events(tree)
		self.thread['events'] = self._format_events()
                
                if self.is_ft and self.is_over:
                    self.is_active = False

                # Perform the update.
		self.post = self.post.edit(
				body=self.thread['header'] + self.thread['lineups'] + \
				     self.thread['events']
		)

	''' Format the kick off times into different timezones. '''
	def _format_timezones(self):

		bst = date_parser.parse(self.kickoff_time)
		nz  = bst.replace(hour=(bst.hour + 11) % 24)
		au  = bst.replace(hour=(bst.hour + 9) % 24)
		sa  = bst.replace(hour=(bst.hour + 1) % 24)
		est = bst.replace(hour=(bst.hour - 5) % 24)
		
		regions = [
				('BST', bst), ('NZ', nz), ('AU', au),
				('SA', sa), ('EST', est)
		]
		
		timezones = []
		for tz in regions:
			hour = str(tz[1].hour)
			minute = str(tz[1].minute)
			
			# Prepend a '0' to any single digit value.
			if tz[1].hour   < 10: hour   = '0' + hour
			if tz[1].minute < 10: minute = '0' + minute

			timezones.append(hour + ':' + minute + ' ' + tz[0])
		
		return ', '.join(timezones)

	''' Format the thread header using Markdown syntax. '''
	def _format_header(self):
		
		# If the game is active then we'll use a different delimiter.
		DELIM = ' - '
		if (self.home_team['score'] == '') and (self.away_team['score'] == ''):
			DELIM = ' vs '
		
		# Format the team names with their respective flairs and scores.
		header = '# ' + self.game_time + ': ' + \
			  self.home_team['name'] + ' ' + self.home_team['flair'] + ' ' + \
			  self.home_team['score'] + DELIM + self.away_team['score'] + ' ' +\
			  self.away_team['flair'] + ' ' + self.away_team['name'] + '\n\n'

		# Format venue and kickoff time.
		header += '### **Venue**: ' + self.venue + '\n\n' + \
			  '### **Kickoff Time**: ' + self.kickoff_time + ' BST' +\
			  '\n\n----\n\n'

		return header

	''' Format the match events using Markdown syntax. '''
	def _format_events(self):

		event_flairs = {
				'red card': '[](#red)',
				'yellow card': '[](#yellow)',
				'substitute': '[](#sub)', 'substituted': '[](#sub)',
				'try': '[](#try)',
				'conversion': '[](#conv)',
				'penalty': '[](#pen)',
				'drop': '[](#drop)'
		}
		
		key_events = ['red card', 'yellow card', 'try', 'conversion', 'penalty']
		events = "## **Match Events**:\n"
		for event in self.events:
                        if event[1].lower().find('end of second half') != -1:
                            self.is_over = True
			
                        # Check for a flair.
			flair = [
					f for f in event_flairs.keys()
					if event[1].lower().find(f) != -1
			]
			
			# Prepend the flair markdown. Bold the event if necessary.
			if flair:
				if flair[0] in key_events:
					event[1] = '**' + event[1] + '**'
				
				event[1] = event_flairs[flair[0]] + ' ' + event[1]
			
                        # Format stoppage time text.
                        '''
                        if event[1][0] == '+' and \
                           event[1].lower().find('end of first half') == -1:
                            prefix = event[1].split(str(self.home_team['score']))[0]
                            event[1] = prefix + ' ' + str(self.home_team['score']) + \
                                       event[1].split(str(self.home_team['score']))[1]
			'''
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

		# Get the game's kickoff time, and date.
                game_time_details = tree.xpath('//div[@class="game-date-time"]')[0]
                game_time_details = game_time_details.text_content().split(',')
                self.kickoff_time = game_time_details[0]
                self.date    	  = game_time_details[1]

		# Get the team names, their flare, and their current score.
                h_team  = tree.xpath('//*[@id="custom-nav"]/header/div[2]'
                                     '/div[1]/div/div[2]/div/div/a/span[2]')[0]
                a_team  = tree.xpath('//*[@id="custom-nav"]/header/div[2]'
                                     '/div[3]/div/div[3]/div/div/a/span[2]')[0]
                
		self.home_team['name']  = h_team.text_content()
                self.away_team['name']  = a_team.text_content()
		
		self.home_team['flair'] = self._get_flair(self.home_team['name'])
		self.away_team['flair'] = self._get_flair(self.away_team['name'])
		
		self.home_team['score'], self.away_team['score'] = self._get_score(tree)

                # Get the current game time.
		self.game_time = self._get_time(tree)
		
		# Get the team lineups (starters & subs).
                h_lineup = tree.xpath('//*[@id="main-container"]/div/div/div[1]/'
                                'article[1]/div/div[1]/div/div/div/table/tbody[1]')[0]
                h_subs   = tree.xpath('//*[@id="main-container"]/div/div/div[1]/'
                                'article[1]/div/div[1]/div/div/div/table/tbody[2]')[0]
		a_lineup = tree.xpath('//*[@id="main-container"]/div/div/div[1]/'
				'article[1]/div/div[2]/div/div/div/table/tbody[1]')[0]
		a_subs	 = tree.xpath('//*[@id="main-container"]/div/div/div[1]/'
				'article[1]/div/div[2]/div/div/div/table/tbody[2]')[0]

                self.home_team['starters'] = self._get_lineup(h_lineup)
                self.home_team['subs'] 	   = self._get_lineup(h_subs)
		self.away_team['starters'] = self._get_lineup(a_lineup)
		self.away_team['subs']	   = self._get_lineup(a_subs)

	''' Returns the flair markdown for the given team.
	    Args:
	    	name: The name of the team.
	'''
	def _get_flair(self, name):
		
		# Team flairs.
		flairs = {
				# Premiership:
 				'wasps': '[](#wasps)',
				'exeter-chiefs': '[](#exeter-chiefs)',
				'saracens': '[](#saracens)', 'bath': '[](#bath)',
 				'leicester': '[](#leicester)',
				'northampton': '[](#northampton)',
 				'harlequins': '[](#harlequins)',
				'newcastle': '[](#newcastle)',
				'gloucester': '[](#gloucester)',
				'sale': '[](#sale)', 'worcester': '[](#worcester)',
 				'bristol': '[](#bristol)',
				
				# PRO 12:
				'leinster': '[](#leinster)', 'ospreys': '[](#ospreys)',
				'munster': '[](#munster)', 'ulster': '[](#ulster)',
				'llanelli-scarlets': '[](#llanelli-scarlets)',
				'glasgow': '[](#glasgow)', 'connacht': '[](#connacht)',
				'cardiff-blues': '[](#cardiff-blues)',
				'edinburgh': '[](#edinburgh)', 'dragons': '[](#newport)',
				'treviso': '[](#treviso)', 'zebre': '[](#zebre)',

				# TOP 14:
				'larochelle': '[](#larochelle)',
				'clermont-auvergne': '[](#clermont-auvergne)',
 				'montpellier': '[](#montpellier)', 'pau': '[](#pau)',
				'castres': '[](#castres)', 'toulon': '[](#toulon)',
 				'racing-metro': '[](#racing-metro)',
				'bordeaux': '[](#bordeaux)', 'brive': '[](#brive)',
 				'toulousain': '[](#toulousain)', 'lyon': '[](#lyon)',
 				'paris': '[](#paris)', 'grenoble': '[](#grenoble)',
 				'bayonne': '[](#bayonne)',

				# Super Rugby:
				'waikato-chiefs': '[](#waikato-chiefs)',
				'jaguares': '[](#jaguares)', 'stormers': '[](#stormers)',
				'brumbies': '[](#brumbies)', 'crusaders': '[](#crusaders)',
				'hurricanes': '[](#hurricanes)', 'lions': '[](#lions)',
				'blues': '[](#blues)', 'sharks': '[](#sharks)',
 				'cheetahs': '[](#cheetahs)', 'reds': '[](#reds)',
				'bulls': '[](#bulls)',
				'western-force': '[](#western-force)',
				'southern-kings': '[](#southern-kings)',
				'highlanders': '[](#highlanders)',
				'waratahs': '[](#waratahs)', 'sunwolves': '[](#sunwolves)',
 				'melbourne-rebels': '[](#melbourne-rebels)'
		}

		# Reformat name.
		name = name.lower()
		if len(name.split(' ')) > 1:
			name = '-'.join(name.split(' '))
		
		# Check for matches.
		if name in flairs:
			return flairs[name]
		else:
			split_name = name.split('-')
			try:
				if (split_name[0] + split_name[1]) in flairs:
					return flairs[split_name[0] + split_name[1]]
			except IndexError: pass
			
			# Get all possible matches. We then return the closest match
			# i.e. the one with the longest key.
			matches = {}
			for _name in split_name:
				results = [f for f in flairs.keys() if f.find(_name) != -1]
				if results: matches[_name] = results
			if matches:
				name = max(matches.keys(), key=len)
				name = matches[name][0]
				return flairs[name]
		
		return ""

	''' Get the current score, and return a tuple like so: (home score, away score)
	    Args:
	    	tree: The HTML document tree.
	'''
	def _get_score(self, tree):
     		
		h_score = tree.xpath('//*[@id="custom-nav"]/header/div[2]'
                                     '/div[1]/div/div[3]/div')[0]
 		a_score = tree.xpath('//*[@id="custom-nav"]/header/div[2]'
                                     '/div[3]/div/div[2]/div')[0]
		
		return (h_score.text_content(), a_score.text_content())

	''' Get the current time in the game.
	    Args:
		tree: The HTML document tree.
	'''
	def _get_time(self, tree):
 
		time = tree.xpath('//*[@id="custom-nav"]/header/div[2]/div[2]/span[3]')[0]
                return time.text_content()

	''' Parses the 'tries' div, and returns a list of tuples where the first
            element is the try scorer's name, and the second is the try time.
            Args:
                e_tries: An HtmlElement containing the match's try data.
        '''
        def _get_tries(self, try_element):

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
        def _get_lineup(self, lineup_element):

                # Go through each row and extract the player data. N.B. -- Sometimes
		# ESPN will screw up the lineup formatting, so we'll need to handle this.
                players = []
                for row in lineup_element.getchildren():
			try:
				number = row.findall('.//span[@class="number"]')\
					 [0].text_content()
				player = row.findall('.//span[@class="name"]')\
					 [0].text_content()
			except IndexError:
				number = row.findall('.//td[@class="number"]')\
					 [0].text_content()
				player = row.findall('.//td[@class="date"]')\
					 [0].text_content()
			
			name = player.split(',')[0]
			pos  = player.split(',')[1].strip()
		
			players.append( (int(number), name, pos) )
		
		# Ensure that players are sorted in ascending order by number.
		players.sort(key=itemgetter(0))
		return players

	''' Get all key events during the match.
	    Args:
		    events_url: The URL to the match's commentary page.
	'''
	def _get_events(self, tree):
		
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

URL	       = 'http://www.espn.co.uk'
SUBREDDIT_NAME = 'rugbyunion'
CACHE_SIZE     = 20
POLL_INTERVAL  = 30
HOURS_BEFORE   = 2

if __name__=='__main__':

        scheduler = Scheduler(url=URL, subreddit_name=SUBREDDIT_NAME,
			      cache_size=CACHE_SIZE, hours_before=HOURS_BEFORE)
	scheduler.run_scheduler(POLL_INTERVAL)

