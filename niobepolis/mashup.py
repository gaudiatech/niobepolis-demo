
#import katagames_sdk as katasdk
#katasdk.bootstrap()
import katagames_engine as kengi
kengi.bootstrap_e()
#kengi = katasdk.kengi
import math
import re
import time
import json


# - global constants
WARP_BACK = [2, 'editor']
DEBUG = False
DEFAULT_SPAWN_LOC = [0, 16, 14]
DELAY_BEFORE_TP = 2.5  # sec

TRIG_LABEL_COLOR = kengi.pal.punk['flashypink'] # instead of (133, 5, 187)
TRIG_LABEL_FTSIZE = 16

the_future_game = None

GameStates = kengi.struct.enum(
    'Explore',
    'Poker'
)

# always try to keep your event number low: model->view or model->ctrl comms only
MyEvTypes = kengi.event.enum_ev_types(
    'MapChanges',  # contains new_map, gate_name

    # in Niobe Polis a portal can teleport you(tp) to another world
    'PortalActivates',  # contains portal_id

    'TerminalStarts',
    'SlotMachineStarts',

    # -----------------------
    #  related to poker
    # -----------------------
    'CashChanges',  # contains int "value"
    'StageChanges',
    'EndRoundRequested',
    'Victory',  # contains: amount
    'Tie',
    'Defeat'  # contains: loss
)

# - aliases
pygame = kengi.pygame
evmodule = kengi.event
CgmEvent = kengi.event.CgmEvent
CogObject = kengi.event.CogObj
IsoMapObject = kengi.isometric.model.IsometricMapObject
ReceiverObj = kengi.event.EventReceiver
EngineEvTypes = kengi.event.EngineEvTypes
BaseGameState = kengi.BaseGameState
Card = kengi.tabletop.StandardCard
PokerHand = kengi.tabletop.PokerHand
StandardCard = kengi.tabletop.StandardCard
find_best_ph = kengi.tabletop.find_best_ph
CardDeck = kengi.tabletop.CardDeck
animobs = kengi.demolib.animobs
dialogue = kengi.demolib.dialogue
pathfinding = kengi.demolib.pathfinding
IsoMap = kengi.isometric.model.IsometricMap

# global variables
gft = None
fps_show = False
main_map_path = 'neo_exterior.tmx'
conv_viewer = None
active_gui_overlay = False
current_path = None
current_tilemap = 0
maps = list()
map_viewer = None
isomap_player_entity = None
path_ctrl = None
screen = None
tilemap_height = tilemap_width = 0

# pr poker
alea_xx = lambda_hand = epic_hand = list()

clock = pygame.time.Clock()
mger = scr = None
lu_event = paint_event = None
keep_going = True


class GlVarsMockup:
    MAXFPS = 74

    PALIAS = {
        'greetings': 'assets/greetings.png',
        'tilefloor': 'assets/floor-tile.png',
        'gridsystem': 'assets/grid-system.png',
    }

    def __init__(self):
        self.cached_gamelist = list()
        self.interruption = None  # used to change cartridge
        self.keep_going = True  # if the game continues, or not
        self.cached_gamelist = None
        self.ref_vmstate = None
        self.assoc_portal_game = {}

    def set_portals(self, ref_li):
        self.assoc_portal_game.clear()
        for portal_id, cart_name in ref_li:
            self.assoc_portal_game[portal_id] = cart_name
        #print('-------- portals set: ---------')
        #print(self.assoc_portal_game)
        for entityobj in TriggerEntity.entities_for_portals.values():
            entityobj.refresh_label()


glvars = GlVarsMockup()


def _load_maps():
    global maps, tilemap_width, tilemap_height
    # could use the legacy mode, so map iso objects
    # use "type" attribute key instead of "class"
    # kengi.isometric.set_tiled_version('1.8')
    kengi.isometric.model.IsometricLayer.flag_csv = True
    maps = [
        IsoMap.load(['assets', ], 'city.tmj', OBJECT_CLASSES),
        None,
        IsoMap.load(['assets', ], 'small_map.tmj', OBJECT_CLASSES),
        IsoMap.load(['assets', ], 'casino.tmj', OBJECT_CLASSES)
    ]
    tilemap_width, tilemap_height = maps[0].width, maps[0].height


def _init_specific_stuff(refscr):
    global map_viewer, maps, isomap_player_entity

    _load_maps()
    # continue init.
    map_viewer = kengi.isometric.IsometricMapViewer(
        maps[0], refscr,
        up_scroll_key=pygame.K_UP, down_scroll_key=pygame.K_DOWN,
        left_scroll_key=pygame.K_LEFT, right_scroll_key=pygame.K_RIGHT
    )
    map_viewer.pc_cls = Character
    map_viewer.show_avatar = True
    map_viewer.set_av_anim_speed(11.77)

    # - add map entities
    if glvars.ref_vmstate and glvars.ref_vmstate.landing_spot:
        landing_loc = glvars.ref_vmstate.landing_spot
        print('drop player to alternative spot: ', landing_loc)
    else:
        print('drop player to default spawn location')
        landing_loc = DEFAULT_SPAWN_LOC  # default location

    isomap_player_entity = Character(landing_loc[1], landing_loc[2])

    # glvars.ref_vmstate.landing_spot = None

    for tm in maps:
        if tm is not None:
            list(tm.objectgroups.values())[0].contents.append(isomap_player_entity)
    map_viewer.set_focused_object(isomap_player_entity)
    # force: center on avatar op.
    isomap_player_entity.x += 0.5

    # tp to another map if its required
    if landing_loc[0] != 0:
        manually_move_player(*landing_loc)

    # the rest
    cursor_image = pygame.image.load("assets/half-floor-tile.png")
    cursor_image.set_colorkey((255, 0, 255))
    map_viewer.cursor = kengi.isometric.IsoCursor(0, 0, cursor_image, maps[0].layers[1])
    return map_viewer


