# Class file for healing item pickup

import math
import pygame
import random
import Maze


class Health_Pickup:
    def __init__(self, maze: Maze.Maze, amount: int, tile: int):
        self.MAP = maze
        self.HealthAmount = amount
        self.pos: tuple[int, int] = None
        self.TILE = tile

    # Finds an open position in the maze, ignoring certain positions to avoid conflicts
    def find_open_position(self, excludePos: list[tuple[int, int]]):
        while True:
            y = random.randint(1, len(self.MAP) - 1)
            x = random.randint(1, len(self.MAP[0]) - 1)
            if self.MAP[y][x] == 0 and (x, y) not in excludePos:
                return x, y

    # Spawns the healing item
    def Spawn(self, excludePos: list[tuple[int, int]]):
        x, y = self.find_open_position(excludePos)
        self.pos = (x, y)

    # Despawn the healing item
    def Despawn(self):
        self.pos = None

    # Draw function
    def Draw(
        self,
        screen: pygame.Surface,
        player_x: float,
        player_y: float,
        player_angle: float,
        fov: int,
        WIDTH: int,
        HEIGHT: int,
        z_buffer: list,
        num_rays: int,
        TILE=100,
        max_distance_tiles=4,
    ):
        """
        Renders the health pickup in-world as a pulsing red cross.
        Uses the same projection/occlusion rules as other in-world items.
        """

        if not self.pos:
            return

        tx, ty = self.pos

        # --- Convert to pixel coords ---
        px, py = player_x, player_y
        tile_cx = tx * TILE + TILE / 2
        tile_cy = ty * TILE + TILE / 2
        dx = tile_cx - px
        dy = tile_cy - py

        # --- Distance check ---
        max_dist_px = max_distance_tiles * TILE
        if dx * dx + dy * dy > max_dist_px * max_dist_px:
            return

        # --- Camera transform ---
        sin_a = math.sin(player_angle)
        cos_a = math.cos(player_angle)

        view_x = dx * cos_a + dy * sin_a  # forward
        view_y = dy * cos_a - dx * sin_a  # lateral

        # Behind camera → skip
        if view_x <= 0.01:
            return

        # --- FOV check ---
        HALF_FOV = fov / 2
        angle_to_item = math.atan2(view_y, view_x)
        if abs(angle_to_item) > HALF_FOV:
            return

        # --- Convert angle to ray index ---
        rel = (angle_to_item + HALF_FOV) / (2 * HALF_FOV)
        ray_idx = int(rel * len(z_buffer))
        if not (0 <= ray_idx < len(z_buffer)):
            return

        # --- Occlusion test vs walls ---
        depth = view_x
        if depth >= z_buffer[ray_idx] - 0.0001:
            return

        # --- Projection ---
        DIST = num_rays / (2 * math.tan(HALF_FOV))

        PROJ_COEFF = 3 * DIST * TILE
        proj_height = PROJ_COEFF / depth
        proj_height = min(proj_height, HEIGHT * 2)

        # Size (small + near the floor)
        h = int(proj_height * 0.35)
        w = h  # square

        # --- Floating / pulsing ---
        bob = math.sin(pygame.time.get_ticks() * 0.004) * (TILE * 0.10)
        pulse = (math.sin(pygame.time.get_ticks() * 0.006) + 1) / 2
        pulse_scale = 0.7 + pulse * 0.3  # between 70% and 100%
        w = int(w * pulse_scale)
        h = int(h * pulse_scale)

        top = int(HEIGHT // 2 + proj_height * 0.3 + bob)  # near the floor

        # --- Convert to screen X ---
        screen_x = int(
            (WIDTH / 2) + view_y * (WIDTH / (2 * math.tan(HALF_FOV))) / view_x
        )

        # --- Draw a red "+" sign ---
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # pygame.draw.ellipse(surf, (255, 40, 40), (0, 0, w, h))

        thickness = max(2, w // 6)

        # vertical bar
        pygame.draw.rect(
            surf, (255, 40, 40), (w // 2 - thickness // 2, 0, thickness, h)
        )
        # horizontal bar
        pygame.draw.rect(
            surf, (255, 40, 40), (0, h // 2 - thickness // 2, w, thickness)
        )

        # Blit onto screen
        screen.blit(surf, (screen_x - w // 2, top))

    # ---------------------------------------------------------------------
    # Collision Check
    # ---------------------------------------------------------------------
    def check_collision_with_player(self, player_x: float, player_y: float):
        """Returns True if player collides with the item"""
        x, y = self.pos
        world_x = x * self.TILE + self.TILE / 2
        world_y = y * self.TILE + self.TILE / 2
        return math.hypot(player_x - world_x, player_y - world_y) < self.TILE * 0.3
