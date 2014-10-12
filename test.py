###
# Copyright (c) 2013-2014, spline
# All rights reserved.
#
#
###

from supybot.test import *

class OddsTestCase(PluginTestCase):
    plugins = ('Odds',)
    
    def testOdds(self):
        self.assertNotError('odds nhl')
        self.assertNotError('odds nfl')
        self.assertNotError('odds mlb')
    


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