# ---------------------- game entities
class Character(IsoMapObject):
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y
        self.surf = pygame.image.load("assets/avatar0.png") #.convert_alpha()
        self.offx = -8
        self.offy = -24
        self.flag_auth = False

    #def __call__(self, dest_surface, sx, sy, mymap):
        # [1]
        # mydest = self.ht.get_rect(midbottom=(sx, sy))
        # dest_surface.blit(self.ht, mydest)
    def __call__(self, dest_surface, sx, sy, mymap):
        # [v2]
        # mydest = self.surf.get_rect(midbottom=(sx + self.ox, sy + self.oy))

        # nb tom:
        # OK i will crop the img on purpose, to cancel the impact of a known BACKEND2 bug
        # (case: blit img -> (surf!=0) )
        dest_surface.blit(self.surf, (sx+self.offx, sy+self.offy), area=(0, 0, 15, 31))


class TriggerEntity(IsoMapObject):
    SPR_SHEET = None
    all_locations = dict()
    entities_for_portals = dict()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.drawingoffset = [-16, 0]

        cls = self.__class__
        cls.all_locations[(self.x, self.y)] = self
        if cls.SPR_SHEET is None:
            cls.SPR_SHEET = kengi.gfx.Spritesheet("assets/flashy-trigger.png")
            cls.SPR_SHEET.set_infos((32, 16))
            for k_elt in range(cls.SPR_SHEET.card):
                cls.SPR_SHEET[k_elt].set_colorkey('BLACK')  # so the alpha is respected in local ctx
        self.emitter = CogObject()
        # pr gerer anim
        # --
        self.frame = -1
        self.phase_thresh = 8
        self.phase = self.phase_thresh

        # if its a portal-bound trigger, (goto:portal)
        # we WILL also display the name of the game
        self.triggerft = self.lbl = None
        if self.properties['goto'] == 'portal':
            x = int(self.properties['ident'])
            self.__class__.entities_for_portals[x] = self

    def refresh_label(self):
        if self.properties['goto'] == 'portal':
            self.triggerft = pygame.font.Font(None, TRIG_LABEL_FTSIZE)
            x = self.properties['ident']
            if x in glvars.assoc_portal_game:
                game_name = glvars.assoc_portal_game[x]
            else:
                game_name = '%void%'
            self.lbl = self.triggerft.render(game_name, False, TRIG_LABEL_COLOR, kengi.pal.c64['blue'])
            self.txtoffset = [
                16,
                -4-5*self.lbl.get_height()
            ]
        else:
            self.triggerft = self.lbl = None

    @classmethod
    def by_location(cls, known_pos):
        return cls.all_locations[known_pos]

    def __call__(self, dest_surface, sx, sy, mymap):
        self.phase += 1
        if self.phase > self.phase_thresh:
            self.phase = 0
            self.frame = (self.frame + 1) % self.SPR_SHEET.card
        # --
        midbottom_p = (sx +self.drawingoffset[0], sy+self.drawingoffset[1])
        dest_surface.blit(
            self.SPR_SHEET[self.frame],
            midbottom_p  # like anchor=midbottom, but was manually computed
        )
        # if its a portal-bound trigger, (goto:portal)
        # we also display the name of the game
        if self.lbl:
            dest_surface.blit(
                self.lbl,
                (midbottom_p[0]+self.txtoffset[0], midbottom_p[1]+self.txtoffset[1])
            )

    def bump(self):
        # prevent invisble triggers:
        if not self.visible:
            return

        # let us use the event manager, so we achieve low-coupling
        if self.goto == 'terminal':
            self.emitter.pev(MyEvTypes.TerminalStarts)

        elif self.goto == 'portal':
            landing_cell = [int(self.cmap), self.x, self.y]
            self.emitter.pev(MyEvTypes.PortalActivates, portal_id=self.ident, portal_lcell=landing_cell)
            print('portal activates ', self.ident)

        elif self.goto == 'npc':
            self.properties["conversation"] = self.ident + '.json'
            with open("assets/" + self.properties["conversation"], 'r') as fconv:
                myconvo = dialogue.Offer.load_jsondata(fconv.read())
                self.emitter.pev(
                    EngineEvTypes.CONVSTARTS, convo_obj=myconvo, portrait=self.properties.get("portrait")
                )

        elif self.goto == 'map':  # TODO can we use: dest_x, dest_y instead of dest_door?
            dest_map = int(self.properties.get("dest_map", 0))
            dest_door = self.properties.get("dest_door")
            # let us use the event manager, so we achieve low-coupling
            self.emitter.pev(MyEvTypes.MapChanges, new_map=dest_map, gate_name=dest_door)


class GlowingPortal(IsoMapObject):
    PORTAL_SPR_SHEET = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.drawoffset = [-32, -48]
        self.emitter = CogObject()
        cls = self.__class__
        if cls.PORTAL_SPR_SHEET is None:
            sprsheet_obj = kengi.gfx.Spritesheet("assets/portalSF.png")
            cls.PORTAL_SPR_SHEET = sprsheet_obj
            cls.PORTAL_SPR_SHEET.set_infos((64, 64))
            for k_elt in range(cls.PORTAL_SPR_SHEET.card):
                cls.PORTAL_SPR_SHEET[k_elt].set_colorkey('BLACK')  # so the alpha is respected in local ctx

        # animated spr
        self.frame = -1
        self.phase_thresh = 14
        self.phase = self.phase_thresh

    def __call__(self, dest_surface, sx, sy, mymap):
        # anim {
        self.phase += 1
        if self.phase > self.phase_thresh:
            self.phase = 0
            self.frame = (self.frame + 1) % self.PORTAL_SPR_SHEET.card
        # } anim done
        dest_surface.blit(
            self.PORTAL_SPR_SHEET[self.frame],
            (sx + self.drawoffset[0], sy + self.drawoffset[1])  # anchor=midbottom -> it was manually computed
        )


