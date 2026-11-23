"""Мир игры: карта, танки, пули, бонусы, эффекты."""

import math
import random

import pygame

from retro import (
    BASE, BRICK, DIRV, DOWN, EMPTY, FIELD_RECT, GRID, LEFT, MARGIN,
    SOLID_FOR_TANK, STEEL, TILE, TREE, WATER, UP, RIGHT,
)

ENEMY_STATS = {
    "basic": dict(speed=44.0, hp=1, bullet=160.0, score=100),
    "fast": dict(speed=88.0, hp=1, bullet=160.0, score=200),
    "power": dict(speed=56.0, hp=1, bullet=235.0, score=300),
    "armor": dict(speed=52.0, hp=4, bullet=180.0, score=400),
}

BASE_CENTER = (MARGIN + 15 * TILE, MARGIN + 26 * TILE)


def build_wave(stage):
    rng = random.Random(7000 + stage * 31)
    total = 20
    wave = ["basic"] * total
    n_fast = min(6, 1 + stage)
    n_power = min(6, max(0, stage - 1))
    n_armor = min(6, max(0, stage - 1) * 2)
    i = total - 1
    for kind, count in (("fast", n_fast), ("power", n_power), ("armor", n_armor)):
        for _ in range(count):
            if i < 4:
                break
            wave[i] = kind
            i -= 1
    rng.shuffle(wave)
    bonus_idx = {3, 10}
    return [(kind, idx in bonus_idx) for idx, kind in enumerate(wave)]


