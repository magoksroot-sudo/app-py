# app.py
# Juego 2D pixel, adaptado para Streamlit.
# Basado en ideas y ejemplos de Pyxel (motor MIT) pero reimplementado/simplificado
# para que pueda ejecutarse dentro de Streamlit con render por frames.
#
# Historia rápida incluida en el juego:
# "Eres Lúm, el recolector de runas. El pueblo de Calder ha perdido las 3 runas del equilibrio.
# Debes explorar 3 salas, recoger runas y volver al altar. Cada sala tiene un mini-desafío.
# Usa botones para moverte. ¡Buena suerte!"
#
# Todo en un único archivo para pegar directamente en Streamlit.

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import time
import random

# -----------------------
# Configuración general
# -----------------------
WIDTH_PIXELS = 240   # ancho de la ventana en pixels
HEIGHT_PIXELS = 160  # alto en pixels
SCALE = 3            # escala para que se vea grande en la pantalla
TILE = 8             # tamaño del tile en px (pixel art block)
MAP_W = WIDTH_PIXELS // TILE
MAP_H = HEIGHT_PIXELS // TILE

# Colores (paleta simple estilo retro)
PALETTE = {
    "bg": (16, 16, 24),
    "tile": (40, 40, 60),
    "player": (220, 180, 50),
    "coin": (240, 200, 80),
    "wall": (30, 60, 90),
    "altar": (200, 100, 230),
    "text": (230, 230, 230),
    "enemy": (200, 50, 50),
}

# -----------------------
# Utilidades de render
# -----------------------
def new_canvas():
    return Image.new("RGB", (WIDTH_PIXELS, HEIGHT_PIXELS), PALETTE["bg"])

def draw_tile(draw, tx, ty, color):
    x0, y0 = tx * TILE, ty * TILE
    draw.rectangle([x0, y0, x0 + TILE - 1, y0 + TILE - 1], fill=color)

def rendermap(mapdata, player_pos, coins, enemies, altar_pos, msg_lines):
    im = new_canvas()
    draw = ImageDraw.Draw(im)
    # tiles
    for y in range(MAP_H):
        for x in range(MAP_W):
            if mapdata[y][x] == 1:
                draw_tile(draw, x, y, PALETTE["wall"])
            else:
                draw_tile(draw, x, y, PALETTE["tile"])
    # altar
    ax, ay = altar_pos
    draw_tile(draw, ax, ay, PALETTE["altar"])
    # coins
    for (cx, cy) in coins:
        draw_tile(draw, cx, cy, PALETTE["coin"])
    # enemies
    for (ex, ey) in enemies:
        draw_tile(draw, ex, ey, PALETTE["enemy"])
    # player (draw on top)
    px, py = player_pos
    draw_tile(draw, px, py, PALETTE["player"])
    # UI text (draw simple)
    font = None
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 10)
    except:
        font = ImageFont.load_default()
    text_x = 4
    text_y = HEIGHT_PIXELS - 28
    for i, line in enumerate(msg_lines):
        draw.text((text_x, text_y + i*10), line, fill=PALETTE["text"], font=font)
    # scale up
    im = im.resize((WIDTH_PIXELS * SCALE, HEIGHT_PIXELS * SCALE), resample=Image.NEAREST)
    return im

# -----------------------
# Game generation
# -----------------------
def make_empty_map():
    # 0 = floor, 1 = wall
    m = [[0 for _ in range(MAP_W)] for __ in range(MAP_H)]
    # border walls
    for x in range(MAP_W):
        m[0][x] = 1
        m[MAP_H - 1][x] = 1
    for y in range(MAP_H):
        m[y][0] = 1
        m[y][MAP_W - 1] = 1
    return m

def carve_rooms(seed=None):
    rnd = random.Random(seed)
    m = make_empty_map()
    # create some random internal walls to make small "rooms"
    for _ in range(30):
        x = rnd.randint(2, MAP_W-3)
        y = rnd.randint(2, MAP_H-3)
        w = rnd.randint(1, 3)
        h = rnd.randint(1, 3)
        for yy in range(y, min(MAP_H-1, y+h)):
            for xx in range(x, min(MAP_W-1, x+w)):
                m[yy][xx] = 1
    # carve a few corridors
    for _ in range(10):
        x1 = rnd.randint(1, MAP_W-2)
        x2 = rnd.randint(1, MAP_W-2)
        y1 = rnd.randint(1, MAP_H-2)
        y2 = rnd.randint(1, MAP_H-2)
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        for x in range(x1, x2+1):
            m[y1][x] = 0
        for y in range(y1, y2+1):
            m[y][x2] = 0
    return m