class SlotMachine(kengi.isometric.model.IsometricMapObject):
    def bump(self):
        # Call this method when the PC bumps into this terminal.
        evmodule.EventManager.instance().post(
            CgmEvent(MyEvTypes.SlotMachineStarts)
        )


def manually_move_player(new_map, new_posx, new_posy):
    global current_path, current_tilemap, isomap_player_entity, map_viewer
    current_path = None
    current_tilemap = new_map
    isomap_player_entity.x, isomap_player_entity.y = new_posx + 0.5, new_posy + 0.5
    map_viewer.switch_map(maps[current_tilemap])


OBJECT_CLASSES = {
    "GlowingPortal": GlowingPortal,
    "trigger": TriggerEntity,
    "SlotMachine": SlotMachine
}


# --------------------------------------------------
#   declarations: IN GAME console
# --------------------------------------------------
ingame_console = None
to_edit = None
leaving_niobe = False

# vars used by the stellar interface /the katagames API
browser_wait = False
need_to_format_pubkey = False

# extra parsing func (for the ig console), lets you call func like: name(arg1,...,argn)
re_function = re.compile(r'(?P<name>\S+)(?P<params>[\(].*[\)])')

CON_FONT_COLOR = (255, 0, 0)  # for now, changing font color doesnt work due to the NEW ft system being incomplete


def build_console(screen):
    global ingame_console
    screensize = screen.get_size()
    ingame_console = kengi.console.CustomConsole(
        screen,
        (0, 0, screensize[0], int(0.9 * screensize[1])),  # takes up 90% of the scr height
        functions=console_functions_listing,
        key_calls={},
        vari={"A": 100, "B": 200, "C": 300},
        syntax={re_function: console_func},
        fontobj=kengi.gui.ImgBasedFont('assets/niobe_font.png', CON_FONT_COLOR)  # the NEW ft system
    )
    ingame_console.set_motd('-Niobe Polis CONSOLE rdy-\n type "help" if needed')


# --------- ignore this code, its just to un-break things
# after removing the dependency to KataSDK
class vStateMockup:  # temporary add-on to the may demo version
    def __init__(self):
        self.gamelist = ['nothing', ]

    def gamelist_func(self):
        return []


def console_func(console, match):
    funcname = match.group("name")
    if funcname in console.func_calls:
        func = console.func_calls[funcname]
    else:
        console.output('unknown function ' + funcname)
        return
    params = console.convert_token(match.group("params"))
    print(funcname, params)
    if not isinstance(params, tuple):
        params = [params]
    try:
        out = func(*params)
    except Exception as strerror:
        console.output(strerror)
    else:
        console.output(out)


# --------------- implem of console functions, docstrings are used for help ------------------START
def _callback_display_stellarinfo(x):
    global browser_wait, need_to_format_pubkey
    browser_wait = False
    if need_to_format_pubkey:
        need_to_format_pubkey = False

        def _chunkstring(string, length):
            return (string[0 + i:length + i] for i in range(0, len(string), length))

        tlines = list(_chunkstring(x, 4))
        dlines = list()
        cpt = 0
        while len(tlines):
            cpt += 1
            if cpt < 4:
                x = tlines.pop(0) + ' ' + tlines.pop(0) + ' ' + tlines.pop(0) + ' ' + tlines.pop(0)
            else:
                x = tlines.pop(0) + ' ' + tlines.pop(0)
            dlines.append(x)
        for one_line in dlines:
            ingame_console.output(one_line)
    else:
        ingame_console.output(x)


def _callback_use_pubkey_to_auth(x):
    global browser_wait, ingame_console
    browser_wait = False
    given_pubkey = x
    errmsg = 'Err: invalid given_pubkey:', given_pubkey
    if len(given_pubkey) > 24 and given_pubkey[0] == 'G':
        c = katasdk.get_pyconnector()
        if not c.set_pubkey(given_pubkey, ingame_console):
            ingame_console.output(errmsg)
            return

        res_auth = c.auth_via_pubkey(given_pubkey)
        if res_auth[0]:
            ingame_console.output('Auth via Stellar acc OK. Welcome {}'.format(res_auth[1]))
            if not isomap_player_entity.flag_auth:
                isomap_player_entity.surf = pygame.image.load('assets/avatar.png')
        else:
            ingame_console.output('Auth via Stellar acc Fails (result:{})'.format(res_auth))
    else:
        ingame_console.output(errmsg)


def gamelist():
    """
    List ALL games. Use: gamelist
    :return:
    """
    if glvars.cached_gamelist:
        ret_txt = ''
        for elt in glvars.cached_gamelist:
            li = elt[0]
            if elt[1]:
                li += ' [r.-o]'
            ret_txt += li + '\n'
        return ret_txt
    return 'cannot get the list now'


def wealth():
    """
    displays the wealth of the player (according to server)
    :return:
    """
    c = katasdk.get_pyconnector()
    if c.is_logged:
        return "you own {:,d} CR".format(math.floor(c.get_user_balance()))
    else:
        return 'cannot read the balance now, use auth first!'


def get_n_sign_xdr(amount):
    """
    Deposit aqua tokens to get the same amount of credits. Use: deposit amount
    :param amount:
    """
    c = katasdk.get_pyconnector()
    if not c.is_logged:
        return 'you must be logged before you can deposit!'
    else:
        if int(amount) < 1:
            return 'error: invalid amount'
        else:
            return c.request_token_deposit(int(amount), ingame_console)


# -----------
# on commence pareil que pr la fonction au-dessus
# -----------
def request_aqua_payment(amount):
    """exchange a given amount of credits for aqua tokens"""
    c = katasdk.get_pyconnector()
    if not c.is_logged:
        return 'you must be logged before you can withdraw!'
    else:
        if int(amount) < 1:
            return 'error: invalid amount'
        else:
            return c.request_withdraw(int(amount))


