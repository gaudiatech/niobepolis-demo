# ------------------------
# *UNSTABLE* ver. of niobepolis
# ------------------------
# remember to config your IDE so that
# the working dir is one level above the "niobepolis" folder!

import json

import random
import re
import time

import katagames_engine as kengi

kengi.bootstrap_e()
pygame = kengi.pygame


# --------- ignore this code, its just to un-break things
# after removing the dependency to KataSDK
class vStateMockup:  # temporary add-on to the may demo version
    def __init__(self):
        self.gamelist = ['nothing', ]


_vmstate = vStateMockup()
clock = pygame.time.Clock()


def runs_in_web():  # temporary add-on to the may demo version
    # -> we avoid calling the SDK, we wish to only use the kengi part,
    # for now
    return False
# ------------- done


sbridge = None
interruption = None  # used to change game

PALIAS = {
    'greetings': 'niobepolis/myassets/greetings.png',
    'tilefloor': 'niobepolis/myassets/floor-tile.png',
    'gridsystem': 'niobepolis/myassets/grid-system.png',
}


# Coords used:
# floorgrid -> 64x32 2D grid
# chargrid  -> 32x16 2D grid
# mapcoords -> isometric large tiles(size of a floor element)
# gamecoords-> isometric small tiles(size of the avatar)


introscree = scr = vscr_size = None

# for async operations (stellar-related stuff)
browser_wait = False
browser_res = ''

avatar_m = viewer = None
keep_going = True
CgmEvent = kengi.event.CgmEvent
mger = None
lu_event = paint_event = None
wctrl = None

# --------------- Extra parsing function --------------------
# this one lets you call functions like: name(arg1,arg2,...,argn)
re_function = re.compile(r'(?P<name>\S+)(?P<params>[\(].*[\)])')


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
def _gencb(x):
    global browser_res, browser_wait, ingame_console
    browser_res = x
    browser_wait = False
    ingame_console.output(browser_res)


def gamelist():
    """
    List all games. Use: gamelist
    :return:
    """
    global glist
    return "\n".join(glist)


def stellar_console_func(subcmd):
    """
    Stellar bridge. Use: stellar test/network/pkey
    """
    global browser_wait
    if sbridge:
        if 'test' == subcmd:
            return sbridge.test_connection()
        elif 'network' == subcmd:
            browser_wait = True
            sbridge.get_network(_gencb)
        elif 'pkey' == subcmd:
            browser_wait = True
            sbridge.get_pkey(_gencb)
        else:
            return 'invalid subcmd'
    else:
        return 'stellar not available in local ctx'


def tp(gametag):
    """
    Teleport to another world. Use: tp gametag
    :param gametag:
    :return:
    """
    global interruption
    interruption = [2, gametag]


def add(a, b):
    """
    Simple add Function! Use: add a b
    """
    return a + b


def mul(a, b):
    """
    Une bete multiplication, tapez: mul a b
    """
    return float(a) * float(b)


def draw(a, b, c):
    """
    Simple draw circle Function! Use: draw 400 400 100
    """
    # scr = pygame.display.get_surface()
    scr = kengi.core.get_screen()
    return pygame.draw.circle(scr, (0, 0, 255), (a, b), c, 1)


def size():
    """
    Provide screen dim info. Use: size
    """
    global vscr_size
    w, h = vscr_size
    return str(w) + ' ' + str(h)


to_edit = None


def cedit(cname):  # -------------------- experimental ----------------
    """
    Edit cartridge. Use: edit cartname
    """
    global to_edit
    to_edit = cname
    return f'...requesting edition {cname}'


leaving_niobe = False

def dohalt():
    """
    Provide screen dim info. Use: halt
    """
    global leaving_niobe
    leaving_niobe = True
    return 'quit niobe requested.'


