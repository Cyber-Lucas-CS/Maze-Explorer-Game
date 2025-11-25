# Maze class file
# Handles everything maze generation related.

import random


class Maze:
    def __init__(self, size, guaranteed_roll=False):
        self.size = size
        self.width = size * 2 + 1
        self.height = size * 2 + 1
        self.grid = [[1 for _ in range(self.width)] for _ in range(self.height)]
        self.visited = [[False for _ in range(size)] for _ in range(size)]
        self.stack = []
        self.rooms = []
        self.end = []
        self.key_loc = ()
        self.guarantee = guaranteed_roll

    # --------------------
    # Place rectangular rooms (store coordinates)
    # --------------------
    def place_rooms(self):
        # Starter room top-left (guaranteed)
        starter_coords = [(1, 1), (1, 2), (2, 1), (2, 2)]
        self.rooms.append({"coords": starter_coords, "center": (1, 1)})

        # Additional rooms based on maze size
        min_room = max(2, self.size // 6)
        max_room = max(3, self.size // 4)
        room_count = max(2, self.size // 2)
        attempts = 0
        rooms_created = 0
        max_attempts = room_count * 20

        while rooms_created < room_count and attempts < max_attempts:
            attempts += 1
            rw = random.randint(min_room, max_room)
            rh = random.randint(min_room, max_room)
            gx = random.randrange(0, self.width - rw * 2, 2)
            gy = random.randrange(0, self.height - rh * 2, 2)

            # Skip overlapping starter room
            if gx <= 1 <= gx + rw * 2 and gy <= 1 <= gy + rh * 2:
                continue

            coords = [
                (x, y)
                for y in range(gy + 1, gy + rh * 2)
                for x in range(gx + 1, gx + rw * 2)
            ]
            self.rooms.append({"coords": coords, "center": (gx + rw, gy + rh)})
            rooms_created += 1

    # --------------------
    # Carve DFS corridors integrating rooms
    # --------------------
    def carve_maze(self):
        start_points = []

        # Mark room tiles as visited and add their centers to DFS start points
        for room in self.rooms:
            for x, y in room["coords"]:
                self.grid[y][x] = 0
            cx, cy = room["center"]
            rx, ry = (cx - 1) // 2, (cy - 1) // 2  # cell coordinates
            if 0 <= rx < self.size and 0 <= ry < self.size:
                self.visited[ry][rx] = True
                start_points.append((rx, ry))

        # If no rooms, start at top-left
        if not start_points:
            start_points = [(0, 0)]
            self.visited[0][0] = True
            self.grid[1][1] = 0

        # Standard DFS to carve corridors
        for sx, sy in start_points:
            stack = [(sx, sy)]
            while stack:
                x, y = stack[-1]
                neighbors = []
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.size and 0 <= ny < self.size:
                        if not self.visited[ny][nx]:
                            neighbors.append((nx, ny))
                if neighbors:
                    nx, ny = random.choice(neighbors)
                    gx1, gy1 = x * 2 + 1, y * 2 + 1
                    gx2, gy2 = nx * 2 + 1, ny * 2 + 1
                    self.grid[(gy1 + gy2) // 2][(gx1 + gx2) // 2] = 0
                    self.grid[gy2][gx2] = 0
                    self.visited[ny][nx] = True
                    stack.append((nx, ny))
                else:
                    stack.pop()

    # --------------------
    # Dead ends
    # --------------------
    def find_dead_ends(self):
        dead_ends = []
        for y in range(1, self.height - 1, 2):
            for x in range(1, self.width - 1, 2):
                if self.grid[y][x] == 0 and (x, y) != (1, 1):
                    walls = sum(
                        1
                        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]
                        if self.grid[y + dy][x + dx] == 1
                    )
                    if walls == 3:
                        dead_ends.append((x, y))
        return dead_ends

    # --------------------
    # Loops / wall removal
    # --------------------
    def add_loops(self, openness=0.1):
        walls = [
            (x, y)
            for y in range(1, self.height - 1)
            for x in range(1, self.width - 1)
            if self.grid[y][x] == 1
        ]
        n_remove = int(len(walls) * openness)
        for _ in range(n_remove):
            x, y = random.choice(walls)
            neighbors = sum(
                1
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]
                if self.grid[y + dy][x + dx] == 0
            )
            if neighbors == 2:
                self.grid[y][x] = 0

    # --------------------
    # Full maze generation
    # --------------------
    def generate(self):
        self.place_rooms()
        self.carve_maze()
        self.add_loops(openness=random.uniform(0.06, 0.14))

        dead_ends = self.find_dead_ends()
        tries = 0
        while len(dead_ends) < 5 and tries < 20:
            tries += 1
            x = random.randrange(1, self.width - 1, 2)
            y = random.randrange(1, self.height - 1, 2)
            for dx, dy in [(0, -1), (1, 0)]:
                wx, wy = x + dx, y + dy
                if self.grid[wy][wx] == 0:
                    self.grid[wy][wx] = 1
            dead_ends = self.find_dead_ends()
        dead_ends = [d for d in dead_ends if d != (1, 1)]

        # Pick 3 exits
        if len(dead_ends) >= 3:
            self.end = random.sample(dead_ends, 3)
        else:
            self.end = dead_ends[:]

        remaining = [d for d in dead_ends if d not in self.end and d != (1, 1)]
        if remaining:
            self.key_loc = random.choice(remaining)
        else:
            self.key_loc = self.end[0]

        return self.grid, self.end, self.key_loc
