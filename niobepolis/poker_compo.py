import katagames_engine as kengi
from defs import MyEvTypes
import time

pygame = kengi.pygame
StandardCard = kengi.tabletop.StandardCard
PokerHand = kengi.tabletop.PokerHand
ReceiverObj = kengi.event.EventReceiver
EngineEvTypes = kengi.event.EngineEvTypes
find_best_ph = kengi.tabletop.find_best_ph
CardDeck = kengi.tabletop.CardDeck


# -----------------------------------------------------------------/
#              ******** MODEL ********
# -----------------------------------------------------------------/
class MoneyInfo(kengi.event.CogObj):
    """
    created a 2nd class (model) so it will be easier to manage
    earning & loosing

    earning := prize due to "Ante" + prize due to "Bet" + prize due to "Blind"
    right now this class isnt used, but it should become active

    ------
    * Si le Croupier a la meilleure combinaison, il récupère toutes les mises des cases « Blinde »,
    « Mise (Ante) » et « Jouer » (cas particulier pour le Bonus, voir ci-dessous)

    * en cas d’égalité, les mises restent aux joueurs sans gain ni perte (cas particulier pour le Bonus, voir ci-dessous)

    * Si un joueur a une meilleure combinaison que le Croupier,
    il récupère l’intégralité de ses mises de départ et ses enjeux seront payés en fonction du tableau de paiement :
    """
    def __init__(self, init_amount=200):
        super().__init__()
        self._cash = init_amount  # starting cash

        # TODO complete the implem & use this class!
        self.ante = self.blind = self.playcost = 0
        self._latest_bfactor = None

        self.recorded_outcome = None  # -1 loss, 0 tie, 1 victory
        self.recorded_prize = 0

    def get_cash_amount(self):
        return self._cash

    def init_play(self, value):
        self.ante = self.blind = value
        self._cash -= 2 * value
        self.pev(MyEvTypes.CashChanges, value=self._cash)

    def bet(self, bet_factor):
        self.playcost = bet_factor * self.ante
        self._cash -= self.playcost
        self.pev(MyEvTypes.CashChanges, value=self._cash)
        self._latest_bfactor = bet_factor

    def update_money_info(self):
        if self.recorded_outcome == 1:
            self._cash += self.recorded_prize
        if self.recorded_outcome > -1:
            self._cash += self.ante + self.blind + self.playcost  # recup toutes les mises

        self.ante = self.blind = self.playcost = 0  # reset play
        self.pev(MyEvTypes.CashChanges, value=self._cash)

    @property
    def is_player_broke(self):
        return self._cash <= 0
        # useful method because someone may want to call .pev(EngineEvTypes.GAMEENDS) when player's broke

    # ---------------------
    #  the 4 methods below compute future gain/loss
    #  but without applying it
    # ---------------------
    @staticmethod
    def compute_blind_multiplier(givenhand):
        # calcul gain spécifique & relatif à la blinde
        # -------------------------------------------
        # Royal flush- 500 pour 1
        # Straigth flush- 50 pour 1
        # Four of a kind - 10 pour 1
        # Full house - 3 pour 1
        # Flush - 1.5 pour 1
        # Suite - 1 pour 1
        # autres mains y a pas eu victore mais simple égalité!
        multiplicateur = {
            'High Card': 0,
            'One Pair': 0,
            'Two Pair': 0,
            'Three of a Kind': 0,
            'Straight': 1,
            'Flush': 1.5,
            'Full House': 3,
            'Four of a Kind': 10,
            'Straight Flush': 50
        }[givenhand.description]
        return multiplicateur

    def announce_victory(self, winning_hand):
        prize = self.ante + self.playcost  # la banque paye à égalité sur ante & playcost
        blind_multiplier = MoneyInfo.compute_blind_multiplier(winning_hand)
        prize += blind_multiplier * self.blind
        self.recorded_prize = prize

        self.recorded_outcome = 1

        self.pev(MyEvTypes.Victory, amount=prize)

    def announce_tie(self):
        self.recorded_outcome = 0
        self.pev(MyEvTypes.Tie)

    def announce_defeat(self):
        self.recorded_outcome = -1
        self.pev(MyEvTypes.Defeat, loss=-1*(self.ante+self.blind+self.playcost))


