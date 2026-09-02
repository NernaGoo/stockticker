# Hardware:
# MatrixPortal Stock Ticker
# https://learn.adafruit.com/adafruit-matrixportal-s3
# 64x32 RGB LED Matrix
# https://www.adafruit.com/product/2278

import time
import board
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_matrixportal.matrixportal import MatrixPortal
from secrets import secrets

# ---------------- FONT FILES ---------------- #
FONT = "./fonts/IBMPlexMono-Medium-24_jep.bdf"
FONT2 = "./fonts/helvB12.bdf"
FONT3 = "./fonts/helvR10.bdf"
FONT4 = "./fonts/6x10.bdf"
FONT5 = "./fonts/Arial-12.bdf"
FONT6 = "./fonts/Arial-14.bdf"

# ---------------- SPECIAL CHARS ----------------- #
# Included here for reference
# ▲, ▼, ►, ◄, ↑, ↓
# €, £, ±, µ, ∞, ≈, ¢, ₿
# °, ℃, ★, ✓, ⚠
# 🚀, 🔥, 🐍
# ± (Plus-Minus), ≈ (Approximately), Δ (Greek Delta - used for "Change"), ∞ (Infinity)
# ½, ¼, ¾
# ✓ (Checkmark), ✗ (X-mark), ⚠ (Warning sign), ★ (Star)
# • (Standard dot), ▪ (Square bullet), ◦ (Hollow bullet)
# █ (Full block)
# ▓ (Dark shade)
# ▒ (Medium shade)
# ░ (Light shade)
# ═ (Double horizontal line)
# ║ (Double vertical line)
# ╔ ╗ ╚ ╝ (Double corners)
# Conditions: ☼ (Sun), ☁ (Cloud), ☂ (Umbrella/Rain), ❄ (Snowflake), ⚡ (Lightning)
# Metrics: ° (Degree), ℃ (Celsius), ℉ (Fahrenheit), % (Percent)


# ----------------- SETUP ----------------- #
matrixportal = MatrixPortal(status_neopixel=None, debug=False)
display = matrixportal.display

price_font = bitmap_font.load_font(FONT4)
name_font = bitmap_font.load_font(FONT4)
UP_ARROW = "▲"  # up arrow symbol when stock is up
DOWN_ARROW = "▼"    # down arrow symbol when stock is down

SCROLL_Y = 8     # top row
STATIC_Y = 24    # bottom row
GAP = 3          # pixel gap between segments within a row

# ----------------- COLOR DEFINITIONS ----------------- #
WHITE = 0xFFFFFF
BLUE = 0x0000FF
YELLOW = 0xFFFF00
GREEN = 0x00FF00
RED = 0xFF0000
CYAN = 0x00FFFF
MAGENTA = 0xFF00FF
ORANGE = 0xFFA500
PURPLE = 0x800080
PINK = 0xFFC0CB
GOLD = 0xFFD700
TEAL = 0x008080
MIDNIGHT = 0x004000
BLACK = 0x000000  # Used to turn text/pixels off


# ----------------- STOCK / API CONFIG ----------------- #
STOCKS = ["AAPL", "MSFT", "GOOGL", "TSLA"] # list of stock symbols for ticker display
API_KEY = secrets["finnhubio_token"]
API_URL = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={API_KEY}"

'''
# Throttle API calls to avoid exceeding the free tier limits of Finnhub.io
# Free tier allows 60 API calls per minute
# limits: 
# 60 API calls/min
# 30 API call per second burst limit
'''
MIN_SECONDS_BETWEEN_CALLS = 2
DATA_INTERVAL = 1200
DAILY_CALL_LIMIT = 500

last_api_call_time = 0
calls_today = 0
day_start = time.monotonic()
SECONDS_PER_DAY = 86400

quotes_cache = {}


def fetch_quote(symbol):
    try:
        response = matrixportal.network.fetch(API_URL.format(symbol=symbol))
        data = response.json()
        return {
            "symbol": symbol,
            "price": data["c"],
            "change": data["d"],
            "percent": data["dp"],
        }
    except Exception as e:
        print("fetch failed for", symbol, ":", e)
        return None


