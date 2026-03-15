import pygame
import math
import random
import sys

pygame.init()

WIDTH, HEIGHT = 1024, 768
MAP_WIDTH, MAP_HEIGHT = 4096, 3072
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
GRID_COLOR = (30, 30, 45)
BORDER_COLOR = (80, 80, 120)


class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0

    def update(self, target):
        self.x = target.x - WIDTH / 2
        self.y = target.y - HEIGHT / 2
        self.x = max(0, min(MAP_WIDTH - WIDTH, self.x))
        self.y = max(0, min(MAP_HEIGHT - HEIGHT, self.y))

    def apply(self, x, y):
        return int(x - self.x), int(y - self.y)


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

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        pygame.draw.circle(screen, BULLET_COLOR, (sx, sy), self.RADIUS)


class Unit:
    RADIUS = 14
    SPEED = 2.5
    SHOOT_COOLDOWN = 25

    ALLY_LIFETIME = 600  # frames (~10 seconds)

    def __init__(self, x, y, color, is_player=False):
        self.x, self.y = float(x), float(y)
        self.color = color
        self.is_player = is_player
        self.cooldown = 0
        self.hp = 5 if is_player else 3
        self.lifetime = -1 if is_player else self.ALLY_LIFETIME

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
        self.x = max(self.RADIUS, min(MAP_WIDTH - self.RADIUS, new_x))
        self.y = max(self.RADIUS, min(MAP_HEIGHT - self.RADIUS, new_y))

    def shoot_at(self, target, bullets):
        if self.cooldown > 0:
            self.cooldown -= 1
            return
        dx, dy = target.x - self.x, target.y - self.y
        if math.hypot(dx, dy) < 350:
            bullets.append(Bullet(self.x, self.y, dx, dy))
            self.cooldown = self.SHOOT_COOLDOWN

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        # Fade ally color based on remaining lifetime
        draw_color = self.color
        if not self.is_player and self.lifetime >= 0:
            fade = max(0.2, self.lifetime / self.ALLY_LIFETIME)
            draw_color = tuple(int(c * fade) for c in self.color)
        pygame.draw.circle(screen, draw_color, (sx, sy), self.RADIUS)
        pygame.draw.circle(screen, (255, 255, 255), (sx, sy), self.RADIUS, 2)
        # HP bar
        bar_w = self.RADIUS * 2
        max_hp = 5 if self.is_player else 3
        filled = bar_w * self.hp / max_hp
        bx = sx - bar_w // 2
        by = sy - self.RADIUS - 8
        pygame.draw.rect(screen, HEALTH_BG, (bx, by, bar_w, 4))
        pygame.draw.rect(screen, HEALTH_FG, (bx, by, int(filled), 4))
        # Lifetime bar for allies
        if not self.is_player and self.lifetime >= 0:
            life_filled = bar_w * self.lifetime / self.ALLY_LIFETIME
            by2 = sy - self.RADIUS - 13
            pygame.draw.rect(screen, HEALTH_BG, (bx, by2, bar_w, 3))
            pygame.draw.rect(screen, (100, 180, 255), (bx, by2, int(life_filled), 3))