class UthModel(kengi.event.CogObj):
    INIT_ST_CODE, DISCOV_ST_CODE, FLOP_ST_CODE, TR_ST_CODE, OUTCOME_ST_CODE, WAIT_STATE = range(1, 6 + 1)

    """
    Uth: Ultimate Texas Holdem
    STAGES ARE

    0: "eden state" -> cards not dealt, no money spent
    1: cards dealt yes, both ante and blind have been paid, you pick one option: check/bet 3x/ bet 4x
      if bet 4x you go straight to the last state
      if check you go to state 2
    2: flop revealed, your pick one option: check/bet 2x
      if bet 2x you go to the last state
      if check you go to state 3
    3: turn & river revealed you pick one option: fold/ bet 1x
      if bet you go to the final state
      if fold you loose everything except whats in bonus state 5
    4(final):
      all remaining cards are returned, if any then player is paid. Current round halts
    5:
      pay bonus only, current round halts
    """

    def __init__(self):
        super().__init__()
        self.wallet = MoneyInfo()
        self.deck = CardDeck()

        self.revealed = {
            'dealer1': False,
            'dealer2': False,
            'flop3': False,
            'flop2': False,
            'flop1': False,
            'turn': False,
            'river': False,
            'player1': False,
            'player2': False
        }

        self.folded = False
        self.autoplay_flag = False
        self.dealer_vhand = self.player_vhand = None

        # stored lists of cards
        self.dealer_hand = []
        self.player_hand = []
        self.flop_cards = []
        self.turnriver_cards = []

        self._stage = None
        self.set_stage(self.INIT_ST_CODE)

    # avoid external modification of stage => encapsulate data
    @property
    def stage(self):
        return self._stage

    @property
    def cash(self):
        return self.wallet.get_cash_amount()

    @property
    def money_info(self):
        # returns smth in the format
        # [(self._mod.ante, 'ante'), (self._mod.blind, 'blind'), (self._mod.bet, 'bet')]
        return [
            (self.wallet.ante, 'ante'),
            (self.wallet.blind, 'blind'),
            (self.wallet.playcost, 'bet')
        ]

    # -----------------------
    #  state transitions
    # -----------------------
    def evolve_state(self):
        if self.DISCOV_ST_CODE == self.stage:
            self.go_flop()
        elif self.FLOP_ST_CODE == self.stage:
            self.go_tr_state()
        elif self.TR_ST_CODE == self.stage:
            self.go_outcome_state()
        elif self.OUTCOME_ST_CODE == self.stage:
            self.go_wait_state()

    def set_stage(self, sid):
        assert 1 <= sid <= 6
        self._stage = sid
        print(f' --new state-- >>> {sid}')
        self.pev(MyEvTypes.StageChanges)

    def go_discov(self, ante_val):
        if self.stage != UthModel.INIT_ST_CODE:
            raise ValueError('calling deal_cards while model isnt in the initial state')
        self.revealed['player2'] = self.revealed['player1'] = True
        # TODO should be deck.draw_cards(2) or smth
        self.dealer_hand.extend(self.deck.deal(2))
        self.player_hand.extend(self.deck.deal(2))
        self.wallet.init_play(ante_val)
        self.set_stage(self.DISCOV_ST_CODE)

    def go_flop(self):
        print('GO FLOP STATE')
        for k in range(1, 3 + 1):
            self.revealed[f'flop{k}'] = True
        self.flop_cards.extend(self.deck.deal(3))
        self.set_stage(self.FLOP_ST_CODE)

    def go_tr_state(self):
        print('GO TR STATE')
        # betting => betx2, or check
        self.turnriver_cards.extend(self.deck.deal(2))
        self.revealed['turn'] = self.revealed['river'] = True
        self.set_stage(self.TR_ST_CODE)

    def describe_pl_hand(self):
        return self.player_vhand.description

    def describe_dealers_hand(self):
        return self.dealer_vhand.description

    def go_outcome_state(self):
        print('GO OUTCOME STATE')
        self.set_stage(self.OUTCOME_ST_CODE)

    def go_wait_state(self):
        # state dedicated to blit the type of hand (Two pair, Full house etc) + the outcome
        print('autoplay OFF!')
        self.autoplay_flag = False

        if self.folded:
            self.wallet.announce_defeat()
            self.revealed['dealer1'] = self.revealed['dealer2'] = False
        else:
            # - vhand like virtual hand,
            # because it contains 7 cards and the program should find the best possible 5-card hand
            self.dealer_vhand = find_best_ph(self.dealer_hand + self.flop_cards + self.turnriver_cards)
            self.player_vhand = find_best_ph(self.player_hand + self.flop_cards + self.turnriver_cards)

            dealrscore = self.dealer_vhand.value
            playrscore = self.player_vhand.value

            if dealrscore > playrscore:
                self.wallet.announce_defeat()
            elif dealrscore == playrscore:
                self.wallet.announce_tie()
            else:
                self.wallet.announce_victory(self.player_vhand)
            self.revealed['dealer1'] = self.revealed['dealer2'] = True
        self.set_stage(self.WAIT_STATE)

    def new_round(self):  # like a reset
        # manage money:
        # TODO could use .pev here, if animations are needed
        #  it can be nice. To do so one would use the controller instead of lines below
        # if self.folded:
        #     self.loose_money()
        # else:
        #     a, b = self.player_vhand.value, self.dealer_vhand.value
        #     if a <= b:
        #         if a == b:
        #             print('EGALITé')
        #             self.refund_money()
        #         else:
        #             print('JAI PERDU')
        #             self.loose_money()
        #     else:
        #         print('JE BATS DEALER')
        #         self.earn_money()
        self.wallet.update_money_info()

        # reset stuff
        self.deck.reset()
        self.folded = False

        # HIDE cards
        for lname in self.revealed.keys():
            self.revealed[lname] = False

        # remove all cards previously dealt
        del self.dealer_hand[:]
        del self.player_hand[:]
        del self.flop_cards[:]
        del self.turnriver_cards[:]

        self.set_stage(self.INIT_ST_CODE)

    def input_bet(self, small_or_big):  # accepted values: {0, 1}
        bullish_choice = small_or_big + 1
        if self.stage == self.INIT_ST_CODE:
            self.go_discov(4)  # 4 is the arbitrary val chosen for 'Ante', need to pick a val that can be
            # paid via chips available on the virtual game table. value 5 would'nt work!
        else:
            if self.stage == self.DISCOV_ST_CODE:
                if bullish_choice == 1:
                    self.wallet.bet(3)
                else:
                    self.wallet.bet(4)
            elif self.stage == self.FLOP_ST_CODE:
                self.wallet.bet(2)
            elif self.stage == self.TR_ST_CODE:
                self.wallet.bet(1)

            self.pev(MyEvTypes.EndRoundRequested, folded=False)

    def input_check(self):
        # doing the CHECK only
        if self.stage == self.DISCOV_ST_CODE:
            self.go_flop()

        elif self.stage == self.FLOP_ST_CODE:
            self.go_tr_state()

        elif self.stage == self.TR_ST_CODE:
            self.folded = True
            self.pev(MyEvTypes.EndRoundRequested)

        elif self.stage == self.WAIT_STATE:
            self.new_round()