listing_all_console_func = {  # IMPORTANT REMINDER!!
    # All functions listed here need to RETURN smth and they
    # need to have 1 line of docstring, and include a
    # "Use: xxx aa bb"
    # part at the end, otherwise the cmd "help cmd_name" would crash the soft!

    "size": size,
    "add": add,
    "mul": mul,
    "draw": draw,
    "halt": dohalt,
    "stellar": stellar_console_func,
    "edit": cedit,
    "tp": tp,
    "gamelist": gamelist
}
# --------------- implem of console functions, docstrings are used for help ------------------END

CON_FONT_COLOR = (13, 253, 8)
ingame_console = None
# ---------- managing the console --------------end


# --- temporary tests ---
# USING A .TMX file to load data
# tmx_map = kengi.tmx.data.TileMap.load(  # uses the base64 zlib compression
#     'niobepolis/myassets/map.tmx',
#     'niobepolis/myassets/sync-tileset.tsx',
#     'niobepolis/myassets/spritesheet.png'
# )
# print(tmx_map)
# print('TMX loading seems to work. * * ###')
# - -

floortile = None
chartile = None

# - charge tuiles syndicate, exploite un mapping code <> surface contenant tile image -
# we need to do it in a stupid way,
# due to how the ROM pseudo-compil works (=>detects raw strings for filepaths, moves assets)
# code2filename = {
#     35: PALIAS['t035'],
#     92: PALIAS['t092'],
#     160: PALIAS['t160'],
#     182: PALIAS['t182'],
#     183: PALIAS['t183'],
#     198: PALIAS['t198'],
#     203: PALIAS['t203'],
# }
# code2tile_map = dict()
# def _loadstuff():
#     for code, fn in code2filename.items():
#         code2tile_map[code] = pygame.image.load(fn)
#
#     for obj in code2tile_map.values():
#         obj.set_colorkey('#ff00ff')


CODE_GRASS = 203
BG_COLOR = (40, 40, 68)
my_x, my_y = 0, 0  # comme un offset purement 2d -> utile pr camera
show_grid = True
posdecor = list()


def gridbased_2d_disp(grid_spec, coords, ref_img):
    local_i, local_j = coords
    scr.blit(ref_img, (my_x + local_i * grid_spec[0], my_y + local_j * grid_spec[1]))


def realise_pavage(gfx_elt, offsets=(0, 0)):
    incx, incy = gfx_elt.get_size()  # 64*32 pour floortile
    for y in range(0, vscr_size[1], incy):
        for x in range(0, vscr_size[0], incx):
            scr.blit(gfx_elt, (offsets[0] + x, offsets[1] + y))


def conv_map_coords_floorgrid(u, v, z):
    base_res = [4, 0]  # mapcoords 0,0
    while u > 0:
        u -= 1
        base_res[0] += 1
        base_res[1] += 1
    while v > 0:
        v -= 1
        base_res[0] -= 1
        base_res[1] += 1
    while z > 0:
        z -= 1
        base_res[1] -= 1
    return base_res


dx = dy = 0
clock = None

# --------------------------------------------
#  Game Def
# --------------------------------------------
glist = []
binded_state = None
EngineEvTypes = kengi.event.EngineEvTypes


class ExtraLayerView(kengi.event.EventReceiver):
    def __init__(self):
        super().__init__()

    def proc_event(self, ev, source=None):
        global show_grid
        if ev.type == EngineEvTypes.PAINT:
            # grid draw
            if show_grid:
                realise_pavage(chartile, offsets=(16 + my_x, 0 + my_y))
                realise_pavage(floortile, offsets=(0 + my_x, 0 + my_y))

            # console draw
            ingame_console.draw()


