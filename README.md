Supybot-Odds
============

Description

    Supybot plugin for displaying sports MLB/NFL/NHL/NBA/MMA/NCAA/Tennis/AFL
    (College) Football/Basketball lines/odds/betting.

History

    This is my third "Odds" plugin for Supybot. I finally found a better provider that gives more
    reliable odds and decided to rewrite and adopt this over to it. It looks the same as my older
    "Odds2" plugin, but has a better core and also caches the data. The cache will prevent a game
    from disappearing when something begins (because betting for the match is off), and will also
    still display odds if the provider has gone down.

Disclaimer

    Obviously, gambling is illegal in many places. I don't condone nor support it. The intent of
    this plugin is for a user on IRC to get an idea of who is favored in a game, which a line or
    odds provide.

Instructions

    First, if you're running Odds2, you can uninstall (rm -rf) and unload.
    Next, download, install and load this. There are no configuration variables (yet).

Notes

    Misc notes and links:

    http://forum.punterslounge.com/threads/30348-XML-Odds-feed
    http://forum.sbrforum.com/handicapper-think-tank/538127-sportsbook-xml-feeds-p2.html
    http://livelines.betonline.com/sys/LineXML/LiveLineObjXml.asp?sport=Basketball&subsport=NBA
    http://xmlfeed.intertops.com/XMLOddsFeed/IntertopsOdds.aspx?all=true&lan=E&
    http://xmlfeed.intertops.com/XMLOddsFeed/
    http://api.pinnaclesports.com/v1/feed?sportid=4&leagueid=487&clientid=EH579260&apikey=<apikey>&oddsformat=0&islive=0&currencycode=USD
    http://pdom.org/wiki/Беттинг
    http://pricefeeds.williamhill.com/bet/en-gb?action=GoPriceFeed
    http://www.pinnaclesports.com/apimanual/commands.aspx
    https://forum.bdp.betfair.com/showthread.php?t=1832&page=2