# -----------------------------------------------------------------/
#              ******** VIEW ********
# -----------------------------------------------------------------/
BACKGROUND_IMG_PATH = 'assets/bg0.jpg'
CARD_SIZE_PX = (82, 120)
CHIP_SIZE_PX = (62, 62)
POS_CASH = (1192, 1007)
CARD_SLOTS_POS = {  # coords in pixel so cards/chips & BG image do match; cards img need an anchor at the middle.
    'dealer1': (905, 329),
    'dealer2': (1000, 333),

    'flop3': (980, 470),
    'flop2': (1075, 473),
    'flop1': (1173, 471),

    'turn': (846, 473),
    'river': (744, 471),

    'player1': (1125, 878),
    'player2': (1041, 880),

    'ante': (935, 757),
    'bet': (935, 850),
    'blind': (1040, 757),

    'raise1': (955, 870),
    'raise2': (961, 871),
    'raise3': (967, 872),
    'raise4': (973, 873),
    'raise5': (980, 875),
    'raise6': (986, 876)
}
PLAYER_CHIPS = {
    '2a': (825, 1000),
    '2b': (905, 1000),
    '5': (985, 1000),
    '10': (1065, 1000),
    '20': (1145, 1000)
}


class UthView(ReceiverObj):
    TEXTCOLOR = (5, 58, 7)
    BG_TEXTCOLOR = (133, 133, 133)
    ASK_SELECTION_MSG = 'SELECT ONE OPTION: '

    def __init__(self, model):
        super().__init__()
        self._assets_rdy = False

        self.bg = None
        self.card_back_img = None

        self.card_images = dict()
        self.chip_spr = dict()

        self._mod = model
        self.ft = pygame.font.Font(None, 72)
        self.small_ft = pygame.font.Font(None, 23)

        self.info_msg0 = None
        self.info_msg1 = None  # will be used to tell the player what he/she has to do!
        self.info_msg2 = None

        # draw cash amount
        self.cash_etq = self.ft.render(str(self._mod.cash)+'$ ', True, self.TEXTCOLOR, self.BG_TEXTCOLOR)

    def _load_assets(self):
        self._assets_rdy = True

        self.bg = pygame.image.load(BACKGROUND_IMG_PATH)
        self.card_back_img = pygame.image.load('assets/source_cards/back-of-card.png').convert_alpha()
        self.card_back_img = pygame.transform.scale(self.card_back_img, CARD_SIZE_PX)

        for card_cod in StandardCard.all_card_codes():
            y = PokerHand.adhoc_mapping(card_cod[0]).lstrip('0') + card_cod[1].upper()  # convert card code to path
            img_path = f'assets/source_cards/{y}.png'
            tempimg = pygame.image.load(img_path).convert_alpha()
            self.card_images[card_cod] = pygame.transform.scale(tempimg, CARD_SIZE_PX)

        for chip_val_info in ('2a', '2b', '5', '10', '20'):
            org = chip_val_info
            if chip_val_info == '2a' or chip_val_info == '2b':
                chip_val_info = '2'
            img_path = f'assets/chip{chip_val_info}.png'
            tempimg = pygame.image.load(img_path).convert_alpha()
            tempimg = pygame.transform.scale(tempimg, CHIP_SIZE_PX)
            tempimg.set_colorkey((255, 0, 255))
            spr = pygame.sprite.Sprite()
            spr.image = tempimg
            spr.rect = spr.image.get_rect()
            spr.rect.center = PLAYER_CHIPS[org]
            self.chip_spr[chip_val_info] = spr

    def _update_displayed_status(self):

        if self._mod.stage == UthModel.INIT_ST_CODE:
            self.info_msg0 = self.ft.render('Press ENTER to begin', True, self.TEXTCOLOR)
            self.info_msg1 = None
            self.info_msg2 = None
            return

        msg = None
        if self._mod.stage == UthModel.DISCOV_ST_CODE:
            msg = ' CHECK, BET x3, BET x4'
        elif self._mod.stage == UthModel.FLOP_ST_CODE and (not self._mod.autoplay_flag):
            msg = ' CHECK, BET x2'
        elif self._mod.stage == UthModel.TR_ST_CODE and (not self._mod.autoplay_flag):
            msg = ' FOLD, BET x1'
        if msg:
            self.info_msg0 = self.ft.render(self.ASK_SELECTION_MSG, True, self.TEXTCOLOR)
            self.info_msg1 = self.small_ft.render(msg, True, self.TEXTCOLOR)

    #     message_table = defaultdict(
    #         default_factory=lambda: None, {
    #             UthModel.INIT_ST_CODE: 'press SPACE to play',
    #             UthModel.DISCOV_ST_CODE: 'CHECK, BET x3, BET x4',
    #             UthModel.FLOP_ST_CODE: 'CHECK, BET x2',
    #             UthModel.TR_ST_CODE: 'FOLD, BET x1'
    #         }
    #     )
    #     elif ev.type == MyEvTypes.PlayerWins:
    #     self.delta_money = ev.amount
    #     self.info_msg0 = self.ft.render('Victory', True, self.TEXTCOLOR)
    #
    # elif ev.type == MyEvTypes.PlayerLooses:
    # # TODO disp. amount lost
    # self.info_msg0 = self.ft.render('Defeat', True, self.TEXTCOLOR)

    def proc_event(self, ev, source):
        if ev.type == EngineEvTypes.PAINT:
            if not self._assets_rdy:
                self._load_assets()
            self._paint(ev.screen)

        elif ev.type == MyEvTypes.StageChanges:
            self._update_displayed_status()

        elif ev.type == MyEvTypes.CashChanges:
            # RE-draw cash value
            self.cash_etq = self.ft.render(str(ev.value) + '$ ', True, self.TEXTCOLOR, self.BG_TEXTCOLOR)

        elif ev.type == MyEvTypes.Victory:
            print('victory event received')
            result = ev.amount
            infoh_player = self._mod.player_vhand.description
            infoh_dealer = self._mod.dealer_vhand.description
            msg = f"Player: {infoh_player}; Dealer: {infoh_dealer}; Change {result}$"
            self.info_msg0 = self.ft.render('Victory!', True, self.TEXTCOLOR)
            self.info_msg1 = self.small_ft.render(msg, True, self.TEXTCOLOR)
            self.info_msg2 = self.small_ft.render('Press BACKSPACE to restart', True, self.TEXTCOLOR)

        elif ev.type == MyEvTypes.Tie:
            print('tie event received')
            self.info_msg0 = self.ft.render('Its a Tie.', True, self.TEXTCOLOR)
            infoh_player = self._mod.player_vhand.description
            infoh_dealer = self._mod.dealer_vhand.description
            self.info_msg1 = self.small_ft.render(
                f"Player: {infoh_player}; Dealer: {infoh_dealer}; Change {0}$",
                True, self.TEXTCOLOR
            )
            self.info_msg2 = self.small_ft.render('Press BACKSPACE to restart', True, self.TEXTCOLOR)

        elif ev.type == MyEvTypes.Defeat:
            print('defeat event received')
            if self._mod.folded:
                msg = 'Player folded.'
            else:
                msg = 'Defeat.'
            self.info_msg0 = self.ft.render(msg, True, self.TEXTCOLOR)
            result = ev.loss
            if self._mod.folded:
                self.info_msg1 = self.small_ft.render(f"You've lost {result}$", True, self.TEXTCOLOR)
            else:
                infoh_dealer = self._mod.dealer_vhand.description
                infoh_player = self._mod.player_vhand.description
                self.info_msg1 = self.small_ft.render(
                    f"Player: {infoh_player}; Dealer: {infoh_dealer}; You've lost {result}$", True, self.TEXTCOLOR
                )
            self.info_msg2 = self.small_ft.render('Press BACKSPACE to restart', True, self.TEXTCOLOR)

    @staticmethod
    def centerblit(refscr, surf, p):
        w, h = surf.get_size()
        refscr.blit(surf, (p[0]-w//2, p[1]-h//2))

    def _paint(self, scr):
        scr.blit(self.bg, (0, 0))

        # ---------- draw visible or hidden cards ---------
        if self._mod.stage == UthModel.INIT_ST_CODE:
            # draw hidden cards' back, at adhoc location
            for loc in ('dealer1', 'dealer2', 'player1', 'player2'):
                UthView.centerblit(scr, self.card_back_img, CARD_SLOTS_POS[loc])

        if self._mod.stage >= UthModel.DISCOV_ST_CODE:  # cards revealed
            # draw hidden cards' back, at adhoc location
            for k in range(1, 3+1):
                UthView.centerblit(scr, self.card_back_img, CARD_SLOTS_POS['flop'+str(k)])

            for loc in ('dealer1', 'dealer2'):
                UthView.centerblit(scr, self.card_back_img, CARD_SLOTS_POS[loc])
            for k, c in enumerate(self._mod.player_hand):
                slotname = 'player'+str(k+1)
                UthView.centerblit(scr, self.card_images[c.code], CARD_SLOTS_POS[slotname])

        if self._mod.stage >= UthModel.FLOP_ST_CODE:
            # draw hidden cards' back, at adhoc location
            for loc in ('turn', 'river'):
                UthView.centerblit(scr, self.card_back_img, CARD_SLOTS_POS[loc])
            for k, c in enumerate(self._mod.flop_cards):
                slotname = 'flop'+str(k+1)
                UthView.centerblit(scr, self.card_images[c.code], CARD_SLOTS_POS[slotname])

        if self._mod.stage >= UthModel.TR_ST_CODE:
            UthView.centerblit(scr, self.card_images[self. _mod.turnriver_cards[0].code], CARD_SLOTS_POS['turn'])
            UthView.centerblit(scr, self.card_images[self._mod.turnriver_cards[1].code], CARD_SLOTS_POS['river'])

        if self._mod.revealed['dealer1'] and self._mod.revealed['dealer2']:
            # show what the dealer has
            UthView.centerblit(scr, self.card_images[self._mod.dealer_hand[0].code], CARD_SLOTS_POS['dealer1'])
            UthView.centerblit(scr, self.card_images[self._mod.dealer_hand[1].code], CARD_SLOTS_POS['dealer2'])

        # -- draw amounts for ante, blind and the bet
        for info_e in self._mod.money_info:
            x, name = info_e
            lbl_surf = self.ft.render(f'{x}', True, self.TEXTCOLOR, self.BG_TEXTCOLOR)
            scr.blit(lbl_surf, CARD_SLOTS_POS[name])

        # -- draw chips & the total cash amount
        for k, v in enumerate((2, 5, 10, 20)):
            adhoc_spr = self.chip_spr[str(v)]
            if v == 2:
                adhoc_spr.rect.center = PLAYER_CHIPS['2b']
            scr.blit(adhoc_spr.image, adhoc_spr.rect.topleft)
        self.chip_spr['2'].rect.center = PLAYER_CHIPS['2a']
        scr.blit(self.chip_spr['2'].image, self.chip_spr['2'].rect.topleft)
        scr.blit(self.cash_etq, POS_CASH)

        # -- display all 3 prompt messages
        for rank, e in enumerate((self.info_msg0, self.info_msg1, self.info_msg2)):
            if e is not None:
                scr.blit(e, (24, 10+50*rank))
        kengi.flip()


# -----------------------------------------------------------------/
#              ******** CONTROLLER ********
# -----------------------------------------------------------------/
class UthCtrl(ReceiverObj):
    AUTOPLAY_DELAY = 0.8  # sec

    def __init__(self, model):
        super().__init__()
        self._mod = model
        self._last_t = None
        self.elapsed = 0

    def proc_event(self, ev, source):

        if ev.type == EngineEvTypes.LOGICUPDATE:
            if self._mod.autoplay_flag:
                elapsed = time.time() - self._last_t
                if elapsed > self.AUTOPLAY_DELAY:
                    self._mod.evolve_state()
                    self._last_t = time.time()

        elif ev.type == MyEvTypes.EndRoundRequested:
            self._mod.autoplay_flag = True
            self._mod.evolve_state()
            self._last_t = time.time()

        elif ev.type == pygame.KEYDOWN:  # -------- manage keyboard
            if ev.key == pygame.K_ESCAPE:
                self.pev(EngineEvTypes.GAMEENDS)

            if self._mod.autoplay_flag:
                return

            # backspace will be used to CHECK / FOLD
            if ev.key == pygame.K_BACKSPACE:
                self._mod.input_check()

            # enter will be used to select the regular BET option, x3, x2 or x1 depends on the stage
            elif ev.key == pygame.K_RETURN:
                # ignore non-valid case
                self._mod.input_bet(0)

            # case: at the beginning of the game the player can select the MEGA-BET x4 lets use space for that
            # we'll also use space to begin the game. State transition: init -> discov
            elif ev.key == pygame.K_SPACE:
                if self._mod.stage == UthModel.INIT_ST_CODE:
                    return
                if self._mod.stage != UthModel.DISCOV_ST_CODE:
                    return
                self._mod.input_bet(1)
