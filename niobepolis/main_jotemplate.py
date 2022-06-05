import katagames_engine as kengi
kengi.bootstrap_e()

import demolib.animobs as animobs
import demolib.dialogue as dialogue
import demolib.pathfinding as pathfinding
import isometric_maps
from defs import MyEvTypes, MAXFPS, DEBUG


kengi.init('old_school', maxfps=MAXFPS)
# IMPORTANT: polarbear component can crash the game if this line isnt added, after kengi.init
kengi.polarbear.my_state.screen = kengi.get_surface()

# - aliases
pygame = kengi.pygame  # alias to keep on using pygame, easily
CgmEvent = kengi.event.CgmEvent
EngineEvTypes = kengi.event.EngineEvTypes

# global variables
conv_viewer = None
conversation_ongoing = False
current_path = None
current_tilemap = 0
maps = list()
map_viewer = None
mypc = mynpc = None
path_ctrl = None
screen = kengi.get_surface()  # retrieve the surface used for display
tilemap_height = tilemap_width = 0


class Character(isometric_maps.IsometricMapObject):
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y
        self.surf = pygame.image.load("assets/sys_icon.png").convert_alpha()
        # self.surf.set_colorkey((0,0,255))

    def __call__(self, dest_surface, sx, sy, mymap):
        mydest = self.surf.get_rect(midbottom=(sx, sy))
        dest_surface.blit(self.surf, mydest)


class MovementPath:
    def __init__(self, mapob, dest, mymap):
        self.mapob = mapob
        self.dest = dest
        self.goal = None
        blocked_tiles = set()
        obgroup = list(mymap.objectgroups.values())[0]
        for ob in obgroup.contents:
            if ob is not mapob:
                blocked_tiles.add((ob.x, ob.y))
                if self.pos_to_index((ob.x, ob.y)) == self.pos_to_index(dest):
                    self.goal = ob
        self.path = pathfinding.AStarPath(
            mymap, self.pos_to_index((mapob.x, mapob.y)), self.pos_to_index(dest), self.tile_is_blocked, blocked_tiles
        )
        if self.path.results:
            self.path.results.pop(0)
        self.all_the_way_to_dest = not (dest in blocked_tiles or self.tile_is_blocked(mymap, *self.pos_to_index(dest)))
        if self.path.results and not self.all_the_way_to_dest:
            self.path.results.pop(-1)
        self.animob = None

    @staticmethod
    def pos_to_index(pos):
        x = int(pos[0] + 0.99)
        y = int(pos[1] + 0.99)
        return x, y

    @staticmethod
    def tile_is_blocked(mymap, x, y):
        return not (mymap.on_the_map(x, y) and mymap.layers[1][x, y] == 0)

    def __call__(self):
        # Called once per update; returns True when the action is completed.
        if self.animob:
            self.animob.update()
            if self.animob.needs_deletion:
                self.animob = None
        if not self.animob:
            if self.path.results:
                if len(self.path.results) == 1 and self.all_the_way_to_dest:
                    nugoal = self.dest
                    self.path.results = []
                else:
                    nugoal = self.path.results.pop(0)
                self.animob = animobs.MoveModel(
                    self.mapob, start=(self.mapob.x, self.mapob.y), dest=nugoal, speed=0.25
                )
            else:
                # print((self.mapob.x,self.mapob.y))
                # sx, sy = viewer.screen_coords(self.mapob.x, self.mapob.y, 0, -8)
                # print(viewer.map_x(sx, sy, return_int=False), viewer.map_y(sx, sy, return_int=False))
                return True


class NPC(isometric_maps.IsometricMapObject):
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y
        self.surf = pygame.image.load("assets/npc.png").convert_alpha()
        # self.surf.set_colorkey((0,0,255))

    def __call__(self, dest_surface, sx, sy, mymap):
        mydest = self.surf.get_rect(midbottom=(sx, sy))
        dest_surface.blit(self.surf, mydest)


