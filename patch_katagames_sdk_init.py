"""
Katasdk allows the creation of games that are super easy to share online

Copyright (C) 2022 Gaudia Tech Inc.

contac@kata.games
twitter.com/CreatePlayEarn
"""

SDKVER_TAG = '0.0.9'

from . import katagames_engine as _kengi

_kengi.get_injector().package_arg = 'katagames_sdk.katagames_engine'
kengi = _kengi

def runs_in_web():
    return False
