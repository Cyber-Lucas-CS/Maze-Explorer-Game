# Maze Explorer
# Lucas Ramage
# 10/23/25

# Imports
import pygame
import math
import sys
import os
import random
import Maze
import Enemy
import Boss
import AtkBall
import HealthItem

# Initialize Pygame
pygame.init()
pygame.display.set_caption("Maze Explorer")

# |=| Settings |=|
DEBUG_MODE = True

# Settings dictionary
settings = {
    "mouse_sensitivity": 0.003,
    "min_sens": 0.001,
    "max_sens": 0.01,
    "FOV_degrees": 75,
}

slider_dragging = False
dragging_fov = False
is_fullscreen = False
score = 0
WIDTH, HEIGHT = 800, 600
BASE_WIDTH, BASE_HEIGHT = 800, 600  # reference resolution
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
HALF_HEIGHT = HEIGHT // 2
TILE = 100
START_MAZE_SIZE = 10
MAZE_SIZE = min(START_MAZE_SIZE + (score // 4), 25)
FRAMERATE = 60
ENEMY_SPAWN_LEVEL = 5
spawn_enemy = True
enemy: Enemy.Enemy = None
enemy1: Enemy.Enemy = None

Boss_Level = False
Boss_Level_Score = 20
Boss_Beaten = False
boss: Boss.Boss_Enemy = None

# |=| Item and Minimap Settings |=|
show_map = False
show_exits_minimap = False
has_map = False
map_pos: tuple[int, int] = None
map_pickup_message = ""
map_pickup_time = 0
MAP_ITEM_COLOR = (0, 200, 255)  # cyan for pickup icon
DYNAMIC_MINIMAP_SIZE = 7  # tiles
healing_spawn_rate = 1.0  # Multiplier
healing_items_per_level = int(4 * healing_spawn_rate)  # Items per level
healing_amount = 10
health_item_list: list[HealthItem.Health_Pickup] = list()

damage_item_list: list[AtkBall.Damage_Item] = list()

# Key settings
has_key = False
key_pickup_message = ""
key_pickup_time = 0

# Torch loss settings
has_torch = True
torch_pos: tuple[int, int] = None
torch_lost_once = False  # track if player has already lost their torch once
TORCH_LOSS_CHANCE = 10  # 10% chance per level after first loss (tweak for testing)
torch_message_list = [
    "Your torch sputters out...",
    "Your torch flickers and dies...",
    "Your light dies out...",
    "You are left in the dark...",
    "The darkness closes in around you...",
]

torch_pickup_message = ""
torch_pickup_time = 0

# Difficulty Settings
current_difficulty = "Normal"
DIFFICULTY_SETTINGS = {
    "Easy": {
        "torch_loss_chance": 5,
        "enemy_damage": 5,
        "enemy_speed": 1.0,
        "torch_always_spawns": True,
        "healing_spawn_rate": 1.5,  # multiplier for future healing
        "healing_amount": 75,
        "lose_random_item": False,
        "enemy_count": 1,
    },
    "Normal": {
        "torch_loss_chance": 10,
        "enemy_damage": 10,
        "enemy_speed": 1.3,
        "torch_always_spawns": True,
        "healing_spawn_rate": 1.0,
        "healing_amount": 50,
        "lose_random_item": False,
        "enemy_count": 1,
    },
    "Hard": {
        "torch_loss_chance": 15,
        "enemy_damage": 10,
        "enemy_speed": 1.6,
        "torch_always_spawns": True,
        "healing_spawn_rate": 1.0,
        "healing_amount": 25,
        "lose_random_item": True,
        "enemy_count": 1,
    },
    "Extra Hard": {
        "torch_loss_chance": 20,
        "enemy_damage": 20,
        "enemy_speed": 2.1,
        "torch_always_spawns": False,
        "healing_spawn_rate": 0.5,
        "healing_amount": 10,
        "lose_random_item": True,
        "enemy_count": 2,
    },
}


# |=| Score Display Settings |=|
game_font = pygame.font.SysFont("Andale Mono", 16)
score_text = f"Level: {score}"
text_surface = game_font.render(score_text, True, (170, 0, 255))
text_rect = text_surface.get_rect()
text_rect.topright = ((WIDTH - 10), 10)

# Sprite Setup
KEY_ICON_SIZE = 32
TORCH_ICON_SIZE = 32

# Get absolute path to this script’s directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "key_icon.png")
TORCH_PATH = os.path.join(BASE_DIR, "torch.png")
WALL_PATH = os.path.join(BASE_DIR, "stone_brick_64.jpg")

try:
    key_icon = pygame.image.load(ICON_PATH).convert_alpha()
    key_icon = pygame.transform.scale(key_icon, (KEY_ICON_SIZE, KEY_ICON_SIZE))
except Exception as e:
    print(f"Failed to load key icon from {ICON_PATH}:", e)
    # fallback simple gold square if the image is missing
    key_icon = pygame.Surface((KEY_ICON_SIZE, KEY_ICON_SIZE), pygame.SRCALPHA)
    pygame.draw.rect(key_icon, (230, 200, 50), (4, 4, 24, 24))

try:
    torch_icon = pygame.image.load(TORCH_PATH).convert_alpha()
    torch_icon = pygame.transform.scale(torch_icon, (TORCH_ICON_SIZE, TORCH_ICON_SIZE))
except Exception as e:
    print(f"Failed to load key icon from {TORCH_PATH}:", e)

brick_texture = pygame.image.load(WALL_PATH).convert()
brick_texture = pygame.transform.scale(brick_texture, (64, 64))
TEXTURE_SIZE = 64

scale_factor = WIDTH / BASE_WIDTH

# scale minimap size (base 300 → grows with screen)
MAP_SIZE = int(500 * scale_factor)
MAP_POS = (WIDTH - MAP_SIZE - 10, 10)

# scale HUD position and size
HUD_MARGIN = int(10 * scale_factor)
HUD_SIZE = int(32 * scale_factor)
key_icon_scaled = pygame.transform.smoothscale(key_icon, (HUD_SIZE, HUD_SIZE))
key_icon_rect = key_icon_scaled.get_rect(bottomleft=(HUD_MARGIN, HEIGHT - HUD_MARGIN))

# Generate random maze
try:
    maze_generator = Maze.Maze(MAZE_SIZE, True)
    MAP, maze_end, maze_key = maze_generator.generate()
    MAP = [[1 if cell == 1 else 0 for cell in row] for row in MAP]
except:
    sys.exit("Maze generation failed. Please try again.")

# Player setup
player_x, player_y = TILE * 1.5, TILE * 1.5
player_angle = 0
player_speed = 2
# player_speed = 3  # Testing allow me to be fast
player_health = 100

# Raycasting settings
WALL_HEIGHT_SCALE = 0.75
FOV = math.radians(settings["FOV_degrees"])
HALF_FOV = FOV / 2
NUM_RAYS = 120
MAX_DEPTH = 800
DELTA_ANGLE = FOV / NUM_RAYS
DIST = NUM_RAYS / (2 * math.tan(HALF_FOV))
PROJ_COEFF = 3 * DIST * TILE
SCALE = WIDTH // NUM_RAYS


# --- Title Screen Function ---
def title_screen(
    screen: pygame.Surface, WIDTH: int, HEIGHT: int, font: pygame.font.Font
):
    """Display the title screen with Start, Settings, and Quit buttons, and fade into game."""
    clock = pygame.time.Clock()

    title_font = pygame.font.Font(None, 96)
    button_font = pygame.font.Font(None, 48)

    # Colors
    BG_COLOR = (10, 10, 10)
    TITLE_COLOR = (200, 100, 255)
    BUTTON_COLOR = (50, 50, 150)
    BUTTON_HOVER = (80, 80, 200)
    TEXT_COLOR = (255, 255, 255)

    # Button setup
    button_width, button_height = 250, 60
    start_button = pygame.Rect(
        WIDTH // 2 - button_width // 2, HEIGHT // 2 - 40, button_width, button_height
    )

    settings_button = pygame.Rect(
        WIDTH // 2 - button_width // 2, HEIGHT // 2 + 40, button_width, button_height
    )

    quit_button = pygame.Rect(
        WIDTH // 2 - button_width // 2,
        HEIGHT // 2 + 40 + button_height + 40,
        button_width,
        button_height,
    )

    fade_out = False
    fade_surface = pygame.Surface((WIDTH, HEIGHT))
    fade_surface.fill((0, 0, 0))
    fade_alpha = 0

    while True:
        screen.fill(BG_COLOR)

        # Title text
        title_surface = title_font.render("Maze Game", True, TITLE_COLOR)
        screen.blit(
            title_surface, (WIDTH // 2 - title_surface.get_width() // 2, HEIGHT // 4)
        )

        # Get mouse position
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = False

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_click = True

        # --- Button Rendering & Logic ---
        for rect, text in [
            (start_button, "Start Game"),
            (settings_button, "Settings"),
            (quit_button, "Quit"),
        ]:
            # Hover detection
            if rect.collidepoint(mouse_pos):
                color = BUTTON_HOVER
                if mouse_click and not fade_out:
                    if text == "Start Game":
                        fade_out = True
                    elif text == "Settings":
                        # Call your settings menu from the title screen
                        settings_menu(screen, WIDTH, HEIGHT, font)
                    elif text == "Quit":
                        pygame.quit()
                        sys.exit()
            else:
                color = BUTTON_COLOR

            pygame.draw.rect(screen, color, rect, border_radius=10)
            label = button_font.render(text, True, TEXT_COLOR)
            screen.blit(
                label,
                (
                    rect.centerx - label.get_width() // 2,
                    rect.centery - label.get_height() // 2,
                ),
            )

        # --- Fade transition ---
        if fade_out:
            fade_alpha += 8
            fade_surface.set_alpha(fade_alpha)
            screen.blit(fade_surface, (0, 0))
            if fade_alpha >= 255:
                return
        else:
            fade_alpha = 0

        pygame.display.flip()
        clock.tick(60)


# --- Difficulty Select Screen ---
def difficulty_select(
    screen: pygame.Surface, WIDTH: int, HEIGHT: int, font: pygame.font.Font
):
    difficulties = ["Easy", "Normal", "Hard", "Extra Hard"]
    selected = 0
    selecting = True

    while selecting:
        screen.fill((0, 0, 0))
        title_text = font.render("Select Difficulty", True, (255, 255, 255))
        screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, 100))

        for i, diff in enumerate(difficulties):
            color = (255, 255, 0) if i == selected else (200, 200, 200)
            text = font.render(diff, True, color)
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, 200 + i * 60))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(difficulties)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(difficulties)
                elif event.key == pygame.K_RETURN:
                    selecting = False
                    return difficulties[selected]


