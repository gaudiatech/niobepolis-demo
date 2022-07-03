import pygame
import katagames_engine as kengi

# GOAL: test
# kengi.anim.SpriteSheet, for loading png+json


def run_game():
    pygame.init()
    scr = pygame.display.set_mode((640, 480))
    fc = pygame.image.load('assets/french-cards.png')
    game_over = False
    while not game_over:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                game_over = True
        scr.fill('orange')
        scr.blit(fc, (60, 60))
        pygame.display.flip()


if __name__ == '__main__':
    run_game()