class Enemy:
    RADIUS = 12
    SPEED = 1.2

    def __init__(self, camera):
        # Spawn at edges of camera view
        cam_left = camera.x
        cam_top = camera.y
        cam_right = camera.x + WIDTH
        cam_bottom = camera.y + HEIGHT
        margin = 60
        side = random.randint(0, 3)
        if side == 0:  # top
            self.x = random.uniform(cam_left - margin, cam_right + margin)
            self.y = cam_top - margin
        elif side == 1:  # bottom
            self.x = random.uniform(cam_left - margin, cam_right + margin)
            self.y = cam_bottom + margin
        elif side == 2:  # left
            self.x = cam_left - margin
            self.y = random.uniform(cam_top - margin, cam_bottom + margin)
        else:  # right
            self.x = cam_right + margin
            self.y = random.uniform(cam_top - margin, cam_bottom + margin)
        # Clamp to map bounds (with some allowance outside)
        self.x = max(-margin, min(MAP_WIDTH + margin, float(self.x)))
        self.y = max(-margin, min(MAP_HEIGHT + margin, float(self.y)))
        self.hp = 2

    def update(self, target):
        dx, dy = target.x - self.x, target.y - self.y
        dist = math.hypot(dx, dy) or 1
        self.x += dx / dist * self.SPEED
        self.y += dy / dist * self.SPEED

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        r = self.RADIUS
        points = [(sx, sy - r), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
        pygame.draw.polygon(screen, ENEMY_COLOR, points)
        pygame.draw.polygon(screen, (200, 40, 40), points, 2)


def find_closest_enemy(unit, enemies):
    best, best_d = None, float('inf')
    for e in enemies:
        d = math.hypot(e.x - unit.x, e.y - unit.y)
        if d < best_d:
            best, best_d = e, d
    return best


def draw_grid(camera):
    grid_size = 128
    # Calculate visible grid lines
    start_x = int(camera.x // grid_size) * grid_size
    start_y = int(camera.y // grid_size) * grid_size
    for x in range(start_x, int(camera.x + WIDTH) + grid_size, grid_size):
        if 0 <= x <= MAP_WIDTH:
            sx = int(x - camera.x)
            pygame.draw.line(screen, GRID_COLOR, (sx, 0), (sx, HEIGHT))
    for y in range(start_y, int(camera.y + HEIGHT) + grid_size, grid_size):
        if 0 <= y <= MAP_HEIGHT:
            sy = int(y - camera.y)
            pygame.draw.line(screen, GRID_COLOR, (0, sy), (WIDTH, sy))
    # Draw map border
    bx, by = camera.apply(0, 0)
    bw, bh = MAP_WIDTH, MAP_HEIGHT
    pygame.draw.rect(screen, BORDER_COLOR, (bx, by, bw, bh), 3)


def run():
    camera = Camera()
    player = Unit(MAP_WIDTH / 2, MAP_HEIGHT / 2, PLAYER_COLOR, is_player=True)
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
            player.x = max(player.RADIUS, min(MAP_WIDTH - player.RADIUS, player.x))
            player.y = max(player.RADIUS, min(MAP_HEIGHT - player.RADIUS, player.y))

        # Update camera
        camera.update(player)

        # Spawn enemies
        spawn_timer += 1
        wave_timer += 1
        if wave_timer > 480:
            wave += 1
            wave_timer = 0
            spawn_interval = max(10, spawn_interval - 14)
        if spawn_timer >= spawn_interval:
            spawn_timer = 0
            for _ in range(wave + wave // 2):
                enemies.append(Enemy(camera))

        # Tick ally lifetimes and remove expired allies
        for a in allies:
            if a.lifetime > 0:
                a.lifetime -= 1
        allies = [a for a in allies if a.lifetime != 0]

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
        bullets = [b for b in bullets if b.life > 0 and
                   -50 <= b.x <= MAP_WIDTH + 50 and -50 <= b.y <= MAP_HEIGHT + 50]

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

        # Spawn allies for kills (1-in-10 chance per kill)
        for _ in range(killed):
            if random.random() < 0.1:
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
                # 1-in-10 chance to convert to ally
                if random.random() < 0.1:
                    color = random.choice(ALLY_COLORS)
                    allies.append(Unit(e.x, e.y, color))
            else:
                surviving.append(e)
        enemies = surviving

        if player.hp <= 0:
            game_over = True

        # Draw
        screen.fill(BG)
        draw_grid(camera)
        for b in bullets:
            b.draw(camera)
        for e in enemies:
            e.draw(camera)
        for a in allies:
            a.draw(camera)
        player.draw(camera)

        # HUD
        hud = font.render(f"Score: {score}   Squad: {1 + len(allies)}   Wave: {wave}", True, (220, 220, 220))
        screen.blit(hud, (10, 10))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run()