def gamelist2():
    """
    List only r.-o games. Use: gamelist
    :return:
    """
    if glvars.cached_gamelist:
        ret_txt = ''
        for elt in glvars.cached_gamelist:
            li = elt[0]
            if elt[1]:
                li += ' [r.-o]'
                ret_txt += li + '\n'
        return ret_txt
    return 'cannot get the list now'


def stellar_console_func(subcmd):
    """
    Stellar bridge. Use: stellar CMD; CMD in {test,network,pubkey}
    """
    global browser_wait, need_to_format_pubkey
    stellar_bridge = katasdk.stellar
    if 'test' == subcmd:
        ret = stellar_bridge.test_connection()

        def _proc_stellartest_result(x, consol):
            consol.output("Freighter plugin's ready!" if bool(x) else "Freighter plugin not available.")

        _proc_stellartest_result(ret, ingame_console)

    elif 'network' == subcmd:
        browser_wait = True
        stellar_bridge.get_network(_callback_display_stellarinfo)

    elif 'pubkey' == subcmd:
        browser_wait = True
        need_to_format_pubkey = True
        stellar_bridge.get_pkey(_callback_display_stellarinfo)
    else:
        return 'error: stellar cmd, cf. help stellar'


def tp(gametag):
    """
    Teleport to another world. Use: tp gametag
    :param gametag:
    :return:
    """
    # check if it exists
    if not katasdk.get_vmstate().has_game(gametag):
        return 'game not found!'
    else:
        glvars.interruption = [2, gametag]
    return 'teleporting...'


def add(a, b):
    """
    Basic addition op! Use: add a b
    """
    return a + b


def mul(a, b):
    """
    Basic multiplication op! Use: mul a b
    """
    y = float(a) * float(b)
    if round(y) == y:
        return int(y)
    return y


def size():
    """
    Info about screen dimension. Use: size
    """
    w, h, = kengi.get_surface().get_size()
    return str(w) + ' ' + str(h)


def cedit(cname):  # -------------------- experimental ----------------
    """
    Edit cartridge code. Use: edit cartname
    """

    def _cedit_creation(saisie):
        global to_edit
        if saisie == 'yes':
            print('file created: ', cname)
            to_edit = cname

    def _cedit_readonly(saisie):
        global to_edit
        if saisie == 'yes':
            print('read-only mode open: ', cname)
            to_edit = cname

    global to_edit
    if not katasdk.get_vmstate().has_game(cname):
        ingame_console.cb_func = _cedit_creation
        return 'cartridge doesnt exist, create it? yes/no'
    if katasdk.get_vmstate().has_ro_flag(cname):
        ingame_console.cb_func = _cedit_readonly
        return 'r.-o cartridge: U wont be able to save, view code anyway? yes/no'
    else:
        to_edit = cname
        return f'editor opens {cname}...'


def erase(cname):
    """
    Erase all source-code in a cartridge (set things to default). Use: erase cartName
    :param cname:
    :return:
    """
    # - handling case read-only stuff!
    if not katasdk.get_vmstate().has_game(cname):
        return 'Not found'
    if katasdk.get_vmstate().has_ro_flag(cname):
        return 'Rejected: r.-o /protected cartridge'
    katasdk.get_vmstate().persist_functions['erase_cart'](cname)
    return 'Reset op. OK'


def clonec(cname1, cname2):
    """
    Create a cartridge by cloning an existing cartridge. Use: clone cartNamA cartNamB
    """
    global ingame_console

    # def _clonec_overwrite(saisie):
    #     if saisie == 'yes':
    #         katasdk.get_vmstate().clone_cart(cname1, cname2)
    #         ingame_console.output('cloning done.')
    vs = katasdk.get_vmstate()
    if not vs.has_game(cname1):
        return 'Source cartridge Not found'
    if vs.has_game(cname2):
        return 'Rejected: target already exists'
        # if vs.has_ro_flag(cname2):
        #     return 'Rejected: target cartridge is r.-o /protected'
        # else:
        #     ingame_console.cb_func = _clonec_overwrite
        #     return 'Target cartridge already exists, overwrite? yes/no'
    vs.clone_cart(cname1, cname2)
    return 'cloning done.'


def dohalt():
    """
    Exit app. Use: halt
    """
    global keep_going
    keep_going = False
    kengi.event.EventManager.instance().post(CgmEvent(EngineEvTypes.GAMEENDS))
    return 'quit niobe requested.'


def signup_cmd():
    """
    Opens a browser tab so the user can Sign Up(create new account)
    :return:
    """
    global glvars
    glvars.ref_vmstate.proc_signup()
    return 'tab opened for sign up!'


def opentab(arg):
    """
    Opens an URL in a new tab of the browser. Usage: opentab URL
    :param arg: what url to open?
    :return:
    """
    if not webctx():
        return 'this does nothing in local ctx'
    global glvars
    glvars.ref_vmstate.open_tab(arg)
    return 'tab open - ok'


def regular_auth_func(name, plain_pwd):
    """
    send an auth request to the game server
    :param name:
    :param plain_pwd:
    :return:
    """
    c = katasdk.get_pyconnector()
    res_auth = c.try_auth_server(name, plain_pwd)
    if not res_auth:
        return False

    if not isomap_player_entity.flag_auth:
        isomap_player_entity.flag_auth = True
        isomap_player_entity.surf = pygame.image.load('assets/avatar.png')
    return res_auth


def request_auth_via_f():
    global browser_wait
    """
    send an auth request using the FREIGHTER plug-in
    :param pubkey:
    :return:
    """
    # lance la procédure en async
    browser_wait = True
    stellar_bridge = katasdk.stellar
    stellar_bridge.get_pkey(_callback_use_pubkey_to_auth)  # .auth_via_pubkey itself will be called by callback func
    return 'processing...'


