Supybot-Odds
============

Description
    
    Supybot plugin for displaying sports (MLB/NFL/NHL/NBA/MMA/NCAA (College) Football/Basketball
    lines/odds/betting.

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
    Consider this beta.

Notes
    
    The following links helped quite a bit:
    
    http://forum.punterslounge.com/threads/30348-XML-Odds-feed
    http://forum.sbrforum.com/handicapper-think-tank/538127-sportsbook-xml-feeds-p2.html
    http://livelines.betonline.com/sys/LineXML/LiveLineObjXml.asp?sport=Basketball&subsport=NBA

