# -*- coding: utf-8 -*-
###
# Copyright (c) 2013, spline
# All rights reserved.
#
#
###

# my libs
import urllib2
import datetime
import time
import os
try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree
from itertools import groupby, izip, count

# supybot libs
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Odds')

@internationalizeDocstring
class Odds(callbacks.Plugin):
    """Add the help for "@plugin help Odds" here
    This should describe *how* to use this plugin."""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(Odds, self)
        self.__parent.__init__(irc)
        self.cachefile = conf.supybot.directories.data.dirize("Odds.xml")
        self.cachetime = time.time()
        if not os.path.isfile(self.cachefile):
            open(self.cachefile, 'w').close()

    def die(self):
        os.remove(self.cachefile)
        self.__parent.die()

    def _batch(self, iterable, size):
        """ Batch generator for output. """
        c = count()
        for k, g in groupby(iterable, lambda x:c.next()//size):
            yield g

    def _fml(self, string):
        """For moneyline: string format a negative with red, positive with green."""
        if string == "":
            return "-"
        elif float(str(string).replace('.0','')) > 0:
            return ircutils.mircColor("+"+(str(string)), 'green')
        elif float(str(string).replace('.0','')) < 0:
            return ircutils.mircColor((str(string)), 'red')
        else:
            return ircutils.bold(string)

    def _dectoml(self, decimal):
        """Convert decimal (European) odds to Moneyline (American)."""
        if float(decimal) >= 2.00:
            return "%d" % ((float(decimal)-1)*100)
        else:
            return "%d" % (-100/(float(decimal)-1))

    def _fixTime(self, date):
        """Add three hours since dates are in PT."""
        dt = datetime.datetime.strptime(date, '%Y%m%d %H:%M:%S') + datetime.timedelta(hours=3)
        if (dt - datetime.datetime.now()) < datetime.timedelta(hours=160): # if within a week, show weekday name.
            return dt.strftime('%a %H:%M')
        else:
            return dt.strftime('%m/%d@%H:%M')

    def odds(self, irc, msg, args, optsport, optinput):
        """<sport> [team]
        Display various odds/lines for sporting events.
        Sport must be one of: NFL, NBA, NCB, EPL, LALIGA, MMA, MLB, NHL.
        Optional: add in string/team to search for. Ex: Odds EPL Manch or Odds NBA LA
        """

        optsport = optsport.upper()
        validsports = { 'NFL':'1', 'NBA':'3', 'NCB':'4','NHL':'7', 'MLB':'5',
                        'EPL':'10003', 'LALIGA':'12159', 'UFC-MMA':'206', 'MMA-BELLATOR':'12636', 
			'MLS':'10007',
                        'LIGUE1':'10005','BUNDESLIGA':'10004','SERIEA':'10002', 'EUROPA':'12613'
                        }


        if not optsport in validsports:
            irc.reply("ERROR: sportname must be one of: {0}".format(validsports.keys()))
            return

        url = 'http://lines.bookmaker.eu/'

        # cache: if the cache time is >6hrs or no file, or file older than 6 hours, regrab via HTTP.
        # otherwise, grab via http and write + update the cachetime.
        # this is done because the host can sometimes be down and its good to have previous entries
        # when the game beguns.
        if ((time.time() - self.cachetime) > 21600) or (os.path.getsize(self.cachefile) < 1) or ((time.time() - os.stat(self.cachefile).st_mtime) > 21600):
            self.log.info("Trying to refresh XML odds file cache...")
            try:
                request = urllib2.Request(url, headers={"Accept" : "application/xml"})
                u = urllib2.urlopen(request)
                with open(self.cachefile, 'w') as cache:
                    cache.writelines(u)
                self.log.info("Writing XML odds to cache.")
                self.cachetime = time.time()
            except Exception,e:
                self.log.error("Failed to open: %s (%s)" % (url,e))
                return
        # now try and parse/open XML. XPath to parse.
        try:
            tree = ElementTree.parse(self.cachefile)
        except ElementTree.ParseError, v:
            irc.reply("Something broke trying to parse the XML. Check logs.")
            return
        root = tree.getroot()
        leagues = tree.findall('./Leagues/league[@IdLeague="%s"]/game' % (validsports[optsport]))
        if len(leagues) < 1:
            irc.reply("ERROR: No events have been found in the {0} category".format(optsport))
            return

        # process each entry and throw into games dict for output later.
        # we do a bit of formatting/logic here to help output processing.
        games = {}
        for i,game in enumerate(leagues):
            tmp = {}
            tmp['sport'] = game.get('idspt')
            tmp['gametype'] = game.get('idgmtyp')
            tmp['date'] = game.get('gmdt')
            tmp['time'] = game.get('gmtm')
            tmp['newdt'] = self._fixTime("{0} {1}".format(tmp['date'],tmp['time'])) # fixed date.
            tmp['away'] = game.get('vtm')
            tmp['home'] = game.get('htm')
            tmp['vsprdoddst'] = game.find('line').get('vsprdoddst')
            tmp['hsprdoddst'] = game.find('line').get('hsprdoddst')
            tmp['awayodds'] = game.find('line').get('voddst')
            tmp['homeodds'] = game.find('line').get('hoddst')
            if game.find('line').attrib['ovt']: # o/u total. abs/fix so its ###.#
                tmp['over'] = "%.12g" % abs(float(game.find('line').get('ovt')))
            else:
                tmp['over'] = None
            tmp['spread'] = game.find('line').get('hsprdt') # find the spread and fix.
            if tmp['spread'] != "0" and not tmp['spread'].startswith('-') and tmp['spread'] != "":
                tmp['spread'] = "+{0}".format(tmp['spread']) #hackey to get + infront of non - spread
            tmp['vspoddst'] = game.find('line').get('vspoddst') # draw odds
            # do something here to bold the favorite.
            if tmp['spread'] and tmp['spread'] != "0":
                if tmp['spread'].startswith('-'):
                    tmp['home'] = ircutils.bold(tmp['home'])
                else:
                    tmp['away'] = ircutils.bold(tmp['away'])
            elif tmp['awayodds'] != "-" and tmp['homeodds'] != "-":
                if tmp['awayodds'] < tmp['homeodds']:
                    tmp['away'] = ircutils.bold(tmp['away'])
                elif tmp['homeodds'] < tmp['awayodds']:
                    tmp['home'] = ircutils.bold(tmp['home'])
            elif tmp['vsprdoddst'] and tmp['hsprdoddst']:
                if tmp['vsprdoddst'] < tmp['hsprdoddst']:
                    tmp['away'] = ircutils.bold(tmp['away'])
                elif tmp['hsprdoddst'] < tmp['vsprdoddst']:
                    tmp['home'] = ircutils.bold(tmp['home'])
            games[int(i)] = tmp # now add

        # preprocess output. each sport is different so work with it.
        output = []
        if optsport in "NFL":
            for (v) in games.values():
                output.append("{0}@{1}[{2}]  o/u: {3}  {4}/{5}  {6}".format(v['away'],v['home'],\
                    v['spread'],v['over'],self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        elif optsport == "MLB":
            for (v) in games.values():
                if v['gametype'] == "9" or v['gametype'] == "1": # make sure they're games.
                    output.append("{0}@{1}  {2}/{3}  {4}".format(v['away'],v['home'],\
                        self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        elif optsport == "NHL":
            for (v) in games.values():
                if v['gametype'] == "1" or v['gametype'] == "9": # make sure they're games.
                    output.append("{0}@{1}  o/u: {2}  {3}/{4}  {5}".format(v['away'],v['home'],\
                        v['over'],self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        elif optsport == "NCB":
            for (v) in games.values():
                if v['spread'] != "" and (v['gametype'] == "1" or v['gametype'] == "3" or v['gametype'] == "9"):
                    output.append("{0}@{1}[{2}]  o/u: {3}  {4}/{5}  {6}".format(v['away'],v['home'],\
                        v['spread'],v['over'],self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        elif optsport == "NBA":
            for (v) in games.values():
                if v['over'] is not None and (v['gametype'] == "1" or v['gametype'] == "3" or v['gametype'] == "9"):
                    output.append("{0}@{1}[{2}]  o/u: {3}  {4}/{5}  {6}".format(v['away'],v['home'],\
                        v['spread'],v['over'],self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        elif optsport in ('EPL', 'LALIGA', 'BUNDESLIGA', 'SERIEA', 'LIGUE1', 'MLS', 'EUROPA'):
            for (v) in games.values():
                if v['gametype'] == "3" or v['gametype'] == "9": # make sure they're games.
                     output.append("{0}@{1}  o/u: {2}  {3}/{4} (Draw: {5})  {6}".format(v['away'],v['home'],\
                        v['over'],self._fml(v['awayodds']),self._fml(v['homeodds']),self._fml(v['vspoddst']),v['newdt']))
        elif optsport in ('UFC-MMA', 'UFC-BELLATOR'):
            for (v) in games.values():
                if v['gametype'] == "29" or v['gametype'] == "2": # make sure it is a match
                    output.append("{0} vs. {1}  {2}/{3}  {4}".format(v['away'],v['home'],\
                        self._fml(v['vsprdoddst']),self._fml(v['hsprdoddst']),v['newdt']))

        # all output are in a list. first, check if we're not looking for optinput.
        # otherwise, if more than 9, we group together. otherwise, one per line.
        if not optinput:
            if len(output) <= 9:
                for each in output: irc.reply(each)
            elif len(output) > 9:
                #self.log.info(str(sum(len(s) for s in output)))
                for N in self._batch(output, 4):
                    irc.reply(" | ".join([item for item in N]))
        else: # handle optinput
            count = 0
            for each in output:
                if optinput.lower() in each.lower() or optinput.lower() in each.lower():
                    if count < 5:
                        irc.reply(each)
                        count += 1
                    else:
                        irc.reply("I found too many results for '{0}' in {1}. Please specify something more specific".format(optinput,optsport))
                        break

    odds = wrap(odds, [('somethingWithoutSpaces'), optional('somethingWithoutSpaces')])

Class = Odds


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
