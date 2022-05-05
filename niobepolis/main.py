# ------------------------
# *UNSTABLE* ver. of niobepolis
# ------------------------

# remember to config your IDE so that
# the working dir is one level above the "niobepolis" folder!

import random
import re
import time

import katagames_engine as kengi

kengi.init('super_retro', caption='niobepolis - unstable')
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

# ---------- file IsoMapModel ------------------start
OMEGA_TILES = [0, 35, 92, 160, 182, 183, 198, 203]


class IsoMapModel:
    """
    model for the game map (will be drawn in the isometric style)
    """

    def __init__(self, width=3, height=3):
        self._w, self._h = width, height  # TODO general case
        self._layers = {
            0: None,
            1: None,
            2: None
        }
        for z in range(3):
            self._layers[z] = list()
            for jidx in range(height):
                temp_li = list()
                for iidx in range(width):
                    temp_li.append(0)
                self._layers[z].append(temp_li)
        for jidx in range(height):
            for iidx in range(width):
                self._layers[0][jidx][iidx] = 1  # grass
        self._layers[1][2][0] = 92  # building
        self._layers[2][2][0] = 92  # building

    @property
    def nb_layers(self):
        return 3

    def __getitem__(self, item):
        return self._layers[item]

    def shuffle(self):
        for j in range(3):
            for i in range(3):
                x = random.choice(OMEGA_TILES)
                self._layers[1][i][j] = x
        self._layers[1][2][0] = 92


# ---------- file IsoMapModel ------------------end

PALIAS = {
    'greetings': 'niobepolis/myassets/greetings.png',

    'tilefloor': 'niobepolis/myassets/floor-tile.png',
    'gridsystem': 'niobepolis/myassets/grid-system.png',
#
#     't035': 'niobepolis/myassets/t035.png',
#     't092': 'niobepolis/myassets/t092.png',
#     't160': 'niobepolis/myassets/t160.png',
#     't182': 'niobepolis/myassets/t182.png',
#     't183': 'niobepolis/myassets/t183.png',
#     't198': 'niobepolis/myassets/t198.png',
#     't203': 'niobepolis/myassets/t203.png',
}


# Coords used:
# floorgrid -> 64x32 2D grid
# chargrid  -> 32x16 2D grid
# mapcoords -> isometric large tiles(size of a floor element)
# gamecoords-> isometric small tiles(size of the avatar)


introscree = scr = vscr_size = None


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
browser_wait = False
browser_res = ''


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


gameover = False


def dohalt():
    """
    Provide screen dim info. Use: halt
    """
    global gameover
    gameover = True
    return 'done.'


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

tmx_map = kengi.tmx.data.TileMap.load(  # uses the base64 zlib compression
    'niobepolis/myassets/map.tmx',
    'niobepolis/myassets/sync-tileset.tsx',
    'niobepolis/myassets/spritesheet.png'
)
print(tmx_map)
print('TMX loading seems to work. * * ###')
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


t_map_changed = None
themap = IsoMapModel()
dx = dy = 0
clock = None

# --------------------------------------------
#  Game Def
# --------------------------------------------
glist = []
binded_state = None


def game_enter(vmstate=None):
    global glist, binded_state, pygame, \
        introscree, scr, vscr_size, ingame_console, floortile, chartile, clock, sbridge

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


def _draw_map(screen):
    # we have disabled old code for draw map as the algorithm was based off a basic [][][] structure in IsoMapModel
    # for locali in range(3):
    #     for localj in range(3):
    #         a, b = conv_map_coords_floorgrid(localj, locali, 0)
    #         gridbased_2d_disp((32, 16), (a, b), code2tile_map[CODE_GRASS])
    # for elt in ((1, themap[1]), (2, themap[2])):  # drawing 2 layers above the ground level
    #     z, tmpl = elt
    #     for locali in range(3):
    #         for localj in range(3):
    #             lcode = tmpl[localj][locali]
    #             a, b = conv_map_coords_floorgrid(locali, localj, z)
    #             if lcode > 0:  # zero denotes no tile
    #                 gridbased_2d_disp((32, 16), (a, b), code2tile_map[lcode])
    pass


def game_update(infot=None):
    global t_map_changed, show_grid, dx, dy, my_x, my_y, gameover, interruption

    all_ev = pygame.event.get()
    ingame_console.process_input(all_ev)

    for ev in all_ev:
        if ev.type == pygame.QUIT:
            return [1, None]
        elif ev.type == pygame.KEYUP:
            keys = pygame.key.get_pressed()
            if (not keys[pygame.K_DOWN]) and (not keys[pygame.K_UP]):
                dy = 0
            if (not keys[pygame.K_LEFT]) and (not keys[pygame.K_RIGHT]):
                dx = 0
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_F1:
                ingame_console.set_active()

            if not ingame_console.active:
                # active console has to block some ev handling in the main UI
                if ev.key == pygame.K_SPACE:
                    show_grid = not show_grid
                elif ev.key == pygame.K_RIGHT:
                    dx = -1
                elif ev.key == pygame.K_LEFT:
                    dx = +1
                elif ev.key == pygame.K_UP:
                    dy = +1
                elif ev.key == pygame.K_DOWN:
                    dy = -1

    # logic
    if gameover:
        return [1, None]

    if binded_state and (to_edit is not None):
        binded_state.cedit_arg = to_edit  # commit name of the file to be edited to VMstate
        interruption = [2, 'editor']

    if interruption is not None:
        return interruption

    my_x += dx
    my_y += dy

    if infot:
        tnow = infot
    else:
        tnow = time.time()
    if t_map_changed is None:
        t_map_changed = tnow
        dt = 0
    else:
        dt = tnow - t_map_changed

    if dt > 3.0:
        themap.shuffle()
        t_map_changed = tnow

    # draw
    scr.fill(BG_COLOR)  # clear viewport

    # map draw
    _draw_map(scr)

    # grid draw
    if show_grid:
        realise_pavage(chartile, offsets=(16 + my_x, 0 + my_y))
        realise_pavage(floortile, offsets=(0 + my_x, 0 + my_y))

    # console draw
    ingame_console.draw()

    kengi.flip()
    clock.tick(60)


def game_exit(vmstate=None):
    print(vmstate, 'bye!')
    kengi.quit()


# --------------------------------------------
#  Entry pt, local ctx
# --------------------------------------------
if __name__ == '__main__':
    game_enter(_vmstate)
    while not gameover:
        uresult = game_update(None)
        if uresult is not None:
            if 0 < uresult[0] < 3:
                gameover = True
    game_exit(_vmstate)
