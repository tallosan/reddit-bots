#
# Bot used to update 
#
# =======================================================================

import os
import git

# Remove the old version, and pull the update. N.B. -- The version on Github
# will NOT have credentials included (for security purposes). Thus, it will be
# necessary to add them in ourselves.
os.remove('rugby_bot.py')
git.cmd.Git('..').pull()

# Get the credentials from our credentials file.
credentials_file = '.credentials'
with open(credentials_file, 'r') as creds:
	CREDENTIALS = creds.read()

# Append the credentials to our bot.
with open('bot.py', 'r+') as rugby_bot:
	content = rugby_bot.read()
	rugby_bot.seek(0, 0)
	rugby_bot.write(CREDENTIALS + '\n' + content)

print 'update completed.'

