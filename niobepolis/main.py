import katagames_engine as kengi
kengi.bootstrap_e()

import app_explore
import app_poker
import glvars
from defs import GameStates, MAXFPS


if __name__ == '__main__':
    # uncomment the following line to test niobe with a new map
    # app_explore.main_map_path = 'bug_exterior.tmx'

    kengi.init('old_school', maxfps=MAXFPS)
    kengi.declare_states(  # so we can use pushstate/changestate operations
        GameStates,
        {
            GameStates.Explore: app_explore.ExploreState,
            GameStates.Poker: app_poker.PokerState
        },
        glvars
    )
    kengi.get_game_ctrl().turn_on().loop()
    kengi.quit()
    print('clean exit -> ok')
