"""Пиксель-арт: танки, тайлы, база, бонусы, взрывы."""

import math
import random

import pygame

from retro import (
    BRICK_C, BRICK_D, BRICK_L, STEEL_C, STEEL_D, STEEL_L,
    TREE_C, TREE_D, TREE_L, WATER_C, WATER_D, WATER_L,
    BLUE, CYAN, DARK, GREEN, ORANGE, PURPLE, RED, WHITE, YELLOW,
)


# ------------------------------------------------------------------ танки
PALETTES = {
    "player": dict(body=(252, 216, 72), dark=(120, 84, 8),
                   light=(255, 248, 168), tread=(92, 68, 16),
                   barrel=(255, 248, 168)),
    "basic": dict(body=(172, 180, 196), dark=(68, 76, 96),
                  light=(224, 232, 244), tread=(44, 50, 68),
                  barrel=(224, 232, 244)),
    "fast": dict(body=(108, 196, 236), dark=(28, 80, 124),
                 light=(196, 240, 255), tread=(20, 52, 84),
                 barrel=(196, 240, 255)),
    "power": dict(body=(228, 84, 76), dark=(108, 28, 28),
                  light=(255, 160, 148), tread=(64, 16, 16),
                  barrel=(255, 160, 148)),
    "armor4": dict(body=(116, 204, 92), dark=(32, 92, 36),
                   light=(184, 244, 152), tread=(24, 60, 24),
                   barrel=(184, 244, 152)),
    "armor3": dict(body=(178, 108, 236), dark=(72, 32, 120),
                   light=(228, 196, 255), tread=(52, 24, 88),
                   barrel=(228, 196, 255)),
    "armor2": dict(body=(224, 148, 52), dark=(108, 60, 12),
                   light=(255, 208, 140), tread=(72, 40, 8),
                   barrel=(255, 208, 140)),
    "armor1": dict(body=(168, 168, 176), dark=(72, 72, 84),
                   light=(228, 228, 236), tread=(48, 48, 60),
                   barrel=(228, 228, 236)),
    "bonus": dict(body=(252, 252, 252), dark=(148, 148, 160),
                  light=(255, 255, 255), tread=(104, 104, 118),
                  barrel=(255, 216, 80)),
}


def _tank_up(pal, frame, star=False, power=False, stripes=False):
    body, dark = pal["body"], pal["dark"]
    light, tread = pal["light"], pal["tread"]
    barrel = (255, 108, 64) if power else pal["barrel"]
    s = pygame.Surface((16, 16), pygame.SRCALPHA)

    # гусеницы
    for tx in (0, 12):
        s.fill(dark, (tx, 0, 4, 16))
        for i in range(4):
            y = 1 + i * 4 + (2 if frame else 0)
            if y + 2 <= 15:
                s.fill(tread, (tx, y, 4, 2))
        s.fill(light, (tx, 0, 4, 1))

    # корпус
    s.fill(dark, (4, 2, 8, 12))
    s.fill(body, (4, 3, 8, 10))
    s.fill(light, (4, 3, 8, 1))
    s.fill(dark, (4, 12, 8, 1))
    if stripes:
        s.fill(light, (4, 8, 8, 1))

    # ствол
    s.fill(dark, (6, 0, 4, 6))
    s.fill(barrel, (7, 0, 2, 6))

    # башня
    s.fill(dark, (5, 4, 6, 7))
    s.fill(light, (6, 5, 4, 5))
    s.fill(body, (6, 7, 4, 2))
    if star:
        s.fill(WHITE, (7, 6, 2, 2))
        s.fill(WHITE, (6, 7, 1, 1))
        s.fill(WHITE, (9, 7, 1, 1))
    return s


class Sprites:
    """Кэш готовых поверхностей."""

    def __init__(self):
        self._tanks = {}
        self._booms = {}
        self.base = build_base(False)
        self.base_dead = build_base(True)
        self.power_icons = {k: build_power_icon(k) for k in
                            ("star", "grenade", "helmet", "shovel", "tank", "clock")}

    def tank(self, style, direction, frame, variant=0):
        key = (style, direction, frame, variant)
        surf = self._tanks.get(key)
        if surf is None:
            pal = PALETTES.get(style, PALETTES["basic"])
            if style == "player":
                up = _tank_up(pal, frame, star=variant >= 1,
                              power=variant >= 2, stripes=variant >= 3)
            else:
                up = _tank_up(pal, frame)
            surf = pygame.transform.rotate(up, -90 * direction)
            self._tanks[key] = surf
        return surf

    def boom_frames(self, radius):
        frames = self._booms.get(radius)
        if frames is None:
            frames = build_boom_frames(radius)
            self._booms[radius] = frames
        return frames


