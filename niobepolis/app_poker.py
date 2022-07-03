import katagames_engine as kengi
kengi.bootstrap_e()

# aliases
BaseGameState = kengi.BaseGameState
Card = kengi.tabletop.StandardCard
PokerHand = kengi.tabletop.PokerHand

from poker_compo import UthModel, UthView, UthCtrl


# - aliases
ReceiverObj = kengi.event.EventReceiver
EngineEvTypes = kengi.event.EngineEvTypes
pygame = kengi.pygame

# - glvars
alea_xx = lambda_hand = epic_hand = list()


# --------------
#  functions only
# --------------
def _init_and_tests():
    """
    ----------------------------------------------
       W.i.p. <> below I perform some tests legacy classes/
       chunks copied from elsewhere still need to be merged/unified
    -----------------------------------------------
    """
    deja_pioche = set()
    future_main = list()
    for _ in range(5):
        card = Card.at_random(deja_pioche)
        print(card, '|', card.code)
        deja_pioche.add(card.code)
        future_main.append(card)

    ma_main = PokerHand(future_main)
    print(ma_main)
    print('-- fin tests affichage --')
    print()

    # TODO implem fct. manquante
    print('flush? ', ma_main.is_flush())
    print('straight? ', ma_main.is_straight())
    print('score= ' + str(ma_main.value))

    print('-- fin tests base modele --')
    print()


class PokerState(BaseGameState):
    def __init__(self, gs_id):
        super().__init__(gs_id)
        self.m = self.v = self.c = None

    def enter(self):
        kengi.screen_param('hd')
        self.m = UthModel()
        self.v = UthView(self.m)
        self.v.turn_on()
        self.c = UthCtrl(self.m)
        self.c.turn_on()

    def release(self):
        self.c.turn_off()
        self.c = None
        self.v.turn_off()
        self.v = None


def standalone_poker():
    global alea_xx, lambda_hand, epic_hand
    _init_and_tests()
    kengi.init('hd')

    # >>> the game loop
    mod = UthModel()
    receivers = [
        UthView(mod),
        UthCtrl(mod),
        kengi.get_game_ctrl()
    ]
    for robj in receivers:
        robj.turn_on()
    receivers[-1].loop()
    print('bye!')


# if __name__ == '__main__':
#     standalone_poker()

if __name__ == '__main__':
    # trying to locate A BUG
    # ranking of hands isnt good for all cases, especially the 'High Card' case
    # TODO fix
    mod = UthModel()
    mod.dealer_hand = [
        Card('Ah'), Card('2h')
    ]
    mod.player_hand = [
        Card('Ad'), Card('Ks')
    ]
    mod.flop_cards = [
        Card('4c'), Card('Td'), Card('8d')
    ]
    mod.turnriver_cards = [
        Card('7h'), Card('Qc')
    ]

    # ----
    optimize_m = kengi.tabletop.find_best_ph
    dealer_vhand = optimize_m(mod.dealer_hand + mod.flop_cards + mod.turnriver_cards)
    player_vhand = optimize_m(mod.player_hand + mod.flop_cards + mod.turnriver_cards)
    print(dealer_vhand, dealer_vhand.value)
    print(player_vhand, player_vhand.value)
