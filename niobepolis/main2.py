import json

import katagames_engine as kengi

kengi.bootstrap_e()


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
        self.surf = pygame.image.load("xassets/sys_icon.png").convert_alpha()
        # self.surf.set_colorkey((0,0,255))
        self.ox = self.oy = 0

    def __call__(self, dest_surface, sx, sy, mymap):
        mydest = self.surf.get_rect(midbottom=(sx+self.ox, sy+self.oy))
        dest_surface.blit(self.surf, mydest)


avatar_m = viewer = None
keep_going = True

CgmEvent = kengi.event.CgmEvent
EngineEvTypes = kengi.event.EngineEvTypes
mger = None
lu_event = paint_event = None

wctrl = None


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
            elif ev.key == pygame.K_d and avatar_m.x < tilemap.width - 1.5:
                ev.x += 0.1
            elif ev.key == pygame.K_a and avatar_m.x > -1:
                avatar_m.x -= 0.1
            elif ev.key == pygame.K_w and avatar_m.y > -1:
                avatar_m.y -= 0.1
            elif ev.key == pygame.K_s and avatar_m.y < tilemap.height - 1.5:
                avatar_m.y += 0.1

        elif ev.type == pygame.QUIT:
            keep_going = False


def game_enter():
    global screen, tilemap, avatar_m, viewer

    global mger, lu_event, paint_event, wctrl

    kengi.init('old_school')

    screen = kengi.get_surface()
    with open('xassets\\test_map.json', 'r') as ff:
        jdict = json.load(ff)
        tilemap = kengi.isometric.IsometricMap.from_json_dict(['xassets', ], jdict)

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
    cursor_image = pygame.image.load("xassets/half-floor-tile.png").convert_alpha()
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


def game_update():
    # using kengi event system
    mger.post(lu_event)
    mger.post(paint_event)
    mger.update()
    kengi.flip()


if __name__ == '__main__':
    game_enter()
    while keep_going:
        game_update()
    kengi.quit()