# ------------------------------------------------------------------ тайлы
def draw_brick(s, x, y):
    s.fill(BRICK_D, (x, y, 8, 8))
    for row in (0, 4):
        s.fill(BRICK_C, (x, y + row, 4, 3))
        s.fill(BRICK_C, (x + 4, y + row, 4, 3))
        s.fill(BRICK_L, (x, y + row, 4, 1))
        s.fill(BRICK_L, (x + 4, y + row, 3, 1))


def draw_steel(s, x, y):
    s.fill(STEEL_D, (x, y, 8, 8))
    s.fill(STEEL_C, (x, y, 7, 7))
    s.fill(STEEL_L, (x, y, 6, 1))
    s.fill(STEEL_L, (x, y, 1, 6))
    s.fill(STEEL_D, (x + 2, y + 2, 1, 1))
    s.fill(STEEL_D, (x + 5, y + 5, 1, 1))


def draw_water(s, x, y, phase):
    s.fill(WATER_D, (x, y, 8, 8))
    s.fill(WATER_C, (x, y + 1, 8, 6))
    off = int(phase) % 8
    for i in range(2):
        yy = (y + 2 + i * 3 + off // 3) % 8
        s.fill(WATER_L, (x + 1, y + yy, 6, 1))


def draw_tree(s, x, y, phase):
    s.fill(TREE_D, (x, y, 8, 8))
    off = int(phase * 2) % 3
    s.fill(TREE_C, (x + 1, y + 1, 6, 6))
    s.fill(TREE_L, (x + 2 + off % 2, y + 2, 2, 2))
    s.fill(TREE_L, (x + 5 - off % 2, y + 4, 1, 1))
    s.fill(TREE_D, (x + 1, y + 6, 3, 1))


def draw_spawn_marker(s, x, y, t):
    """Мигающая звезда в точке появления врага."""
    frame = int(t * 10) % 4
    colors = (WHITE, YELLOW, RED, YELLOW)
    c = colors[frame]
    if frame == 3:
        return
    cx, cy = x + 8, y + 8
    s.fill(c, (cx - 1, cy - 5, 2, 10))
    s.fill(c, (cx - 5, cy - 1, 10, 2))
    s.fill(c, (cx - 3, cy - 3, 2, 2))
    s.fill(c, (cx + 1, cy - 3, 2, 2))
    s.fill(c, (cx - 3, cy + 1, 2, 2))
    s.fill(c, (cx + 1, cy + 1, 2, 2))


def draw_mini_tank(s, x, y, color=(140, 148, 168)):
    s.fill(color, (x, y, 2, 7))
    s.fill(color, (x + 6, y, 2, 7))
    s.fill(color, (x + 2, y + 1, 4, 5))
    s.fill((230, 236, 248), (x + 3, y + 2, 2, 2))


# ------------------------------------------------------------------ база
def build_base(dead=False):
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    if dead:
        s.fill((48, 40, 40), (2, 10, 12, 5))
        s.fill((88, 76, 64), (3, 9, 4, 3))
        s.fill((72, 60, 52), (9, 8, 4, 4))
        s.fill((120, 108, 92), (6, 11, 4, 2))
        s.fill((40, 32, 32), (5, 4, 3, 5))
        s.fill((28, 22, 22), (8, 3, 2, 4))
        s.fill(RED, (7, 6, 2, 2))
        return s

    gold, light, dark = (232, 192, 64), (255, 244, 168), (104, 68, 8)
    # крылья
    pygame.draw.polygon(s, dark, [(0, 5), (7, 2), (7, 11), (1, 10)])
    pygame.draw.polygon(s, dark, [(15, 5), (8, 2), (8, 11), (14, 10)])
    pygame.draw.polygon(s, gold, [(1, 6), (7, 4), (7, 10), (3, 9)])
    pygame.draw.polygon(s, gold, [(14, 6), (8, 4), (8, 10), (12, 9)])
    pygame.draw.polygon(s, light, [(2, 7), (6, 5), (6, 6), (3, 8)])
    pygame.draw.polygon(s, light, [(13, 7), (9, 5), (9, 6), (12, 8)])
    # тело и голова
    s.fill(dark, (6, 2, 4, 10))
    s.fill(gold, (7, 4, 2, 8))
    s.fill(dark, (6, 0, 5, 4))
    s.fill(light, (7, 1, 2, 2))
    # постамент
    s.fill(dark, (2, 11, 12, 4))
    s.fill(STEEL_C, (3, 11, 10, 2))
    s.fill(STEEL_L, (4, 11, 8, 1))
    s.fill((56, 64, 88), (4, 13, 8, 1))
    return s


# ------------------------------------------------------------------ бонусы
def build_power_icon(kind):
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    s.fill((16, 16, 26), (0, 0, 16, 16))
    pygame.draw.rect(s, (188, 196, 216), (0, 0, 16, 16), 1)
    s.fill((24, 24, 38), (1, 1, 14, 14))

    if kind == "star":
        pts = [(8, 2), (9, 6), (14, 6), (10, 9), (12, 14),
               (8, 11), (4, 14), (6, 9), (2, 6), (7, 6)]
        pygame.draw.polygon(s, YELLOW, pts)
        s.fill((150, 116, 8), (8, 5, 1, 1))
        s.fill(WHITE, (7, 7, 2, 2))

    elif kind == "grenade":
        pygame.draw.circle(s, (60, 64, 76), (8, 10), 5)
        pygame.draw.circle(s, (108, 116, 136), (7, 9), 3)
        s.fill((168, 176, 196), (6, 8, 2, 2))
        s.fill((120, 84, 36), (8, 3, 2, 3))
        s.fill((200, 160, 64), (9, 2, 2, 2))
        s.fill((248, 216, 96), (12, 4, 1, 1))

    elif kind == "helmet":
        pygame.draw.circle(s, (64, 176, 208), (8, 8), 6, draw_top_left=True,
                           draw_top_right=True)
        s.fill((64, 176, 208), (2, 8, 12, 3))
        s.fill((160, 240, 255), (4, 5, 3, 2))
        s.fill((32, 96, 128), (3, 11, 10, 1))

    elif kind == "shovel":
        s.fill((140, 96, 40), (7, 2, 2, 8))
        s.fill((196, 148, 72), (7, 2, 1, 8))
        s.fill((104, 68, 24), (5, 2, 6, 2))
        s.fill((148, 156, 180), (4, 9, 8, 5))
        s.fill((208, 216, 236), (5, 9, 4, 2))
        s.fill((88, 96, 120), (6, 13, 4, 1))

    elif kind == "tank":
        s.fill((120, 200, 240), (2, 4, 3, 8))
        s.fill((120, 200, 240), (11, 4, 3, 8))
        s.fill((200, 240, 255), (5, 5, 6, 7))
        s.fill((80, 150, 200), (7, 2, 2, 4))
        s.fill(WHITE, (6, 7, 2, 2))

    elif kind == "clock":
        pygame.draw.circle(s, (232, 236, 244), (8, 8), 6)
        pygame.draw.circle(s, (60, 72, 96), (8, 8), 6, 1)
        s.fill((60, 72, 96), (8, 4, 1, 5))
        s.fill((60, 72, 96), (8, 8, 4, 1))
        s.fill((200, 208, 224), (8, 4, 1, 1))
    return s


# ------------------------------------------------------------------ взрывы
def build_boom_frames(radius=22, seed=1):
    frames = []
    size = radius * 2
    for f in range(5):
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        rng = random.Random(seed * 131 + f * 17)
        rr = radius * (0.45 + 0.14 * f)
        for py in range(0, size, 2):
            for px in range(0, size, 2):
                dx = (px + 1 - radius) / rr
                dy = (py + 1 - radius) / rr
                d = math.hypot(dx, dy)
                if d <= 1.0 - 0.28 * rng.random():
                    if d < 0.30:
                        c = (255, 255, 224)
                    elif d < 0.55:
                        c = (255, 216, 96)
                    elif d < 0.78:
                        c = (248, 140, 48)
                    else:
                        c = (204, 52, 32)
                    s.fill(c, (px, py, 2, 2))
        frames.append(s)
    return frames