def throttled_fetch_quote(symbol):
    global last_api_call_time
    now = time.monotonic()
    wait = MIN_SECONDS_BETWEEN_CALLS - (now - last_api_call_time)
    if wait > 0:
        time.sleep(wait)
    last_api_call_time = time.monotonic()
    return fetch_quote(symbol)


def blank_labels():
    # Clear all segment text when quotes are being refreshed.
    name_label.text = ""
    price_label.text = ""
    arrow_label.text = ""
    change_label.text = ""
    percent_sign_label.text = ""
    percent_value_label.text = ""


def refresh_all_quotes():
    global calls_today, day_start
    now = time.monotonic()
    if now - day_start > SECONDS_PER_DAY:
        calls_today = 0
        day_start = now

    blank_labels()

    for symbol in STOCKS:
        if calls_today >= DAILY_CALL_LIMIT:
            print("Daily API call limit reached; using cached data.")
            break
        q = throttled_fetch_quote(symbol)
        calls_today += 1
        if q is not None:
            quotes_cache[symbol] = q


# ----------------- DISPLAY LAYOUT ----------------- #
# --- Scrolling row - font and colors: price | arrow | dollar delta
price_label = Label(price_font, text="", y=SCROLL_Y, color=CYAN)
arrow_label = Label(price_font, text="", y=SCROLL_Y, color=YELLOW)
change_label = Label(price_font, text="", y=SCROLL_Y, color=GREEN)

# --- Static row - font and colors: name | percent delta
name_label = Label(name_font, text="", x=2, y=STATIC_Y, color=WHITE)
percent_sign_label = Label(name_font, text="", y=STATIC_Y, color=MAGENTA)
percent_value_label = Label(name_font, text="", y=STATIC_Y, color=GREEN)

def make_row_background(y, height):
    """Solid black bar spanning the full display width, to guarantee clean overwrite each frame."""
    bmp = displayio.Bitmap(display.width, height, 1)
    pal = displayio.Palette(1)
    pal[0] = 0x000000
    return displayio.TileGrid(bmp, pixel_shader=pal, x=0, y=y)

scroll_row_bg = make_row_background(0, SCROLL_Y + 6)
static_row_bg = make_row_background(SCROLL_Y + 6, display.height - (SCROLL_Y + 6))

group = displayio.Group()
group.append(scroll_row_bg)
group.append(static_row_bg)
group.append(price_label)
group.append(arrow_label)
group.append(change_label)
group.append(name_label)
group.append(percent_sign_label)
group.append(percent_value_label)
display.root_group = group

scroll_row_width = 0  # total pixel width of the scrolling row; set in apply_quote()


def layout_scroll_row(base_x):
    """Position price/arrow/change segments side by side starting at base_x."""
    price_label.x = base_x
    arrow_label.x = price_label.x + price_label.bounding_box[2] + GAP
    change_label.x = arrow_label.x + arrow_label.bounding_box[2] + GAP


def layout_static_percent():
    """Right-align the percent sign + value pair as a single unit."""
    pair_width = percent_sign_label.bounding_box[2] + percent_value_label.bounding_box[2]
    start_x = display.width - pair_width - 2
    percent_sign_label.x = start_x
    percent_value_label.x = percent_sign_label.x + percent_sign_label.bounding_box[2]


def scale_color(color, factor):
    r = int(((color >> 16) & 0xFF) * factor)
    g = int(((color >> 8) & 0xFF) * factor)
    b = int((color & 0xFF) * factor)
    return (r << 16) | (g << 8) | b


