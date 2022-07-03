"""
SCRIPT GOAL:
test kengi.anim.SpriteSheet, see if it can load png+json properly...
"""

import pygame
import katagames_engine as kengi
kengi.bootstrap_e()


def run_game():
    pygame.init()
    scr = pygame.display.set_mode((640, 480))
    my_sprsheet = kengi.gfx.JsonBasedSprSheet('assets/french-cards')

    game_over = False
    while not game_over:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                game_over = True
        scr.fill('orange')
        scr.blit(my_sprsheet['back-of-card.png'], (60, 60))
        scr.blit(my_sprsheet['3S.png'], (260, 60))
        scr.blit(my_sprsheet['13H.png'], (260, 230))
        pygame.display.flip()


if __name__ == '__main__':
    run_game()