def place_items_on_map(m, count, rnd):
    empty = [(x,y) for y in range(MAP_H) for x in range(MAP_W) if m[y][x]==0]
    rnd.shuffle(empty)
    return empty[:count]

# -----------------------
# Game state init
# -----------------------
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.seed = random.randint(0, 999999)
    st.session_state.mapdata = carve_rooms(st.session_state.seed)
    # Starting area: center-ish free tile
    free_tiles = [(x,y) for y in range(MAP_H) for x in range(MAP_W) if st.session_state.mapdata[y][x]==0]
    start = random.choice(free_tiles)
    st.session_state.player = start
    # place 3 runas/coins across the map (objectivo)
    rnd = random.Random(st.session_state.seed)
    coins = place_items_on_map(st.session_state.mapdata, 6, rnd)  # 6 items, but 3 are runas especiales
    # mark 3 as runas (we'll treat all as coins but point system)
    st.session_state.coins = coins
    st.session_state.runas_collected = 0
    st.session_state.total_runas = 3
    # randomly choose 3 runas among coins positions
    st.session_state.runas_positions = set(rnd.sample(st.session_state.coins, st.session_state.total_runas))
    # enemies simple
    st.session_state.enemies = place_items_on_map(st.session_state.mapdata, 3, rnd)
    # altar position near border
    # pick a free tile close to border
    possible_altars = [p for p in free_tiles if p[0] < 3 or p[0] > MAP_W-4 or p[1] < 3 or p[1] > MAP_H-4]
    st.session_state.altar = rnd.choice(possible_altars)
    st.session_state.moves = 0
    st.session_state.msg = "Eres Lúm: recoge 3 runas y vuelve al altar."
    st.session_state.level = 1
    st.session_state.game_over = False
    st.session_state.victory = False

# -----------------------
# Game logic helpers
# -----------------------
def can_move_to(m, pos):
    x,y = pos
    if x < 0 or y < 0 or x >= MAP_W or y >= MAP_H:
        return False
    return m[y][x] == 0

def step_enemy(enemy_pos, player_pos, m):
    ex, ey = enemy_pos
    px, py = player_pos
    dx = np.sign(px - ex)
    dy = np.sign(py - ey)
    # try to move in x then y if free, else random
    new = (ex + dx, ey)
    if dx != 0 and can_move_to(m, new):
        return new
    new = (ex, ey + dy)
    if dy != 0 and can_move_to(m, new):
        return new
    # else random small step
    choices = [(ex+1,ey),(ex-1,ey),(ex,ey+1),(ex,ey-1)]
    random.shuffle(choices)
    for c in choices:
        if can_move_to(m,c):
            return c
    return (ex,ey)

def handle_move(dx, dy):
    if st.session_state.game_over:
        return
    px, py = st.session_state.player
    nx, ny = px + dx, py + dy
    if not can_move_to(st.session_state.mapdata, (nx, ny)):
        st.session_state.msg = "Te golpeaste con una pared."
        return
    st.session_state.player = (nx, ny)
    st.session_state.moves += 1
    st.session_state.msg = ""
    # coin pickup
    if st.session_state.player in st.session_state.coins:
        st.session_state.coins.remove(st.session_state.player)
        if st.session_state.player in st.session_state.runas_positions:
            st.session_state.runas_collected += 1
            st.session_state.msg = f"Has recogido una Runa! ({st.session_state.runas_collected}/{st.session_state.total_runas})"
        else:
            st.session_state.msg = "Recogiste un fragmento (no una runa)."
    # enemy moves and collisions
    new_enemies = []
    for e in st.session_state.enemies:
        ne = step_enemy(e, st.session_state.player, st.session_state.mapdata)
        new_enemies.append(ne)
    st.session_state.enemies = new_enemies
    # check collisions with enemies
    if st.session_state.player in st.session_state.enemies:
        st.session_state.game_over = True
        st.session_state.msg = "Un guardián te alcanzó. Game Over."
    # check victory condition: has all runas and stands on altar
    if st.session_state.runas_collected >= st.session_state.total_runas and st.session_state.player == st.session_state.altar:
        st.session_state.victory = True
        st.session_state.game_over = True
        st.session_state.msg = "¡Has restaurado las runas al altar! ¡Victoria!"

