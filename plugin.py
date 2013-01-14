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

    def _fml(self, string):
        """For moneyline: string format a negative with red, positive with green."""
        try:
            if float(str(string).replace('.0','')) > 0:
                string = ircutils.mircColor((str(string)), 'green')
            else:
                string = ircutils.mircColor((str(string)), 'red')
            return string
        except:
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
            return dt.strftime('%Y%m%d %H:%M')

    def odds(self, irc, msg, args, optsport, optinput):
        """
        odds.
        """
        
        optsport = optsport.upper()
        validsports = {'NFL':'1', 'NBA':'3', 'NCB':'4', 'EPL':'10003', 'LALIGA':'12159', 'MMA':'206'}
        
        if not optsport in validsports:
            irc.reply("ERROR: sportname must be one of: {0}".format(validsports.keys()))
            return
        
        url = 'http://lines.bookmaker.eu/'
        
        # cache: if the cache time is >6hrs or no file, regrab via HTTP.
        # otherwise, grab via http and write + update the cachetime.
        # this is done because the host can sometimes be down and its good to have previous entries
        # when the game beguns.
        if (time.time() - self.cachetime) > 21600 or os.path.getsize(self.cachefile) < 1:
            try:
                request = urllib2.Request(url, headers={"Accept" : "application/xml"})
                u = urllib2.urlopen(request)
            except Exception,e:
                self.log.error("Failed to open: %s (%s)" % (url,e))
                return

            cache = open(self.cachefile, "w")
            cache.writelines(u)
            cache.close()
            self.cachetime = time.time()

        # with open('podcasts.opml', 'rt') as f:
        # tree = ElementTree.parse(f)
        try:
            tree = ElementTree.parse(self.cachefile)
        except ElementTree.ParseError, v:
            irc.reply("Something broke trying to parse the XML. Check logs.")
            return
        
        # now do some xml parsing via XPath.
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
            tmp['sport'] = game.attrib['idspt']
            tmp['gametype'] = game.attrib['idgmtyp']
            tmp['date'] = game.attrib['gmdt']
            tmp['time'] = game.attrib['gmtm']
            tmp['newdt'] = self._fixTime("{0} {1}".format(tmp['date'],tmp['time'])) # fixed date.
            tmp['away'] = game.attrib['vtm']
            tmp['home'] = game.attrib['htm'] 
            tmp['vsprdoddst'] = game.find('line').attrib['vsprdoddst'] 
            tmp['hsprdoddst'] = game.find('line').attrib['hsprdoddst']
            tmp['awayodds'] = game.find('line').attrib['voddst'] 
            tmp['homeodds'] = game.find('line').attrib['hoddst']
            if tmp['awayodds'] == "": # if odds (ml) is blank, go -
                tmp['awayodds'] = '-'
            if tmp['homeodds'] == "":
                tmp['homeodds'] = '-'
            if game.find('line').attrib['ovt']: # o/u total. abs/fix so its ###.#
                tmp['over'] = "%.12g" % abs(float(game.find('line').attrib['ovt']))
            else:
                tmp['over'] = None
            tmp['spread'] = game.find('line').attrib['hsprdt'] # find the spread and fix.
            if tmp['spread'] != "0" and not tmp['spread'].startswith('-') and tmp['spread'] != "": 
                tmp['spread'] = "+{0}".format(tmp['spread']) #+ infront of non - spread
            tmp['vspoddst'] = game.find('line').attrib['vspoddst'] # draw odds
            # do something here to bold the favorite.
            if tmp['spread'] and tmp['spread'] != "0":
                self.log.info("MMA SPREAD")
                if tmp['spread'].startswith('-'):
                    tmp['home'] = ircutils.bold(tmp['home'])
                else:
                    tmp['away'] = ircutils.bold(tmp['away'])
            elif tmp['awayodds'] != "-" and tmp['homeodds'] != "-":
                self.log.info("MMA ODDS")
                if tmp['awayodds'] < tmp['homeodds']:
                    tmp['away'] = ircutils.bold(tmp['away'])
                elif tmp['homeodds'] < tmp['awayodds']:
                    tmp['home'] = ircutils.bold(tmp['home'])
            elif tmp['vsprdoddst'] and tmp['hsprdoddst']:
                self.log.info("MMA VSPRD")
                if tmp['vsprdoddst'] < tmp['hsprdoddst']:
                    tmp['away'] = ircutils.bold(tmp['away'])
                elif tmp['hsprdoddst'] < tmp['vsprdoddst']:
                    tmp['home'] = ircutils.bold(tmp['home'])
            games[int(i)] = tmp # now add
        
        # output time. each sport is different so work with it.
        if optsport == "NFL":
            for (v) in games.values():
                irc.reply("{0}@{1}[{2}]  o/u: {3}  {4}/{5}  {6}".format(v['away'],v['home'],\
                    v['spread'],v['over'],self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        elif optsport == "NCB":
            for (v) in games.values():
                if v['spread'] != "":
                    irc.reply("{0}@{1}[{2}]  o/u: {3}  {4}/{5}  {6}".format(v['away'],v['home'],\
                        v['spread'],v['over'],self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        elif optsport == "NBA": 
            for (v) in games.values():
                if v['over'] is not None:
                    irc.reply("{0}@{1}[{2}]  o/u: {3}  {4}/{5}  {6}".format(v['away'],v['home'],\
                        v['spread'],v['over'],self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        elif optsport == "EPL" or optsport == "LALIGA":
            for (v) in games.values():
                if v['gametype'] == "3": # make sure they're games.
                     irc.reply("{0}@{1}  o/u: {2}  {3}/{4} (Draw: {5})  {6}".format(v['away'],v['home'],\
                        v['over'],self._fml(v['awayodds']),self._fml(v['homeodds']),self._fml(v['vspoddst']),v['newdt']))
        elif optsport == "MMA":
            for (v) in games.values():
                if v['gametype'] == "29": # make sure it is a match
                    self.log.info(str(v))
                    irc.reply("{0} vs. {1}  {2}/{3}  {4}".format(v['away'],v['home'],v['vsprdoddst'],v['hsprdoddst'],v['newdt']))


    odds = wrap(odds, [('somethingWithoutSpaces'), optional('somethingWithoutSpaces')])

Class = Odds


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
