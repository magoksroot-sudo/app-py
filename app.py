# app.py
# Juego 2D pixel-style profesional para Streamlit
# - Un solo archivo (pegar entero en app.py)
# - Controles con TECLAS FLECHA (usa streamlit-shortcuts)
# - Render con Pillow (sprites dibujados con vectores simples)
# - Historia y objetivos: recoge 3 runas y vuelve al altar
#
# NOTA: instala requirements.txt (ver abajo) y ejecuta:
#    pip install -r requirements.txt
#    streamlit run app.py

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import random
import math
from streamlit_shortcuts import add_shortcuts  # atajos para teclas (arrow keys)

# -------------------------
# Config y paleta (profesional)
# -------------------------
SCALE = 3                     # escala de la imagen final
TILE = 10                     # tamaño lógico del "tile" en px base
MAP_W = 28
MAP_H = 18
WIDTH = MAP_W * TILE
HEIGHT = MAP_H * TILE

PALETTE = {
    "bg": (10, 12, 20),
    "floor": (28, 34, 60),
    "wall": (18, 22, 36),
    "player": (255, 210, 90),
    "coin": (255, 220, 100),
    "altar": (170, 110, 230),
    "enemy": (230, 80, 80),
    "ui_text": (230, 230, 235),
    "highlight": (255, 240, 160),
    "shadow": (6, 8, 14),
}

# -------------------------
# Utilidades de dibujo (sprite vectorial)
# -------------------------
def new_canvas():
    return Image.new("RGB", (WIDTH, HEIGHT), PALETTE["bg"])

def draw_tile(draw, x, y, color):
    x0, y0 = x * TILE, y * TILE
    draw.rectangle([x0, y0, x0+TILE-1, y0+TILE-1], fill=color)

def draw_player(draw, tx, ty):
    x0, y0 = tx*TILE, ty*TILE
    cx, cy = x0 + TILE/2, y0 + TILE/2
    r = TILE*0.42
    # shadow
    draw.ellipse([cx - r + 1, cy - r + 2, cx + r + 1, cy + r + 2], fill=PALETTE["shadow"])
    # body
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PALETTE["player"])
    # eyes
    eye_r = max(1, TILE//6)
    draw.ellipse([cx - eye_r - 2, cy - eye_r/2 - 1, cx - 2, cy + eye_r - 1], fill=(15,15,20))
    draw.ellipse([cx + 2, cy - eye_r/2 - 1, cx + eye_r + 2, cy + eye_r - 1], fill=(15,15,20))
    # small shine
    draw.ellipse([cx - r + 3, cy - r + 2, cx - r + 6, cy - r + 5], fill=PALETTE["highlight"])

def draw_coin(draw, tx, ty):
    x0, y0 = tx*TILE, ty*TILE
    cx, cy = x0 + TILE/2, y0 + TILE/2
    r = TILE*0.33
    # central circle
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=PALETTE["coin"])
    # subtle cross to make it feel like "runa"
    draw.line([cx - r/1.3, cy, cx + r/1.3, cy], fill=(180,120,30), width=max(1,int(TILE/8)))
    draw.line([cx, cy - r/1.3, cx, cy + r/1.3], fill=(200,150,50), width=max(1,int(TILE/10)))

def draw_enemy(draw, tx, ty):
    x0, y0 = tx*TILE, ty*TILE
    cx, cy = x0 + TILE/2, y0 + TILE/2
    r = TILE*0.42
    # triangle-ish guard
    pts = [(cx, cy-r),(cx+r, cy+r),(cx-r, cy+r)]
    draw.polygon(pts, fill=PALETTE["enemy"])
    # eyes
    draw.rectangle([cx-4, cy-2, cx-1, cy+1], fill=(20,20,30))
    draw.rectangle([cx+1, cy-2, cx+4, cy+1], fill=(20,20,30))

