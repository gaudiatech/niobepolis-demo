import katagames_engine as kengi
kengi.bootstrap_e()


# aliases
pygame = kengi.pygame
ReceiverObj = kengi.event.EventReceiver
EngineEvTypes = kengi.event.EngineEvTypes


MyEvTypes = kengi.event.enum_ev_types(
    'TileChanges',  # contains tile_idx
)


class Gstate:
    def __init__(self):
        self.x = 0


class SprSheetInfos:
    def __init__(self):
        self.nb_col = 16
        self.nb_rows = 16
        self.tilew = 64
        self.tileh = 48

    def scrpos_to_idx(self, mpos):
        i = mpos[0] // self.tilew
        j = mpos[1] // self.tileh
        return j * self.nb_col + i


class TileView(ReceiverObj):
    SCR_POS_TILE = (1050, 256)
    UPINK = (255, 0, 255)

    def __init__(self, mod, img_tileset):
        super().__init__()
        self.model = mod
        self.img = img_tileset
        self.tmp_tile = None

        # - comp stats - how many tiles are fixed/completed?
        x = 0
        for tidx in range(256):
            t = self.get_tiledata(tidx)
            if TileView.has_gfx_flag_ok(t):
                x += 1
        print(f'usable tiles count: {x} /256')
        self.completion_ratio = x / 256
        print('ratio= {}'.format(self.completion_ratio))

    @staticmethod
    def has_gfx_flag_ok(surfobj):
        a = surfobj.get_at((0, 0))
        b = surfobj.get_at((1, 0))
        c = surfobj.get_at((0, 1))
        d = surfobj.get_at((1, 1))
        sumr = a[0] + b[0] + c[0] + d[0]
        sumg = a[1] + b[1] + c[1] + d[1]
        sumb = a[2] + b[2] + c[2] + d[2]
        return (not sumr) and (not sumb) and (sumg == 4*0xff)

    def get_tiledata(self, idx):
        k = self.model.nb_col
        i, j = idx % k, idx // k
        x = self.model.tilew * i
        y = self.model.tileh * j
        ref = self.img.subsurface((x, y), (self.model.tilew, self.model.tileh))
        ref.copy()
        tmp = pygame.transform.scale(ref, (3*self.model.tilew, 3*self.model.tileh))  # upscaling x3
        return tmp

    def proc_event(self, ev, source):
        if ev.type == MyEvTypes.TileChanges:
            self.tmp_tile = self.get_tiledata(ev.tile_idx)
            self.tmp_tile.set_colorkey(self.UPINK)

            print('displayed tile rank is: #', ev.tile_idx)

        elif ev.type == EngineEvTypes.PAINT:
            if self.tmp_tile:
                ev.screen.blit(self.tmp_tile, self.SCR_POS_TILE)
            else:
                self.tmp_tile = self.get_tiledata(0)
                self.tmp_tile.set_colorkey(self.UPINK)
            pygame.display.flip()


class MainCtrl(ReceiverObj):

    def __init__(self, mod, gstate, image_tileset):
        super().__init__()
        self.model = mod
        self.gstate = gstate
        self.screen = kengi.get_surface()
        self.img = image_tileset

        # gui & controls
        self.mdown = False

    def proc_event(self, ev, source):
        if ev.type == EngineEvTypes.PAINT:
            self.screen.fill('navyblue')
            self.screen.blit(self.img, (0, 0))

        elif ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
            self.pev(EngineEvTypes.GAMEENDS)

        elif ev.type == pygame.MOUSEBUTTONDOWN:
            self.mdown = True
            self.pev(MyEvTypes.TileChanges, tile_idx=self.model.scrpos_to_idx(ev.pos))

        elif ev.type == pygame.MOUSEBUTTONUP:
            self.mdown = False


def run_game():
    kengi.init('custom', screen_dim=(280 + 1024, 768))

    mod = SprSheetInfos()
    state = Gstate()
    spritesheetimg = pygame.image.load('assets/s.wip-tileset.png')

    mctrl = MainCtrl(mod, state, spritesheetimg)
    mctrl.turn_on()

    tileview = TileView(mod, spritesheetimg)
    tileview.turn_on()

    gctrl = kengi.get_game_ctrl()
    gctrl.turn_on()
    gctrl.loop()

    print('bye')
    kengi.quit()


if __name__ == '__main__':
    run_game()
