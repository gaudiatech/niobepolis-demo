import katagames_engine as kengi

import glvars
import oldfunc


ReceiverObj = kengi.event.EventReceiver
EngineEvTypes = kengi.event.EngineEvTypes
pygame = kengi.pygame


class DebugV(ReceiverObj):
    """
    on se sert de ca pour debug le submodule .isometric en web ctx...
    """

    def __init__(self, viewer, cons):  # isometric map viewer
        super().__init__()
        self.viewer = viewer
        self.console = cons
        self.pbase = [44, 44]
        self.show_grid = False
        self.showin_tileset = False

        self.chartile = pygame.image.load(glvars.PALIAS['gridsystem'])
        self.chartile.set_colorkey('#ff00ff')

        self.floortile = pygame.image.load(glvars.PALIAS['tilefloor'])
        self.floortile.set_colorkey('#ff00ff')

    def proc_event(self, ev, source=None):
        if ev.type == EngineEvTypes.PAINT:
            # only here so the user can know that the DebugV component is active & rdy
            pygame.draw.circle(ev.screen, 'orange', self.pbase, 16)

            if self.show_grid:
                oldfunc.realise_pavage(self.chartile, offsets=(16 + oldfunc.my_x, 0 + oldfunc.my_y))
                oldfunc.realise_pavage(self.floortile, offsets=(0 + oldfunc.my_x, 0 + oldfunc.my_y))

            if self.showin_tileset:
                ev.screen.blit(self.viewer.isometric_map.tilesets[2].tile_surface, (self.pbase[0] + 32, self.pbase[1]))
                ev.screen.blit(self.viewer.isometric_map.tilesets[6].tile_surface, (self.pbase[0] + 122, self.pbase[1]))
                ev.screen.blit(self.viewer.isometric_map.tilesets[3].tile_surface, (self.pbase[0] + 212, self.pbase[1]))

                ev.screen.blit(self.viewer.isometric_map.tilesets[4].tile_surface, (self.pbase[0] + 32, self.pbase[1] + 60))
                ev.screen.blit(self.viewer.isometric_map.tilesets[5].tile_surface, (self.pbase[0] + 122, self.pbase[1] + 60))
                ev.screen.blit(self.viewer.isometric_map.tilesets[1].tile_surface, (self.pbase[0] + 212, self.pbase[1] + 60))

                ev.screen.blit(self.viewer.isometric_map.tilesets[7].tile_surface, (self.pbase[0] + 32, self.pbase[1] + 120))
                ev.screen.blit(self.viewer.isometric_map.tilesets[8].tile_surface,
                               (self.pbase[0] + 122, self.pbase[1] + 120))
                ev.screen.blit(self.viewer.isometric_map.tilesets[9].tile_surface,
                               (self.pbase[0] + 212, self.pbase[1] + 120))

        elif ev.type == pygame.KEYDOWN:
            if not self.console.active:
                if ev.key == pygame.K_BACKSPACE:
                    self.showin_tileset = not self.showin_tileset
                elif ev.key == pygame.K_SPACE:
                    self.show_grid = not self.show_grid