def draw_altar(draw, tx, ty):
    x0, y0 = tx*TILE, ty*TILE
    cx, cy = x0 + TILE/2, y0 + TILE/2
    w = TILE*0.8
    h = TILE*0.6
    draw.rectangle([cx - w/2, cy - h/2, cx + w/2, cy + h/2], fill=PALETTE["altar"])
    # gem
    draw.polygon([(cx, cy-h/2+2),(cx+w/6, cy+h/2-2),(cx-w/6, cy+h/2-2)], fill=(255,240,250))

# -------------------------
# Map gen (profesional y jugable)
# -------------------------
def make_map(seed):
    rnd = random.Random(seed)
    m = [[0 for _ in range(MAP_W)] for __ in range(MAP_H)]
    # border walls
    for x in range(MAP_W):
        m[0][x] = 1
        m[MAP_H-1][x] = 1
    for y in range(MAP_H):
        m[y][0] = 1
        m[y][MAP_W-1] = 1
    # rooms
    rooms = []
    for _ in range(6):
        rw = rnd.randint(4,8)
        rh = rnd.randint(3,6)
        rx = rnd.randint(2, MAP_W-rw-2)
        ry = rnd.randint(2, MAP_H-rh-2)
        rooms.append((rx,ry,rw,rh))
        for yy in range(ry, ry+rh):
            for xx in range(rx, rx+rw):
                m[yy][xx] = 0
    # internal random walls to create corridors
    for _ in range(80):
        x = rnd.randint(1, MAP_W-2)
        y = rnd.randint(1, MAP_H-2)
        if rnd.random() < 0.12:
            m[y][x] = 1
    # ensure reachability: carve simple paths between rooms
    for i in range(len(rooms)-1):
        x1 = rooms[i][0] + rooms[i][2]//2
        y1 = rooms[i][1] + rooms[i][3]//2
        x2 = rooms[i+1][0] + rooms[i+1][2]//2
        y2 = rooms[i+1][1] + rooms[i+1][3]//2
        # carve L-shape
        for x in range(min(x1,x2), max(x1,x2)+1):
            m[y1][x] = 0
        for y in range(min(y1,y2), max(y1,y2)+1):
            m[y][x2] = 0
    return m

def free_positions(mapdata):
    return [(x,y) for y in range(MAP_H) for x in range(MAP_W) if mapdata[y][x]==0]

# -------------------------
# Estado del juego (session_state)
# -------------------------
if "inited" not in st.session_state:
    st.session_state.inited = True
    st.session_state.seed = random.randint(0,9999999)
    st.session_state.map = make_map(st.session_state.seed)
    free = free_positions(st.session_state.map)
    st.session_state.player = random.choice(free)
    st.session_state.altar = random.choice([p for p in free if p[0]<3 or p[0]>MAP_W-4 or p[1]<3 or p[1]>MAP_H-4])
    rnd = random.Random(st.session_state.seed)
    st.session_state.coins = rnd.sample([p for p in free if p != st.session_state.player and p != st.session_state.altar], 7)
    st.session_state.total_runas = 3
    st.session_state.runas_positions = set(rnd.sample(st.session_state.coins, st.session_state.total_runas))
    st.session_state.enemies = rnd.sample([p for p in free if p not in st.session_state.coins and p != st.session_state.player and p != st.session_state.altar], 4)
    st.session_state.runas_collected = 0
    st.session_state.moves = 0
    st.session_state.msg = "Recoge 3 runas y vuelve al altar. Usa las flechas ← ↑ ↓ →"
    st.session_state.victory = False
    st.session_state.game_over = False

# -------------------------
# Lógica de juego
# -------------------------
def can_move(mapdata, pos):
    x,y = pos
    if x < 0 or y < 0 or x >= MAP_W or y >= MAP_H:
        return False
    return mapdata[y][x] == 0