# --------------------------------------------
# Define controllers etc
# --------------------------------------------
class BasicCtrl(kengi.event.EventReceiver):
    def proc_event(self, gdi, source):
        global conversation_ongoing, map_viewer, mypc, current_tilemap, current_path

        if gdi.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP, pygame.MOUSEBUTTONUP):
            if conversation_ongoing:
                pass  # block all movement when the conversation is active
            else:
                cursor = map_viewer.cursor
                if cursor:
                    cursor.update(map_viewer, gdi)
                if gdi.type == pygame.MOUSEBUTTONUP and gdi.button == 1:
                    #TODO: There are some glitches in the movement system, when the player character will not move to
                    # a tile that has been clicked. It generally happens with tiles that are adjacent to the PC's
                    # current position, but it doesn't happen all the time. I will look into this later.
                    current_path = MovementPath(mypc, map_viewer.cursor.get_pos(), maps[current_tilemap])
                    if DEBUG:
                        print('movement path has been set')

        elif gdi.type == pygame.KEYDOWN:
            if gdi.key == pygame.K_ESCAPE:
                if conversation_ongoing:
                    # abort
                    self.pev(MyEvTypes.ConvEnds)
                else:
                    self.pev(EngineEvTypes.GAMEENDS)
            elif gdi.key == pygame.K_m:
                # mouse_x, mouse_y = pygame.mouse.get_pos()
                # print(viewer.map_x(mouse_x, mouse_y, return_int=False),
                #       viewer.map_y(mouse_x, mouse_y, return_int=False))
                # print(viewer.relative_x(0, 0), viewer.relative_y(0, 0))
                # print(viewer.relative_x(0, 19), viewer.relative_y(0, 19))
                pass
            elif gdi.key == pygame.K_d and mypc.x < tilemap_width - 1.5:
                mypc.x += 0.1
            elif gdi.key == pygame.K_a and mypc.x > -1:
                mypc.x -= 0.1
            elif gdi.key == pygame.K_w and mypc.y > -1:
                mypc.y -= 0.1
            elif gdi.key == pygame.K_s and mypc.y < tilemap_height - 1.5:
                mypc.y += 0.1
            elif gdi.key == pygame.K_TAB:
                current_tilemap = 1 - current_tilemap
                map_viewer.switch_map(maps[current_tilemap])


class PathCtrl(kengi.event.EventReceiver):
    def __init__(self):
        super().__init__()

    def proc_event(self, event, source):
        global current_path, conv_viewer, conversation_ongoing

        if event.type == EngineEvTypes.LOGICUPDATE:
            if current_path is not None:
                ending_reached = current_path()
                if ending_reached:
                    if current_path.goal:
                        conversation_ongoing = True
                        myconvo = dialogue.Offer.load_json("assets/conversation.json")
                        conv_viewer = dialogue.ConversationView(myconvo)
                        conv_viewer.turn_on()
                    current_path = None

        elif event.type == MyEvTypes.ConvEnds:
            conversation_ongoing = False  # unlock player movements
            if conv_viewer.active:
                conv_viewer.turn_off()


def _load_maps():
    global maps, tilemap_width, tilemap_height
    maps.append(
        isometric_maps.IsometricMap.load('assets/test_map.tmx')
    )
    maps.append(
        isometric_maps.IsometricMap.load('assets/test_map2.tmx')
    )
    tilemap_width, tilemap_height = maps[0].width, maps[0].height
    maps[0].wrap_x = True
    maps[0].wrap_y = True
    #maps[1].wrap_x = True
    #maps[1].wrap_y = True


def _add_map_entities(gviewer):
    global mypc, mynpc
    mypc = Character(10, 10)
    mynpc = NPC(15, 15)
    tm, tm2 = maps[0], maps[1]
    list(tm.objectgroups.values())[0].contents.append(mypc)
    list(tm2.objectgroups.values())[0].contents.append(mypc)

    list(tm.objectgroups.values())[0].contents.append(mynpc)
    list(tm2.objectgroups.values())[0].contents.append(mynpc)

    gviewer.set_focused_object(mypc)
    # force: center on avatar op.
    mypc.x += 0.5


def _init_specific_stuff():
    global map_viewer, maps

    _load_maps()
    map_viewer = kengi.isometric.IsometricMapViewer(
        maps[0], screen,
        up_scroll_key=pygame.K_UP, down_scroll_key=pygame.K_DOWN,
        left_scroll_key=pygame.K_LEFT, right_scroll_key=pygame.K_RIGHT
    )
    _add_map_entities(map_viewer)

    cursor_image = pygame.image.load("assets/half-floor-tile.png").convert_alpha()
    cursor_image.set_colorkey((255, 0, 255))
    map_viewer.cursor = isometric_maps.IsometricMapQuarterCursor(0, 0, cursor_image, maps[0].layers[1])
    pctrl = PathCtrl()

    map_viewer.turn_on()
    pctrl.turn_on()

    bctrl = BasicCtrl()
    bctrl.turn_on()


def run_game():
    _init_specific_stuff()
    gctrl = kengi.get_game_ctrl()

    gctrl.turn_on()
    gctrl.loop()
    kengi.quit()
    print('bye!')


if __name__ == '__main__':
    run_game()
