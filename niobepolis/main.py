"""
------------------------
*UNSTABLE* ver. of niobe polis. May 21th
------------------------
Coords used in this game:
floorgrid -> 64x32 2D grid
chargrid  -> 32x16 2D grid
mapcoords -> isometric large tiles(size of a floor element)
gamecoords-> isometric small tiles(size of the avatar)
"""
import katagames_sdk as katasdk
katasdk.bootstrap(0)

import katagames_engine as kengi
kengi.bootstrap_e()

from declarations import init_tilemap_etc, ExtraLayerView, ExtraGuiLayerCtrl, vStateMockup, build_console
import time
import glvars


pygame = kengi.pygame
clock = pygame.time.Clock()
ingame_console = None
keep_going = True
lu_event = paint_event = None
mger = None
scr = None
CgmEvent = kengi.event.CgmEvent
EngineEvTypes = kengi.event.EngineEvTypes


def game_enter(vmstate):
    global mger, scr, ingame_console, lu_event, paint_event  #cached_gamelist, binded_state, vscr_size

    kengi.init('super_retro', caption='niobepolis - unstable')
    mger = kengi.event.EventManager.instance()  # works only after a .init(...) operation
    scr = kengi.get_surface()

    lu_event = CgmEvent(EngineEvTypes.LOGICUPDATE, curr_t=None)
    paint_event = CgmEvent(EngineEvTypes.PAINT, screen=kengi.get_surface())

    init_tilemap_etc(scr)
    ingame_console = build_console(scr)

    extra_gui_v = ExtraLayerView(ingame_console)
    extra_gui_ctrl = ExtraGuiLayerCtrl(ingame_console)
    for elk in (extra_gui_v, extra_gui_ctrl):
        elk.turn_on()

    cached_gamelist = vmstate.gamelist_func()
    binded_state = vmstate


def game_update(infot=None):
    global lu_event, paint_event, mger, scr
    vscr_size = scr.get_size()

    # use the kengi event system
    lu_event.curr_t = infot
    mger.post(lu_event)

    mger.post(paint_event)
    mger.update()

    if not glvars.keep_going:
        interruption = [1, None]

    if glvars.interruption:
        return glvars.interruption

    # SUPER bad fix to hid borders (pb with backned cant crop)
    if not ingame_console.active:
        ttt = 12
        pygame.draw.rect(paint_event.screen, 'black', (0, 0, ttt, vscr_size[1] - 1))
        pygame.draw.rect(paint_event.screen, 'black', (vscr_size[0] - ttt, 0, ttt, vscr_size[1] - 1))

        pygame.draw.rect(paint_event.screen, 'black', (0, 0, vscr_size[0] - 1, ttt))
        pygame.draw.rect(paint_event.screen, 'black', (0, vscr_size[1] - ttt, vscr_size[0] - 1, ttt))

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