def enemy_step(e, player, mapdata):
    ex,ey = e
    px,py = player
    dx = np.sign(px - ex)
    dy = np.sign(py - ey)
    # prioridad en acercamiento diagonalizado
    candidates = []
    if dx != 0 and can_move(mapdata, (ex+dx, ey)):
        candidates.append((ex+dx, ey))
    if dy != 0 and can_move(mapdata, (ex, ey+dy)):
        candidates.append((ex, ey+dy))
    # diagonal attempt
    if dx!=0 and dy!=0 and can_move(mapdata, (ex+dx, ey+dy)):
        candidates.insert(0, (ex+dx, ey+dy))
    # fallback random
    dirs = [(1,0),(-1,0),(0,1),(0,-1)]
    random.shuffle(dirs)
    for d in dirs:
        np = (ex+d[0], ey+d[1])
        if can_move(mapdata, np):
            candidates.append(np)
    for c in candidates:
        if can_move(mapdata, c): return c
    return (ex,ey)

def attempt_move(dx, dy):
    if st.session_state.game_over: return
    px,py = st.session_state.player
    nx,ny = px+dx, py+dy
    if not can_move(st.session_state.map, (nx,ny)):
        st.session_state.msg = "Te has chocado."
        return
    st.session_state.player = (nx,ny)
    st.session_state.moves += 1
    st.session_state.msg = ""
    # pickup
    if st.session_state.player in st.session_state.coins:
        st.session_state.coins.remove(st.session_state.player)
        if st.session_state.player in st.session_state.runas_positions:
            st.session_state.runas_collected += 1
            st.session_state.msg = f"Runa recogida ({st.session_state.runas_collected}/{st.session_state.total_runas})"
        else:
            st.session_state.msg = "Fragmento recogido."
    # enemies move after player
    new_en = []
    for e in st.session_state.enemies:
        new_en.append(enemy_step(e, st.session_state.player, st.session_state.map))
    st.session_state.enemies = new_en
    # collision
    if st.session_state.player in st.session_state.enemies:
        st.session_state.game_over = True
        st.session_state.msg = "Un guardián te atrapó. FIN."
    # victory
    if st.session_state.runas_collected >= st.session_state.total_runas and st.session_state.player == st.session_state.altar:
        st.session_state.victory = True
        st.session_state.game_over = True
        st.session_state.msg = "¡Victoria! Las runas han vuelto al altar."

# -------------------------
# Rendering final (mejor calidad)
# -------------------------
def render_image():
    im = new_canvas()
    draw = ImageDraw.Draw(im)
    # floor/walls (con patrón sutil)
    for y in range(MAP_H):
        for x in range(MAP_W):
            if st.session_state.map[y][x] == 1:
                # wall with subtle gradient
                draw.rectangle([x*TILE, y*TILE, (x+1)*TILE-1, (y+1)*TILE-1], fill=PALETTE["wall"])
                # inner lighter edge
                draw.line([x*TILE+1, y*TILE+1, x*TILE+TILE-3, y*TILE+1], fill=(40,50,80))
            else:
                draw.rectangle([x*TILE, y*TILE, (x+1)*TILE-1, (y+1)*TILE-1], fill=PALETTE["floor"])
    # altar
    ax,ay = st.session_state.altar
    draw_altar(draw, ax, ay)
    # coins
    for c in list(st.session_state.coins):
        draw_coin(draw, c[0], c[1])
    # enemies
    for e in st.session_state.enemies:
        draw_enemy(draw, e[0], e[1])
    # player
    draw_player(draw, st.session_state.player[0], st.session_state.player[1])
    # UI overlay (transparent rectangle bottom)
    ui_h = TILE*3
    draw.rectangle([0, HEIGHT-ui_h, WIDTH, HEIGHT], fill=(8,10,14))
    # text
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 12)
    except:
        font = ImageFont.load_default()
    txt1 = f"Runas: {st.session_state.runas_collected}/{st.session_state.total_runas}   Movs: {st.session_state.moves}"
    txt2 = st.session_state.msg
    draw.text((6, HEIGHT - ui_h + 6), txt1, font=font, fill=PALETTE["ui_text"])
    draw.text((6, HEIGHT - ui_h + 22), txt2, font=font, fill=PALETTE["ui_text"])
    # scale nearest for crisp pixels
    im = im.resize((WIDTH*SCALE, HEIGHT*SCALE), resample=Image.NEAREST)
    return im

