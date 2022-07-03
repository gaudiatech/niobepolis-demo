import katagames_engine as kengi
kengi.bootstrap_e()

import app_explore
import app_poker
import glvars
from defs import GameStates, MyEvTypes, MAXFPS


pygame = kengi.pygame
CgmEvent = kengi.event.CgmEvent
EngineEvTypes = kengi.event.EngineEvTypes
ReceiverObj = kengi.event.EventReceiver

# global variables
conv_viewer = None
conversation_ongoing = False
current_path = None
current_tilemap = 0
maps = list()
map_viewer = None
mypc = None
path_ctrl = None
screen = None
tilemap_height = tilemap_width = 0


# ---------------------------------------
#  Add-ons, was previously a part of main_zero.py
#
#  will be used in this demo:
# ---------------------------------------
# class ExtraLayerView(ReceiverObj)
# class ExtraGuiLayerCtrl(ReceiverObj)
# func build_console(screen)
# --- end of add-ons

# ------------------------------------
#  Temporary class: DEBUG tool
#  we use this class only to ensure that game entities fire up events
# ------------------------------------
class GameEventLogger(kengi.event.EventReceiver):
    def __init__(self):
        super().__init__()

    def proc_event(self, ev, source):
        if ev.type == MyEvTypes.TerminalStarts:
            print('Terminal ---------')
        elif ev.type == MyEvTypes.SlotMachineStarts:
            print('Slot machine------------')
        elif ev.type == MyEvTypes.PortalActivates:
            print('portal has been activated! portal_id= ', ev.portal_id)


if __name__ == '__main__':
    kengi.init('old_school', maxfps=MAXFPS)
    screen = kengi.get_surface()

    kengi.declare_states(
        GameStates,
        {
            GameStates.Explore: app_explore.ExploreState,
            GameStates.Poker: app_poker.PokerState
        },
        glvars
    )
    gctrl = kengi.get_game_ctrl()
    gctrl.turn_on()  # so we can use/push another gamestate
    gctrl.loop()

    kengi.quit()
    print('bye!')