# IMPORTANT REMINDER:
# functions listed below need to RETURN smth, plus they need to have 1 line of docstring,
# including a "Use: xxx aa bb" part at the end
console_functions_listing = {
    # "help", "clear", "echo" are all built-in within the IgConsole object
    # sept22 -> commented junk commands
    #"add": add,
    "auth": regular_auth_func,
    "fauth": request_auth_via_f,
    "balance": wealth,
    "clone": clonec,
    "edit": cedit,
    "erase": erase,
    "gamelist": gamelist,
    #"mul": mul,
    #"opentab": opentab,
    #"scrsize": size,
    "templates": gamelist2,  # it's like gamelist but shows only read-only games
    "tp": tp,

    "signup": signup_cmd,
    # related to the crypto bridge
    "deposit": get_n_sign_xdr,
    "withdraw": request_aqua_payment,
}


def webctx():
    return False #katasdk.runs_in_web()


if not webctx():
    console_functions_listing["halt"] = dohalt
else:
    console_functions_listing["stellar"] = stellar_console_func


class ExtraLayerView(ReceiverObj):
    def __init__(self, cons):
        super().__init__()
        self.console = cons
        self.img_fps = None
        self.ft = pygame.font.Font(None, 17)
        self.countdown = None
        self.last_t = None

    def proc_event(self, ev, source=None):
        global clock, the_future_game

        if ev.type == EngineEvTypes.LOGICUPDATE:
            # --- showing fps
            if the_future_game:
                if self.countdown:
                    elapsed = ev.curr_t-self.last_t
                    self.countdown -= elapsed
                    if not(self.countdown>0):
                        glvars.interruption = [2, the_future_game]
                else:
                    self.countdown = DELAY_BEFORE_TP
                self.last_t = ev.curr_t

        elif ev.type == EngineEvTypes.PAINT:
            global ingame_console
            # ev.screen.fill('navyblue')
            try:
                self.console.draw()  # console draw
            except ValueError:
                ingame_console = None
                build_console(kengi.get_surface())
                self.console = ingame_console
                self.console.output('A console crash occured, sorry')
                # self.console = kengi.console.CustomConsole()
            if self.img_fps:
                ev.screen.blit(self.img_fps, (4, 4))


class ExtraGuiLayerCtrl(ReceiverObj):
    def __init__(self, ):
        super().__init__()
        self.mode = 'legacy'  # you can set this var to 'modern' to use Terminal events instead of F1 to open

    def proc_event(self, ev, source=None):
        global ingame_console, active_gui_overlay

        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                pass
            else:
            # ----------------------------------
            #  uncomment this if you need to refine the megaoptim stuff
            # ----------------------------------
            # elif ev.key == pygame.K_RIGHT:
            #     kengi.isometric.IsometricMapViewer.FLOOR_MAN_OFFSET[0][0] -= 1
            #     print(kengi.isometric.IsometricMapViewer.FLOOR_MAN_OFFSET)
            # elif ev.key == pygame.K_LEFT:
            #     kengi.isometric.IsometricMapViewer.FLOOR_MAN_OFFSET[0][0] += 1
            #     print(kengi.isometric.IsometricMapViewer.FLOOR_MAN_OFFSET)
            # elif ev.key == pygame.K_UP:
            #     kengi.isometric.IsometricMapViewer.FLOOR_MAN_OFFSET[0][1] += 1
            #     print(kengi.isometric.IsometricMapViewer.FLOOR_MAN_OFFSET)
            # elif ev.key == pygame.K_DOWN:
            #     kengi.isometric.IsometricMapViewer.FLOOR_MAN_OFFSET[0][1] -= 1
            #     print(kengi.isometric.IsometricMapViewer.FLOOR_MAN_OFFSET)

            # elif ev.key == pygame.K_F4:
            #     game_exit(None)
            #     game_enter(glvars.ref_vmstate)
                ingame_console.process_input([ev, ])  # ne sais pas cmt gerer ca autrement

        elif ev.type == MyEvTypes.TerminalStarts:
            active_gui_overlay = True
            ingame_console.activate()

        elif ev.type == MyEvTypes.SlotMachineStarts:
            self.pev(EngineEvTypes.PUSHSTATE, state_ident=GameStates.Poker)

        elif ev.type == EngineEvTypes.LOGICUPDATE:
            if to_edit is not None:
                glvars.ref_vmstate.cedit_arg = to_edit  # commit name of the file to be edited to VMstate
                glvars.interruption = WARP_BACK

            if leaving_niobe:
                glvars.interruption = [1, None]