# -------------------------
# UI Streamlit
# -------------------------
st.set_page_config(page_title="Lúm: Runas (Pro)", layout="wide")
st.title("Lúm: Runas de Calder — PRO (flechas del teclado)")
st.markdown("Historia: recupera 3 runas y vuelve al altar. Usa las flechas del teclado para moverte — la experiencia ha sido optimizada para Streamlit.")

left, right = st.columns([1.8,1])

with left:
    img = render_image()
    st.image(img, use_column_width=True)

    # visible control botones (también sirven para clic y accesibilidad)
    c_up, c_mid, c_down = st.columns([1,1,1])
    if c_up.button("↑", key="btn_up"):
        attempt_move(0, -1)
    cols = st.columns([1,1,1])
    if cols[0].button("←", key="btn_left"):
        attempt_move(-1, 0)
    if cols[2].button("→", key="btn_right"):
        attempt_move(1, 0)
    if c_down.button("↓", key="btn_down"):
        attempt_move(0, 1)

with right:
    st.subheader("Estado")
    st.write(f"**Runas:** {st.session_state.runas_collected}/{st.session_state.total_runas}")
    st.write(f"**Movimientos:** {st.session_state.moves}")
    st.write(f"**Posición:** {st.session_state.player}")
    st.write(f"**Altar:** {st.session_state.altar}")
    st.write(f"**Guardias:** {len(st.session_state.enemies)}")
    st.write("---")
    st.write("Consejos:")
    st.write("- Usa las flechas del teclado (← ↑ → ↓).")
    st.write("- Evita a los guardianes; planifica movimientos.")
    st.write("- Las runas brillan: recógelas y regresa al altar.")
    st.write("---")

    if st.session_state.game_over:
        if st.session_state.victory:
            st.success("¡Has restaurado el Equilibrio! 🎉")
        else:
            st.error("Derrotado — reinicia para intentarlo de nuevo.")
    if st.button("Reiniciar (nueva semilla)"):
        # re-init
        st.session_state.seed = random.randint(0,9999999)
        st.session_state.map = make_map(st.session_state.seed)
        free = free_positions(st.session_state.map)
        st.session_state.player = random.choice(free)
        st.session_state.altar = random.choice([p for p in free if p[0]<3 or p[0]>MAP_W-4 or p[1]<3 or p[1]>MAP_H-4])
        rnd = random.Random(st.session_state.seed)
        st.session_state.coins = rnd.sample([p for p in free if p != st.session_state.player and p != st.session_state.altar], 7)
        st.session_state.total_runas = 3
        st.session_state.runas_positions = set(rnd.sample(st.session_state.coins, st.session_state.total_runas))
        st.session_state.enemies = rnd.sample([p for p in free if p not in st.session_state.coins and p != st.session_state.player and p != st.session_state.altar], 4)
        st.session_state.runas_collected = 0
        st.session_state.moves = 0
        st.session_state.msg = "Partida reiniciada. ¡Adelante!"
        st.session_state.victory = False
        st.session_state.game_over = False

# -------------------------
# BIND TECLAS: streamlit-shortcuts
# -------------------------
# Mapea las flechas a los botones que creamos arriba para que funcionen con teclado
# NOTA: streamlit-shortcuts espera el 'key' del widget, aquí usamos las keys de los botones.
add_shortcuts(btn_up="arrowup", btn_left="arrowleft", btn_right="arrowright", btn_down="arrowdown")

# -------------------------
# Historia / notas
# -------------------------
st.markdown("---")
st.markdown("**Historia:** El pueblo de Calder perdió 3 runas. Eres Lúm, el recolector. Recupera las runas y vuelve al altar evitando guardianes. Cada guardián tiene movimiento simple pero efectivo — piensa en cada paso.")
st.markdown("**Detalles técnicos:** Capturamos atajos de teclado con `streamlit-shortcuts` (mapeo directo de flechas). El render está hecho con Pillow para asegurar compatibilidad y buen rendimiento en Streamlit.")
