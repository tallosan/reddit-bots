#
# Rugby Bot: Creates a match thread for each Rugby Union fixture.
#
# ========================================================================


import praw
import requests
from lxml import html


'''   Responsible for getting any rugby matches scheduled, and creating threads
      when necessary. '''
class Scheduler(object):

	''' Create a scheduler.
	    Args:
	    	poll_interval: The interval between polls.
		*url: The URL to get the match data from.
	'''
	def __init__(self, url='http://www.espn.co.uk'):
		
		self.base_url 	   = url
		self.url 	   = self.base_url + '/rugby/scoreboard'
		self.matches	   = []
	
	''' Run the scheduler to determine which match threads need to be created.
	    Args:
		poll_interval: The interval between polls.
	'''
	def run_scheduler(self, poll_interval):
		
		matches = self.get_matches(self.url)
		for match in matches:
			if match.is_posted:
				match.update_thread()
			else:
				match.post_thread()
			laksjd;

	''' Returns a list of Match objects that are not currently in the
	    scheduler's cache.
	'''
	def get_matches(self, url):

		request = requests.get(url)
		tree = html.fromstring(request.content)

		# Get the relative match URLs, and create full URLs.
		schedule = tree.xpath('//a[@class="competitors"]')
		matches  = []
		for match in schedule:
			matches.append(
					Match(self.base_url + match.get('href'))
			)
		
		return matches


'''   Represents a rugby union match. '''
class Match(object):

        ''' Create a Match object. '''
        def __init__(self, url):

                self.url = url

                # Match data.
		self.competition = None
                self.game_time   = None
		self.key_events	 = None
		self.thread 	 = ""

                self.home_team   = {}
                self.away_team   = {}

		# Monitors the status of the game.
		self.is_posted	 = False
		self.is_active	 = False

		# Populate fields.
                self.parse_gamethread(self.url)
 
 	''' Create a thread for this Match. '''
	def post_thread(self):
                
		# Score
		# Try scorers
		# Thread title.
		title = "# Match Thread: " + \
			self.home_team['name'] + ' ' + self.game_time + \
			self.away_team['name'] + '[' + self.competition + ']'
		
		# Title / Header.
		thread = ""
		thread += '# ' + self.home_team['name'] + ' vs ' + self.away_team['name']
		thread += '\n\n----\n\n'
		
		# Lineups: Starters, then Replacements.
		thread += "## Lineups:\n\n"
		thread += "|:--:|\n"
		thread += "**" + self.home_team['name'] + "** | **" + \
				 self.away_team['name'] + "**\n"
		
		thread += "**Player** | **Position** | **Player** | **Position**\n\n"
		for h_player, a_player in zip(self.home_team['starters'],
					      self.away_team['starters']):
			thread += h_player[0] + '  ' + h_player[1] + ' | ' + h_player[2]
			thread += ' | '
			thread += a_player[0] + '  ' + a_player[1] + ' | ' + a_player[2]
			thread += '\n'
		thread += "|:--:|\n"
		thread += "| **Replacements** |\n"
		thread += "**Player** | **Position** | **Player** | **Position**\n\n"
		for h_sub, a_sub in zip(self.home_team['subs'], self.away_team['subs']):
			thread += h_sub[0] + '  ' + h_sub[1] + ' | ' + h_sub[2]
			thread += ' | '
			thread += a_sub[0] + '  ' + a_sub[1] + ' | ' + a_sub[2]
			thread += '\n'
		
		thread += "----"
		self.thread = thread
		
		# Set posted flag.
		self.is_posted = True
	
	def update_thread(self):
		pass

        ''' Parse the website linked via the 'url' parameter, and return all
            relevant match info (e.g. score, current time in game, etc).
            Args:
                url: The URL of the site to parse.
        '''
        def parse_gamethread(self, url):

                request = requests.get(url)
                tree = html.fromstring(request.content)

                # Get the competition name.
                competition = tree.xpath('//*[@id="custom-nav"]/header/div[1]')[0]
                self.competition = competition.text_content()

                # Get the team names, and their current score.
                h_team  = tree.xpath('//*[@id="custom-nav"]/header/div[2]'
                                     '/div[1]/div/div[2]/div/div/a/span[2]')[0]
                h_score = tree.xpath('//*[@id="custom-nav"]/header/div[2]'
                                     '/div[1]/div/div[3]/div')[0]
                a_team  = tree.xpath('//*[@id="custom-nav"]/header/div[2]'
                                     '/div[3]/div/div[3]/div/div/a/span[2]')[0]
                a_score = tree.xpath('//*[@id="custom-nav"]/header/div[2]'
                                     '/div[3]/div/div[2]/div')[0]

                self.home_team['name']  = h_team.text_content()
                self.home_team['score'] = h_score.text_content()

                self.away_team['name']  = a_team.text_content()
                self.away_team['score'] = a_score.text_content()

                # Get the current game time.
                time = tree.xpath('//*[@id="custom-nav"]/header/div[2]/div[2]/span[3]')
                self.game_time = time[0].text_content()

                # Get the try info (scorers and try time).
                h_tries = tree.xpath('//*[@id="custom-nav"]/div[1]/div/div/'
                                       'div[1]/div')[0]
                a_tries = tree.xpath('//*[@id="custom-nav"]/div[1]/div/div/'
                                       'div[2]/div')[0]

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

		# TODO: Get KeyEvents.
		events = tree.xpath('//*[@id="tab1"]/table/tbody')[0]
		self.key_events = self.get_key_events(events)

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

	def get_key_events(self, event_element):
		pass


URL = 'http://www.espn.co.uk/rugby/match?gameId=290096&league=267979'

scheduler = Scheduler()
scheduler.run_scheduler(poll_interval=30)

laskdj;
# ========================================================================

USER_AGENT = 'RugbyUnionBot'
USERNAME   = 'RugbyUnionBot'
PASSWORD   = 'rugbyunionbot1234'

POLL_INTERVAL = 30

r = praw.Reddit(user_agent=USER_AGENT)
r.login(username=USERNAME, password=PASSWORD, disable_warning=True)


if __name__=='__main__':
        
	scheduler = Scheduler()
	scheduler.run_scheduler(poll_interval=POLL_INTERVAL)