# -----------------------
# UI / Controls
# -----------------------
st.set_page_config(page_title="Lúm: Runas de Calder", layout="wide")
st.title("Lúm: Runas de Calder — versión Streamlit")
st.markdown("Historia: eres Lúm, recolector de runas. Recolecta 3 runas escondidas y vuelve al altar. Controles: usa los botones para moverte.")

# left column: juego
col1, col2 = st.columns([2,1])

with col1:
    # render current map to image
    img = rendermap(st.session_state.mapdata, st.session_state.player, st.session_state.coins, st.session_state.enemies, st.session_state.altar, [
        st.session_state.msg,
        f"Runas: {st.session_state.runas_collected}/{st.session_state.total_runas}  |  Movimientos: {st.session_state.moves}",
        f"Nivel: {st.session_state.level}"
    ])
    st.image(img, use_column_width=True)

    # movement controls (buttons)
    cols = st.columns(3)
    if cols[1].button("↑"):
        handle_move(0, -1)
    c1, c2, c3 = st.columns(3)
    if c1.button("←"):
        handle_move(-1, 0)
    if c3.button("→"):
        handle_move(1, 0)
    if cols[2].button("↓"):
        handle_move(0, 1)

with col2:
    st.header("Estado")
    st.write(f"- Runas recogidas: **{st.session_state.runas_collected}/{st.session_state.total_runas}**")
    st.write(f"- Movimientos: **{st.session_state.moves}**")
    st.write(f"- Posición: **{st.session_state.player}**")
    st.write(f"- Altar en: **{st.session_state.altar}**")
    st.write(f"- Enemigos: **{len(st.session_state.enemies)}**")
    st.write("---")
    st.write("Objetos restantes:", len(st.session_state.coins))
    st.write("Consejos:")
    st.write("• Pulsa en las flechas para moverte.")
    st.write("• Evita enemigos y busca runas (brillan en amarillo).")
    st.write("• Cuando tengas las 3 runas, ve al altar (morado).")
    st.write("---")
    if st.session_state.game_over:
        if st.session_state.victory:
            st.success("¡VICTORIA! Restauraste el equilibrio de Calder.")
        else:
            st.error("Has sido derrotado. Pulsa Reiniciar")
    if st.button("Reiniciar (nueva semilla)"):
        # re-init everything
        st.session_state.seed = random.randint(0, 999999)
        st.session_state.mapdata = carve_rooms(st.session_state.seed)
        free_tiles = [(x,y) for y in range(MAP_H) for x in range(MAP_W) if st.session_state.mapdata[y][x]==0]
        st.session_state.player = random.choice(free_tiles)
        rnd = random.Random(st.session_state.seed)
        st.session_state.coins = place_items_on_map(st.session_state.mapdata, 6, rnd)
        st.session_state.runas_collected = 0
        st.session_state.runas_positions = set(rnd.sample(st.session_state.coins, st.session_state.total_runas))
        st.session_state.enemies = place_items_on_map(st.session_state.mapdata, 3, rnd)
        possible_altars = [p for p in free_tiles if p[0] < 3 or p[0] > MAP_W-4 or p[1] < 3 or p[1] > MAP_H-4]
        st.session_state.altar = rnd.choice(possible_altars)
        st.session_state.moves = 0
        st.session_state.msg = "Nueva partida. Buena suerte."
        st.session_state.game_over = False
        st.session_state.victory = False

# bottom story / flavour
st.markdown("---")
st.markdown("**Historia breve:** El pueblo de Calder vive apacible gracias a las Runas del Equilibrio. Hace siglos se sellaron en un altar; recientemente tres runas fueron robadas por la niebla. Eres Lúm, el joven que se ofreció a recuperarlas. No solo debes recogerlas: algunos guardianes vagan por las salas. Razonamiento y paciencia valen más que fuerza bruta.")
st.markdown("**Nota técnica:** Este juego adapta mecánicas retro y las hace compatibles con Streamlit (render por frames). No hay animación continua para mantener rendimiento en el navegador.")

# End of file