def _init_partie1():
    global screen, tilemap, avatar_m, viewer

    global mger, lu_event, paint_event, wctrl

    kengi.init('old_school', caption='niobepolis - unstable')

    screen = kengi.get_surface()
    with open('niobepolis\\xassets\\test_map.json', 'r') as ff:
        jdict = json.load(ff)
        tilemap = kengi.isometric.IsometricMap.from_json_dict(['niobepolis', 'xassets', ], jdict)

    avatar_m = Character(10.5, 10.5)
    avatar_m.ox = -8
    avatar_m.oy = -32-8
    list(tilemap.objectgroups.values())[0].contents.append(avatar_m)

    viewer = kengi.isometric.IsometricMapViewer(
        tilemap, screen,
        up_scroll_key=pygame.K_UP,
        down_scroll_key=pygame.K_DOWN,
        left_scroll_key=pygame.K_LEFT,
        right_scroll_key=pygame.K_RIGHT
    )
    viewer.turn_on()

    # using a cursor -> YE
    cursor_image = pygame.image.load("niobepolis/xassets/half-floor-tile.png").convert_alpha()
    cursor_image.set_colorkey((255, 0, 255))
    viewer.cursor = kengi.isometric.IsometricMapQuarterCursor(0, 0, cursor_image, tilemap.layers[1])

    # camera focus avatar
    viewer.set_focused_object(avatar_m)  # center camera
    avatar_m.x += 0.1

    # chunk taken from PBGE, also it sets key repeat freq.
    pygame.time.set_timer(pygame.USEREVENT, int(1000 / FPS_PBGE))
    pygame.key.set_repeat(200, 75)
    # TODO port Pbge to kengi CogObj+EventReceiver+event system,
    #  so we can avoid using pygame.USEREVENT and viewer() like here

    # - refactoring -> let's use the kengi event system
    lu_event = CgmEvent(EngineEvTypes.LOGICUPDATE, curr_t=None)
    paint_event = CgmEvent(EngineEvTypes.PAINT, screen=kengi.get_surface())
    mger = kengi.event.EventManager.instance()
    wctrl = WorldCtrl()
    wctrl.turn_on()



def game_enter(vmstate=None):
    global glist, binded_state, pygame, \
        introscree, scr, vscr_size, ingame_console, floortile, chartile, clock, sbridge

    _init_partie1()
    extra_gui_v = ExtraLayerView()
    extra_gui_ctrl = ExtraGuiLayerCtrl()
    for elk in (extra_gui_v, extra_gui_ctrl):
        elk.turn_on()

    introscree = pygame.image.load(PALIAS['greetings'])
    scr = kengi.core.get_screen()
    vscr_size = scr.get_size()

    # init vars
    if runs_in_web():
        sbridge = katasdk.stellar
    if vmstate.gamelist is None:
        vmstate.gamelist = list()
    ingame_console = kengi.console.CustomConsole(
        kengi.core.get_screen(),
        (0, 0, vscr_size[0], int(0.9 * vscr_size[1])),  # takes up 90% of the scr height

        functions=listing_all_console_func,
        key_calls={},
        vari={"A": 100, "B": 200, "C": 300},
        syntax={re_function: console_func},

        fontobj=kengi.gui.ImgBasedFont('niobepolis/myassets/gibson1_font.png', CON_FONT_COLOR)
        # - using the new ft system
    )
    floortile = pygame.image.load(PALIAS['tilefloor'])
    floortile.set_colorkey('#ff00ff')

    chartile = pygame.image.load(PALIAS['gridsystem'])
    chartile.set_colorkey('#ff00ff')

    # _loadstuff()

    clock = pygame.time.Clock()
    # - fin init vars

    glist.extend(vmstate.gamelist)
    binded_state = vmstate

    global t_map_changed
    print(vmstate)
    # themap.shuffle()
    t_map_changed = time.time()


def game_update(infot=None):
    global lu_event, paint_event, interruption
    # using kengi event system
    lu_event.curr_t = infot
    mger.post(lu_event)
    mger.post(paint_event)

    mger.update()
    if interruption:
        print(' ~~~', interruption)
        return interruption
    kengi.flip()


