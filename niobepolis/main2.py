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


def game_enter():
    global screen, tilemap, avatar_m, viewer
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


def game_update():
    global keep_going

    # gdi = pbge.wait_event()
    for gdi in pygame.event.get():
        viewer.check_event(gdi)

        if gdi.type == pygame.USEREVENT:  # pbge.TIMEREVENT:
            viewer()
            kengi.flip()

        elif gdi.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = kengi.core.proj_to_vscreen(pygame.mouse.get_pos())
            tx, ty = viewer.map_x(mouse_x, mouse_y, return_int=False), viewer.map_y(mouse_x, mouse_y, return_int=False)
            print(tx, ty)
            avatar_m.x, avatar_m.y = tx, ty
            # print(viewer.relative_x(0, 0), viewer.relative_y(0, 0))
            # print(viewer.relative_x(0, 19), viewer.relative_y(0, 19))

        elif gdi.type == pygame.KEYDOWN:
            if gdi.key == pygame.K_ESCAPE:
                keep_going = False
            elif gdi.key == pygame.K_d and avatar_m.x < tilemap.width - 1.5:
                avatar_m.x += 0.1
            elif gdi.key == pygame.K_a and avatar_m.x > -1:
                avatar_m.x -= 0.1
            elif gdi.key == pygame.K_w and avatar_m.y > -1:
                avatar_m.y -= 0.1
            elif gdi.key == pygame.K_s and avatar_m.y < tilemap.height - 1.5:
                avatar_m.y += 0.1

        elif gdi.type == pygame.QUIT:
            keep_going = False


if __name__ == '__main__':
    game_enter()
    while keep_going:
        game_update()
    kengi.quit()
