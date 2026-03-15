import pygame
import math
import random
import sys

pygame.init()

WIDTH, HEIGHT = 1024, 768
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Squad Survivors")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)

# Colors
BG = (20, 20, 30)
PLAYER_COLOR = (80, 200, 255)
ALLY_COLORS = [
    (100, 255, 100), (255, 255, 100), (255, 180, 50),
    (200, 100, 255), (255, 100, 200), (100, 255, 220),
]
ENEMY_COLOR = (255, 60, 60)
BULLET_COLOR = (255, 255, 200)
HEALTH_BG = (60, 60, 60)
HEALTH_FG = (80, 220, 80)


class Bullet:
    SPEED = 8
    RADIUS = 4
    LIFETIME = 90  # frames

    def __init__(self, x, y, dx, dy):
        self.x, self.y = x, y
        length = math.hypot(dx, dy) or 1
        self.vx = dx / length * self.SPEED
        self.vy = dy / length * self.SPEED
        self.life = self.LIFETIME

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self):
        pygame.draw.circle(screen, BULLET_COLOR, (int(self.x), int(self.y)), self.RADIUS)


class Unit:
    RADIUS = 14
    SPEED = 2.5
    SHOOT_COOLDOWN = 25

    def __init__(self, x, y, color, is_player=False):
        self.x, self.y = float(x), float(y)
        self.color = color
        self.is_player = is_player
        self.cooldown = 0
        self.hp = 5 if is_player else 3

    def move_towards(self, tx, ty, allies):
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 3:
            return
        nx, ny = dx / dist * self.SPEED, dy / dist * self.SPEED
        new_x, new_y = self.x + nx, self.y + ny
        # Separation from allies
        for a in allies:
            if a is self:
                continue
            adx, ady = new_x - a.x, new_y - a.y
            adist = math.hypot(adx, ady)
            if adist < self.RADIUS * 2.5 and adist > 0:
                push = (self.RADIUS * 2.5 - adist) * 0.3
                new_x += adx / adist * push
                new_y += ady / adist * push
        self.x = max(self.RADIUS, min(WIDTH - self.RADIUS, new_x))
        self.y = max(self.RADIUS, min(HEIGHT - self.RADIUS, new_y))

    def shoot_at(self, target, bullets):
        if self.cooldown > 0:
            self.cooldown -= 1
            return
        dx, dy = target.x - self.x, target.y - self.y
        if math.hypot(dx, dy) < 350:
            bullets.append(Bullet(self.x, self.y, dx, dy))
            self.cooldown = self.SHOOT_COOLDOWN

    def draw(self):
        pos = (int(self.x), int(self.y))
        pygame.draw.circle(screen, self.color, pos, self.RADIUS)
        pygame.draw.circle(screen, (255, 255, 255), pos, self.RADIUS, 2)
        # HP bar
        bar_w = self.RADIUS * 2
        max_hp = 5 if self.is_player else 3
        filled = bar_w * self.hp / max_hp
        bx = int(self.x - bar_w / 2)
        by = int(self.y - self.RADIUS - 8)
        pygame.draw.rect(screen, HEALTH_BG, (bx, by, bar_w, 4))
        pygame.draw.rect(screen, HEALTH_FG, (bx, by, int(filled), 4))


class Enemy:
    RADIUS = 12
    SPEED = 1.2

    def __init__(self):
        side = random.randint(0, 3)
        if side == 0:
            self.x, self.y = random.randint(0, WIDTH), -30
        elif side == 1:
            self.x, self.y = random.randint(0, WIDTH), HEIGHT + 30
        elif side == 2:
            self.x, self.y = -30, random.randint(0, HEIGHT)
        else:
            self.x, self.y = WIDTH + 30, random.randint(0, HEIGHT)
        self.x, self.y = float(self.x), float(self.y)
        self.hp = 2

    def update(self, target):
        dx, dy = target.x - self.x, target.y - self.y
        dist = math.hypot(dx, dy) or 1
        self.x += dx / dist * self.SPEED
        self.y += dy / dist * self.SPEED

    def draw(self):
        # Draw as diamond
        cx, cy = int(self.x), int(self.y)
        r = self.RADIUS
        points = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        pygame.draw.polygon(screen, ENEMY_COLOR, points)
        pygame.draw.polygon(screen, (200, 40, 40), points, 2)


