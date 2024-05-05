# Unstable niobepolis

*Disclaimer: all you will find here is mostly legacy/abandoned code !!!*

This used to be the main virtual universe (associated with the 2023 Kata.games prototype
platform, this one had a metaverse-like UX).

To reach the original author: thomas.iw@kata.games


### How to run the demo?

To run this demo, you'll need an old compatible version of the katasdk,
but also of the game engine.

To make things simpler, the revision `0.0.9`
of the `katasdk` ships with the legacy game engine (unknown revision).

So the procedure is:
1. Grab the source-code via Pypi:
[just follow this link](https://pypi.org/project/katasdk/)
Please note that this is an unstable version of the engine!
Also you will need a weird trick, copy the whole `katagames_engine` folder
to the root of the project. Files are duped.
2. patch the file `katagames_sdk/__init__.py` with the one provided
3. patch the file `katagames_engine/looparts/isometric/__init__.py` with the one provided

Then you can run either `main.py` (older version, uses HD graphics but the old map and
old assets), or `mashup.py` that is a more compact and newer version.

### Features that were planned

A virtual open world where players can:
- use teleporters to enter different games
- play poker
- use a terminal to interact with kata.games infrastructure
- chat with other people