# ------------- util class for movement -------------
class MovementPath:
    def __init__(self, mapob, dest, mymap):
        self.mob_entity = mapob
        self.dest = dest
        print(dest)
        # self.goal = None
        self.mymap = mymap
        blocked_tiles = set()
        # obgroup = list(mymap.objectgroups.values())[0]
        # for ob in obgroup.contents:
        #     if ob is not mapob:
        #         blocked_tiles.add((ob.x, ob.y))
        #         if self.pos_to_index((ob.x, ob.y)) == self.pos_to_index(dest):
        #             self.goal = ob
        a2 = self.pos_to_index((mapob.x, mapob.y))
        a3 = self.pos_to_index(dest)
        print('astar creation: args a2, a3 are:', a2, a3)

        self.path = pathfinding.AStarPath(
            mymap, a2, a3, self.tile_is_blocked,
            mymap.clamp_pos_int,
            blocked_tiles=blocked_tiles,
            wrap_x=mymap.wrap_x, wrap_y=mymap.wrap_y
        )

        if self.path.results:
            self.path.results.pop(0)
            self.all_the_way_to_dest = not (
                    dest in blocked_tiles or self.tile_is_blocked(mymap, *self.pos_to_index(dest))
            )
            if not self.all_the_way_to_dest:
                self.path.results.pop(-1)
        else:
            print("No path found!")

        self.movement_type = None

    @staticmethod
    def pos_to_index(pos):
        def spefilter(val):
            xinf, xmid, xsup = math.floor(val), math.floor(val) + 0.5, math.ceil(val)
            a, b, c = abs(val - xinf), abs(val - xmid), abs(val - xsup)
            if c < a:
                if c < b:
                    rez = xsup
                else:
                    rez = xmid
            else:
                if a < b:
                    rez = xinf
                else:
                    rez = xmid
            return rez

        return spefilter(pos[0]), spefilter(pos[1])

    @staticmethod
    def tile_is_blocked(mymap, x, y):
        return mymap.tile_is_blocked(x, y)

    def __call__(self):
        # called once per update; returns True when the action is completed.
        if self.movement_type:
            self.movement_type.update()
            if self.movement_type.needs_deletion:
                self.movement_type = None

        if not self.movement_type:
            if self.path.results:
                if len(self.path.results) == 1 and self.all_the_way_to_dest:
                    nx, ny = self.dest
                    self.path.results = []
                else:
                    nx, ny = self.path.results.pop(0)
                # De-clamp the nugoal coordinates.
                nx = min([nx, nx - self.mymap.width, nx + self.mymap.width], key=lambda x: abs(x - self.mob_entity.x))
                ny = min([ny, ny - self.mymap.height, ny + self.mymap.height], key=lambda y: abs(y - self.mob_entity.y))
                self.movement_type = animobs.MoveModel(
                    self.mob_entity, dest=(nx, ny), speed=0.25
                )
            else:
                return True


# --------------------------------------------
# Define controllers etc
# --------------------------------------------
class BasicCtrl(kengi.event.EventReceiver):
    def proc_event(self, event, source):
        global map_viewer, isomap_player_entity, current_tilemap, current_path, conv_viewer
        global fps_show, active_gui_overlay, the_future_game

        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP, pygame.MOUSEBUTTONUP):
            if active_gui_overlay:
                pass  # block all movement when the conversation is active
            else:
                cursor = map_viewer.cursor
                if cursor:
                    cursor.update(map_viewer, event)
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    # TODO: There are some glitches in the movement system, when the player character will not move to
                    # a tile that has been clicked. It generally happens with tiles that are adjacent to the PC's
                    # current position, but it doesn't happen all the time. I will look into this later.
                    current_path = MovementPath(isomap_player_entity, map_viewer.cursor.get_pos(),
                                                maps[current_tilemap])
                    print('movement path has been set')

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F4:
                fps_show = not fps_show

            if event.key == pygame.K_F3:
                map_viewer.show_avatar = not map_viewer.show_avatar
                print(f'show avatar? {map_viewer.show_avatar}')

            elif event.key == pygame.K_ESCAPE:
                if ingame_console.active:
                    ingame_console.desactivate()
                    active_gui_overlay = False
                elif active_gui_overlay:  # means it was an active convo
                    self.pev(EngineEvTypes.CONVENDS)  # stop convo

            elif event.key == pygame.K_F2:
                self.pev(MyEvTypes.TerminalStarts)

            elif event.key == pygame.K_TAB and current_tilemap in (0, 1):
                current_tilemap = 1 - current_tilemap
                map_viewer.switch_map(maps[current_tilemap])
                isomap_player_entity.x = 10
                isomap_player_entity.y = 10
            elif event.key == pygame.K_F1:
                print(map_viewer.cursor.get_pos())

        elif event.type == MyEvTypes.MapChanges:
            if hasattr(event, 'new_map'):
                print(event.gate_name)
                new_gate = maps[event.new_map].get_object_by_name(event.gate_name)
                manually_move_player(event.new_map, new_gate.x, new_gate.y)

        elif event.type == MyEvTypes.PortalActivates:
            if event.portal_id in glvars.assoc_portal_game:
                the_future_game = glvars.assoc_portal_game[event.portal_id]
                # save data
                glvars.ref_vmstate.landing_spot = event.portal_lcell

                # launch the TP fancy anim!
                map_viewer.show_avatar = False
                # fine tune gfx
                map_viewer.anim_av_offset[0] = -16
                map_viewer.anim_av_offset[1] = -20

                s_obj = kengi.gfx.Spritesheet("assets/tpanim1.png")
                s_obj.set_infos((32, 32))
                for k_elt in range(s_obj.card):
                    s_obj[k_elt].set_colorkey('BLACK')  # respect alpha in local ctx...
                map_viewer.extra_anim = s_obj

                print('portal has been turned on! lcell=', event.portal_lcell)

        elif event.type == EngineEvTypes.CONVSTARTS:
            active_gui_overlay = True
            dialogue.ConversationView.BG_COL = '#352879'  # replace with a purple that matches portraits

            conv_viewer = dialogue.ConversationView(
                event.convo_obj, None, 16, "assets/" + event.portrait
            )
            conv_viewer.primitive_style = True  # goal: speed up rendering
            conv_viewer.turn_on()


class PathCtrl(kengi.event.EventReceiver):
    def __init__(self):
        super().__init__()

    def proc_event(self, event, source):
        global current_path, conv_viewer, active_gui_overlay

        if event.type == EngineEvTypes.LOGICUPDATE:
            if current_path is not None:
                mvt_ended = current_path()
                if mvt_ended:
                    current_path = None
                    # TODO call .pev if the player steps on a trigger, at the end of his travel.
                    needle = (isomap_player_entity.x, isomap_player_entity.y)
                    print('finpath - ', needle)
                    if needle in TriggerEntity.all_locations:
                        TriggerEntity.by_location(needle).bump()

        elif event.type == EngineEvTypes.CONVENDS:
            active_gui_overlay = False  # unlock player movements
            if conv_viewer.active:
                conv_viewer.turn_off()


