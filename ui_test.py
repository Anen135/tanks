import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from tanks import Game

g = Game()
g.start_game()
for i in range(30):
    g.update(1 / 60)
    g.draw()
g.toggle_fullscreen()
g.draw()
print("fullscreen size:", g.win.get_size(), "crt:", g.crt_key)
g.toggle_fullscreen()
g.win = pygame.display.set_mode((700, 500), pygame.RESIZABLE)
g.crt_key = None
g.draw()
print("resized:", g.win.get_size(), "crt:", g.crt_key)
g.state = 3  # paused
g.draw()
g.state = 4  # clear
g.draw()
g.state = 5  # gameover
g.draw()
print("screens ok")
pygame.quit()
