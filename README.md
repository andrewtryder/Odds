[![Build Status](https://travis-ci.org/reticulatingspline/Odds.svg?branch=master)](https://travis-ci.org/reticulatingspline/Odds)

# Odds plugin for Supybot / Limnoria

## Introduction

People are always looking for the lines / spreads / odds on various sporting events. I made
this plugin to service that need. Please note, the source I use doesn't always have the
most up-to-date or reliable lines. I intended this plugin as an information-tool only.
It supports almost all sports out there from NFL, MLB, CFB, NBA, NHL, Tennis, etc.

## Install

You will need a working Limnoria bot on Python 2.7 for this to work.

Go into your Limnoria plugin dir, usually ~/supybot/plugins and run:

```
git clone https://github.com/reticulatingspline/Odds
```

To install additional requirements, run:

```
pip install -r requirements.txt 
```

Next, load the plugin:

```
/msg bot load Odds
```

You are done.

## Example Usage

```
<spline> @odds NFL denver
<myybot> DENVER@NY JETS[+10]  o/u: 47.5  -450/+355  13:00
<myybot> @odds MLB
<myybot> SFO GIANTS@STL CARDINALS  +108/-118  20:05
<myybot> BAL ORIOLES@KC ROYALS  -109/-101  Mon 20:05
```

## About

All of my plugins are free and open source. When I first started out, one of the main reasons I was
able to learn was due to other code out there. If you find a bug or would like an improvement, feel
free to give me a message on IRC or fork and submit a pull request. Many hours do go into each plugin,
so, if you're feeling generous, I do accept donations via Amazon or browse my [wish list](http://amzn.com/w/380JKXY7P5IKE).

I'm always looking for work, so if you are in need of a custom feature, plugin or something bigger, contact me via GitHub or IRC.