class ExploreState(BaseGameState):
    def __init__(self, gs_id):
        super().__init__(gs_id)
        self.m = self.explore_view = self.v2 = self.c = None

    def enter(self):
        global ingame_console
        the_screen = kengi.get_surface()

        self.explore_view = _init_specific_stuff(the_screen)
        # self.explore_view.block_wallpaper = True
        self.explore_view.turn_on()

        # GameEventLogger().turn_on()
        PathCtrl().turn_on()
        BasicCtrl().turn_on()

        build_console(the_screen)
        ingame_cons = ingame_console
        self.v2 = ExtraLayerView(ingame_cons)
        self.v2.turn_on()

        # self.m = UthModel()
        # self.v = UthView(self.m)
        # self.v.turn_on()
        tmp = ExtraGuiLayerCtrl()
        tmp.mode = 'modern'
        self.c = tmp
        self.c.turn_on()

    def pause(self):
        self.c.turn_off()
        self.v2.turn_off()
        self.explore_view.turn_off()

    def resume(self):
        # kengi.screen_param(MONMODE, paintev=paint_event)
        # self.v.screen = kengi.get_surface()  # manually update the ref on vscreen
        self.explore_view.turn_on()
        self.v2.turn_on()
        self.c.turn_on()

    def release(self):
        self.c.turn_off()
        self.c = None
        self.explore_view = None


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
        self.pev(MyEvTypes.Defeat, loss=-1 * (self.ante + self.blind + self.playcost))


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
BACKGROUND_IMG_PATH = 'assets/pokerbackground3.png'
CARD_SIZE_PX = (69, 101)  # (82, 120)
CHIP_SIZE_PX = (40, 40)  # (62, 62)
POS_CASH = (1192 / 2, 1007 / 2)
CARD_SLOTS_POS = {  # coords in pixel so cards/chips & BG image do match; cards img need an anchor at the middle.
    'dealer1': (140, 48),
    'dealer2': (140 + 40, 48),

    'player1': (140, 206),
    'player2': (140 + 40, 206),

    'flop3': (238 - 40 * 2, 115),
    'flop2': (238 - 40 * 1, 115),
    'flop1': (238, 115),

    'river': (110 - 40, 115),
    'turn': (110, 115),

    'ante': (935 / 3, 757 / 3),
    'bet': (935 / 3, 850 / 3),
    'blind': (1040 / 3, 757 / 3),

    'raise1': (955 / 3, 870 / 3),
    'raise2': (961 / 3, 871 / 3),
    'raise3': (967 / 3, 872 / 3),
    'raise4': (973 / 3, 873 / 3),
    'raise5': (980 / 3, 875 / 3),
    'raise6': (986 / 3, 876 / 3)
}
PLAYER_CHIPS = {
    '2a': (825 / 2, 1000 / 2),
    '2b': (905 / 2, 1000 / 2),
    '5': (985 / 2, 1000 / 2),
    '10': (1065 / 2, 1000 / 2),
    '20': (1145 / 2, 1000 / 2)
}


