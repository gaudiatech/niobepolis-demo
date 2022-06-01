"""
------------------------
*UNSTABLE* ver. of niobe polis. May 30th
------------------------

To run, use and IDE and set the Working directory one level below "niobepolis/"

Coords used in this game are:
 floorgrid -> 64x32 2D grid
 chargrid  -> 32x16 2D grid
 mapcoords -> isometric large tiles(size of a floor element)
 gamecoords-> isometric small tiles(size of the avatar)
"""

import katagames_sdk as katasdk

# a trick so we can load the stable katasdk but use the latest (dev/unstable) ver. of kengi
katasdk.bootstrap(0)

import katagames_engine as kengi
kengi.bootstrap_e()

from declarations import init_tilemap_etc, ExtraLayerView, ExtraGuiLayerCtrl, vStateMockup, build_console
import declarations  # to access variables in this scope
from niobepolis import debug_tool

import time
import glvars


pygame = kengi.pygame
clock = pygame.time.Clock()
keep_going = True
lu_event = paint_event = None
mger = None
scr = None
CgmEvent = kengi.event.CgmEvent
EngineEvTypes = kengi.event.EngineEvTypes
debug_v = None


def game_enter(vmstate):
    global mger, scr, lu_event, paint_event, debug_v

    kengi.init('super_retro', caption='niobepolis - unstable')
    mger = kengi.event.EventManager.instance()  # works only after a .init(...) operation
    scr = kengi.get_surface()

    lu_event = CgmEvent(EngineEvTypes.LOGICUPDATE, curr_t=None)
    paint_event = CgmEvent(EngineEvTypes.PAINT, screen=kengi.get_surface())

    init_tilemap_etc(scr)
    build_console(scr)  # sets declarations.ingame_console

    extra_gui_v = ExtraLayerView(declarations.ingame_console)
    extra_gui_ctrl = ExtraGuiLayerCtrl(declarations.ingame_console)
    for elk in (extra_gui_v, extra_gui_ctrl):
        elk.turn_on()

    debug_v = debug_tool.DebugV(declarations.isomap_viewer, declarations.ingame_console)

    debug_v.turn_on()


def game_update(infot=None):
    global lu_event, paint_event, mger, scr

    # use the kengi event system
    lu_event.curr_t = infot
    mger.post(lu_event)

    mger.post(paint_event)
    mger.update()

    if not glvars.keep_going:
        glvars.interruption = [1, None]

    if glvars.interruption:
        return glvars.interruption

    kengi.flip()
    clock.tick(glvars.MAXFPS)


def game_exit(vmstate):
    print('niobepolis->EXIT. The vmstate is: ', vmstate)
    kengi.quit()


if __name__ == '__main__':
    _dummy_vmstate = vStateMockup()
    game_enter(_dummy_vmstate)
    while glvars.keep_going:
        uresult = game_update(time.time())
        if uresult is not None:
            if 0 < uresult[0] < 3:
                glvars.keep_going = False
    game_exit(_dummy_vmstate)