class ExtraGuiLayerCtrl(kengi.event.EventReceiver):
    def __init__(self):
        super().__init__()

    def proc_event(self, ev, source=None):
        global t_map_changed, show_grid, interruption, ingame_console

        ingame_console.process_input([ev, ])  # ne sais pas cmt gerer ca autrement

        if ev.type == pygame.KEYUP:
            pass
            # keys = pygame.key.get_pressed()
            # if (not keys[pygame.K_DOWN]) and (not keys[pygame.K_UP]):
            #     dy = 0
            # if (not keys[pygame.K_LEFT]) and (not keys[pygame.K_RIGHT]):
            #     dx = 0

        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_F1:
                ingame_console.set_active()

            # TODO active console has to block key press, in the new system TOO!
            # example (old system):
            if not ingame_console.active:
                if ev.key == pygame.K_SPACE:
                    show_grid = not show_grid
            #     elif ev.key == pygame.K_RIGHT:
            #         dx = -1
            #     elif ev.key == pygame.K_LEFT:
            #         dx = +1
            #     elif ev.key == pygame.K_UP:
            #         dy = +1
            #     elif ev.key == pygame.K_DOWN:
            #         dy = -1

        elif ev.type == EngineEvTypes.LOGICUPDATE:

            if binded_state and (to_edit is not None):
                binded_state.cedit_arg = to_edit  # commit name of the file to be edited to VMstate
                interruption = [2, 'editor']

            if leaving_niobe:
                interruption = [1, None]

            # - old system for moving the camera
            # my_x += dx
            # my_y += dy

            # - mutating map periodically
            # tnow = ev.curr_t
            # if t_map_changed is None:
            #     t_map_changed = tnow
            #     dt = 0
            # else:
            #     dt = tnow - t_map_changed
            # if dt > 3.0:
            #    themap.shuffle()
            #    t_map_changed = tnow


def game_exit(vmstate=None):
    print(vmstate, 'bye!')
    kengi.quit()


# constants
FPS_PBGE = 30

pygame = kengi.pygame
screen = None
tilemap = tilemap2 = None
# pbge = kengi.polarbear


def get_maps():
    global tilemap, tilemap2
    return tilemap, tilemap2


class Character(kengi.isometric.IsometricMapObject):
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y
        self.surf = pygame.image.load("niobepolis/xassets/sys_icon.png").convert_alpha()
        # self.surf.set_colorkey((0,0,255))
        self.ox = self.oy = 0

    def __call__(self, dest_surface, sx, sy, mymap):
        mydest = self.surf.get_rect(midbottom=(sx+self.ox, sy+self.oy))
        dest_surface.blit(self.surf, mydest)


class WorldCtrl(kengi.event.EventReceiver):
    def __init__(self):
        super().__init__()

    def proc_event(self, ev, source=None):
        global keep_going, viewer

        if ev.type == EngineEvTypes.LOGICUPDATE:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]:
                viewer.scroll_to(0)
            elif keys[pygame.K_DOWN]:
                viewer.scroll_to(2)
            if keys[pygame.K_RIGHT]:
                viewer.scroll_to(1)
            elif keys[pygame.K_LEFT]:
                viewer.scroll_to(3)

        if ev.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = kengi.core.proj_to_vscreen(pygame.mouse.get_pos())
            tx, ty = viewer.map_x(mouse_x, mouse_y, return_int=False), viewer.map_y(mouse_x, mouse_y, return_int=False)
            print(tx, ty)
            avatar_m.x, avatar_m.y = tx, ty
            # print(viewer.relative_x(0, 0), viewer.relative_y(0, 0))
            # print(viewer.relative_x(0, 19), viewer.relative_y(0, 19))

        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                keep_going = False
            # -- avatar movement via arrow keys

            # elif ev.key == pygame.K_d and avatar_m.x < tilemap.width - 1.5:
            #     ev.x += 0.1
            # elif ev.key == pygame.K_a and avatar_m.x > -1:
            #     avatar_m.x -= 0.1
            # elif ev.key == pygame.K_w and avatar_m.y > -1:
            #     avatar_m.y -= 0.1
            # elif ev.key == pygame.K_s and avatar_m.y < tilemap.height - 1.5:
            #     avatar_m.y += 0.1

        elif ev.type == pygame.QUIT:
            keep_going = False


if __name__ == '__main__':
    game_enter(_vmstate)
    while keep_going:
        uresult = game_update(time.time())
        if uresult is not None:
            if 0 < uresult[0] < 3:
                keep_going = False
    game_exit(_vmstate)