def find_closest_enemy(unit, enemies):
    best, best_d = None, float('inf')
    for e in enemies:
        d = math.hypot(e.x - unit.x, e.y - unit.y)
        if d < best_d:
            best, best_d = e, d
    return best


def run():
    player = Unit(WIDTH / 2, HEIGHT / 2, PLAYER_COLOR, is_player=True)
    allies = []
    enemies = []
    bullets = []
    score = 0
    spawn_timer = 0
    spawn_interval = 90  # frames between spawns
    wave = 1
    wave_timer = 0

    running = True
    game_over = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if game_over and event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                return run()

        if game_over:
            screen.fill(BG)
            t = font.render(f"GAME OVER — Score: {score}  Press R to restart", True, (255, 100, 100))
            screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2))
            pygame.display.flip()
            clock.tick(FPS)
            continue

        # Input
        keys = pygame.key.get_pressed()
        mx, my = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            my -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            my += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            mx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            mx += 1
        if mx or my:
            length = math.hypot(mx, my)
            player.x += mx / length * 3.5
            player.y += my / length * 3.5
            player.x = max(player.RADIUS, min(WIDTH - player.RADIUS, player.x))
            player.y = max(player.RADIUS, min(HEIGHT - player.RADIUS, player.y))

        # Spawn enemies
        spawn_timer += 1
        wave_timer += 1
        if wave_timer > 600:
            wave += 1
            wave_timer = 0
            spawn_interval = max(20, spawn_interval - 8)
        if spawn_timer >= spawn_interval:
            spawn_timer = 0
            for _ in range(wave):
                enemies.append(Enemy())

        # Allies follow player loosely
        squad = [player] + allies
        for i, a in enumerate(allies):
            # Orbit around player
            angle = (2 * math.pi * i) / max(len(allies), 1)
            orbit_r = 50 + len(allies) * 5
            tx = player.x + math.cos(angle) * orbit_r
            ty = player.y + math.sin(angle) * orbit_r
            a.move_towards(tx, ty, squad)

        # Shooting — player and allies shoot at closest enemy
        for u in squad:
            target = find_closest_enemy(u, enemies)
            if target:
                u.shoot_at(target, bullets)

        # Update bullets
        for b in bullets:
            b.update()
        bullets = [b for b in bullets if b.life > 0 and 0 <= b.x <= WIDTH and 0 <= b.y <= HEIGHT]

        # Bullet-enemy collision
        new_enemies = []
        killed = 0
        for e in enemies:
            hit = False
            for b in bullets:
                if math.hypot(b.x - e.x, b.y - e.y) < e.RADIUS + b.RADIUS:
                    e.hp -= 1
                    b.life = 0
                    if e.hp <= 0:
                        hit = True
                        killed += 1
                    break
            if not hit:
                new_enemies.append(e)
        enemies = new_enemies
        score += killed

        # Spawn allies for kills
        for _ in range(killed):
            color = random.choice(ALLY_COLORS)
            a = Unit(player.x + random.uniform(-30, 30),
                     player.y + random.uniform(-30, 30), color)
            allies.append(a)

        # Update enemies
        for e in enemies:
            e.update(player)

        # Enemy-player collision (damage player)
        surviving = []
        for e in enemies:
            if math.hypot(e.x - player.x, e.y - player.y) < e.RADIUS + player.RADIUS:
                player.hp -= 1
                score += 1
                # Also convert to ally
                color = random.choice(ALLY_COLORS)
                allies.append(Unit(e.x, e.y, color))
            else:
                surviving.append(e)
        enemies = surviving

        if player.hp <= 0:
            game_over = True

        # Draw
        screen.fill(BG)
        for b in bullets:
            b.draw()
        for e in enemies:
            e.draw()
        for a in allies:
            a.draw()
        player.draw()

        # HUD
        hud = font.render(f"Score: {score}   Squad: {1 + len(allies)}   Wave: {wave}", True, (220, 220, 220))
        screen.blit(hud, (10, 10))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run()