# --- Pause Menu ---
def pause_menu(screen: pygame.Surface, WIDTH: int, HEIGHT: int, font: pygame.font.Font):
    """Display pause menu and suspend gameplay until resumed or quit."""
    clock = pygame.time.Clock()

    title_font = pygame.font.Font(None, 72)
    button_font = pygame.font.Font(None, 48)

    # Colors
    BG_COLOR = (10, 10, 10)
    OVERLAY_COLOR = (0, 0, 0, 180)
    BUTTON_COLOR = (50, 50, 150)
    BUTTON_HOVER = (80, 80, 200)
    TEXT_COLOR = (255, 255, 255)

    # Semi-transparent overlay
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill(OVERLAY_COLOR)

    # Button setup
    button_width, button_height = 260, 60
    spacing = 20
    offset = 50  # push buttons down slightly to avoid overlapping title
    total_height = (button_height + spacing) * 3
    start_y = (HEIGHT - total_height) // 2 + offset

    buttons = {
        "Resume": pygame.Rect(
            WIDTH // 2 - button_width // 2, start_y, button_width, button_height
        ),
        "Settings": pygame.Rect(
            WIDTH // 2 - button_width // 2,
            start_y + button_height + spacing,
            button_width,
            button_height,
        ),
        "Quit": pygame.Rect(
            WIDTH // 2 - button_width // 2,
            start_y + 2 * (button_height + spacing),
            button_width,
            button_height,
        ),
    }

    # Pause input behavior
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)

    while True:
        screen.blit(overlay, (0, 0))

        # Title
        title_surface = title_font.render("Paused", True, TEXT_COLOR)
        screen.blit(
            title_surface, (WIDTH // 2 - title_surface.get_width() // 2, HEIGHT // 4)
        )

        mouse_pos = pygame.mouse.get_pos()
        mouse_click = False

        # Event handling — blocks main game loop here until unpaused
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # Resume on ESC
                pygame.mouse.set_visible(False)
                pygame.event.set_grab(True)
                return  # exits pause_menu, resumes main loop

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_click = True

        # Draw buttons
        for label, rect in buttons.items():
            if rect.collidepoint(mouse_pos):
                color = BUTTON_HOVER
                if mouse_click:
                    if label == "Resume":
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                        return
                    elif label == "Settings":
                        settings_menu(screen, WIDTH, HEIGHT, font)
                    elif label == "Quit":
                        pygame.quit()
                        sys.exit()
            else:
                color = BUTTON_COLOR

            pygame.draw.rect(screen, color, rect, border_radius=10)
            text_surface = button_font.render(label, True, TEXT_COLOR)
            screen.blit(
                text_surface,
                (
                    rect.centerx - text_surface.get_width() // 2,
                    rect.centery - text_surface.get_height() // 2,
                ),
            )

        pygame.display.flip()
        clock.tick(60)


# --- Settings Menu ---
def settings_menu(
    screen: pygame.Surface, WIDTH: int, HEIGHT: int, font: pygame.font.Font
):
    global slider_dragging
    clock = pygame.time.Clock()

    while True:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        screen.fill((25, 25, 25))

        # ---- Title ----
        title = font.render("Settings", True, (255, 255, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        # ---- Slider Label ----
        label = game_font.render("Mouse Sensitivity", True, (255, 255, 255))
        screen.blit(label, (WIDTH // 2 - 150, 200))

        # Normalized slider value
        norm = (settings["mouse_sensitivity"] - settings["min_sens"]) / (
            settings["max_sens"] - settings["min_sens"]
        )
        norm = max(0, min(1, norm))

        # ---- Slider background ----
        slider_x = WIDTH // 2 - 150
        slider_y = 250
        slider_w = 300
        slider_h = 20

        pygame.draw.rect(
            screen,
            (100, 100, 100),
            (slider_x, slider_y + slider_h // 2 - 4, slider_w, 8),
        )

        # Slider handle
        handle_x = slider_x + int(norm * slider_w)
        handle_rect = pygame.Rect(handle_x - 10, slider_y, 20, 20)
        pygame.draw.rect(screen, (200, 50, 50), handle_rect)

        # --- Draw numeric value under slider (2 decimal places) ---
        mouse_sensitivity = settings["mouse_sensitivity"] * 100
        value_text = game_font.render(f"{mouse_sensitivity:.2f}", True, (255, 255, 255))
        value_rect = value_text.get_rect(center=(WIDTH // 2, slider_y + 40))
        screen.blit(value_text, value_rect)

        # --- FOV Slider Parameters ---
        FOV_MIN = 30
        FOV_MAX = 120
        fov_slider_rect = pygame.Rect(
            slider_x, (slider_y + 100) + slider_h // 2 - 4, slider_w, 8
        )

        # Map fov degrees (30–120) into slider position
        fov_ratio = (settings["FOV_degrees"] - FOV_MIN) / (FOV_MAX - FOV_MIN)
        fov_knob_x = fov_slider_rect.x + int(fov_ratio * fov_slider_rect.w)
        fov_knob_rect = pygame.Rect(fov_knob_x - 10, slider_y + 100, 20, 20)

        # --- Draw slider bar ---
        pygame.draw.rect(screen, (100, 100, 100), fov_slider_rect)

        # --- Draw knob ---
        fov_knob_rect.x = (
            fov_slider_rect.x
            + int(
                (settings["FOV_degrees"] - FOV_MIN)
                / (FOV_MAX - FOV_MIN)
                * fov_slider_rect.w
            )
            - 8
        )
        pygame.draw.rect(screen, (200, 50, 50), fov_knob_rect)

        # --- Label ---
        label = game_font.render("Field of View", True, (255, 255, 255))
        screen.blit(label, (fov_slider_rect.x, fov_slider_rect.y - 30))

        # --- Value text (display degrees, e.g. '70°') ---
        value_label = game_font.render(
            f"{settings['FOV_degrees']:.2f}°", True, (255, 255, 255)
        )
        FOV_label_rect = value_label.get_rect(
            center=(WIDTH // 2, fov_slider_rect.y + 40)
        )
        screen.blit(value_label, FOV_label_rect)

        # ---- Back Button ----
        back_rect = pygame.Rect(WIDTH // 2 - 100, slider_y + 200, 200, 50)
        pygame.draw.rect(screen, (200, 200, 200), back_rect)
        back_label = font.render("Back", True, (0, 0, 0))
        screen.blit(
            back_label,
            (
                back_rect.centerx - back_label.get_width() // 2,
                back_rect.centery - back_label.get_height() // 2,
            ),
        )

        pygame.display.flip()

        # ---- Event handling ----
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if handle_rect.collidepoint(mouse_x, mouse_y):
                    slider_dragging = True

                if fov_knob_rect.collidepoint(mouse_x, mouse_y):
                    dragging_fov = True

                if back_rect.collidepoint(mouse_x, mouse_y):
                    slider_dragging = False
                    return

            if event.type == pygame.MOUSEBUTTONUP:
                slider_dragging = False
                dragging_fov = False

            if event.type == pygame.MOUSEMOTION and slider_dragging:
                rel = (mouse_x - slider_x) / slider_w
                rel = max(0.0, min(1.0, rel))

                settings["mouse_sensitivity"] = settings["min_sens"] + rel * (
                    settings["max_sens"] - settings["min_sens"]
                )

            if event.type == pygame.MOUSEMOTION and dragging_fov:
                rel = (mouse_x - slider_x) / slider_w
                rel = max(0.0, min(1.0, rel))

                settings["FOV_degrees"] = FOV_MIN + rel * (FOV_MAX - FOV_MIN)

        clock.tick(60)


# --- Death Screen ---
def death_screen(
    screen: pygame.Surface, WIDTH: int, HEIGHT: int, font: pygame.font.Font
):
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)

    # Button settings
    button_width = 240
    button_height = 60
    spacing = 20

    # Pre-rendered text
    death_text = font.render("You have died...", True, (255, 50, 50))
    score_text = font.render(f"Level Reached: {score}", True, (255, 255, 255))

    restart_button = pygame.Rect(
        WIDTH // 2 - button_width // 2,
        HEIGHT // 2 - 20,
        button_width,
        button_height,
    )

    menu_button = pygame.Rect(
        WIDTH // 2 - button_width // 2,
        HEIGHT // 2 + button_height + spacing - 20,
        button_width,
        button_height,
    )

    while True:
        screen.fill((0, 0, 0))

        # Draw title
        screen.blit(death_text, (WIDTH // 2 - death_text.get_width() // 2, HEIGHT // 4))

        # Draw score
        screen.blit(
            score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 4 + 60)
        )

        # Draw buttons
        mx, my = pygame.mouse.get_pos()

        # Restart button highlight
        color = (
            (255, 255, 100) if restart_button.collidepoint(mx, my) else (200, 200, 200)
        )
        pygame.draw.rect(screen, color, restart_button)
        restart_label = font.render("Restart", True, (0, 0, 0))
        screen.blit(
            restart_label,
            (
                restart_button.centerx - restart_label.get_width() // 2,
                restart_button.centery - restart_label.get_height() // 2,
            ),
        )

        # Main menu button highlight
        color = (255, 255, 100) if menu_button.collidepoint(mx, my) else (200, 200, 200)
        pygame.draw.rect(screen, color, menu_button)
        menu_label = font.render("Main Menu", True, (0, 0, 0))
        screen.blit(
            menu_label,
            (
                menu_button.centerx - menu_label.get_width() // 2,
                menu_button.centery - menu_label.get_height() // 2,
            ),
        )

        pygame.display.flip()

        # Input handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if restart_button.collidepoint(mx, my):
                    # Restart game with same difficulty
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)
                    return "restart"

                if menu_button.collidepoint(mx, my):
                    # Return to main menu
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)
                    return "menu"


# --- Recalculate projection ---
def recalc_projection_constants():
    """Recalculate projection constants dependent on current WIDTH/HEIGHT."""
    global WIDTH, HEIGHT, HALF_HEIGHT, SCALE, PROJ_COEFF

    HALF_HEIGHT = HEIGHT / 2.0

    # column width (float) to avoid rounding gaps
    SCALE = float(WIDTH) / float(NUM_RAYS)

    # compute vertical half-FOV from horizontal FOV and aspect ratio
    # V_half = atan( (H/W) * tan(H_half) )
    aspect = float(HEIGHT) / float(WIDTH)
    v_half = math.atan(aspect * math.tan(HALF_FOV))

    # distance from camera to projection plane using vertical FOV and screen height
    # dist_to_plane = (screen_pixel_half_height) / tan(v_half)
    dist_to_plane = (HEIGHT / 2.0) / math.tan(v_half)

    # projection coefficient so proj_height = (TILE * dist_to_plane) / depth
    PROJ_COEFF = TILE * dist_to_plane

    # make these floats/ints available for other code
    # (HALF_HEIGHT used in raycasting expects int when drawing; convert when needed)


def mapping(x, y):
    return int(x // TILE), int(y // TILE)


# Ceiling Shading
def draw_shaded_ceiling(
    screen: pygame.Surface,
    base_color: tuple[int, int, int],
    min_depth=1.0,
    max_depth=140.0,
):
    r0, g0, b0 = base_color

    shade_amount = 0.0001 if has_torch else 0.00025

    start_y = 0  # top of screen
    end_y = int(HALF_HEIGHT)  # horizon
    span = end_y - start_y
    if span <= 0:
        return
    for i in range(span):
        y = start_y + i
        t = i / (span - 1) if span > 1 else 1.0

        # Depth interpolation: top = min_depth (bright), horizon = max_depth (dark)
        depth = max_depth * t + min_depth * (1.0 - t)

        brightness = 1.0 / (1.0 + (depth * depth) * shade_amount)
        brightness = max(0.2, min(1.0, brightness))

        r = int(r0 * brightness)
        g = int(g0 * brightness)
        b = int(b0 * brightness)

        pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))


# Floor Shading
def draw_shaded_floor(
    screen: pygame.Surface,
    base_color: tuple[int, int, int],
    min_depth=1.0,
    max_depth=140.0,
):
    """
    Draw a vertically shaded floor that is BRIGHTER near the player (bottom of screen)
    and DARKER at the horizon, using the same lighting formula as the walls.

    - base_color: tuple(R,G,B)
    - has_torch: bool (controls shade_amount)
    - min_depth: depth value (in same units used by wall shading) at the very bottom (closest)
    - max_depth: depth value at the horizon (farthest)
    """
    r0, g0, b0 = base_color

    # same shade_amount used in raycasting
    shade_amount = 0.0001 if has_torch else 0.00025

    start_y = int(HALF_HEIGHT)  # horizon
    end_y = HEIGHT  # bottom of screen
    span = end_y - start_y
    if span <= 0:
        return

    # We'll compute a depth for each scanline that goes from max_depth (horizon) down to min_depth (bottom)
    # t = 0 => horizon, t = 1 => bottom
    for i in range(span):
        y = start_y + i
        t = (i) / (span - 1) if span > 1 else 1.0

        # depth increases toward horizon; near (bottom) should be small depth (brighter)
        # So we interpolate depth = max_depth * (1 - t) + min_depth * t
        # which gives depth=max_depth at t=0 (horizon), depth=min_depth at t=1 (bottom)
        depth = max_depth * (1.0 - t) + min_depth * t

        # brightness same formula as walls
        brightness = 1.0 / (1.0 + (depth * depth) * shade_amount)
        brightness = max(0.2, min(1.0, brightness))  # clamp to match wall clamp

        r = int(r0 * brightness)
        g = int(g0 * brightness)
        b = int(b0 * brightness)

        # draw scanline
        pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))


# Raycasting that fills a z-buffer for occlusion checks
def ray_casting(
    screen: pygame.Surface, player_pos: tuple[float, float], player_angle: float
):
    global z_buffer
    px, py = player_pos
    px /= TILE
    py /= TILE

    cur_angle = player_angle - HALF_FOV
    col_w = WIDTH / NUM_RAYS
    z_buffer = [float("inf")] * NUM_RAYS

    for ray in range(NUM_RAYS):
        sin_a = math.sin(cur_angle)
        cos_a = math.cos(cur_angle)

        map_x, map_y = int(px), int(py)

        delta_dist_x = abs(1 / cos_a) if cos_a != 0 else 1e30
        delta_dist_y = abs(1 / sin_a) if sin_a != 0 else 1e30

        if cos_a < 0:
            step_x = -1
            side_dist_x = (px - map_x) * delta_dist_x
        else:
            step_x = 1
            side_dist_x = (map_x + 1 - px) * delta_dist_x

        if sin_a < 0:
            step_y = -1
            side_dist_y = (py - map_y) * delta_dist_y
        else:
            step_y = 1
            side_dist_y = (map_y + 1 - py) * delta_dist_y

        hit = False
        side = 0

        while not hit:
            if side_dist_x < side_dist_y:
                side_dist_x += delta_dist_x
                map_x += step_x
                side = 0
            else:
                side_dist_y += delta_dist_y
                map_y += step_y
                side = 1

            if 0 <= map_x < len(MAP[0]) and 0 <= map_y < len(MAP):
                if MAP[map_y][map_x] == 1:
                    hit = True
            else:
                hit = True

        if side == 0:
            wall_dist = (map_x - px + (1 - step_x) / 2) / cos_a
            hit_pos = py + wall_dist * sin_a
        else:
            wall_dist = (map_y - py + (1 - step_y) / 2) / sin_a
            hit_pos = px + wall_dist * cos_a

        # convert to world units and correct fisheye
        corrected_depth = max(
            wall_dist * TILE * math.cos(player_angle - cur_angle), 0.0001
        )
        z_buffer[ray] = corrected_depth

        proj_height = (PROJ_COEFF * WALL_HEIGHT_SCALE) / corrected_depth
        h = max(1, int(proj_height))

        # centered projection (no eye-level offset)
        top = int(HALF_HEIGHT - h // 2)
        bottom = top + h

        left = int(ray * col_w)
        slice_w = max(1, int(col_w))

        # texture X coordinate (stable)
        frac = hit_pos - int(hit_pos)
        tex_x = int(frac * TEXTURE_SIZE)
        tex_x = max(0, min(TEXTURE_SIZE - 1, tex_x))

        # Extract 1px column from texture and scale it to full wall height (h)
        # We'll crop the scaled column if part of it is off-screen.
        column = brick_texture.subsurface(tex_x, 0, 1, TEXTURE_SIZE)
        try:
            column_scaled = pygame.transform.scale(column, (slice_w, h))
        except Exception:
            # fallback: if scaling fails for any reason, skip this column
            cur_angle += DELTA_ANGLE
            continue

        # Compute visible portion of column_scaled and destination Y
        visible_y0 = 0  # start row in scaled column
        dest_y = top  # destination y on screen

        if top < 0:
            # top is above screen: skip -top pixels from the top of the scaled column
            visible_y0 = -top
            dest_y = 0

        # how many pixels of the scaled column actually fit on-screen
        visible_h = h - visible_y0
        if dest_y + visible_h > HEIGHT:
            visible_h = HEIGHT - dest_y

        # If nothing visible, skip drawing
        if visible_h <= 0:
            cur_angle += DELTA_ANGLE
            continue

        # Now safely obtain the subsurface of the scaled column we want to blit
        # (use integer rects)
        src_rect = pygame.Rect(0, visible_y0, slice_w, visible_h)

        # Apply shading to a copy of just the visible slice (cheap-ish)
        # To avoid modifying the original scaled column for subsequent rays
        slice_surface = column_scaled.subsurface(src_rect).copy()

        shade_amount = 0.0001 if has_torch else 0.00025
        brightness = max(0.2, min(1.0, 1 / (1 + corrected_depth**2 * shade_amount)))
        slice_surface.fill(
            (int(200 * brightness),) * 3, special_flags=pygame.BLEND_MULT
        )

        # Blit the visible slice to screen at (left, dest_y)
        screen.blit(slice_surface, (left, dest_y))

        cur_angle += DELTA_ANGLE


def draw_exits(
    screen: pygame.Surface,
    player_pos: tuple[float, float],
    player_angle: float,
    max_distance_tiles=6,
):
    """
    Draw exit ovals only when player is within `max_distance_tiles`.

    - player_pos: (px, py) in pixels
    - player_angle: radians
    - relies on z_buffer populated by ray_casting (global or returned)
    """
    if not maze_end:
        return

    exit_set = set(maze_end)  # set of (ex, ey) in tile coords
    col_w = WIDTH / NUM_RAYS
    cos_a = math.cos(player_angle)
    sin_a = math.sin(player_angle)

    px, py = player_pos
    max_distance_px = max_distance_tiles * TILE
    max_distance_px_sq = max_distance_px * max_distance_px

    exit_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    for ex, ey in exit_set:
        # tile center in world pixels
        tile_cx = ex * TILE + TILE / 2
        tile_cy = ey * TILE + TILE / 2

        # quick distance check (in pixels) — avoids doing trigonometry for far tiles
        dx = tile_cx - px
        dy = tile_cy - py
        dist_sq = dx * dx + dy * dy
        if dist_sq > max_distance_px_sq:
            continue  # too far, skip

        # transform into camera/view space
        view_x = dx * cos_a + dy * sin_a  # forward distance
        view_y = dy * cos_a - dx * sin_a  # lateral offset

        # skip if behind the player
        if view_x <= 0.01:
            continue

        # skip if outside FOV
        angle_to_tile = math.atan2(view_y, view_x)
        if abs(angle_to_tile) > HALF_FOV:
            continue

        # map angle to ray index
        rel = (angle_to_tile + HALF_FOV) / (2 * HALF_FOV)
        ray_idx = int(rel * NUM_RAYS)
        if not (0 <= ray_idx < NUM_RAYS):
            continue

        # occlusion: if a wall was recorded closer than this tile on this ray, skip
        tile_depth = view_x
        if tile_depth >= z_buffer[ray_idx] - 0.0001:
            continue

        # Projected size: 1 tile tall, 1/2 tile wide (scale by depth)
        proj_height = PROJ_COEFF / tile_depth
        proj_height = min(proj_height, HEIGHT * 2)
        h = int(proj_height)
        w = max(2, int(h * 0.5))
        top = int(HALF_HEIGHT - h // 2)

        # Compute screen X (center)
        screen_x = int(
            (WIDTH / 2) + view_y * (WIDTH / (2 * math.tan(HALF_FOV))) / view_x
        )

        # Pulse color
        pulse = (math.sin(pygame.time.get_ticks() * 0.006) + 1) / 2
        glow = int(180 + 75 * pulse)
        if has_key or (Boss_Level and Boss_Beaten):
            color = (50, glow, 50, 200)  # RGBA (alpha ~200)
        else:
            color = (glow, 50, 50, 200)

        # Draw oval on temporary surface and blit
        oval_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(oval_surf, color, (0, 0, w, h))
        # blit centered horizontally at screen_x, with vertical top
        exit_surface.blit(oval_surf, (screen_x - w // 2, top))

    # Finally blit all exits at once
    screen.blit(exit_surface, (0, 0))


def draw_key_in_world(
    screen: pygame.Surface, player_pos: tuple[float, float], player_angle: float
):
    """Draws the floating key sprite in-world if not yet collected."""
    if has_key or maze_key is None:
        return  # already collected or undefined

    px, py = player_pos
    cos_a = math.cos(player_angle)
    sin_a = math.sin(player_angle)

    # World position of key (convert tile coords to pixel center)
    key_tx, key_ty = maze_key
    key_world_x = key_tx * TILE + TILE / 2
    key_world_y = key_ty * TILE + TILE / 2

    # Distance check: only render within 8 tiles
    dist_sq = (key_world_x - px) ** 2 + (key_world_y - py) ** 2
    if dist_sq > (6 * TILE) ** 2:
        return

    # Compute vector from player to key
    dx = key_world_x - px
    dy = key_world_y - py

    # Transform into camera space
    view_x = dx * cos_a + dy * sin_a  # distance forward
    view_y = dy * cos_a - dx * sin_a  # horizontal offset

    # Skip if behind player
    if view_x <= 0.01:
        return

    # Check FOV bounds
    angle_to_key = math.atan2(view_y, view_x)
    if abs(angle_to_key) > HALF_FOV:
        return

    # Map angle to ray index
    rel = (angle_to_key + HALF_FOV) / (2 * HALF_FOV)
    ray_idx = int(rel * NUM_RAYS)
    if not (0 <= ray_idx < NUM_RAYS):
        return

    # Occlusion: only draw if not hidden behind a wall
    if view_x >= z_buffer[ray_idx] - 0.001:
        return

    # --- Floating animation ---
    time = pygame.time.get_ticks() * 0.003  # slower oscillation
    float_offset = math.sin(time) * (TILE * 0.05)  # about 5% of tile height

    # --- Projection ---
    proj_height = PROJ_COEFF / view_x
    proj_height *= 0.25  # make it about a quarter tile high
    h = int(proj_height)
    w = int(proj_height)
    top = int(HALF_HEIGHT - h // 2 - TILE * 0.25 + float_offset)

    # Screen X position
    screen_x = int((WIDTH / 2) + view_y * (WIDTH / (2 * math.tan(HALF_FOV))) / view_x)

    # Draw with alpha blending
    key_surf_scaled = pygame.transform.scale(key_icon, (w, h))
    rect = key_surf_scaled.get_rect(center=(screen_x, top + h // 2))
    screen.blit(key_surf_scaled, rect)


def draw_torch_in_world(
    screen: pygame.Surface,
    player_pos: tuple[float, float],
    player_angle: float,
    max_distance_tiles=4,
):
    """
    Draws the in-world torch only if the player does not have it.
    Uses the same projection and occlusion logic as draw_key_in_world.
    """
    global has_torch, torch_pos, z_buffer

    if has_torch or not torch_pos:
        return

    tx, ty = torch_pos
    px, py = player_pos
    cos_a = math.cos(player_angle)
    sin_a = math.sin(player_angle)
    col_w = WIDTH / NUM_RAYS

    # distance check (in pixels)
    tile_cx = tx * TILE + TILE / 2
    tile_cy = ty * TILE + TILE / 2
    dx = tile_cx - px
    dy = tile_cy - py
    dist_sq = dx * dx + dy * dy
    max_distance_px = max_distance_tiles * TILE
    if dist_sq > max_distance_px * max_distance_px:
        return

    # transform into camera space
    view_x = dx * cos_a + dy * sin_a  # forward
    view_y = dy * cos_a - dx * sin_a  # lateral

    if view_x <= 0.01:
        return

    # skip if outside FOV
    angle_to_tile = math.atan2(view_y, view_x)
    if abs(angle_to_tile) > HALF_FOV:
        return

    # map to ray index
    rel = (angle_to_tile + HALF_FOV) / (2 * HALF_FOV)
    ray_idx = int(rel * NUM_RAYS)
    if not (0 <= ray_idx < NUM_RAYS):
        return

    # occlusion check with z-buffer
    tile_depth = view_x
    if tile_depth >= z_buffer[ray_idx] - 0.0001:
        return

    # Floating animation
    bob = math.sin(pygame.time.get_ticks() * 0.004) * (TILE * 0.1)

    # projected size — smaller than exits
    proj_height = PROJ_COEFF / tile_depth
    proj_height = min(proj_height, HEIGHT * 2)
    h = int(proj_height * 0.4)  # about half wall height
    w = int(h * 0.5)
    top = int(HALF_HEIGHT - h // 2 + bob)

    # compute screen x center
    screen_x = int((WIDTH / 2) + view_y * (WIDTH / (2 * math.tan(HALF_FOV))) / view_x)

    # flickering color effect
    pulse = (math.sin(pygame.time.get_ticks() * 0.008) + 1) / 2
    glow = int(180 + 60 * pulse)
    color = (glow, int(glow * 0.6), 30, 220)

    # draw torch body (elliptical flame shape)
    torch_surface = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(torch_surface, color, (0, 0, w, w))
    screen.blit(torch_surface, (screen_x - w // 2, top))

    torch_surf_scaled = pygame.transform.scale(torch_icon, (h, h))
    rect = torch_surf_scaled.get_rect(center=(screen_x, top + h // 2))
    screen.blit(torch_surf_scaled, rect)


def draw_map_item_in_world(
    screen: pygame.Surface,
    player_pos: tuple[float, float],
    player_angle: float,
    max_distance_tiles=4,
):
    """
    Draws the in-world map item (cyan) using identical logic to draw_torch_in_world.
    """
    global has_map, map_pos, z_buffer

    if has_map or not map_pos:
        return

    tx, ty = map_pos
    px, py = player_pos
    cos_a = math.cos(player_angle)
    sin_a = math.sin(player_angle)
    col_w = WIDTH / NUM_RAYS

    # --- Distance check (in pixels) ---
    tile_cx = tx * TILE + TILE / 2
    tile_cy = ty * TILE + TILE / 2
    dx = tile_cx - px
    dy = tile_cy - py
    dist_sq = dx * dx + dy * dy
    max_distance_px = max_distance_tiles * TILE
    if dist_sq > max_distance_px * max_distance_px:
        return

    # --- Transform into camera space ---
    view_x = dx * cos_a + dy * sin_a  # forward component
    view_y = dy * cos_a - dx * sin_a  # lateral component

    if view_x <= 0.01:
        return

    # --- Skip if outside FOV ---
    angle_to_tile = math.atan2(view_y, view_x)
    if abs(angle_to_tile) > HALF_FOV:
        return

    # --- Map angle to ray index ---
    rel = (angle_to_tile + HALF_FOV) / (2 * HALF_FOV)
    ray_idx = int(rel * NUM_RAYS)
    if not (0 <= ray_idx < NUM_RAYS):
        return

    # --- Occlusion test using z-buffer ---
    tile_depth = view_x
    if tile_depth >= z_buffer[ray_idx] - 0.0001:
        return

    # --- Floating animation ---
    bob = math.sin(pygame.time.get_ticks() * 0.004) * (TILE * 0.1)

    # --- Projection math (matches key/torch scaling) ---
    proj_height = PROJ_COEFF / tile_depth
    proj_height = min(proj_height, HEIGHT * 2)

    # Map item size (same scale as torch)
    h = int(proj_height * 0.4)
    w = int(h * 0.5)

    top = int(HALF_HEIGHT - h // 2 + bob)

    # --- Compute screen X ---
    screen_x = int((WIDTH / 2) + view_y * (WIDTH / (2 * math.tan(HALF_FOV))) / view_x)

    # --- Draw simple ellipse for map item ---
    item_surface = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(item_surface, MAP_ITEM_COLOR, (0, 0, w, w))
    screen.blit(item_surface, (screen_x - w // 2, top))


def draw_map():
    if not show_map:
        return  # skip drawing if hidden

    map_height = len(MAP)
    map_width = len(MAP[0])

    # Determine scaling factor so the maze fits within MAP_SIZE x MAP_SIZE
    cell_w = MAP_SIZE / map_width
    cell_h = MAP_SIZE / map_height

    # Position minimap in top-left corner (you can adjust x,y)
    offset_x, offset_y = (WIDTH // 2) - (MAP_SIZE // 2), 10

    # Create an opaque surface for the background (fully opaque as requested)
    map_surface = pygame.Surface((MAP_SIZE + 10, MAP_SIZE + 10))
    map_surface.fill((0, 0, 0))  # fully opaque background
    screen.blit(map_surface, (offset_x - 5, offset_y - 5))

    # Draw maze cells
    for j, row in enumerate(MAP):
        for i, tile in enumerate(row):
            color = (200, 200, 200) if tile else (50, 50, 50)
            if (
                show_exits_minimap and (i, j) in maze_end
            ):  # Display exits as green if enabled
                if has_key or (Boss_Level and Boss_Beaten):
                    color = (50, 200, 50)
                else:
                    color = (200, 50, 50)
            if (
                show_exits_minimap and (i, j) == maze_key and not has_key
            ):  # Display key as yellow if enabled
                color = (200, 200, 50)
            if (
                show_exits_minimap and (torch_pos is not None) and (i, j) == torch_pos
            ):  # Display torch if enabled
                color = (255, 200, 50)
            if (
                show_exits_minimap and (map_pos is not None) and (i, j) == map_pos
            ):  # Display map item
                color = MAP_ITEM_COLOR
            if show_exits_minimap and (len(health_item_list) > 0):
                for item in health_item_list:
                    if item.pos is not None and (i, j) == item.pos:
                        color = (40, 255, 40)
            if show_exits_minimap and (len(damage_item_list) > 0):
                for item in damage_item_list:
                    if item.pos is not None and (i, j) == item.pos:
                        color = (40, 40, 255)
            rect = pygame.Rect(
                offset_x + i * cell_w, offset_y + j * cell_h, cell_w - 1, cell_h - 1
            )
            pygame.draw.rect(screen, color, rect)

    # --- Direction indicator (arrow/line) ---
    px = offset_x + (player_x / (len(MAP[0]) * TILE)) * MAP_SIZE
    py = offset_y + (player_y / (len(MAP) * TILE)) * MAP_SIZE

    # length scales with cell size so it looks proportional on the larger map
    arrow_length = max(8, int(min(cell_w, cell_h) * 0.25))
    end_x = px + math.cos(player_angle) * arrow_length
    end_y = py + math.sin(player_angle) * arrow_length

    # Draw a slightly thicker yellow line for visibility
    pygame.draw.line(
        screen, (170, 50, 200), (int(px), int(py)), (int(end_x), int(end_y)), 2
    )  # inner bright line

    # Draw player on map (scaled position)
    pygame.draw.circle(
        screen,
        (170, 50, 200),
        (int(px), int(py)),
        max(3, int(min(cell_w, cell_h) * 0.2)),
    )

    # --- Draw enemy on minimap ---
    if show_exits_minimap:
        try:
            if enemy:  # assuming you have an active enemy object
                ex = offset_x + (enemy.x / (len(MAP[0]) * TILE)) * MAP_SIZE
                ey = offset_y + (enemy.y / (len(MAP) * TILE)) * MAP_SIZE
                pygame.draw.circle(screen, (255, 50, 50), (int(ex), int(ey)), 3)
            if enemy1:  # assuming you have an active enemy object
                e1x = offset_x + (enemy1.x / (len(MAP[0]) * TILE)) * MAP_SIZE
                e1y = offset_y + (enemy1.y / (len(MAP) * TILE)) * MAP_SIZE
                pygame.draw.circle(screen, (255, 50, 50), (int(e1x), int(e1y)), 3)
        except NameError:
            pass  # enemy might not exist yet


def draw_dynamic_minimap():
    radius = 3  # 3 tiles in each direction = 7×7 area
    MAP_SCALE = 12

    px = int(player_x // TILE)
    py = int(player_y // TILE)

    start_x = px - radius
    start_y = py - radius

    TRUE_MAP_SIZE = (2 * MAZE_SIZE) + 1

    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):

            tx = px + dx
            ty = py + dy

            sx = (dx + radius) * MAP_SCALE + 10
            sy = (dy + radius) * MAP_SCALE + 10

            # bounds check
            if 0 <= tx < TRUE_MAP_SIZE and 0 <= ty < TRUE_MAP_SIZE:
                tile = MAP[ty][tx]
                color = (70, 70, 70) if tile == 1 else (20, 20, 20)
                if (tx, ty) in maze_end and has_map:
                    if has_key or (Boss_Level and Boss_Beaten):
                        color = (50, 200, 50)
                    else:
                        color = (200, 50, 50)

                pygame.draw.rect(screen, color, (sx, sy, MAP_SCALE, MAP_SCALE))

                # show collectibles/enemy only if has_map
                if has_map:
                    if maze_key == (tx, ty) and not has_key:
                        pygame.draw.rect(
                            screen, (200, 200, 50), (sx, sy, MAP_SCALE, MAP_SCALE)
                        )
                    if torch_pos == (tx, ty) and not has_torch:
                        pygame.draw.rect(
                            screen, (255, 200, 50), (sx, sy, MAP_SCALE, MAP_SCALE)
                        )
                    if map_pos == (tx, ty):
                        pygame.draw.rect(
                            screen, MAP_ITEM_COLOR, (sx, sy, MAP_SCALE, MAP_SCALE)
                        )
                    if enemy:
                        ex, ey = int(enemy.x // TILE), int(enemy.y // TILE)
                        if (ex, ey) == (tx, ty):
                            pygame.draw.rect(
                                screen, (255, 50, 50), (sx, sy, MAP_SCALE, MAP_SCALE)
                            )
                    if enemy1:
                        e1x, e1y = int(enemy1.x // TILE), int(enemy1.y // TILE)
                        if (e1x, e1y) == (tx, ty):
                            pygame.draw.rect(
                                screen, (255, 50, 50), (sx, sy, MAP_SCALE, MAP_SCALE)
                            )
                    if len(health_item_list) > 0:
                        for item in health_item_list:
                            if item.pos is not None and (tx, ty) == item.pos:
                                pygame.draw.rect(
                                    screen,
                                    (255, 40, 40),
                                    (sx, sy, MAP_SCALE, MAP_SCALE),
                                )

    # player marker in center
    px_screen = radius * MAP_SCALE + 10
    py_screen = radius * MAP_SCALE + 10
    pygame.draw.rect(
        screen, (170, 50, 200), (px_screen, py_screen, MAP_SCALE, MAP_SCALE)
    )


def draw_hud():
    """Draws on-screen HUD elements like the key icon."""
    if has_torch:
        # 10 px margin from bottom-left
        torch_x = 10
        torch_y = HEIGHT - TORCH_ICON_SIZE - 10
        screen.blit(torch_icon, (torch_x, torch_y))
    if has_key:
        # 10 px margin from the torch
        icon_x = 20 + TORCH_ICON_SIZE
        icon_y = HEIGHT - KEY_ICON_SIZE - 10
        screen.blit(key_icon, (icon_x, icon_y))

    health_text = f"HP: {player_health}"
    h_text_surface = game_font.render(health_text, True, (250, 0, 170))
    h_text_rect = h_text_surface.get_rect()
    h_text_rect.bottomright = ((WIDTH - 10), (HEIGHT - 10))
    screen.blit(h_text_surface, h_text_rect)


# --- Main Game Loop --- #
clock = pygame.time.Clock()

# Settings
MOUSE_SENSITIVITY = settings["mouse_sensitivity"]
running = True
paused = False
window_focused = True

# Initialize screen, etc.
t_screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Maze Game")
font = pygame.font.Font(None, 36)

# --- Call the Title Screen ---
title_screen(t_screen, WIDTH, HEIGHT, font)

# Difficulty selection
d_screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Maze Game")
font = pygame.font.Font(None, 36)
current_difficulty = difficulty_select(d_screen, WIDTH, HEIGHT, font)

# Update settings
TORCH_LOSS_CHANCE = DIFFICULTY_SETTINGS[current_difficulty]["torch_loss_chance"]
# print(TORCH_LOSS_CHANCE)
enemy_damage = DIFFICULTY_SETTINGS[current_difficulty]["enemy_damage"]
enemy_speed = DIFFICULTY_SETTINGS[current_difficulty]["enemy_speed"]
# print(enemy_speed)
TORCH_ALWAYS_SPAWNS = DIFFICULTY_SETTINGS[current_difficulty]["torch_always_spawns"]
healing_spawn_rate = DIFFICULTY_SETTINGS[current_difficulty]["healing_spawn_rate"]
healing_items_per_level = int(4 * healing_spawn_rate)
healing_amount = DIFFICULTY_SETTINGS[current_difficulty]["healing_amount"]
lose_item = DIFFICULTY_SETTINGS[current_difficulty]["lose_random_item"]
enemy_count = DIFFICULTY_SETTINGS[current_difficulty]["enemy_count"]

# Start with the mouse hidden & grabbed when focused
pygame.mouse.set_visible(False)
pygame.event.set_grab(True)
pygame.mouse.get_rel()  # reset motion delta

MOUSE_SENSITIVITY = settings["mouse_sensitivity"]
FOV = math.radians(settings["FOV_degrees"])
HALF_FOV = FOV / 2
DELTA_ANGLE = FOV / NUM_RAYS
DIST = NUM_RAYS / (2 * math.tan(HALF_FOV))
PROJ_COEFF = 3 * DIST * TILE
recalc_projection_constants()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if not paused:
                paused = True
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
                pause_menu(screen, WIDTH, HEIGHT, font)
                MOUSE_SENSITIVITY = settings["mouse_sensitivity"]
                FOV = math.radians(settings["FOV_degrees"])
                HALF_FOV = FOV / 2
                DELTA_ANGLE = FOV / NUM_RAYS
                DIST = NUM_RAYS / (2 * math.tan(HALF_FOV))
                PROJ_COEFF = 3 * DIST * TILE
                recalc_projection_constants()
                paused = False
                pygame.mouse.get_rel()  # resets relative movement so no jump on resume
                pygame.mouse.set_visible(False)
                pygame.event.set_grab(True)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            show_map = not show_map
        elif (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_e
            and DEBUG_MODE
            and not has_map
        ):
            show_exits_minimap = not show_exits_minimap
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_z and DEBUG_MODE:
            try:
                if score < 19:
                    score += 1
                score_text = f"Level: {score}"
                text_surface = game_font.render(score_text, True, (170, 0, 255))
                MAZE_SIZE = min(START_MAZE_SIZE + (score // 4), 25)
                # Generate new random maze
                maze_generator = Maze.Maze(MAZE_SIZE)
                MAP, maze_end, maze_key = maze_generator.generate()
                has_key = True
                MAP = [[1 if cell == 1 else 0 for cell in row] for row in MAP]
                # --- Torch placement ---
                torch_pos = None
                if not has_torch:
                    # Find a random walkable tile not near the player or key
                    walkable = [
                        (x, y)
                        for y, row in enumerate(MAP)
                        for x, cell in enumerate(row)
                        if cell == 0
                        and (x, y) != (int(player_x // TILE), int(player_y // TILE))
                    ]
                    if walkable:
                        torch_pos = random.choice(walkable)
                if score >= ENEMY_SPAWN_LEVEL:
                    enemy = Enemy.Enemy(MAP, TILE, enemy_speed)
                    if enemy_count == 2:
                        enemy1 = Enemy.Enemy(MAP, TILE, enemy_speed)
                # --- Spawn Map Item on level 2 ---
                if not has_map and score >= 2:
                    # pick a random free tile far enough from player start
                    free_tiles = [
                        (x, y)
                        for y, row in enumerate(MAP)
                        for x, cell in enumerate(row)
                        if cell == 0
                        and (x, y) != (int(player_x // TILE), int(player_y // TILE))
                    ]

                    if free_tiles:
                        map_pos = random.choice(free_tiles)

                # --- Initialize healing items only on levels with enemies ---
                if score >= ENEMY_SPAWN_LEVEL:
                    health_item_list = list()
                    for i in range(healing_items_per_level):
                        health_item_list.append(
                            HealthItem.Health_Pickup(MAP, healing_amount, TILE)
                        )
                else:
                    health_item_list = list()

                # --- Spawn healing items ---
                if len(health_item_list) > 0:
                    excludeList = [(1, 1), maze_key, torch_pos]
                    for end in maze_end:
                        excludeList.append(end)
                    for item in health_item_list:
                        item.Spawn(excludeList)
                        excludeList.append(item.pos)

            except:
                # Handle an error in maze generation
                print("Maze generation failed, try again")

            # Player setup
            player_x, player_y = TILE * 1.5, TILE * 1.5
            player_angle = 0
            player_speed = 2
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            is_fullscreen = not is_fullscreen
            if is_fullscreen:
                screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                WIDTH, HEIGHT = screen.get_size()
            else:
                screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
                WIDTH, HEIGHT = 800, 600

            recalc_projection_constants()
            pygame.mouse.set_visible(False)
            pygame.event.set_grab(True)
            pygame.mouse.get_rel()

            scale_factor = WIDTH / BASE_WIDTH

            # scale map size (base 300 → grows with screen)
            MAP_SIZE = int(300 * scale_factor)
            MAP_POS = (WIDTH - MAP_SIZE - 10, 10)

            # scale HUD position and size
            HUD_MARGIN = int(10 * scale_factor)
            HUD_SIZE = int(32 * scale_factor)
            key_icon_scaled = pygame.transform.smoothscale(
                key_icon, (HUD_SIZE, HUD_SIZE)
            )
            key_icon_rect = key_icon_scaled.get_rect(
                bottomleft=(HUD_MARGIN, HEIGHT - HUD_MARGIN)
            )

            # update dependent values
            HALF_HEIGHT = HEIGHT // 2
            SCALE = WIDTH // NUM_RAYS
            text_rect.topright = ((WIDTH - 10), 10)
        elif event.type == pygame.VIDEORESIZE and not is_fullscreen:
            WIDTH, HEIGHT = event.size
            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
            recalc_projection_constants()
            HALF_HEIGHT = HEIGHT // 2
            SCALE = WIDTH // NUM_RAYS
            text_rect.topright = ((WIDTH - 10), 10)
            scale_factor = WIDTH / BASE_WIDTH

            # scale map size (base 300 → grows with screen)
            MAP_SIZE = int(300 * scale_factor)
            MAP_POS = (WIDTH - MAP_SIZE - 10, 10)

            # scale HUD position and size
            HUD_MARGIN = int(10 * scale_factor)
            HUD_SIZE = int(32 * scale_factor)
            key_icon_scaled = pygame.transform.smoothscale(
                key_icon, (HUD_SIZE, HUD_SIZE)
            )
            key_icon_rect = key_icon_scaled.get_rect(
                bottomleft=(HUD_MARGIN, HEIGHT - HUD_MARGIN)
            )
        elif event.type == pygame.WINDOWFOCUSGAINED:
            window_focused = True
            pygame.mouse.set_visible(False)
            pygame.event.set_grab(True)
            pygame.mouse.get_rel()  # clear old delta
        elif event.type == pygame.WINDOWFOCUSLOST:
            window_focused = False
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)

    # --- Mouse turning only if focused ---
    if window_focused and not paused:
        mouse_dx, _ = pygame.mouse.get_rel()
        player_angle += mouse_dx * MOUSE_SENSITIVITY

    # --- Keyboard movement ---
    keys = pygame.key.get_pressed()
    sin_a = math.sin(player_angle)
    cos_a = math.cos(player_angle)
    dx = dy = 0
    speed = player_speed

    if not show_map and not paused:
        if keys[pygame.K_w]:
            dx += cos_a * speed
            dy += sin_a * speed
        if keys[pygame.K_s]:
            dx -= cos_a * speed
            dy -= sin_a * speed
        if keys[pygame.K_a]:
            dx += sin_a * speed
            dy -= cos_a * speed
        if keys[pygame.K_d]:
            dx -= sin_a * speed
            dy += cos_a * speed

    # --- Enemy AI and Behavior ---
    delta_time = clock.get_time() / 1000  # milliseconds → seconds

    # Primary enemy
    if enemy:
        enemy.update(player_x, player_y, delta_time)

        # Check for player collision
        if enemy.check_collision_with_player(player_x, player_y):
            player_health -= enemy_damage  # lose health on contact

            # Lose a random item
            take_list = list()
            if has_key:
                take_list.append("key")
            if has_torch:
                take_list.append("torch")
            if has_map:
                take_list.append("map")

            if len(take_list) > 0 and lose_item:
                lost_item = random.choice(take_list)
                print(f"You have lost your {lost_item}!")

                if lost_item == "key":
                    has_key = False
                elif lost_item == "torch":
                    has_torch = False
                elif lost_item == "map":
                    has_map = False
                    show_exits_minimap = False

            # Despawn enemy and respawn somewhere new
            enemy = Enemy.Enemy(MAP, TILE, enemy_speed)

            # Optional: brief screen flash or sound
            # flash_surface = pygame.Surface((WIDTH, HEIGHT))
            # flash_surface.fill((200, 0, 0))
            # screen.blit(flash_surface, (0, 0))
            # pygame.display.flip()
            # pygame.time.delay(100)

            # Optional: player death check
            if player_health <= 0:
                choice = death_screen(screen, WIDTH, HEIGHT, font)

                if choice == "restart":
                    # Reset score and regenerate maze
                    score = 0
                    MAZE_SIZE = START_MAZE_SIZE
                    player_health = 100
                    # however your code handles maze regen
                    score_text = f"Level: {score}"
                    text_surface = font.render(score_text, True, (170, 0, 255))
                    # --- Fade-out effect ---
                    fade_surface = pygame.Surface((WIDTH, HEIGHT))
                    fade_surface.fill((0, 0, 0))
                    for alpha in range(0, 255, 10):
                        fade_surface.set_alpha(alpha)
                        screen.blit(fade_surface, (0, 0))
                        pygame.display.flip()
                        pygame.time.delay(15)

                    has_torch = True
                    has_map = False
                    torch_lost_once = False

                    try:
                        maze_generator = Maze.Maze(MAZE_SIZE)
                        MAP, maze_end, maze_key = maze_generator.generate()
                        has_key = False
                        MAP = [[1 if cell == 1 else 0 for cell in row] for row in MAP]
                        # --- Torch placement ---
                        torch_pos = None
                        if TORCH_ALWAYS_SPAWNS:
                            spawn_torch = True
                        else:
                            spawn_torch = random.choice(True, False)
                        if not has_torch and spawn_torch:
                            # Find a random walkable tile not near the player or key
                            walkable = [
                                (x, y)
                                for y, row in enumerate(MAP)
                                for x, cell in enumerate(row)
                                if cell == 0
                                and (x, y)
                                != (int(player_x // TILE), int(player_y // TILE))
                            ]
                            if walkable:
                                torch_pos = random.choice(walkable)

                    except:
                        print("Maze generation failed, try again")

                    continue  # restart game loop

                elif choice == "menu":
                    return_to_main_menu = True
                    break  # exit game loop and go back to your main menu logic

    # Secondary enemy for higher difficulty
    if enemy1:
        enemy1.update(player_x, player_y, delta_time)

        # Check for player collision
        if enemy1.check_collision_with_player(player_x, player_y):
            player_health -= enemy_damage  # lose health on contact

            # Lose a random item
            take_list = list()
            if has_key:
                take_list.append("key")
            if has_torch:
                take_list.append("torch")
            if has_map:
                take_list.append("map")

            if len(take_list) > 0 and lose_item:
                lost_item = random.choice(take_list)
                print(f"You have lost your {lost_item}!")

                if lost_item == "key":
                    has_key = False
                elif lost_item == "torch":
                    has_torch = False
                elif lost_item == "map":
                    has_map = False
                    show_exits_minimap = False

            # Despawn enemy and respawn somewhere new
            enemy1 = Enemy.Enemy(MAP, TILE, enemy_speed)

            # Optional: brief screen flash or sound
            # flash_surface = pygame.Surface((WIDTH, HEIGHT))
            # flash_surface.fill((200, 0, 0))
            # screen.blit(flash_surface, (0, 0))
            # pygame.display.flip()
            # pygame.time.delay(100)

            # Optional: player death check
            if player_health <= 0:
                choice = death_screen(screen, WIDTH, HEIGHT, font)

                if choice == "restart":
                    # Reset score and regenerate maze
                    score = 0
                    MAZE_SIZE = START_MAZE_SIZE
                    player_health = 100
                    # however your code handles maze regen
                    score_text = f"Level: {score}"
                    text_surface = font.render(score_text, True, (170, 0, 255))
                    # --- Fade-out effect ---
                    fade_surface = pygame.Surface((WIDTH, HEIGHT))
                    fade_surface.fill((0, 0, 0))
                    for alpha in range(0, 255, 10):
                        fade_surface.set_alpha(alpha)
                        screen.blit(fade_surface, (0, 0))
                        pygame.display.flip()
                        pygame.time.delay(15)

                    has_torch = True
                    has_map = False
                    torch_lost_once = False

                    try:
                        maze_generator = Maze.Maze(MAZE_SIZE)
                        MAP, maze_end, maze_key = maze_generator.generate()
                        has_key = False
                        MAP = [[1 if cell == 1 else 0 for cell in row] for row in MAP]
                        # --- Torch placement ---
                        torch_pos = None
                        if TORCH_ALWAYS_SPAWNS:
                            spawn_torch = True
                        else:
                            spawn_torch = random.choice(True, False)
                        if not has_torch and spawn_torch:
                            # Find a random walkable tile not near the player or key
                            walkable = [
                                (x, y)
                                for y, row in enumerate(MAP)
                                for x, cell in enumerate(row)
                                if cell == 0
                                and (x, y)
                                != (int(player_x // TILE), int(player_y // TILE))
                            ]
                            if walkable:
                                torch_pos = random.choice(walkable)

                    except:
                        print("Maze generation failed, try again")

                    continue  # restart game loop

                elif choice == "menu":
                    return_to_main_menu = True
                    break  # exit game loop and go back to your main menu logic

    # --- Collision detection ---
    next_x = player_x + dx
    next_y = player_y + dy
    if MAP[int(player_y // TILE)][int(next_x // TILE)] == 0:
        player_x = next_x
    if MAP[int(next_y // TILE)][int(player_x // TILE)] == 0:
        player_y = next_y

    # --- Key collection ---
    key_x, key_y = maze_key
    if not has_key:
        # convert key coordinates from tile units to world units
        key_world_x = (key_x + 0.5) * TILE
        key_world_y = (key_y + 0.5) * TILE
        distance_to_key = math.hypot(player_x - key_world_x, player_y - key_world_y)
        if distance_to_key < TILE * 0.5:  # within half-tile radius
            has_key = True
            key_pickup_message = "You found the key!"
            key_pickup_time = pygame.time.get_ticks()

    # --- Torch pickup ---
    if torch_pos and not has_torch:
        px, py = int(player_x // TILE), int(player_y // TILE)
        if (px, py) == torch_pos:
            has_torch = True
            torch_pos = None
            torch_pickup_message = "You picked up the torch!"
            torch_pickup_time = pygame.time.get_ticks()

    # --- Map Item pickup ---
    if map_pos:
        px_tile = int(player_x // TILE)
        py_tile = int(player_y // TILE)
        if (px_tile, py_tile) == map_pos:
            has_map = True
            show_exits_minimap = True
            map_pos = None
            map_pickup_message = "You found a map!"
            map_pickup_time = pygame.time.get_ticks()

    # --- Health Item Pickup and Despawn ---
    for item in health_item_list:
        if item.pos is not None:
            if item.check_collision_with_player(player_x, player_y):
                if player_health < 100 or DEBUG_MODE:
                    player_health += item.HealthAmount
                    if player_health > 100 and not DEBUG_MODE:
                        player_health = 100
                    item.Despawn()

    # --- Damage Item Pickup and Despawn ---
    for item in damage_item_list:
        if item.pos is not None:
            if item.check_collision_with_player(player_x, player_y):
                # Deal damage to boss enemy
                item.Despawn()

    # --- Check if player reached an exit ---
    player_tile = (int(player_x // TILE), int(player_y // TILE))
    if player_tile in maze_end and (has_key or (Boss_Level and Boss_Beaten)):
        # Increase score
        score += 1
        score_text = f"Level: {score}"
        text_surface = game_font.render(score_text, True, (170, 0, 255))
        MAZE_SIZE = min(START_MAZE_SIZE + (score // 4), 25)

        # --- Fade-out effect ---
        fade_surface = pygame.Surface((WIDTH, HEIGHT))
        fade_surface.fill((0, 0, 0))
        for alpha in range(0, 255, 10):
            fade_surface.set_alpha(alpha)
            screen.blit(fade_surface, (0, 0))
            pygame.display.flip()
            pygame.time.delay(15)

        # --- Loss of Torch ---
        if score == 4:
            has_torch = False
            torch_lost_once = True

            # --- Torch out message ---
            message = random.choice(torch_message_list)
            msg_surface = game_font.render(message, True, (255, 200, 50))
            msg_bg = pygame.Surface(msg_surface.get_size())
            msg_bg.fill((0, 0, 0))
            msg_bg.set_alpha(180)

            msg_x = (WIDTH - msg_surface.get_width()) // 2
            msg_y = HEIGHT // 2 - msg_surface.get_height() // 2

            # Fade-in and fade-out message
            for alpha in list(range(0, 256, 15)) + list(range(255, -1, -15)):
                # Draw current frame
                msg_bg.set_alpha(int(alpha * 0.7))
                screen.blit(msg_bg, (msg_x, msg_y))
                msg_surface.set_alpha(alpha)
                screen.blit(msg_surface, (msg_x, msg_y))
                pygame.display.flip()
                pygame.time.delay(40)
        elif torch_lost_once:
            if random.randint(0, 100) <= TORCH_LOSS_CHANCE:
                has_torch = False

                # --- Torch out message ---
                message = random.choice(torch_message_list)
                msg_surface = game_font.render(message, True, (255, 200, 50))
                msg_bg = pygame.Surface(msg_surface.get_size())
                msg_bg.fill((0, 0, 0))
                msg_bg.set_alpha(180)

                msg_x = (WIDTH - msg_surface.get_width()) // 2
                msg_y = HEIGHT // 2 - msg_surface.get_height() // 2
                # Fade-in and fade-out message
                for alpha in list(range(0, 256, 15)) + list(range(255, -1, -15)):
                    # Draw current frame
                    msg_bg.set_alpha(int(alpha * 0.7))
                    screen.blit(msg_bg, (msg_x, msg_y))
                    msg_surface.set_alpha(alpha)
                    screen.blit(msg_surface, (msg_x, msg_y))
                    pygame.display.flip()
                    pygame.time.delay(40)

        # --- Enemy Spawn Message on level 5 ---
        if score == ENEMY_SPAWN_LEVEL:
            enemy_message = "You hear something echoing through the halls..."
            mob_msg_surface = game_font.render(enemy_message, True, (255, 50, 50))
            mob_msg_bg = pygame.Surface(mob_msg_surface.get_size())
            mob_msg_bg.fill((0, 0, 0))
            mob_msg_bg.set_alpha(180)

            mob_msg_x = (WIDTH - mob_msg_surface.get_width()) // 2
            mob_msg_y = HEIGHT // 2 - mob_msg_surface.get_height() // 2
            # Fade-in and fade-out message
            for alpha in list(range(0, 256, 15)) + list(range(255, -1, -15)):
                # Draw current frame
                mob_msg_bg.set_alpha(int(alpha * 0.7))
                screen.blit(mob_msg_bg, (mob_msg_x, mob_msg_y))
                mob_msg_surface.set_alpha(alpha)
                screen.blit(mob_msg_surface, (mob_msg_x, mob_msg_y))
                pygame.display.flip()
                pygame.time.delay(40)

        # --- Generate a new maze ---
        try:
            if score == Boss_Level_Score:
                Boss_Level = True
                if not (
                    current_difficulty == "Hard" or current_difficulty == "Extra Hard"
                ):
                    spawn_enemy = False
            maze_generator = Maze.Maze(MAZE_SIZE)
            MAP, maze_end, maze_key = maze_generator.generate()
            has_key = False
            MAP = [[1 if cell == 1 else 0 for cell in row] for row in MAP]
            # --- Torch placement ---
            torch_pos = None
            if TORCH_ALWAYS_SPAWNS:
                spawn_torch = True
            else:
                spawn_torch = random.choice((True, False))
            if not has_torch and spawn_torch:
                # Find a random walkable tile not near the player or key
                walkable = [
                    (x, y)
                    for y, row in enumerate(MAP)
                    for x, cell in enumerate(row)
                    if cell == 0
                    and (x, y) != (int(player_x // TILE), int(player_y // TILE))
                ]
                if walkable:
                    torch_pos = random.choice(walkable)

            # --- Spawn Map Item on level 2 ---
            if not has_map and score >= 2:
                # pick a random free tile far enough from player start
                free_tiles = [
                    (x, y)
                    for y, row in enumerate(MAP)
                    for x, cell in enumerate(row)
                    if cell == 0
                    and (x, y) != (int(player_x // TILE), int(player_y // TILE))
                ]

                if free_tiles:
                    map_pos = random.choice(free_tiles)

            # --- Initialize healing items only on levels with enemies ---
            if score >= ENEMY_SPAWN_LEVEL:
                health_item_list = list()
                for i in range(healing_items_per_level):
                    health_item_list.append(
                        HealthItem.Health_Pickup(MAP, healing_amount, TILE)
                    )
            else:
                health_item_list = list()

            # --- Spawn healing items ---
            if len(health_item_list) > 0:
                excludeList = [(1, 1), maze_key, torch_pos]
                for end in maze_end:
                    excludeList.append(end)
                for item in health_item_list:
                    item.Spawn(excludeList)
                    excludeList.append(item.pos)

            # --- Initialize damage items ---
            # USES HEALING ITEM STATS FOR NOW
            if Boss_Level:
                damage_item_list = list()
                for i in range(healing_items_per_level):
                    damage_item_list.append(
                        AtkBall.Damage_Item(MAP, healing_amount, TILE)
                    )

            if len(damage_item_list) > 0:
                excludeList = [(1, 1), maze_key, torch_pos]
                for end in maze_end:
                    excludeList.append(end)
                for item in health_item_list:
                    excludeList.append(item.pos)
                for item in damage_item_list:
                    item.Spawn(excludeList)
                    excludeList.append(item.pos)
        except:
            print("Maze generation failed, try again")

        # --- Enemy Spawn at later levels ---
        if score >= ENEMY_SPAWN_LEVEL and spawn_enemy:
            enemy = Enemy.Enemy(MAP, TILE, enemy_speed)
            if enemy_count == 2:
                enemy1 = Enemy.Enemy(MAP, TILE, enemy_speed)
        elif score >= ENEMY_SPAWN_LEVEL and not spawn_enemy:
            enemy = None
            enemy1 = None

        # Spawn Boss Enemy

        # Reset player position and angle
        player_x, player_y = TILE * 1.5, TILE * 1.5
        player_angle = 0

        # --- Fade-in effect ---
        for alpha in range(255, -1, -10):
            fade_surface.set_alpha(alpha)
            # redraw a blank frame so you don't see the previous maze
            screen.fill((0, 0, 0))
            screen.blit(fade_surface, (0, 0))
            pygame.display.flip()
            pygame.time.delay(15)

    # --- Render ---
    # ambient background before raycasting
    ceiling_color = (25, 25, 25)
    floor_color = (25, 25, 25)

    excludeList = [(1, 1), maze_key, torch_pos]
    for end in maze_end:
        excludeList.append(end)
    if len(health_item_list) > 0:
        for item in health_item_list:
            if item.pos is not None:
                excludeList.append(item.pos)
    if len(damage_item_list) > 0:
        for item in damage_item_list:
            if item.pos is not None:
                excludeList.append(item.pos)

    # screen.fill(ceiling_color)
    draw_shaded_ceiling(screen, ceiling_color)
    draw_shaded_floor(screen, floor_color)

    ray_casting(screen, (player_x, player_y), player_angle)
    if not Boss_Level:
        draw_key_in_world(screen, (player_x, player_y), player_angle)
    draw_torch_in_world(screen, (player_x, player_y), player_angle)
    draw_map_item_in_world(screen, (player_x, player_y), player_angle)
    draw_exits(screen, (player_x, player_y), player_angle)
    if len(health_item_list) > 0:
        for item in health_item_list:
            if Boss_Level and item.pos is None:
                item.Spawn(excludeList)
                excludeList.append(item.pos)
            if item.pos is not None:
                item.Draw(
                    screen,
                    player_x,
                    player_y,
                    player_angle,
                    FOV,
                    WIDTH,
                    HEIGHT,
                    z_buffer,
                    NUM_RAYS,
                )
    if len(damage_item_list) > 0:
        for item in damage_item_list:
            if Boss_Level and item.pos is None:
                item.Spawn(excludeList)
                excludeList.append(item.pos)
            if item.pos is not None:
                item.Draw(
                    screen,
                    player_x,
                    player_y,
                    player_angle,
                    FOV,
                    WIDTH,
                    HEIGHT,
                    z_buffer,
                    NUM_RAYS,
                )
    if enemy:
        enemy.draw(
            screen,
            player_x,
            player_y,
            player_angle,
            FOV,
            WIDTH,
            HEIGHT,
            z_buffer,
        )
    if enemy1:
        enemy1.draw(
            screen, player_x, player_y, player_angle, FOV, WIDTH, HEIGHT, z_buffer
        )
    draw_map()
    draw_dynamic_minimap()
    draw_hud()

    # --- Item pickup message fade-out ---
    if torch_pickup_message:
        elapsed = pygame.time.get_ticks() - torch_pickup_time
        if elapsed < 2000:  # show for 2 seconds
            alpha = max(0, 255 - int((elapsed / 2000) * 255))
            msg_surface = game_font.render(torch_pickup_message, True, (255, 180, 50))
            msg_surface.set_alpha(alpha)
            screen.blit(
                msg_surface, (WIDTH // 2 - msg_surface.get_width() // 2, HEIGHT - 80)
            )
        else:
            torch_pickup_message = ""
    if key_pickup_message:
        elapsed = pygame.time.get_ticks() - key_pickup_time
        if elapsed < 2000:
            alpha = max(0, 255 - int((elapsed / 2000) * 255))
            msg_surface = game_font.render(key_pickup_message, True, (255, 255, 120))
            msg_surface.set_alpha(alpha)
            screen.blit(
                msg_surface, (WIDTH // 2 - msg_surface.get_width() // 2, HEIGHT - 110)
            )
        else:
            key_pickup_message = ""
    if map_pickup_message:
        elapsed = pygame.time.get_ticks() - map_pickup_time
        if elapsed < 2000:
            alpha = max(0, 255 - int((elapsed / 2000) * 255))
            msg_surface = game_font.render(map_pickup_message, True, MAP_ITEM_COLOR)
            msg_surface.set_alpha(alpha)
            screen.blit(
                msg_surface, (WIDTH // 2 - msg_surface.get_width() // 2, HEIGHT - 140)
            )
        else:
            map_pickup_message = ""

    screen.blit(text_surface, text_rect)

    pygame.display.flip()
    clock.tick(FRAMERATE)

pygame.quit()
sys.exit()
