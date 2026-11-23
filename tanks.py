"""ТАНЧИКИ — ретро-аркада в духе Battle City / SEGA.

Запуск:  python tanks.py
"""

import math
import os
import random
import sys

import numpy as np
import pygame

from art import (
    Sprites, draw_brick, draw_mini_tank, draw_spawn_marker, draw_steel,
    draw_tree, draw_water,
)
from audio import Audio
from retro import (
    BG, BG_FIELD, CYAN, DARK, DIM, DOWN, FIELD, FIELD_RECT, FPS, FRAME_C,
    FRAME_D, FRAME_L, GAMEOVER, GREEN, GRID, INTRO, LEFT, LOGICAL_H, LOGICAL_W,
    MARGIN, ORANGE, PANEL_BG, PANEL_LINE, PANEL_X, PAUSED, PLAYING, PURPLE,
    PixelFont, RED, RIGHT, STEEL, TEXT, TILE, TITLE, UP, WHITE, YELLOW,
    BRICK, EMPTY, TREE, WATER, BASE, CLEAR, clamp,
)
from world import (
    BASE_CENTER, Boom, Enemy, Level, Particle, Player, PowerUp,
    POWER_KINDS, POWER_NAMES, build_wave,
)

HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.txt")


def load_highscore():
    try:
        with open(HIGHSCORE_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip() or 0)
    except Exception:
        return 0