class UthView(ReceiverObj):
    TEXTCOLOR = (5, 58, 7)
    BG_TEXTCOLOR = (133, 133, 133)
    ASK_SELECTION_MSG = 'SELECT ONE OPTION: '

    def __init__(self, model):
        super().__init__()
        self.bg = None
        self._my_assets = dict()
        self.chip_spr = dict()
        self._assets_rdy = False
        self._mod = model
        self.ft = pygame.font.Font(None, 34)
        self.small_ft = pygame.font.Font(None, 21)
        self.info_msg0 = None
        self.info_msg1 = None  # will be used to tell the player what he/she has to do!
        self.info_msg2 = None
        txt = str(self._mod.cash) + '$ '
        self.cash_etq = self.ft.render(txt, True, self.TEXTCOLOR, self.BG_TEXTCOLOR)  # draw cash amount

    def _load_assets(self):
        self.bg = pygame.image.load(BACKGROUND_IMG_PATH)
        spr_sheet = kengi.gfx.JsonBasedSprSheet('assets/pxart-french-cards')
        self._my_assets['card_back'] = spr_sheet[
            'back-blue.png']  # pygame.transform.scale(spr_sheet['back-of-card.png'], CARD_SIZE_PX)
        for card_cod in StandardCard.all_card_codes():
            y = PokerHand.adhoc_mapping(card_cod[0]).lstrip('0') + card_cod[1].upper()  # convert card code to path
            self._my_assets[card_cod] = spr_sheet[
                f'{y}.png']  # pygame.transform.scale(spr_sheet[f'{y}.png'], CARD_SIZE_PX)
        spr_sheet2 = kengi.gfx.JsonBasedSprSheet('assets/pokerchips')
        for chip_val_info in ('2a', '2b', '5', '10', '20'):
            y = {
                '2a': 'chip02.png',
                '2b': 'chip02.png',
                '5': 'chip05.png',
                '10': 'chip10.png',
                '20': 'chip20.png'
            }[chip_val_info]  # adapt filename
            tempimg = spr_sheet2[y]  # pygame.transform.scale(spr_sheet2[y], CHIP_SIZE_PX)
            # tempimg.set_colorkey((255, 0, 255))
            spr = pygame.sprite.Sprite()
            spr.image = tempimg
            spr.rect = spr.image.get_rect()
            spr.rect.center = PLAYER_CHIPS[chip_val_info]
            self.chip_spr['2' if chip_val_info in ('2a', '2b') else chip_val_info] = spr
        self._assets_rdy = True

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
        refscr.blit(surf, (p[0] - w // 2, p[1] - h // 2))

    def _paint(self, refscr):
        refscr.blit(self.bg, (0, 0))
        cardback = self._my_assets['card_back']

        # ---------- draw visible or hidden cards ---------
        if self._mod.stage == UthModel.INIT_ST_CODE:
            # draw hidden cards' back, at adhoc location
            for loc in ('dealer1', 'dealer2', 'player1', 'player2'):
                UthView.centerblit(scr, cardback, CARD_SLOTS_POS[loc])

        if self._mod.stage >= UthModel.DISCOV_ST_CODE:  # cards revealed
            # draw hidden cards' back, at adhoc location
            for k in range(1, 3 + 1):
                UthView.centerblit(scr, cardback, CARD_SLOTS_POS['flop' + str(k)])

            for loc in ('dealer1', 'dealer2'):
                UthView.centerblit(scr, cardback, CARD_SLOTS_POS[loc])
            for k, c in enumerate(self._mod.player_hand):
                slotname = 'player' + str(k + 1)
                UthView.centerblit(scr, self._my_assets[c.code], CARD_SLOTS_POS[slotname])

        if self._mod.stage >= UthModel.FLOP_ST_CODE:
            # draw hidden cards' back, at adhoc location
            for loc in ('turn', 'river'):
                UthView.centerblit(scr, cardback, CARD_SLOTS_POS[loc])
            for k, c in enumerate(self._mod.flop_cards):
                slotname = 'flop' + str(k + 1)
                UthView.centerblit(scr, self._my_assets[c.code], CARD_SLOTS_POS[slotname])

        if self._mod.stage >= UthModel.TR_ST_CODE:
            UthView.centerblit(scr, self._my_assets[self._mod.turnriver_cards[0].code], CARD_SLOTS_POS['turn'])
            UthView.centerblit(scr, self._my_assets[self._mod.turnriver_cards[1].code], CARD_SLOTS_POS['river'])

        if self._mod.revealed['dealer1'] and self._mod.revealed['dealer2']:
            # show what the dealer has
            UthView.centerblit(scr, self._my_assets[self._mod.dealer_hand[0].code], CARD_SLOTS_POS['dealer1'])
            UthView.centerblit(scr, self._my_assets[self._mod.dealer_hand[1].code], CARD_SLOTS_POS['dealer2'])

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
                scr.blit(e, (24, 10 + 50 * rank))


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
        self.recent_date = None

    def proc_event(self, ev, source):

        if ev.type == EngineEvTypes.LOGICUPDATE:
            self.recent_date = ev.curr_t
            if self._mod.autoplay_flag:
                elapsed = ev.curr_t - self._last_t
                if elapsed > self.AUTOPLAY_DELAY:
                    self._mod.evolve_state()
                    self._last_t = ev.curr_t

        elif ev.type == MyEvTypes.EndRoundRequested:
            self._mod.autoplay_flag = True
            self._mod.evolve_state()
            self._last_t = self.recent_date

        elif ev.type == pygame.KEYDOWN:  # -------- manage keyboard
            if ev.key == pygame.K_ESCAPE:
                self.pev(EngineEvTypes.POPSTATE)

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


class PokerState(BaseGameState):
    def __init__(self, gs_id):
        super().__init__(gs_id)
        self.m = self.v = self.c = None

    def enter(self):
        # kengi.screen_param('hd', paintev=paint_event)
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


# -------------------------------
#  base functions for katasdk compatibility
# -------------------------------
# @katasdk.tag_gameenter
def game_enter(vmstate):
    global mger, scr, paint_event, lu_event, gft

    # bind vmstate to glvars, update glvars accordingly
    # bind vmstate to glvars, update glvars accordingly
    tmpportals = None
    if vmstate:
        glvars.ref_vmstate = vmstate
        print('* det gamelist xx *')
        glvars.cached_gamelist = vmstate.get_gamelist()
        glvars.ref_vmstate = vmstate
        tmpportals = vmstate.portals_func()
    else:
        print('----- running niobe without VM -------')

    kengi.init(3)
    IsoViewCls = kengi.isometric.IsometricMapViewer
    # enable mega-optim (pre-rendered floor)
    # + fine-tune offset to display the latest(august) VERY large city.png img...
    IsoViewCls.MEGAOPTIM = True
    IsoViewCls.FLOOR_MAN_OFFSET[0] = [1984, 95]

    mger = kengi.event.EventManager.instance()  # works only after a .init(...) operation
    mger.hard_reset()

    scr = kengi.get_surface()
    lu_event = CgmEvent(EngineEvTypes.LOGICUPDATE, curr_t=None)
    paint_event = CgmEvent(EngineEvTypes.PAINT, screen=scr)
    kengi.declare_states(
        GameStates,
        {
            GameStates.Explore: ExploreState,
            GameStates.Poker: PokerState
        },
        glvars
    )
    kengi.get_game_ctrl().turn_on()

    kengi.get_game_ctrl().init_state0()

    # IN CASE YOU DEBUG POKER ::
    # mger.post(CgmEvent(MyEvTypes.SlotMachineStarts))
    gft = pygame.font.Font(None, 18)

    if vmstate:
        glvars.set_portals(tmpportals)


# @katasdk.tag_gameupdate
def game_update(infot=None):
    global lu_event, paint_event, mger, keep_going
    # use the kengi event system
    lu_event.curr_t = infot
    mger.post(lu_event)
    mger.post(paint_event)
    mger.update()
    if not keep_going:
        glvars.interruption = [1, None]
    if glvars.interruption:
        print('game_update returns ', glvars.interruption)
        return glvars.interruption

    if fps_show:
        lbl = gft.render('{:.2f}'.format(clock.get_fps()), 0, (0,0,0), (233, 233, 200))
        scr.blit(lbl, (4, 4))

    kengi.flip()
    if (not webctx()) and glvars.MAXFPS:
        clock.tick(glvars.MAXFPS)
    else:
        clock.tick()


# @katasdk.tag_gameexit
def game_exit(vmstate):
    kengi.quit()


if __name__ == '__main__':
    game_enter(None)
    ret = None
    while (ret is None) or ret[0] != 1:
        ret = game_update(time.time())
    game_exit(None)
