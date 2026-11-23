import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from tanks import Game
from world import Enemy, PowerUp, Bullet, BASE_CENTER
from retro import (
    PLAYING, CLEAR, GAMEOVER, MARGIN, TILE, UP, EMPTY, BRICK, BASE, YELLOW,
)

ok = True


def check(name, cond, extra=""):
    global ok
    print(("OK  " if cond else "FAIL"), name, extra)
    ok = ok and bool(cond)


g = Game()
g.start_game()
g.state = PLAYING
g.intro_timer = 0
g.player.shield = 99

# --- стрельба по кирпичу
px, py = int(g.player.x), int(g.player.y)
tile_x, tile_y = (px - MARGIN) // TILE + 0, (py - MARGIN) // TILE - 1
g.level.grid[tile_y][tile_x] = BRICK
g.player.dir = UP
g.player.cooldown = 0
g.player.shoot()
for _ in range(30):
    g.update(1 / 60)
check("brick destroyed by shot", g.level.grid[tile_y][tile_x] == EMPTY,
      str(g.level.grid[tile_y][tile_x]))

# --- подбор бонуса «звезда»
g.state = PLAYING
g.weapon = 0
g.player.weapon = 0
pu = PowerUp(g, "star", int(g.player.x), int(g.player.y))
g.powerups.append(pu)
g.update(1 / 60)
check("star pickup -> weapon 1", g.player.weapon == 1)

# --- подбор «жизнь»
lives_before = g.lives
g.powerups.append(PowerUp(g, "tank", int(g.player.x), int(g.player.y)))
g.update(1 / 60)
check("tank pickup -> +1 life", g.lives == lives_before + 1)

# --- «лопата» превращает стену в сталь
g.powerups.append(PowerUp(g, "shovel", int(g.player.x), int(g.player.y)))
g.update(1 / 60)
from retro import STEEL
check("shovel -> steel walls", g.shovel > 0 and
      g.level.grid[25][13] == STEEL)

# --- своя пуля не должна разрушать базу
g.state = PLAYING
g.bullets.clear()
bx, by = BASE_CENTER
g.bullets.append(Bullet(g, g.player, bx + 4, by + 4, UP, 200))
for _ in range(5):
    g.update(1 / 60)
check("player bullet spares the base", g.level.base_alive)
g.bullets.clear()

# --- уничтожение врага пулей
g.enemies = []
ex, ey = int(g.player.x), int(g.player.y) - 20
enemy = Enemy(g, ex, ey, "basic")
g.enemies.append(enemy)
g.player.dir = UP
g.player.cooldown = 0
kills_before = g.kills
g.player.shoot()
for _ in range(40):
    g.update(1 / 60)
check("enemy killed by bullet", g.kills == kills_before + 1,
      f"kills {g.kills}")

# --- зачистка уровня
g.enemies = []
g.kills = g.total_enemies
for _ in range(150):
    g.update(1 / 60)
check("stage clear reached", g.state == CLEAR, str(g.state))
for _ in range(60 * 6):
    g.update(1 / 60)
check("next stage loaded", g.stage == 2 and g.state == PLAYING, f"stage {g.stage} {g.state}")

# --- game over из-за базы
g.destroy_base()
for _ in range(60 * 4):
    g.update(1 / 60)
check("base destroyed -> game over", g.state == GAMEOVER, str(g.state))

print("\nRESULT:", "ALL OK" if ok else "HAS FAILURES")
pygame.quit()
raise SystemExit(0 if ok else 1)
