# Boss Enemy class file
# Handles everything boss related

import math
import random
import pygame
import heapq
import Maze


class Boss_Enemy:
    def __init__(self, maze: Maze.Maze, tile_size: int, speed=1.2):
        self.MAP = maze
        self.TILE = tile_size
        self.speed = speed + 0.3
        self.x, self.y = self.random_open_position()
        self.path = []  # list of (tile_x, tile_y)
        self.state = "wander"  # "wander" or "chase"
        self.target_tile = None
        self.repath_timer = 0  # time accumulator for periodic path recalculation
        self.detection_range = 8  # tiles
        self.memory_time = 5.0  # how long enemy remembers player after losing sight
        self.health = 200
        self.dead = False

    def random_open_position(self):
        """Finds a random walkable tile in the maze."""
        while True:
            j = random.randint(0, len(self.MAP) - 1)
            i = random.randint(0, len(self.MAP[0]) - 1)
            if self.MAP[j][i] == 0:
                return (i + 0.5) * self.TILE, (j + 0.5) * self.TILE

    def _health_check(self):
        if self.health <= 0:
            self.dead = True

    def _despawn(self):
        self.x, self.y = None, None

    # ---------------------------------------------------------------------
    # A* PATHFINDING
    # ---------------------------------------------------------------------
    def find_path(self, start: tuple[int, int], goal: tuple[int, int]):
        """A* pathfinding algorithm on the MAP grid."""
        rows, cols = len(self.MAP), len(self.MAP[0])
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}

        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])  # Manhattan distance

        while open_set:
            _, current = heapq.heappop(open_set)
            if current == goal:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                return path

            cx, cy = current
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= ny < rows and 0 <= nx < cols and self.MAP[ny][nx] == 0:
                    neighbor = (nx, ny)
                    tentative_g = g_score[current] + 1
                    if tentative_g < g_score.get(neighbor, float("inf")):
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g
                        f_score = tentative_g + heuristic(neighbor, goal)
                        heapq.heappush(open_set, (f_score, neighbor))
        return []  # no path found

    # ---------------------------------------------------------------------
    # --- Line of Sight (LOS) Check ---
    # ---------------------------------------------------------------------
    def can_see_player(self, player_x: float, player_y: float):
        """Check if enemy has line of sight to the player using raycasting."""
        x0, y0 = int(self.x // self.TILE), int(self.y // self.TILE)
        x1, y1 = int(player_x // self.TILE), int(player_y // self.TILE)
        dx, dy = x1 - x0, y1 - y0
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            return True

        for i in range(steps + 1):
            t = i / steps
            x = int((x0 + dx * t))
            y = int((y0 + dy * t))
            if 0 <= y < len(self.MAP) and 0 <= x < len(self.MAP[0]):
                if self.MAP[y][x] == 1:
                    return False
            else:
                return False
        return True

    # ---------------------------------------------------------------------
    # --- Update with LOS + memory ---
    # ---------------------------------------------------------------------
    def update(self, player_x: float, player_y: float, delta_time: float):
        self._health_check()
        if self.dead:
            self._despawn()
            return
        player_tile = (int(player_x // self.TILE), int(player_y // self.TILE))
        enemy_tile = (int(self.x // self.TILE), int(self.y // self.TILE))
        dist_to_player = math.hypot(player_x - self.x, player_y - self.y) / self.TILE

        sees_player = self.can_see_player(player_x, player_y)

        # Behavior transitions
        if sees_player and dist_to_player < self.detection_range:
            self.state = "chase"
            self.time_since_seen = 0
            target_tile = player_tile
        else:
            if self.state == "chase":
                self.time_since_seen += delta_time
                if self.time_since_seen > self.memory_time:
                    self.state = "wander"
            target_tile = self.target_tile

        # Recalculate path occasionally
        self.repath_timer += delta_time
        if self.repath_timer > 1.0 or not self.path:
            self.repath_timer = 0
            if self.state == "chase":
                self.path = self.find_path(enemy_tile, player_tile)
            elif self.state == "wander":
                if not self.target_tile or enemy_tile == self.target_tile:
                    self.target_tile = self.random_open_tile()
                self.path = self.find_path(enemy_tile, self.target_tile)
            # print(self.state)

        # Follow path
        if self.path:
            next_tile = self.path[0]
            tx, ty = (next_tile[0] + 0.5) * self.TILE, (next_tile[1] + 0.5) * self.TILE
            dx, dy = tx - self.x, ty - self.y
            dist = math.hypot(dx, dy)

            if dist < 2:
                self.path.pop(0)
            else:
                self.x += (dx / dist) * self.speed * delta_time * 60
                self.y += (dy / dist) * self.speed * delta_time * 60

    def random_open_tile(self):
        """Returns coordinates of a random open tile."""
        while True:
            i = random.randint(0, len(self.MAP[0]) - 1)
            j = random.randint(0, len(self.MAP) - 1)
            if self.MAP[j][i] == 0:
                return (i, j)

    # ---------------------------------------------------------------------
    # RENDERING
    # ---------------------------------------------------------------------
    def draw(
        self,
        screen: pygame.Surface,
        player_x: float,
        player_y: float,
        player_angle: float,
        fov: float,
        width: int,
        height: int,
        z_buffer: list[float],
    ):
        """
        Simple pseudo-3D sprite rendering placeholder.
        Replace later with raycast-aware rendering if desired.
        """
        TILE = self.TILE  # or use your global TILE constant
        FOV = fov
        HALF_FOV = FOV / 2
        WIDTH = width
        HEIGHT = height

        # Calculate vector to enemy
        dx = self.x - player_x
        dy = self.y - player_y

        # Distance to enemy (for scaling)
        dist = math.hypot(dx, dy)

        # Transform into view space
        cos_a = math.cos(player_angle)
        sin_a = math.sin(player_angle)
        view_x = dx * cos_a + dy * sin_a
        view_y = dy * cos_a - dx * sin_a

        if view_x <= 0.01:
            return  # behind player

        # Determine if within FOV
        angle_to_enemy = math.atan2(view_y, view_x)
        if abs(angle_to_enemy) > HALF_FOV:
            return  # outside field of view

        # Determine which ray (screen column) enemy aligns with
        rel = (angle_to_enemy + HALF_FOV) / (2 * HALF_FOV)
        ray_index = int(rel * len(z_buffer))
        if not (0 <= ray_index < len(z_buffer)):
            return

        # --- Occlusion check ---
        if dist >= z_buffer[ray_index] - 0.001:
            return  # hidden behind wall

        # --- Project enemy sprite ---
        PROJ_COEFF = 3 * (len(z_buffer) / (2 * math.tan(HALF_FOV))) * TILE
        proj_height = PROJ_COEFF / dist
        proj_height *= 0.5  # adjust size of enemy sprite
        h = int(proj_height)
        w = h
        screen_x = int(
            (WIDTH / 2) + view_y * (WIDTH / (2 * math.tan(HALF_FOV))) / view_x
        )
        top = int(HEIGHT / 2 - h // 2)

        # --- Draw enemy ---
        enemy_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.circle(enemy_surface, (255, 30, 30, 220), (w // 2, h // 2), h // 2)
        rect = enemy_surface.get_rect(center=(screen_x, top + h // 2))
        screen.blit(enemy_surface, rect)

    # ---------------------------------------------------------------------
    # Collision Check
    # ---------------------------------------------------------------------
    def check_collision_with_player(self, player_x: float, player_y: float):
        """Returns True if the enemy touches the player."""
        return math.hypot(player_x - self.x, player_y - self.y) < self.TILE * 0.3