class Level:
    """Сетка 30x30 по 8 пикселей."""

    SPAWNS = ((0, 0), (14, 0), (28, 0))
    PLAYER_SPAWN = (10, 26)

    def __init__(self, stage):
        self.stage = stage
        self.rng = random.Random(4242 + stage * 977)
        self.grid = [[EMPTY] * GRID for _ in range(GRID)]
        self.base_tiles = [(14, 26), (15, 26), (14, 27), (15, 27)]
        self.wall_tiles = [(x, y) for y in (24, 25, 26, 27, 28, 29)
                           for x in (12, 13, 14, 15, 16, 17)
                           if (x, y) not in self.base_tiles]
        self.base_alive = True
        self._generate(stage)

    # ---------------------------------------------------------------- карта
    def _clear(self, x0, y0, x1, y1):
        for gy in range(max(0, y0), min(GRID, y1 + 1)):
            for gx in range(max(0, x0), min(GRID, x1 + 1)):
                self.grid[gy][gx] = EMPTY

    def _generate(self, stage):
        rng = self.rng
        blocks = [[EMPTY] * 15 for _ in range(15)]
        clusters = 24 + min(20, stage * 3)
        for _ in range(clusters):
            bx = rng.randrange(0, 8)
            by = rng.randrange(0, 15)
            r = rng.random()
            if r < 0.60:
                t = BRICK
            elif r < 0.76:
                t = STEEL if stage > 1 else BRICK
            elif r < 0.90:
                t = WATER
            else:
                t = TREE
            w = rng.randint(1, 3)
            h = rng.randint(1, 3)
            for yy in range(by, min(15, by + h)):
                for xx in range(bx, min(8, bx + w)):
                    if rng.random() < 0.85:
                        blocks[yy][xx] = t
                        blocks[yy][14 - xx] = t

        for by in range(15):
            for bx in range(15):
                t = blocks[by][bx]
                if t == EMPTY:
                    continue
                for gy in (by * 2, by * 2 + 1):
                    for gx in (bx * 2, bx * 2 + 1):
                        self.grid[gy][gx] = t

        # свободные зоны: спавны, база, старт игрока
        self._clear(0, 0, 3, 3)
        self._clear(13, 0, 16, 3)
        self._clear(26, 0, 29, 3)
        self._clear(9, 25, 12, 28)
        self._clear(10, 23, 19, 29)
        # открытая стартовая площадка и выход к центральному коридору
        self._clear(4, 22, 11, 29)
        self._clear(8, 22, 17, 23)

        # центральный коридор всегда проходим (сталь/вода убираются)
        for gy in range(0, 25):
            for gx in range(12, 18):
                if self.grid[gy][gx] in (STEEL, WATER):
                    self.grid[gy][gx] = BRICK if rng.random() < 0.55 else EMPTY

        # гарантированные водоёмы и стальные блоки для разнообразия
        for _ in range(2 + (1 if stage > 2 else 0)):
            for _try in range(40):
                gx = rng.randrange(1, 25)
                gy = rng.randrange(4, 21)
                if 12 <= gx <= 17 or gx + 3 > GRID - 1:
                    continue
                w = rng.randint(2, 4)
                h = rng.randint(2, 3)
                self._stamp(gx, gy, w, h, WATER)
                self._stamp(GRID - 1 - gx - w, gy, w, h, WATER)
                break
        for _ in range(1 + stage // 2):
            for _try in range(40):
                gx = rng.randrange(1, 26)
                gy = rng.randrange(4, 21)
                if 12 <= gx <= 17:
                    continue
                self._stamp(gx, gy, 2, 2, STEEL)
                self._stamp(GRID - 1 - gx - 1, gy, 2, 2, STEEL)
                break

        for gx, gy in self.base_tiles:
            self.grid[gy][gx] = BASE
        for gx, gy in self.wall_tiles:
            self.grid[gy][gx] = BRICK

    def _stamp(self, gx0, gy0, w, h, tile):
        for gy in range(gy0, min(GRID, gy0 + h)):
            for gx in range(gx0, min(GRID, gx0 + w)):
                if gx >= 0:
                    self.grid[gy][gx] = tile

    # ---------------------------------------------------------------- утилиты
    def set_wall(self, steel):
        for gx, gy in self.wall_tiles:
            self.grid[gy][gx] = STEEL if steel else BRICK

    def tile(self, gx, gy):
        if 0 <= gx < GRID and 0 <= gy < GRID:
            return self.grid[gy][gx]
        return STEEL

    def px_to_tile(self, px, py):
        return int((px - MARGIN) // TILE), int((py - MARGIN) // TILE)

    def blocked_rect(self, rect):
        if (rect.left < FIELD_RECT.left or rect.top < FIELD_RECT.top
                or rect.right > FIELD_RECT.right or rect.bottom > FIELD_RECT.bottom):
            return True
        x0 = max(0, (rect.left - MARGIN) // TILE)
        x1 = min(GRID - 1, (rect.right - 1 - MARGIN) // TILE)
        y0 = max(0, (rect.top - MARGIN) // TILE)
        y1 = min(GRID - 1, (rect.bottom - 1 - MARGIN) // TILE)
        for gy in range(y0, y1 + 1):
            row = self.grid[gy]
            for gx in range(x0, x1 + 1):
                if row[gx] in SOLID_FOR_TANK:
                    return True
        return False


# ====================================================================== танки
class Tank:
    SIZE = 16
    team = "enemy"

    def __init__(self, game, x, y, direction=UP):
        self.game = game
        self.x = float(x)
        self.y = float(y)
        self.dir = direction
        self.speed = 60.0
        self.hp = 1
        self.alive = True
        self.moving = False
        self.tread = 0.0
        self.cooldown = 0.0
        self.shield = 0.0
        self.flash = 0.0

    # ------------------------------------------------------------- свойства
    @property
    def cx(self):
        return self.x + 8

    @property
    def cy(self):
        return self.y + 8

    @property
    def hitbox(self):
        return pygame.Rect(int(round(self.x)) + 2, int(round(self.y)) + 2, 12, 12)

    @property
    def rect(self):
        return pygame.Rect(int(round(self.x)), int(round(self.y)), 16, 16)

    # ------------------------------------------------------------- движение
    def can_be_at(self, x, y):
        r = pygame.Rect(int(x) + 2, int(y) + 2, 12, 12)
        if self.game.level.blocked_rect(r):
            return False
        for other in self.game.tanks():
            if other is self or not other.alive:
                continue
            if r.colliderect(other.hitbox):
                return False
        return True

    def move_axis(self, dx, dy):
        dist = max(abs(dx), abs(dy))
        if dist <= 0:
            return False
        steps = max(1, int(math.ceil(dist)))
        sx, sy = dx / steps, dy / steps
        moved = False
        for _ in range(steps):
            if not self.can_be_at(self.x + sx, self.y + sy):
                break
            self.x += sx
            self.y += sy
            moved = True
        if not moved:
            # помощь на поворотах: чуть сместиться вбок и проскользнуть
            offs = (2, -2, 3, -3)
            for off in offs:
                nx, ny = (self.x, self.y + off) if dx else (self.x + off, self.y)
                if self.can_be_at(nx + sx, ny + sy):
                    self.x, self.y = nx, ny
                    moved = True
                    break
        if moved:
            self.tread += dist
        return moved

    def hit(self):
        self.hp -= 1
        if self.hp <= 0:
            self.alive = False
            self.game.on_enemy_killed(self)
        else:
            self.flash = 0.12
            self.game.audio.play("hit")
            self.game.add_sparks(self.cx, self.cy, 4)


# ====================================================================== игрок
class Player(Tank):
    team = "player"

    def __init__(self, game, x, y, weapon=0):
        super().__init__(game, x, y, UP)
        self.speed = 80.0
        self.weapon = weapon
        self.bullet_speed = 205.0 if weapon < 1 else 265.0
        self.shield = 3.0

    def update(self, dt):
        g = self.game
        self.cooldown = max(0.0, self.cooldown - dt)
        self.shield = max(0.0, self.shield - dt)
        self.flash = max(0.0, self.flash - dt)

        if g.bot_mode:
            d = g.bot_dir
            fire = g.bot_fire
        else:
            keys = pygame.key.get_pressed()
            d = None
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                d = UP
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                d = DOWN
            elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
                d = LEFT
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                d = RIGHT
            fire = keys[pygame.K_SPACE]

        if d is not None:
            self.dir = d
            dx, dy = DIRV[d]
            self.moving = self.move_axis(dx * self.speed * dt, dy * self.speed * dt)
        else:
            self.moving = False

        if fire and self.cooldown <= 0.0:
            self.shoot()

    def max_bullets(self):
        return 2 if self.weapon >= 1 else 1

    def shoot(self):
        g = self.game
        live = sum(1 for b in g.bullets if b.owner is self and not b.dead)
        if live >= self.max_bullets():
            return
        dx, dy = DIRV[self.dir]
        bx = self.cx + dx * 9 - 2
        by = self.cy + dy * 9 - 2
        power = self.weapon >= 2
        g.bullets.append(Bullet(g, self, bx, by, self.dir,
                                self.bullet_speed, power=power))
        self.cooldown = 0.20
        g.audio.play("shoot_power" if power else "shoot")

    def hurt(self):
        if self.shield > 0.0:
            self.game.add_sparks(self.cx, self.cy, 6)
            self.game.audio.play("steel")
            return
        self.alive = False
        self.game.on_player_destroyed(self)


# ====================================================================== враги
class Enemy(Tank):
    team = "enemy"

    def __init__(self, game, x, y, kind="basic", bonus=False):
        super().__init__(game, x, y, DOWN)
        stats = ENEMY_STATS[kind]
        self.kind = kind
        self.bonus = bonus
        self.hp = stats["hp"]
        self.max_hp = stats["hp"]
        self.speed = stats["speed"] + game.speed_bonus
        self.bullet_speed = stats["bullet"]
        self.score = stats["score"]
        self.think = 0.0
        self.shoot_timer = random.uniform(0.6, 1.6)
        self.dir = random.choice((DOWN, LEFT, RIGHT))

    def update(self, dt):
        g = self.game
        self.flash = max(0.0, self.flash - dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        if g.freeze > 0.0:
            self.moving = False
            return

        self.think -= dt
        if self.think <= 0.0:
            self.choose_dir()
            self.think = random.uniform(0.5, 1.5)

        dx, dy = DIRV[self.dir]
        self.moving = self.move_axis(dx * self.speed * dt, dy * self.speed * dt)
        if not self.moving:
            self.choose_dir(force=True)
            self.think = random.uniform(0.25, 0.7)

        self.shoot_timer -= dt
        if self.shoot_timer <= 0.0:
            if self._aligned() or random.random() < 0.35:
                self.shoot()
            self.shoot_timer = random.uniform(0.7, 1.9)

    # --------------------------------------------------------------- ИИ
    def choose_dir(self, force=False):
        g = self.game
        target = BASE_CENTER
        if g.player is not None and random.random() < 0.65:
            target = (g.player.cx, g.player.cy)
        dx = target[0] - self.cx
        dy = target[1] - self.cy
        dirs = [UP, RIGHT, DOWN, LEFT]
        random.shuffle(dirs)
        if not force and random.random() < 0.8:
            pref = []
            if abs(dx) > 8:
                pref.append(RIGHT if dx > 0 else LEFT)
            if abs(dy) > 8:
                pref.append(DOWN if dy > 0 else UP)
            random.shuffle(pref)
            dirs = pref + dirs
        for d in dirs:
            vx, vy = DIRV[d]
            if self.can_be_at(self.x + vx * 10, self.y + vy * 10):
                self.dir = d
                return

    def _aligned(self):
        g = self.game
        targets = [BASE_CENTER]
        if g.player is not None and g.level.base_alive:
            targets.append((g.player.cx, g.player.cy))
        for tx, ty in targets:
            if self.dir in (UP, DOWN):
                if abs(tx - self.cx) < 9 and (ty - self.cy) * DIRV[self.dir][1] > 0:
                    return True
            else:
                if abs(ty - self.cy) < 9 and (tx - self.cx) * DIRV[self.dir][0] > 0:
                    return True
        return False

    def shoot(self):
        g = self.game
        if any(b.owner is self and not b.dead for b in g.bullets):
            return
        dx, dy = DIRV[self.dir]
        bx = self.cx + dx * 9 - 2
        by = self.cy + dy * 9 - 2
        g.bullets.append(Bullet(g, self, bx, by, self.dir, self.bullet_speed))
        g.audio.play("shoot")
        self.shoot_timer = random.uniform(0.8, 1.8)


# ====================================================================== пули
class Bullet:
    def __init__(self, game, owner, x, y, direction, speed, power=False):
        self.game = game
        self.owner = owner
        self.team = owner.team
        self.x = float(x)
        self.y = float(y)
        self.dir = direction
        self.dx, self.dy = DIRV[direction]
        self.speed = speed
        self.power = power
        self.dead = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), 4, 4)

    @property
    def cx(self):
        return self.x + 2

    @property
    def cy(self):
        return self.y + 2

    def update(self, dt):
        dist = self.speed * dt
        steps = max(1, int(math.ceil(dist / 2.0)))
        step = dist / steps
        for _ in range(steps):
            if self.dead:
                return
            self.x += self.dx * step
            self.y += self.dy * step
            self._check()

    def _check(self):
        g = self.game
        lvl = g.level
        r = self.rect
        if (r.left < FIELD_RECT.left or r.top < FIELD_RECT.top
                or r.right > FIELD_RECT.right or r.bottom > FIELD_RECT.bottom):
            self.dead = True
            g.add_sparks(self.cx, self.cy, 3)
            return

        x0 = max(0, (r.left - MARGIN) // TILE)
        x1 = min(GRID - 1, (r.right - 1 - MARGIN) // TILE)
        y0 = max(0, (r.top - MARGIN) // TILE)
        y1 = min(GRID - 1, (r.bottom - 1 - MARGIN) // TILE)
        for gy in range(y0, y1 + 1):
            for gx in range(x0, x1 + 1):
                t = lvl.grid[gy][gx]
                if t in (BRICK, STEEL, BASE, TREE, WATER):
                    if t in (BRICK, STEEL, BASE):
                        self._hit_tile(gx, gy)
                        return

        for tank in g.tanks():
            if tank.team == self.team or not tank.alive:
                continue
            if r.colliderect(tank.hitbox):
                self.dead = True
                g.add_sparks(self.cx, self.cy, 4)
                if tank.team == "player":
                    tank.hurt()
                else:
                    tank.hit()
                return

    def _hit_tile(self, gx, gy):
        g = self.game
        lvl = g.level
        t = lvl.grid[gy][gx]
        self.dead = True
        if t == BASE:
            if self.team == "player":
                g.audio.play("steel")
                g.add_sparks(self.cx, self.cy, 4)
                return
            g.destroy_base()
            return
        if t == STEEL and not self.power:
            g.audio.play("steel")
            g.add_sparks(self.cx, self.cy, 4)
            return
        if t in (BRICK, STEEL):
            lvl.grid[gy][gx] = EMPTY
            # дырка шириной с танк: сносим соседний кирпич поперёк полёта
            if self.dx:
                alt = gy + (-1 if self.cy < MARGIN + gy * TILE + 4 else 1)
                if 0 <= alt < GRID and lvl.grid[alt][gx] == BRICK:
                    lvl.grid[alt][gx] = EMPTY
            else:
                alt = gx + (-1 if self.cx < MARGIN + gx * TILE + 4 else 1)
                if 0 <= alt < GRID and lvl.grid[gy][alt] == BRICK:
                    lvl.grid[gy][alt] = EMPTY
            g.audio.play("brick")
            g.add_sparks(self.cx, self.cy, 5)


# ====================================================================== бонусы
POWER_KINDS = ("star", "grenade", "helmet", "shovel", "tank", "clock")
POWER_NAMES = {
    "star": "ЗВЕЗДА",
    "grenade": "БОМБА",
    "helmet": "ЩИТ",
    "shovel": "ЛОПАТА",
    "tank": "ЖИЗНЬ",
    "clock": "ЗАМОРОЗКА",
}


class PowerUp:
    def __init__(self, game, kind, x, y):
        self.game = game
        self.kind = kind
        self.x = x
        self.y = y
        self.ttl = 22.0

    @property
    def rect(self):
        return pygame.Rect(self.x + 1, self.y + 1, 14, 14)

    def update(self, dt):
        self.ttl -= dt
        return self.ttl > 0.0


# ====================================================================== эффекты
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")

    def __init__(self, x, y, vx, vy, life, color, size=2):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= dt
        return self.life > 0.0


class Boom:
    def __init__(self, x, y, radius=22, dur=0.45):
        self.x = x
        self.y = y
        self.radius = radius
        self.dur = dur
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        return self.t < self.dur

    def draw(self, surf, sprites):
        frames = sprites.boom_frames(self.radius)
        idx = min(len(frames) - 1, int(self.t / self.dur * len(frames)))
        img = frames[idx]
        surf.blit(img, (int(self.x - self.radius), int(self.y - self.radius)))
