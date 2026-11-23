import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from tanks import Game
from world import Bullet, Enemy, PowerUp
from retro import (
    DOWN, EMPTY, LEFT, MARGIN, PLAYING, RIGHT, TILE, UP, BASE, BRICK,
)

os.makedirs("docs", exist_ok=True)

g = Game()
g.stage = 3
g.score = 4200
g.lives = 2
g.weapon = 1
g.start_stage()
g.state = PLAYING
g.intro_timer = 0
g.player.shield = 6.0
g.player.x = MARGIN + 6 * TILE
g.player.y = MARGIN + 18 * TILE
g.player.dir = UP
g.player.tread = 7

# открытая площадка для сцены
for gy in range(16, 23):
    for gx in range(4, 13):
        if g.level.grid[gy][gx] not in (BASE,):
            g.level.grid[gy][gx] = EMPTY


def spot(gx, gy):
    return MARGIN + gx * TILE, MARGIN + gy * TILE


for kind, (gx, gy), d in (
    ("basic", (12, 4), DOWN),
    ("fast", (18, 9), LEFT),
    ("power", (4, 6), DOWN),
    ("armor", (20, 16), LEFT),
):
    e = Enemy(g, *spot(gx, gy), kind)
    e.dir = d
    e.tread = 3
    e.hp = 3 if kind == "armor" else 1
    g.enemies.append(e)

g.powerups.append(PowerUp(g, "star", *spot(8, 12)))
g.powerups.append(PowerUp(g, "clock", *spot(15, 10)))

# пара пуль в полёте
g.bullets.append(Bullet(g, g.player, g.player.cx + 1, g.player.cy - 26, UP, 0))
g.bullets.append(Bullet(g, g.enemies[0], g.enemies[0].cx + 1,
                        g.enemies[0].cy + 24, DOWN, 0))

# взрыв и искры
g.add_boom(*spot(9, 14), 22, 0.6)
g.booms[-1].t = 0.12
g.add_sparks(*spot(9, 14), 12)

g.toast = ["ЗВЕЗДА", 1.2]
g.draw()
pygame.image.save(pygame.transform.scale(g.logical, (1280, 1024)),
                  "docs/gameplay.png")

g.state = 1  # noqa: intro-состояние не важно, титул ниже
g.state = 0
g.title_t = 2.0
g.high_score = 12800
g.draw()
pygame.image.save(pygame.transform.scale(g.logical, (1280, 1024)),
                  "docs/title.png")

print("docs/gameplay.png, docs/title.png saved")
pygame.quit()