def apply_quote(index):
    """Populate all segments for the stock at `index`. Returns the direction color (RED/GREEN)."""
    global scroll_row_width
 
    symbol = STOCKS[index]
    quote = quotes_cache.get(symbol)
    if quote is None:
        print("apply_quote: no cached quote for", symbol)
        return None
 
    is_up = quote["change"] >= 0
    direction_color = GREEN if is_up else RED
 
    # Push scrolling segments off-screen FIRST, before changing their text --
    # this avoids a brief flash of the new text at its old (visible) position.
    price_label.x = display.width
    arrow_label.x = display.width
    change_label.x = display.width
 
    name_label.text = quote["symbol"]  # always white
 
    price_label.text = "${:.2f} ".format(quote["price"])
    arrow_label.text = UP_ARROW if is_up else DOWN_ARROW
    arrow_label.color = BLUE if is_up else YELLOW
    change_label.text = "${:.2f}".format(abs(quote["change"]))
    change_label.color = direction_color
 
    percent_sign_label.text = "+" if is_up else "-"
    percent_value_label.text = "{:.2f}%".format(abs(quote["percent"]))
    percent_value_label.color = direction_color
 
    layout_scroll_row(display.width)
    scroll_row_width = (change_label.x + change_label.bounding_box[2]) - price_label.x
 
    layout_static_percent()
 
    return direction_color


# ============================================================
# Smooth fade transition between stocks
# ============================================================
FADE_STEPS = 10
FADE_DELAY = 0.02
ticker_state = {"last_change_color": WHITE}


def set_scroll_row_colors(factor, change_color):
    """Scale each scrolling-row segment toward its own target color by factor.
    change_color is GREEN (up) or RED (down) -- also used here to pick the
    matching arrow color (BLUE for up, YELLOW for down)."""
    arrow_color = BLUE if change_color == GREEN else YELLOW
    price_label.color = scale_color(CYAN, factor)
    arrow_label.color = scale_color(arrow_color, factor)
    change_label.color = scale_color(change_color, factor)


def set_static_percent_colors(factor, change_color):
    percent_color = BLUE if change_color == GREEN else PURPLE
    percent_sign_label.color = scale_color(MAGENTA, factor)
    percent_value_label.color = scale_color(change_color, factor)


def run_transition(next_index):
    """Fade out (each segment toward its own color), swap data, fade back in.
    name_label stays white throughout - it is not part of the fade."""
    prev_change_color = ticker_state["last_change_color"]

    for step in range(FADE_STEPS, -1, -1):
        factor = step / FADE_STEPS
        set_scroll_row_colors(factor, prev_change_color)
        set_static_percent_colors(factor, prev_change_color)
        time.sleep(FADE_DELAY)

    new_change_color = apply_quote(next_index)
    if new_change_color is None:
        new_change_color = WHITE

    for step in range(FADE_STEPS + 1):
        factor = step / FADE_STEPS
        set_scroll_row_colors(factor, new_change_color)
        set_static_percent_colors(factor, new_change_color)
        time.sleep(FADE_DELAY)

    ticker_state["last_change_color"] = new_change_color


# --------- INITIAL LOAD OF FIRST STOCK --------- #
active_index = 0
refresh_all_quotes()
initial_change_color = apply_quote(active_index) or WHITE
set_scroll_row_colors(1.0, initial_change_color)
set_static_percent_colors(1.0, initial_change_color)
ticker_state["last_change_color"] = initial_change_color

last_data_update = time.monotonic()
SCROLL_SPEED = 0.03
REPEATS_PER_QUOTE = 3
scroll_repeat_count = 0
scroll_base_x = display.width
refresh_due = False

# ----------------- MAIN LOOP ----------------- #
while True:
    scroll_base_x -= 1
    layout_scroll_row(scroll_base_x)

    scroll_finished = scroll_base_x < -scroll_row_width
    if scroll_finished:
        scroll_base_x = display.width
        scroll_repeat_count += 1

    now = time.monotonic()

    if now - last_data_update > DATA_INTERVAL:
        refresh_due = True

    if scroll_finished and refresh_due:
        refresh_all_quotes()
        color = apply_quote(active_index) or WHITE
        set_scroll_row_colors(1.0, color)
        set_static_percent_colors(1.0, color)
        ticker_state["last_change_color"] = color
        last_data_update = now
        scroll_base_x = display.width
        refresh_due = False

    if scroll_repeat_count >= REPEATS_PER_QUOTE:
        active_index = (active_index + 1) % len(STOCKS)
        run_transition(active_index)
        scroll_repeat_count = 0
        scroll_base_x = display.width

    time.sleep(SCROLL_SPEED)