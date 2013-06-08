# -*- coding: utf-8 -*-
###
# Copyright (c) 2013, spline
# All rights reserved.
#
#
###
# my libs
import datetime
import os  # fs ops.
try:  # xml handling.
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree
from itertools import groupby, count  # batch.
# extra supybot libs
import supybot.log as log
import supybot.conf as conf
import supybot.schedule as schedule
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
        self.XMLURL = 'http://lines.bookmaker.eu/'
        self.CACHEFILE = conf.supybot.directories.data.dirize("Odds.xml")
        try: # every 3hours make sure the schedule is fresh.
            schedule.addPeriodicEvent(self.cachexml(), 7200, now=True, name='cachexml')
        except AssertionError:
            try:
                schedule.removeEvent('cachexml')
            except KeyError:
                pass
            schedule.addPeriodicEvent(self.cachexml(), 7200, now=True, name='cachexml')

    def die(self):
        try:
            schedule.removeEvent('cachexml')
        except KeyError:
            pass
        self.__parent.die()

    def cachexml(self):
        """Try and update the XMLTV cache."""

        self.log.info("CacheXML: Running...")
        if (not os.path.isfile(self.CACHEFILE) or (os.path.getsize(self.CACHEFILE) < 1)
            or (self._now() - os.stat(self.CACHEFILE).st_mtime > 1200)): # no file, under 1 byte, 20 minutes old.
            self.log.info("CacheXML: File does not exist, is too small or old. Fetching.")
            try:
                response = utils.web.getUrl(self.XMLURL)
                self.log.info("CacheXML: Fetched XMLURL at {0}".format(self.XMLURL))
            except utils.web.Error as e:
                self.log.error("CacheXML: Failed to open: {0} ({1})".format(self.XMLURL, e))
                self.log.error("CacheXML: I cannot update the Cache.")
                return
            # we have response object. test and verify the XML.
            try:  # try to parse for validity.
                ElementTree.fromstring(response)
            except ElementTree.ParseError, e: # if there is an exception, report and return.
                self.log.error("CacheXML: ERROR PARSING received XML: {0}".format(e))
                return
            # we have response object. write to cachefile.
            with open(self.CACHEFILE, 'w') as cache:
                cache.writelines(response)
                self.log.info("CacheXML: Wrote XMLURL to cache.")
        else:  # cachefile is good and intact.
            self.log.info("CacheXML: XML file is good.")

    ######################
    # INTERNAL FUNCTIONS #
    ######################

    def _now(self):
        """Returns the time.time() using only datetime."""

        td = datetime.datetime.utcnow() - datetime.datetime(1970,1,1)
        now = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 1e6
        return now

    def _batch(self, iterable, size):
        """ Batch generator for output."""

        c = count()
        for k, g in groupby(iterable, lambda x:c.next()//size):
            yield g

    def _fml(self, string):
        """Format and color moneyline based on value (-/+)."""

        if string == "":  # empty.
            return "-"
        elif float(str(string).replace('.0','')) > 0:  # positive
            return ircutils.mircColor("+"+(str(string)), 'green')
        elif float(str(string).replace('.0','')) < 0:  # negative
            return ircutils.mircColor((str(string)), 'red')
        else:  # no clue what to do so just bold.
            return ircutils.bold(string)

    def _dectoml(self, decimal):
        """Convert decimal (European) odds to Moneyline (American)."""

        if float(decimal) >= 2.00:
            return "%d" % ((float(decimal)-1)*100)
        else:
            return "%d" % (-100/(float(decimal)-1))

    def _fixtime(self, date):
        """Clean up dt string. Add 3 hours due to PT. If dt > week later, add date."""

        dt = datetime.datetime.strptime(date, '%Y%m%d %H:%M:%S') + datetime.timedelta(hours=3)
        if (dt - datetime.datetime.now()) < datetime.timedelta(hours=160):
            return dt.strftime('%a %H:%M')  # earlier than a week so just d/t.
        else:  # later than a week from now. ad month/day@HH:MM
            return dt.strftime('%m/%d@%H:%M')

    ######################################
    # ODDS PROCESSING INTERNAL FUNCTIONS #
    ######################################

    def _processgame(self, game):
        """Process a single XML line for a game/event."""

        tmp = {}  # dict container.
        tmp['sport'] = game.get('idspt')
        tmp['gametype'] = game.get('idgmtyp')  # gametype. used to detect props.
        tmp['date'] = game.get('gmdt')  # game date.
        tmp['time'] = game.get('gmtm')  # game time.
        tmp['vpt'] = game.get('vpt')  # visiting pitcher.
        tmp['hpt'] = game.get('hpt')  # home pitcher.
        tmp['newdt'] = self._fixtime("{0} {1}".format(tmp['date'], tmp['time']))  # fixed date.
        tmp['away'] = game.get('vtm').encode('utf-8')  # visiting/away team.
        tmp['home'] = game.get('htm').encode('utf-8')  # home team.
        tmp['haschild'] = game.find('line').get('haschild')  # odd XML var. checks for games.
        # handle odds. we check for one field then another.
        tmp['awayodds'] = game.find('line').get('voddst')  # find visitor odds.
        if tmp['awayodds'] == '':  # empty/blank or not there.
            tmp['awayodds'] = game.find('line').get('vsprdoddst')  # alt. visitor odds.
        tmp['homeodds'] = game.find('line').get('hoddst')  # home odds.
        if tmp['homeodds'] == '':  # empty/blank or not there.
            tmp['homeodds'] = game.find('line').get('hsprdoddst')  # alternate home odds.
        # get the over/under total here.
        if game.find('line').attrib['ovt']:  # abs/fix so its ###.#
            tmp['over'] = "%.12g" % abs(float(game.find('line').get('ovt')))
        else:  # sometimes no o/u.
            tmp['over'] = None
        # find the spread and fix it if we have it.
        tmp['spread'] = game.find('line').get('hsprdt')  # find the spread and fix.
        if tmp['spread'] != '0' and not tmp['spread'].startswith('-') and tmp['spread'] != '':
            tmp['spread'] = "+{0}".format(tmp['spread'])  # hackey to get + infront of non - spread.
        # some matches like soccer have a draw line.
        tmp['vspoddst'] = game.find('line').get('vspoddst')
        # do something here to bold the favorite. this is tricky since odds can be in different fields.
        if tmp['spread'] and tmp['spread'] != '' and tmp['spread'] != "0":  # first try to use the spread if it's there. then turn to odds.
            if tmp['spread'].startswith('-'):  # if the spread is -, the hometeam is favored.
                tmp['home'] = ircutils.bold(tmp['home'])
            else:  # we bold
                tmp['away'] = ircutils.bold(tmp['away'])
        elif tmp['awayodds'] != "-" and tmp['homeodds'] != "-" and tmp['awayodds'] != '' and tmp['homeodds'] != '':
            if tmp['awayodds'] < tmp['homeodds']:
                tmp['away'] = ircutils.bold(tmp['away'])
            elif tmp['homeodds'] < tmp['awayodds']:
                tmp['home'] = ircutils.bold(tmp['home'])
        # now that we're done, return.
        return tmp

    def _processprop(self, prop):
        """Process prop lines where it's a team/name and line. Returns a dict for sorting."""

        tmp = {}
        tmp['tmname'] = prop.get('tmname').encode('utf-8')
        tmp['line'] = int(prop.get('odds'))
        return tmp

    #########
    # NOTES #
    #########

    # <league IdLeague="12003" IdSport="TNT" Description="GOLF PICK WINNER">
    # <game idgm="1582092" idgmtyp="3" gmdt="20130613" idlg="0" gmtm="06:00:00" idspt="TNT" vpt="" hpt="" vnum="0" hnum="0" evtyp="" idgp="0" gpd="" vtm="" htm="WIN US OPEN- (JUNE 13-16) ALL IN" stats="false">
    # and it's a prop. does IdLeague change?

    ####################
    # PUBLIC FUNCTIONS #
    ####################

    def odds(self, irc, msg, args, optsport, optinput):
        """<sport> [team]
        Display various odds/lines for sporting events.
        Issue odds sports to see a complete list of valid sports.
        Optional: add in string/team to search for. Ex: Odds EPL Manch or Odds NBA LA
        """

        # validate input/sports.
        optsport, optprop = optsport.upper(), False  # upper to match. False on the prop.
        validsports = {'NFL':'1', 'NBA':'3', 'NCB':'4','NHL':'7', 'MLB':'5',
                       'EPL':'10003', 'LALIGA':'12159', 'UFC-MMA':'206', 'UFC-BELLATOR':'12636',
                       'MLS':'10007', 'UEFA-CL':'10016', 'LIGUE1':'10005','BUNDESLIGA':'10004',
                       'SERIEA':'10002', 'UEFA-EUROPA':'12613', 'BOXING':'12064',
                       'TENNIS-M':'12331', 'TENNIS-W':'12332' }
        if not optsport in validsports:  # error if not in above.
            validprops = { 'NFL-SUPERBOWL':'1561335', 'NFL-MVP':'1583283'}
            if optsport in validprops:
                optprop = optsport
                optsport = "PROP"
            else:  # prop not found. so we display only the sports.
                irc.reply("ERROR: '{0}' is invalid. Valid sports: {1}".format(optsport, " | ".join(sorted(validsports.keys()))))
                return

        # now try and parse/open XML.
        # we then have to process games and lines differently.
        try:
            tree = ElementTree.parse(self.CACHEFILE)
        except ElementTree.ParseError, e:
            self.log.error("ERROR: parsing cached XML :: {0}".format(e))
            irc.reply("ERROR: Something broke trying to parse the XML. Check logs.")
            return
        # now that we have XML, it must be processed differently depending on props/games.
        if optsport == "PROP":  # processing PROPS here.
            lines = tree.findall(".//game[@idgm='%s']/line" % validprops[optprop])
            if len(lines) == 0:  # prop or no items found inside the prop.
                irc.reply("ERROR: I did not find {0} line or any odds in it.".format(optprop))
                return
            # we did find prop+lines, so process each one.
            props = {}  # everything goes into props dict so we can sort.
            for i, line in enumerate(lines):  # must add with unique key since some odds are same.
                tmp = self._processprop(line)  # send to prop handler.
                props[i] = tmp
            props = sorted(props.items(), key=lambda x: x[1])  # sort. lowest odds first.
        else:  # processing GAMES here not props.
            leagues = tree.findall('./Leagues/league[@IdLeague="%s"]/game' % (validsports[optsport]))
            if len(leagues) == 0:  # check if empty (no games) or nothing found (wrong time of the year).
                irc.reply("ERROR: I did not find any events in the {0} category.".format(optsport))
                return
            # we must process each "game" or match.
            games = {}  # k will be an int++ and value = game string.
            for i, game in enumerate(leagues):
                tmp = self._processgame(game)  # send to game .handler.
                games[i] = tmp  # now add our game into the dict.

        # now, we must preprocess the output in the dicts.
        # each sport is different and we append into a list for output.
        output = []
        # first, handle props and props only.
        if optsport == "PROP":  # we join all of the props/lines into one entry.
            proplist = " | ".join([q['tmname'].title() + " (" + self._fml(str(q['line'])) + ")" for (v, q) in props])
            output.append("{0} :: {1}".format(ircutils.mircColor(optprop, 'red'), proplist))
        # REST ARE NON-PROP. EACH HANDLES A SPORT DIFFERENTLY.
        # handle NFL football.
        elif optsport == "NFL":
            for (v) in games.values():
                if v['haschild'] == "True":
                    output.append("{0}@{1}[{2}]  o/u: {3}  {4}/{5}  {6}".format(v['away'],v['home'],\
                        v['spread'],v['over'],self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        # handle tennis:
        elif optsport in ('TENNIS-M', 'TENNIS-W'):
            for (v) in games.values():
                #if v['haschild'] == "True":
                output.append("{0}@{1}  {2}/{3}  {4}".format(v['away'],v['home'],\
                    self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        # handle baseball.
        elif optsport == "MLB":
            for (v) in games.values():
                if v['haschild'] == "True":
                    output.append("{0}@{1}  {2}/{3}  {4}".format(v['away'],v['home'],\
                        self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        # handle hockey.
        elif optsport == "NHL":
            for (v) in games.values():
                if v['haschild'] == "True":
                    output.append("{0}@{1}  o/u: {2}  {3}/{4}  {5}".format(v['away'],v['home'],\
                        v['over'],self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        # handle college basketball output.
        elif optsport == "NCB":
            for (v) in games.values():
                #if v['spread'] != "" and (v['gametype'] == "1" or v['gametype'] == "3" or v['gametype'] == "9"):
                if v['haschild'] == "True":
                    output.append("{0}@{1}[{2}]  o/u: {3}  {4}/{5}  {6}".format(v['away'],v['home'],\
                        v['spread'],v['over'],self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        # handle NBA output.
        elif optsport == "NBA":
            for (v) in games.values():
                #if v['over'] is not None and (v['gametype'] == "1" or v['gametype'] == "3" or v['gametype'] == "9"):
                if v['haschild'] == "True":
                    output.append("{0}@{1}[{2}]  o/u: {3}  {4}/{5}  {6}".format(v['away'],v['home'],\
                        v['spread'],v['over'],self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        # handle soccer output.
        elif optsport in ('EPL', 'LALIGA', 'BUNDESLIGA', 'SERIEA', 'LIGUE1', 'MLS', 'UEFA-EUROPA', 'UEFA-CL'):
            for (v) in games.values():
                if v['haschild'] == "True": # make sure they're games.
                     output.append("{0}@{1}  o/u: {2}  {3}/{4} (Draw: {5})  {6}".format(v['away'],v['home'],\
                        v['over'],self._fml(v['awayodds']),self._fml(v['homeodds']),self._fml(v['vspoddst']),v['newdt']))
        # handle UFC output.
        elif optsport in ('UFC-MMA', 'UFC-BELLATOR'):
            for (v) in games.values():
                #if v['gametype'] in ("29", "2"): # or v['gametype'] == "2": # make sure it is a match
                if v['homeodds'] != '' and v['awayodds'] != '':
                    output.append("{0} vs. {1}  {2}/{3}  {4}".format(v['away'],v['home'],\
                        self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))
        # handle boxing output.
        elif optsport == "BOXING":
            for (v) in games.values():
                # if v['gametype'] in ["2", "3"] or v['haschild'] == "True": # not sure if this will work or not.
                if v['homeodds'] != '' and v['awayodds'] != '':
                    output.append("{0} vs. {1}  {2}/{3}  {4}".format(v['away'],v['home'],\
                        self._fml(v['awayodds']),self._fml(v['homeodds']),v['newdt']))

        # output time.
        # checks if optinput (looking for something)
        if not optinput or optsport == "PROP":  # just display the games.
            if len(output) <= 9:  # 9 or under, one per line.
                for each in output: irc.reply(each)
            elif len(output) > 9:  # more than 9, we batch 4 per line.
                for N in self._batch(output, 4):
                    irc.reply(" | ".join([item for item in N]))
        else:  # we do want to limit output to only matching items.
            count = 0  # to handle a max # of 5.
            for each in output:  # iterate through output list.
                if optinput.lower() in each.lower():  # match.
                    if count < 5:  # output matching items.
                        irc.reply(each)
                        count += 1 # ++
                    else:  # too many.
                        irc.reply("I found too many results for '{0}'. Please specify something more specific".format(optinput))
                        break

    odds = wrap(odds, [('somethingWithoutSpaces'), optional('text')])

Class = Odds


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