class Game:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption("ТАНЧИКИ — RETRO BATTLE")
        info = pygame.display.Info()
        scale = max(2, min(4, (info.current_h - 140) // LOGICAL_H))
        self.windowed_size = (LOGICAL_W * scale, LOGICAL_H * scale)
        self.win = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.logical = pygame.Surface((LOGICAL_W, LOGICAL_H)).convert()
        self.clock = pygame.time.Clock()
        self.font = PixelFont()
        self.sprites = Sprites()
        pygame.display.set_icon(
            pygame.transform.scale(self.sprites.tank("player", UP, 0, 0), (32, 32)))
        self.small_icons = {k: pygame.transform.scale(v, (12, 12))
                            for k, v in self.sprites.power_icons.items()}
        self.audio = Audio()
        self.running = True
        self.fullscreen = False
        self.crt_key = None
        self.scan_surf = None
        self.vignette = None
        self.veil = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)

        # общее состояние
        self.state = TITLE
        self.title_t = 0.0
        self.time = 0.0
        self.flash = 0.0
        self.shake = 0.0
        self.high_score = load_highscore()
        self.score = 0
        self.lives = 3
        self.weapon = 0
        self.stage = 1
        self.level = None
        self.player = None
        self.enemies = []
        self.bullets = []
        self.powerups = []
        self.particles = []
        self.booms = []
        self.wave = []
        self.spawned = 0
        self.kills = 0
        self.total_enemies = 20
        self.freeze = 0.0
        self.shovel = 0.0
        self.spawn_cd = 0.0
        self.spawn_marker = None
        self.marker_timer = 0.0
        self.respawn_timer = 0.0
        self.base_alive = True
        self.pending_clear = 0.0
        self.pending_over = 0.0
        self.clear_timer = 0.0
        self.clear_bonus = 0
        self.over_timer = 0.0
        self.intro_timer = 0.0
        self.toast = None
        self.speed_bonus = 0.0

        # автотест
        self.bot_mode = False
        self.bot_dir = None
        self.bot_fire = False

    # ================================================================ запуск
    def start_game(self):
        self.score = 0
        self.lives = 3
        self.weapon = 0
        self.stage = 1
        self.start_stage()

    def start_stage(self):
        self.level = Level(self.stage)
        self.time = 0.0
        self.bullets = []
        self.enemies = []
        self.powerups = []
        self.particles = []
        self.booms = []
        self.wave = build_wave(self.stage)
        self.spawned = 0
        self.kills = 0
        self.total_enemies = len(self.wave)
        self.freeze = 0.0
        self.shovel = 0.0
        self.spawn_cd = 1.2
        self.spawn_marker = None
        self.marker_timer = 0.0
        self.respawn_timer = 0.0
        self.base_alive = True
        self.pending_clear = 0.0
        self.pending_over = 0.0
        self.clear_timer = 0.0
        self.over_timer = 0.0
        self.toast = None
        self.speed_bonus = min(16.0, (self.stage - 1) * 2.0)
        self.player = None
        self.spawn_player()
        self.state = INTRO
        self.intro_timer = 1.8
        self.audio.start_music()

    def spawn_player(self):
        gx, gy = Level.PLAYER_SPAWN
        self.player = Player(self, MARGIN + gx * TILE, MARGIN + gy * TILE,
                             self.weapon)
        self.player.shield = 3.0

    # ================================================================ события
    def tanks(self):
        out = []
        if self.player is not None and self.player.alive:
            out.append(self.player)
        out.extend(e for e in self.enemies if e.alive)
        return out

    def add_boom(self, x, y, radius=22, dur=0.45):
        self.booms.append(Boom(x, y, radius, dur))

    def add_sparks(self, x, y, count, colors=None):
        palette = colors or (WHITE, YELLOW, ORANGE, RED)
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(20, 90)
            self.particles.append(Particle(
                x, y, math.cos(ang) * spd, math.sin(ang) * spd,
                random.uniform(0.18, 0.45), random.choice(palette),
                random.choice((1, 1, 2))))

    def on_enemy_killed(self, enemy):
        self.kills += 1
        self.score += enemy.score
        self.add_boom(enemy.cx, enemy.cy, 22, 0.45)
        self.add_sparks(enemy.cx, enemy.cy, 10)
        self.audio.play("boom")
        self.shake = max(self.shake, 0.35)
        if enemy.bonus:
            self.drop_powerup()

    def on_player_destroyed(self, player):
        self.add_boom(player.cx, player.cy, 26, 0.6)
        self.add_sparks(player.cx, player.cy, 16)
        self.audio.play("bigboom")
        self.flash = 0.6
        self.shake = 0.7
        self.player = None
        self.lives -= 1
        if self.lives < 0:
            self.pending_over = 2.0
        else:
            self.respawn_timer = 1.4

    def destroy_base(self):
        if not self.level.base_alive:
            return
        self.level.base_alive = False
        self.base_alive = False
        for gx, gy in self.level.base_tiles:
            self.level.grid[gy][gx] = EMPTY
        bx, by = BASE_CENTER
        self.add_boom(bx, by, 34, 0.85)
        self.add_sparks(bx, by, 26, (WHITE, YELLOW, ORANGE, RED))
        self.audio.play("bigboom")
        self.shake = 1.0
        self.flash = 0.9
        self.pending_over = 2.4

    def drop_powerup(self):
        for _ in range(100):
            gx = random.randint(2, 27)
            gy = random.randint(4, 24)
            if self.level.grid[gy][gx] in (EMPTY, TREE):
                kind = random.choices(POWER_KINDS,
                                      weights=(30, 14, 16, 14, 10, 16))[0]
                self.powerups.append(PowerUp(self, kind,
                                             MARGIN + gx * TILE,
                                             MARGIN + gy * TILE))
                return

    def show_toast(self, text):
        self.toast = [text, 1.6]

    def pickup(self, pu):
        self.powerups.remove(pu)
        self.audio.play("pickup")
        self.score += 500
        self.show_toast(POWER_NAMES[pu.kind])
        if pu.kind == "star":
            self.weapon = min(3, self.weapon + 1)
            if self.player is not None:
                self.player.weapon = self.weapon
                self.player.bullet_speed = 205.0 if self.weapon < 1 else 265.0
        elif pu.kind == "grenade":
            for e in self.enemies:
                if e.alive:
                    e.alive = False
                    self.kills += 1
                    self.score += e.score
                    self.add_boom(e.cx, e.cy, 22, 0.45)
                    self.add_sparks(e.cx, e.cy, 8)
            self.enemies = []
            self.audio.play("bigboom")
            self.shake = 0.9
        elif pu.kind == "helmet":
            if self.player is not None:
                self.player.shield = 12.0
        elif pu.kind == "shovel":
            self.shovel = 18.0
            self.level.set_wall(True)
        elif pu.kind == "tank":
            self.lives += 1
            self.audio.play("life")
        elif pu.kind == "clock":
            self.freeze = 8.0

    def finish_clear(self):
        self.state = CLEAR
        self.clear_bonus = 500 * self.stage
        self.score += self.clear_bonus
        self.clear_timer = 5.0
        self.audio.play("clear")

    def finish_game_over(self):
        self.state = GAMEOVER
        self.over_timer = 0.0
        self.save_highscore()
        self.audio.play("over")

    def next_stage(self):
        self.stage += 1
        self.start_stage()

    def save_highscore(self):
        if self.score > self.high_score:
            self.high_score = self.score
            try:
                with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
                    f.write(str(self.high_score))
            except Exception:
                pass

    # ================================================================ ввод
    def on_key(self, key):
        if key == pygame.K_F11:
            self.toggle_fullscreen()
            return
        if key == pygame.K_m:
            self.audio.toggle_mute()
            return
        if key == pygame.K_n:
            self.audio.toggle_music()
            return

        if self.state == TITLE:
            if key == pygame.K_ESCAPE:
                self.running = False
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.audio.play("pause")
                self.start_game()
        elif self.state == PLAYING:
            if key in (pygame.K_p, pygame.K_ESCAPE):
                self.state = PAUSED
                self.audio.play("pause")
        elif self.state == PAUSED:
            if key in (pygame.K_p, pygame.K_ESCAPE, pygame.K_RETURN):
                self.state = PLAYING
                self.audio.play("pause")
        elif self.state == CLEAR:
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.next_stage()
        elif self.state == GAMEOVER:
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) \
                    and self.over_timer > 1.0:
                self.state = TITLE
                self.title_t = 0.0

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.VIDEORESIZE and not self.fullscreen:
                size = (max(LOGICAL_W, e.w), max(LOGICAL_H, e.h))
                self.win = pygame.display.set_mode(size, pygame.RESIZABLE)
                self.crt_key = None
            elif e.type == pygame.KEYDOWN:
                self.on_key(e.key)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            info = pygame.display.Info()
            self.win = pygame.display.set_mode(
                (info.current_w, info.current_h), pygame.FULLSCREEN)
        else:
            self.win = pygame.display.set_mode(self.windowed_size,
                                               pygame.RESIZABLE)
        self.crt_key = None

    # ================================================================ логика
    def update(self, dt):
        self.time += dt
        self.flash = max(0.0, self.flash - dt * 2.5)
        self.shake = max(0.0, self.shake - dt * 3.0)

        if self.state == TITLE:
            self.title_t += dt
            return
        if self.state == INTRO:
            self.intro_timer -= dt
            self._update_effects(dt)
            if self.intro_timer <= 0:
                self.state = PLAYING
            return
        if self.state == PLAYING:
            self._update_playing(dt)
            self._update_effects(dt)
            return
        if self.state == PAUSED:
            return
        if self.state == CLEAR:
            self._update_effects(dt)
            self.clear_timer -= dt
            if self.clear_timer <= 0:
                self.next_stage()
            return
        if self.state == GAMEOVER:
            self._update_effects(dt)
            self.over_timer += dt
            return

    def _update_effects(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]
        self.booms = [b for b in self.booms if b.update(dt)]
        if self.toast:
            self.toast[1] -= dt
            if self.toast[1] <= 0:
                self.toast = None

    def _update_playing(self, dt):
        if self.freeze > 0.0:
            self.freeze -= dt
        if self.shovel > 0.0:
            self.shovel -= dt
            if self.shovel <= 0.0:
                self.level.set_wall(False)

        if self.player is not None:
            self.player.update(dt)
        elif self.lives >= 0 and self.pending_over <= 0:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0.0:
                self.spawn_player()

        for e in self.enemies:
            if e.alive:
                e.update(dt)

        for b in self.bullets:
            if not b.dead:
                b.update(dt)
        self._resolve_bullet_clash()

        # бонусы
        player = self.player
        for pu in list(self.powerups):
            if not pu.update(dt):
                self.powerups.remove(pu)
            elif player is not None and player.alive \
                    and pu.rect.colliderect(player.rect):
                self.pickup(pu)

        self.enemies = [e for e in self.enemies if e.alive]
        self.bullets = [b for b in self.bullets if not b.dead]

        # появление врагов
        if self.spawn_marker is not None:
            self.marker_timer -= dt
            if self.marker_timer <= 0.0:
                self._do_spawn()
        elif self.spawned < len(self.wave) and len(self.enemies) < 4:
            self.spawn_cd -= dt
            if self.spawn_cd <= 0.0:
                self._begin_spawn()

        # итоги раунда
        if self.pending_over > 0.0:
            self.pending_over -= dt
            if self.pending_over <= 0.0:
                self.finish_game_over()
            return
        if self.kills >= self.total_enemies and not self.enemies:
            if self.pending_clear <= 0.0:
                self.pending_clear = 1.2
        if self.pending_clear > 0.0:
            self.pending_clear -= dt
            if self.pending_clear <= 0.0:
                self.finish_clear()

    def _resolve_bullet_clash(self):
        live = [b for b in self.bullets if not b.dead]
        for i in range(len(live)):
            a = live[i]
            if a.dead:
                continue
            for j in range(i + 1, len(live)):
                b = live[j]
                if b.dead or a.team == b.team:
                    continue
                if a.rect.colliderect(b.rect):
                    a.dead = b.dead = True
                    self.add_sparks((a.cx + b.cx) / 2, (a.cy + b.cy) / 2, 4)
                    self.audio.play("steel")
                    break

    def _spawn_spot_busy(self, x, y):
        r = pygame.Rect(x - 2, y - 2, 20, 20)
        for tank in self.tanks():
            if r.colliderect(tank.rect):
                return True
        return False

    def _begin_spawn(self):
        spots = list(Level.SPAWNS)
        random.shuffle(spots)
        for gx, gy in spots:
            x = MARGIN + gx * TILE
            y = MARGIN + gy * TILE
            if not self._spawn_spot_busy(x, y):
                self.spawn_marker = (x, y)
                self.marker_timer = 1.0
                return
        self.spawn_cd = 0.4

    def _do_spawn(self):
        x, y = self.spawn_marker
        if self._spawn_spot_busy(x, y):
            self.spawn_marker = None
            self.spawn_cd = 0.4
            return
        kind, bonus = self.wave[self.spawned]
        self.spawned += 1
        self.enemies.append(Enemy(self, x, y, kind, bonus))
        self.spawn_marker = None
        self.spawn_cd = random.uniform(1.5, 2.8)
        self.audio.play("thud")

    # ================================================================ отрисовка
    def draw(self):
        s = self.logical
        s.fill(BG)
        if self.state == TITLE:
            self._draw_title(s)
        else:
            self._draw_field(s)
            self._draw_hud(s)
            if self.state == INTRO:
                self._draw_intro(s)
            elif self.state == PAUSED:
                self._draw_pause(s)
            elif self.state == CLEAR:
                self._draw_clear(s)
            elif self.state == GAMEOVER:
                self._draw_gameover(s)
        if self.flash > 0.0:
            self.veil.fill((255, 255, 255, int(min(150, self.flash * 220))))
            s.blit(self.veil, (0, 0))
        self.present()

    # ---------------------------------------------------------------- поле
    def _draw_field(self, s):
        s.fill(BG_FIELD, FIELD_RECT)
        lvl = self.level
        if lvl is None:
            return
        trees = []
        phase = self.time * 4.0
        for gy in range(GRID):
            row = lvl.grid[gy]
            for gx in range(GRID):
                t = row[gx]
                if t == EMPTY or t == BASE:
                    continue
                x = MARGIN + gx * TILE
                y = MARGIN + gy * TILE
                if t == BRICK:
                    draw_brick(s, x, y)
                elif t == STEEL:
                    draw_steel(s, x, y)
                elif t == WATER:
                    draw_water(s, x, y, phase)
                elif t == TREE:
                    trees.append((x, y))

        bx = MARGIN + 14 * TILE
        by = MARGIN + 26 * TILE
        s.blit(self.sprites.base if lvl.base_alive else self.sprites.base_dead,
               (bx, by))

        if self.spawn_marker is not None:
            mx, my = self.spawn_marker
            draw_spawn_marker(s, mx, my, self.time)

        for pu in self.powerups:
            if pu.ttl < 5.0 and int(self.time * 8) % 2 == 0:
                continue
            s.blit(self.sprites.power_icons[pu.kind], (pu.x, pu.y))

        for e in self.enemies:
            if e.alive:
                self._draw_enemy(s, e)
        if self.player is not None and self.player.alive:
            self._draw_player(s, self.player)

        for b in self.bullets:
            if b.dead:
                continue
            col = (255, 244, 176) if b.team == "player" else (255, 168, 120)
            x, y = int(b.x), int(b.y)
            s.fill(col, (x, y, 4, 4))
            s.fill(WHITE, (x + 1, y + 1, 2, 2))

        for boom in self.booms:
            boom.draw(s, self.sprites)

        for p in self.particles:
            a = clamp(p.life / p.max_life, 0.0, 1.0)
            if a > 0.45 or int(self.time * 30) % 2 == 0:
                s.fill(p.color, (int(p.x), int(p.y), p.size, p.size))

        for x, y in trees:
            draw_tree(s, x, y, phase)

        self._draw_frame(s)

        if self.toast:
            text, _ = self.toast
            w = self.font.width(text)
            rect = pygame.Rect(LOGICAL_W // 2 - w // 2 - 5, 12, w + 10, 13)
            s.fill((8, 10, 20), rect)
            pygame.draw.rect(s, (92, 104, 136), rect, 1)
            self.font.draw(s, text, LOGICAL_W // 2, 15, YELLOW, 1, center=True)

    def _draw_frame(self, s):
        outer = pygame.Rect(MARGIN - 4, MARGIN - 4, FIELD + 8, FIELD + 8)
        pygame.draw.rect(s, FRAME_D, outer, 4)
        pygame.draw.rect(s, FRAME_C, outer, 1)
        pygame.draw.rect(s, (56, 64, 92),
                         pygame.Rect(MARGIN - 1, MARGIN - 1, FIELD + 2, FIELD + 2),
                         1)
        for cx, cy in ((outer.left + 1, outer.top + 1),
                       (outer.right - 3, outer.top + 1),
                       (outer.left + 1, outer.bottom - 3),
                       (outer.right - 3, outer.bottom - 3)):
            s.fill(FRAME_L, (cx, cy, 2, 2))

    def _tank_frame(self, tank):
        return int(tank.tread // 5.0) % 2 if tank.moving else 0

    def _draw_enemy(self, s, e):
        style = e.kind
        if e.kind == "armor":
            style = "armor%d" % max(1, e.hp)
        if e.flash > 0 or (e.bonus and int(self.time * 8) % 2 == 0):
            style = "bonus"
        img = self.sprites.tank(style, e.dir, self._tank_frame(e))
        s.blit(img, (int(round(e.x)), int(round(e.y))))

    def _draw_player(self, s, p):
        img = self.sprites.tank("player", p.dir, self._tank_frame(p), p.weapon)
        s.blit(img, (int(round(p.x)), int(round(p.y))))
        if p.shield > 0.0 and int(self.time * 12) % 2 == 0:
            pygame.draw.rect(s, CYAN, p.rect.inflate(2, 2), 1)
            for cx, cy in ((p.cx - 9, p.cy), (p.cx + 9, p.cy),
                           (p.cx, p.cy - 9), (p.cx, p.cy + 9)):
                s.fill(WHITE, (int(cx), int(cy), 1, 1))

    # ---------------------------------------------------------------- HUD
    def _draw_hud(self, s):
        s.fill(PANEL_BG, (PANEL_X, 0, LOGICAL_W - PANEL_X, LOGICAL_H))
        pygame.draw.line(s, PANEL_LINE, (PANEL_X, 0), (PANEL_X, LOGICAL_H - 1))
        f = self.font
        x = PANEL_X + 6

        f.draw(s, "УРОВЕНЬ", x, 8, DIM)
        f.draw(s, f"{self.stage:02d}", x, 18, YELLOW, 2)
        pygame.draw.line(s, (36, 42, 62), (x, 37), (LOGICAL_W - 8, 37))

        f.draw(s, "ВРАГИ", x, 42, DIM)
        remaining = max(0, self.total_enemies - self.kills)
        for i in range(min(20, self.total_enemies)):
            col = i % 4
            row = i // 4
            ix = x + col * 12
            iy = 53 + row * 10
            if i < remaining:
                draw_mini_tank(s, ix, iy, (180, 188, 208))
            else:
                s.fill((38, 42, 58), (ix + 1, iy + 2, 6, 4))

        f.draw(s, "ЖИЗНИ", x, 110, DIM)
        draw_mini_tank(s, x, 121, YELLOW)
        f.draw(s, f"X{max(0, self.lives)}", x + 12, 122, TEXT)

        pygame.draw.line(s, (36, 42, 62), (x, 134), (LOGICAL_W - 8, 134))
        f.draw(s, "ОЧКИ", x, 140, DIM)
        f.draw(s, f"{min(self.score, 99999):05d}", x - 1, 150, TEXT, 2)

        f.draw(s, "РЕКОРД", x, 172, DIM)
        f.draw(s, f"{min(self.high_score, 99999):05d}", x, 182, (168, 176, 200))

        effects = []
        if self.player is not None and self.player.shield > 0:
            effects.append(("helmet", self.player.shield, 12.0))
        if self.freeze > 0:
            effects.append(("clock", self.freeze, 8.0))
        if self.shovel > 0:
            effects.append(("shovel", self.shovel, 18.0))
        for i, (kind, left, total) in enumerate(effects[:3]):
            ix = x + i * 15
            s.blit(self.small_icons[kind], (ix, 206))
            w = int(12 * clamp(left / total, 0.0, 1.0))
            s.fill((52, 58, 80), (ix, 220, 12, 2))
            s.fill(CYAN, (ix, 220, w, 2))

        f.draw(s, "M-ЗВУК", x, 236, (64, 72, 96))

    # ---------------------------------------------------------------- экраны
    def _draw_intro(self, s):
        band = pygame.Surface((PANEL_X, 52), pygame.SRCALPHA)
        band.fill((4, 6, 14, 224))
        s.blit(band, (0, 102))
        pygame.draw.line(s, (70, 80, 110), (0, 102), (PANEL_X, 102))
        pygame.draw.line(s, (70, 80, 110), (0, 153), (PANEL_X, 153))
        self.font.draw(s, f"УРОВЕНЬ {self.stage:02d}", LOGICAL_W // 2, 110,
                       YELLOW, 3, center=True, shadow=(40, 24, 0))
        self.font.draw(s, "ЗАЩИТИ БАЗУ", LOGICAL_W // 2, 136, TEXT, 1,
                       center=True, shadow=(0, 0, 0))

    def _draw_pause(self, s):
        self.veil.fill((4, 6, 14, 170))
        s.blit(self.veil, (0, 0))
        self.font.draw(s, "ПАУЗА", LOGICAL_W // 2, 96, WHITE, 4, center=True,
                       shadow=(20, 20, 40))
        self.font.draw(s, "P — ПРОДОЛЖИТЬ", LOGICAL_W // 2, 140, DIM, 1,
                       center=True)

    def _draw_clear(self, s):
        self.veil.fill((4, 6, 14, 180))
        s.blit(self.veil, (0, 0))
        self.font.draw(s, "УРОВЕНЬ ПРОЙДЕН", LOGICAL_W // 2, 84, YELLOW, 2,
                       center=True, shadow=(30, 16, 0))
        self.font.draw(s, f"БОНУС +{self.clear_bonus}", LOGICAL_W // 2, 112,
                       CYAN, 1, center=True)
        self.font.draw(s, f"ОЧКИ {min(self.score, 99999):05d}", LOGICAL_W // 2, 128, TEXT, 1,
                       center=True)
        if int(self.time * 2) % 2 == 0:
            self.font.draw(s, "ENTER — ДАЛЬШЕ", LOGICAL_W // 2, 152, WHITE, 1,
                           center=True)

    def _draw_gameover(self, s):
        self.veil.fill((8, 2, 8, 190))
        s.blit(self.veil, (0, 0))
        self.font.draw(s, "ИГРА ОКОНЧЕНА", LOGICAL_W // 2, 80, RED, 2,
                       center=True, shadow=(30, 0, 0))
        self.font.draw(s, f"ОЧКИ {min(self.score, 99999):05d}", LOGICAL_W // 2, 112, TEXT, 1,
                       center=True)
        if self.score >= self.high_score > 0:
            self.font.draw(s, "НОВЫЙ РЕКОРД!", LOGICAL_W // 2, 126, YELLOW, 1,
                           center=True)
        else:
            self.font.draw(s, f"РЕКОРД {self.high_score:05d}", LOGICAL_W // 2,
                           126, DIM, 1, center=True)
        if self.over_timer > 1.0 and int(self.time * 2) % 2 == 0:
            self.font.draw(s, "ENTER — В МЕНЮ", LOGICAL_W // 2, 156, WHITE, 1,
                           center=True)

    # ---------------------------------------------------------------- титул
    def _draw_title(self, s):
        s.fill((6, 6, 14))
        for i in range(0, LOGICAL_H, 8):
            s.fill((10, 12, 24), (0, i, LOGICAL_W, 1))
        for i in range(0, LOGICAL_W, 32):
            s.fill((9, 11, 22), (i, 0, 1, LOGICAL_H))

        t = self.title_t
        # цветной логотип
        letters = "TANKS"
        colors = (RED, ORANGE, YELLOW, GREEN, CYAN)
        total_w = self.font.width(letters, 6)
        x0 = LOGICAL_W // 2 - total_w // 2
        for i, ch in enumerate(letters):
            self.font.draw(s, ch, x0 + i * 36 + 2, 26 + 3, (48, 24, 40), 6)
            self.font.draw(s, ch, x0 + i * 36, 26, colors[i % len(colors)], 6)
        self.font.draw(s, "ТАНЧИКИ", LOGICAL_W // 2, 76, CYAN, 3, center=True,
                       shadow=(0, 24, 40))
        self.font.draw(s, "RETRO BATTLE CITY", LOGICAL_W // 2, 104, DIM, 1,
                       center=True)

        if int(t * 2) % 2 == 0:
            self.font.draw(s, "НАЖМИ ENTER", LOGICAL_W // 2, 124, WHITE, 2,
                           center=True, shadow=(24, 24, 40))

        lines = ("СТРЕЛКИ / WASD — ЕЗДА", "ПРОБЕЛ — ОГОНЬ",
                 "P / ESC — ПАУЗА", "M — ЗВУК   N — МУЗЫКА",
                 "F11 — ПОЛНЫЙ ЭКРАН")
        for i, line in enumerate(lines):
            self.font.draw(s, line, LOGICAL_W // 2, 146 + i * 11, (168, 180, 208),
                           1, center=True)

        # парад танков
        road_y = 206
        s.fill((18, 20, 34), (0, road_y + 12, LOGICAL_W, 1))
        for i in range(0, LOGICAL_W, 12):
            s.fill((28, 30, 48), (i, road_y + 12, 5, 1))
        px = int((t * 34) % (LOGICAL_W + 48)) - 24
        frame = int(t * 12) % 2
        s.blit(self.sprites.tank("player", RIGHT, frame, 0), (px, road_y - 4))
        ex = LOGICAL_W - (int(t * 26) % (LOGICAL_W + 48)) + 20
        s.blit(self.sprites.tank("power", LEFT, frame), (ex, road_y + 14))
        if int(t * 3) % 3 == 0:
            s.fill(YELLOW, (px + 18, road_y + 2, 3, 2))
        if int(t * 3) % 4 == 1:
            s.fill(ORANGE, (ex - 3, road_y + 20, 3, 2))

        pygame.draw.line(s, (44, 50, 74), (48, 238), (LOGICAL_W - 48, 238))
        self.font.draw(s, f"РЕКОРД {self.high_score:05d}", LOGICAL_W // 2, 242,
                       YELLOW, 1, center=True)

    # ---------------------------------------------------------------- вывод
    def present(self):
        w, h = self.win.get_size()
        scale = max(1, min(w // LOGICAL_W, h // LOGICAL_H))
        sw, sh = LOGICAL_W * scale, LOGICAL_H * scale
        if self.crt_key != (scale, sw, sh):
            self._build_crt(scale, sw, sh)
        img = pygame.transform.scale(self.logical, (sw, sh))
        self.win.fill((0, 0, 0))
        ox = (w - sw) // 2
        oy = (h - sh) // 2
        if self.shake > 0.0:
            amp = int(self.shake * 6)
            if amp > 0:
                ox += random.randint(-amp, amp)
                oy += random.randint(-amp, amp)
        self.win.blit(img, (ox, oy))
        self.win.blit(self.scan_surf, (ox, oy))
        self.win.blit(self.vignette, (ox, oy))
        pygame.display.flip()

    def _build_crt(self, scale, sw, sh):
        self.scan_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for y in range(0, sh, max(1, scale)):
            pygame.draw.line(self.scan_surf, (0, 0, 0, 30), (0, y), (sw, y))
        xs = np.linspace(-1.0, 1.0, sw)
        ys = np.linspace(-1.0, 1.0, sh)
        d = np.sqrt((xs[None, :] ** 2) * 0.85 + (ys[:, None] ** 2))
        alpha = (np.clip((d - 0.62) / 0.9, 0.0, 1.0) ** 1.7) * 170.0
        rgba = np.zeros((sh, sw, 4), dtype=np.uint8)
        rgba[..., 3] = alpha.astype(np.uint8)
        self.vignette = pygame.image.frombuffer(
            rgba.tobytes(), (sw, sh), "RGBA").convert_alpha()
        self.crt_key = (scale, sw, sh)

    # ---------------------------------------------------------------- цикл
    def run(self):
        while self.running:
            dt = min(0.05, self.clock.tick(FPS) / 1000.0)
            self.handle_events()
            self.update(dt)
            self.draw()
        self.save_highscore()
        pygame.quit()


# ==================================================================== отладка
def selftest(frames=3000):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    g = Game()
    g.bot_mode = True
    g.start_game()
    rng = random.Random(5)
    overs = 0
    for i in range(frames):
        if i % 30 == 0:
            g.bot_dir = rng.choice([UP, DOWN, LEFT, RIGHT, None])
            g.bot_fire = rng.random() < 0.75
        g.update(1.0 / 60.0)
        if i % 15 == 0:
            g.draw()
        if g.state == GAMEOVER:
            overs += 1
            if overs > 2:
                break
            g.start_game()
            g.bot_mode = True
    print("selftest ok | state", g.state, "| stage", g.stage,
          "| kills", g.kills, "| score", g.score,
          "| enemies", len(g.enemies), "| bullets", len(g.bullets))
    pygame.quit()


def screenshots():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    g = Game()
    g.bot_mode = True
    g.start_game()
    g.state = PLAYING
    rng = random.Random(11)
    for i in range(300):
        if i % 25 == 0:
            g.bot_dir = rng.choice([UP, DOWN, LEFT, RIGHT])
            g.bot_fire = rng.random() < 0.8
        g.update(1.0 / 60.0)
    g.pending_over = 0.0
    g.pending_clear = 0.0
    if g.player is None:
        g.spawn_player()
    g.player.shield = 0.0
    g.state = PLAYING
    g.draw()
    pygame.image.save(pygame.transform.scale(g.logical, (1280, 1024)),
                      "shot_play.png")

    g.state = TITLE
    g.title_t = 2.2
    g.draw()
    pygame.image.save(pygame.transform.scale(g.logical, (1280, 1024)),
                      "shot_title.png")
    print("saved shot_play.png / shot_title.png")
    pygame.quit()


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--shot" in sys.argv:
        screenshots()
    else:
        Game().run()
