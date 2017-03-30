#
# Rugby Bot: Creates a match thread for each Rugby Union fixture.
#
# ========================================================================


import praw
import requests
from lxml import html


'''   Represents a rugby union match. '''
class Match(object):

        ''' Create a Match object. '''
        def __init__(self, url):

                self.url = url

                self.competition = None

                self.home_team   = {}
                self.away_team   = {}

                self.game_time   = None

                self.parse_gamethread(self.url)

        ''' Parse the website linked via the 'url' parameter, and return all
            relevant match info (e.g. score, current time in game, etc).
            Args:
                url: The URL of the site to parse.
        '''
        def parse_gamethread(self, url):

                request = requests.get(url)
                tree = html.fromstring(request.content)

                #TODO: Don't forget to use this!
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

                #TODO: Don't forget to use this!
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
                                      'article[1]/div/div[2]/div')[0]

                self.home_team['starters'] = self.get_lineup(h_lineup)

                print self.home_team
  		print self.away_team
                print

        def create_thread(self):
                pass


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

                # N.B -- We need to traverse the tree to get each row.
                players = []
                for e in lineup_element.getchildren():
                        row     = e.getchildren()[0].getchildren()[0].getchildren()[0]

                        # Parse the player's number, then their name and position.
                        number  = row.getchildren()[1].text_content()

                        player  = row.getchildren()[2].text_content().split(',')
                        name    = player[0]
                        pos     = player[1][1:].split(' ')[0]

                        players.append( (number, name, pos) )

                return players


def run_scheduler():
        pass


URL = 'http://www.espn.co.uk/rugby/match?gameId=290096&league=267979'
URL = 'http://www.espn.co.uk/rugby/match?gameId=290097&league=267979'
m = Match(URL)

laskdj;


# ========================================================================

USER_AGENT = 'RugbyUBot'
USERNAME   = 'RugbyUBot'
PASSWORD   = None

r = praw.Reddit(user_agent=USER_AGENT)
r.login(username=USERNAME, password=PASSWORD, disable_warning=True)


if __name__=='__main__':
        run_scheduler()

