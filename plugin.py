# -*- coding: utf-8 -*-
###
# Copyright (c) 2013, spline
# All rights reserved.
#
#
###
# my libs
import datetime  # timeops/datefix.
import pytz  # timeops/datefix.
import os  # fs ops.
try:  # xml handling.
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree
from itertools import groupby, count  # batch.
from operator import itemgetter  # sorting.
# extra supybot libs
import supybot.conf as conf
import supybot.schedule as schedule
# supybot libs
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
        self.displaytz = self.registryValue('displayTZ')
        self.XMLURL = 'http://lines.bookmaker.eu/'
        self.CACHEFILE = conf.supybot.directories.data.dirize("Odds.xml")
        def oddscachexmlcron():
            self.oddscachexml()
        try: # every 1hours make sure the schedule is fresh.
            schedule.addPeriodicEvent(oddscachexmlcron, 3600, now=True, name='oddscachexml')
        except AssertionError:
            try:
                schedule.removeEvent('oddscachexml')
            except KeyError:
                pass
            schedule.addPeriodicEvent(oddscachexmlcron, 3600, now=True, name='oddscachexml')

    def die(self):
        try:
            schedule.removeEvent('oddscachexml')
        except KeyError:
            pass
        self.__parent.die()

    def oddscachexml(self):
        """Try and update the XMLTV cache."""

        self.log.info("CacheXML: Running...")
        if (not os.path.isfile(self.CACHEFILE) or (os.path.getsize(self.CACHEFILE) < 1)
            or (self._now() - os.stat(self.CACHEFILE).st_mtime > 9000)): # no file, under 1 byte, 2.5 hours old.
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
                tree = ElementTree.fromstring(response)  # look for an error code.
                if tree.attrib['ErrorCode'] != "0":  # 0 means no error. anything else = error.
                    self.log.error("CacheXML: ERROR in XML fetched. :: {0}".format(tree.attrib['ErrorMessage']))
                    return
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
        # total.seconds()
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

    def _local_to_utc(self, dt, tz_name):
        """Convert a dt string, given tz, to UTC. Return UTC dt object."""

        dt = pytz.timezone(tz_name).localize(dt)
        utc_dt = pytz.utc.normalize(dt.astimezone(pytz.utc))
        return utc_dt

    def _utc_to_local(self, dt, tz_name):
        """Takes a UTC dt object, convert to localized based on tz_name."""

        local_tz = pytz.timezone(tz_name)
        dt = local_tz.normalize(dt.astimezone(local_tz))
        return dt

    def _fixtime(self, date):
        """Convert a datetime string into a localized dt object."""

        dt = datetime.datetime.strptime(date, '%Y%m%d %H:%M:%S') # datetime string into dt object.
        dt = self._local_to_utc(dt, "US/Pacific")  # normalize time into UTC from Pacific.
        dt = self._utc_to_local(dt, self.displaytz)  # now we "localize" the dtobject to what we want out.
        # now, we're gonna return a string of the dt below. conditional depending on when it is.
        if (dt - datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)) < datetime.timedelta(hours=145):  # is the date < 145 hours away?
            todaydaynum = datetime.datetime.strftime(datetime.datetime.today(), '%a')  # today's day #.
            stringdaynum = datetime.datetime.strftime(dt, '%a')  # day of event.
            # are the days of the week same or different?
            if todaydaynum == stringdaynum: # same date. return w/o day of week.
                return dt.strftime('%H:%M')  # ie: 19:05
            else:  # not the same day of the week.
                return dt.strftime('%a %H:%M')  # ie: Sat 19:05
        else:  # later than 145 hours from now. add month/day@HH:MM.
            return dt.strftime('%m/%d@%H:%M')

    ######################################
    # ODDS PROCESSING INTERNAL FUNCTIONS #
    ######################################

    def _processgame(self, game):
        """Process a single XML line for a game/event."""

        tmp = {}  # dict container.
        tmp['gpd'] = game.get('gpd')  # gameplayed? helpful for soccer.
        tmp['gametype'] = game.get('idgmtyp')  # gametype. used to detect props.
        tmp['date'] = game.get('gmdt')  # game date.
        tmp['time'] = game.get('gmtm')  # game time.
        tmp['vpt'] = game.get('vpt')  # visiting pitcher. (mlb)
        tmp['hpt'] = game.get('hpt')  # home pitcher. (mlb)
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
            else:  # we bold the away team because it's + or regular number.
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
        tmp['line'] = int(prop.get('odds'))  # to sort.
        return tmp

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
        validsports = {'NFL':'1', 'NBA':'3', 'NCB':'4','NHL':'7', 'MLB':'5', 'INTL-FRIENDLY':'10090',
                       'EPL':'10003', 'LALIGA':'12159', 'UFC-MMA':'206', 'UFC-BELLATOR':'12636',
                       'MLS':'10007', 'UEFA-CL':'10016', 'LIGUE1':'10005','BUNDESLIGA':'10004',
                       'SERIEA':'10002', 'UEFA-EUROPA':'12613', 'BOXING':'12064', 'TENNIS-M':'12331',
                       'TENNIS-W':'12332', 'AUSSIERULES':'12118', 'GOLF':'12003', 'WCQ-UEFA':'12321',
                       'WCQ-CONMEBOL':'12451', 'WCQ-CAF':'12461', 'WCQ-CONCACAF':'12484', 'NASCAR':'12015',
                       'CFL':'12145'}

        if not optsport in validsports:  # error if not in above.
            validprops = { 'NFL-SUPERBOWL':'1561335', 'NFL-MVP':'1583283'}
            if optsport in validprops:
                optprop = optsport
                optsport = "PROP"
            else:  # prop not found. so we display only the sports.
                irc.reply("ERROR: '{0}' is invalid. Valid sports: {1}".format(optsport, " | ".join(sorted(validsports.keys()))))
                return

        # now try and parse/open XML.
        try:
            tree = ElementTree.parse(self.CACHEFILE)
        except ElementTree.ParseError, e:
            self.log.error("ERROR: parsing cached XML :: {0}".format(e))
            irc.reply("ERROR: Something broke trying to parse the XML. Check logs.")
            return

        # now that we have XML, it must be processed differently depending on props/games.
        if optsport in ("GOLF", "NASCAR"):  # specific handler for golf. we label sport but handle as prop.
            line = tree.findall('./Leagues/league[@IdLeague="%s"]/game' % validsports[optsport])
            if not line:
                irc.reply("ERROR: I did not find any {0} prop/future odds.".format(optsport))
                return
            # we only grab the first [0]. we could do more than one.
            propname = line[0].attrib['htm']  # tournament here.
            props = []  # list to dump out in for processing.
            for l in (line[0].findall('line')):  # we enumerate over all "line" in the entry.
                props.append(self._processprop(l))  # send to prop handler and append.
            # now sort (lowest first) before we prep the output. (creates a list w/dict in it.)
            props = sorted(props, key=itemgetter('line'))
        elif optsport == "PROP":  # processing PROPS/futures here.
            line = tree.find(".//game[@idgm='%s']" % validprops[optprop])
            if not line:  # prop or no items found inside the prop.
                irc.reply("ERROR: I did not find {0} prop/future or any odds in it.".format(optprop))
                return
            # we did find prop+lines, so lets grab the name and the lines.
            propname = line.attrib['htm']  # htm contains the "name" of the prop/future.
            props = []  # everything goes into props dict so we can sort.
            for l in (line.findall('line')):  # we enumerate over all "line" in the entry.
                props.append(self._processprop(l))  # send to prop handler and append.
            # now sort (lowest first) before we prep the output. (creates a list w/dict in it.)
            props = sorted(props, key=itemgetter('line'))
        else:  # processing GAMES here not props.
            leagues = tree.findall('./Leagues/league[@IdLeague="%s"]/game' % (validsports[optsport]))
            if len(leagues) == 0:  # check if empty (no games) or nothing found (wrong time of the year).
                irc.reply("ERROR: I did not find any events in the {0} category.".format(optsport))
                return
            # we must process each "game" or match.
            games = []  # list to store dicts of processed games.
            for game in leagues:  # each entry is a game/match.
                games.append(self._processgame(game))  # add processesed xml list.
            # now, we should sort by dt (epoch seconds) with output (earliest first).
            games = sorted(games, key=itemgetter('date', 'time'))

        # now, we must preprocess the output in the dicts.
        # each sport is different and we append into a list for output.
        output = []
        # first, handle props and prop-like sports (GOLF ONLY).
        if optsport == "PROP" or optsport in ("GOLF", "NASCAR"):  # we join all of the props/lines into one entry. title.
            proplist = " | ".join([q['tmname'].title().strip() + " (" + self._fml(q['line']) + ")" for q in props])
            output.append("{0} :: {1}".format(ircutils.mircColor(propname, 'red'), proplist))
        # REST ARE NON-PROP. EACH HANDLES A SPORT DIFFERENTLY.
        # handle NFL football.
        elif optsport in ("NFL", "CFL"):
            for (v) in games:
                if v['spread'] != "":
                    output.append("{0}@{1}[{2}]  o/u: {3}  {4}/{5}  {6}".format(v['away'], v['home'],\
                        v['spread'], v['over'], self._fml(v['awayodds']), self._fml(v['homeodds']), v['newdt']))
        # handle tennis.
        elif optsport in ('TENNIS-M', 'TENNIS-W'):
            for v in games:
                output.append("{0}@{1}  {2}/{3}  {4}".format(v['away'], v['home'],\
                    self._fml(v['awayodds']), self._fml(v['homeodds']), v['newdt']))
        # handle aussie rules.
        elif optsport == "AUSSIERULES":
            for (v) in games:
                output.append("{0}@{1}  {2}/{3}  {4}".format(v['away'], v['home'],\
                    self._fml(v['awayodds']), self._fml(v['homeodds']), v['newdt']))
        # handle baseball.
        elif optsport == "MLB":
            for (v) in games:
                if v['haschild'] == "True":
                    output.append("{0}@{1}  {2}/{3}  {4}".format(v['away'], v['home'],\
                        self._fml(v['awayodds']), self._fml(v['homeodds']), v['newdt']))
        # handle hockey.
        elif optsport == "NHL":
            for (v) in games:
                if v['haschild'] == "True":
                    output.append("{0}@{1}  o/u: {2}  {3}/{4}  {5}".format(v['away'], v['home'],\
                        v['over'], self._fml(v['awayodds']), self._fml(v['homeodds']), v['newdt']))
        # handle college basketball output.
        elif optsport == "NCB":
            for (v) in games:
                if v['haschild'] == "True":
                    output.append("{0}@{1}[{2}]  o/u: {3}  {4}/{5}  {6}".format(v['away'], v['home'],\
                        v['spread'], v['over'], self._fml(v['awayodds']), self._fml(v['homeodds']), v['newdt']))
        # handle NBA output.
        elif optsport == "NBA":
            for (v) in games:
                if v['haschild'] == "True":
                    output.append("{0}@{1}[{2}]  o/u: {3}  {4}/{5}  {6}".format(v['away'], v['home'],\
                        v['spread'], v['over'], self._fml(v['awayodds']), self._fml(v['homeodds']), v['newdt']))
        # handle soccer output.
        elif optsport in ('EPL', 'LALIGA', 'BUNDESLIGA', 'SERIEA', 'LIGUE1', 'MLS', 'UEFA-EUROPA', 'UEFA-CL',
                          'WCQ-UEFA', 'WCQ-CONMEBOL', 'WCQ-CAF', 'WCQ-CONCACAF', 'INTL-FRIENDLY'):
            for (v) in games:  # we check for Game below because it blocks out 1H/2H lines.
                if v['homeodds'] != '' and v['awayodds'] != '' and v['gpd'] == 'Game':
                     output.append("{0}@{1}  o/u: {2}  {3}/{4} (Draw: {5})  {6}".format(v['away'], v['home'],\
                        v['over'], self._fml(v['awayodds']), self._fml(v['homeodds']), self._fml(v['vspoddst']), v['newdt']))
        # handle UFC output.
        elif optsport in ('UFC-MMA', 'UFC-BELLATOR'):
            for (v) in games:
                if v['homeodds'] != '' and v['awayodds'] != '':
                    output.append("{0} vs. {1}  {2}/{3}  {4}".format(v['away'], v['home'],\
                        self._fml(v['awayodds']), self._fml(v['homeodds']), v['newdt']))
        # handle boxing output.
        elif optsport == "BOXING":
            for (v) in games:
                if v['homeodds'] != '' and v['awayodds'] != '':
                    output.append("{0} vs. {1}  {2}/{3}  {4}".format(v['away'], v['home'],\
                        self._fml(v['awayodds']), self._fml(v['homeodds']), v['newdt']))

        # output time.
        # checks if optinput (looking for something)
        if not optinput or optsport == "PROP":  # just display the games.
            outlength = len(output)  # calc once.
            if outlength == 0:  # nothing.
                irc.reply("Sorry, I did not find any active odds in {0}.".format(optsport))
            if outlength <= 9:  # 9 or under, one per line.
                for each in output: irc.reply(each)
            else:  # more than 9, we batch 4 per line.
                for N in self._batch(output, 4):
                    irc.reply(" | ".join([item for item in N]))
        else:  # we do want to limit output to only matching items.
            count = 0  # to handle a max # of 5.
            for each in output:  # iterate through output list.
                if optinput.lower() in each.lower():  # match.
                    if count < 5:  # output matching items.
                        irc.reply(each)
                        count += 1 # ++
                    else:  # too many to output after 5. breaks,
                        irc.reply("I found too many results for '{0}'. Please specify something more specific".format(optinput))
                        break
            # last check for if we outputted NOTHING.
            if count == 0:  # nothing came out.
                irc.reply("Sorry, I did not find any odds matching '{0}' in {1} category.".format(optinput, optsport))

    odds = wrap(odds, [('somethingWithoutSpaces'), optional('text')])

Class = Odds


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
