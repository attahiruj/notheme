"""notheme Pixel cursor theme: hand-drawn 10x10 sprites, auto-outlined, written as Xcursor files.

Pure standard library. Every sprite is a 10x10 (max) grid of cells; one cell is 2px at the
24px default size, and the sprites scale in whole cells to 36/48/72/96px, so edges stay crisp.

Legend: '#' white, '+' accent, '.' gray, ' ' transparent. The black outline is generated.
"""
import math
import struct

CELL_SIZES = (24, 36, 48, 72, 96)   # canvas is 12 cells: 10 of artwork plus 1 of outline each side
CANVAS = 12
WHITE, BLACK, GRAY = (0xF2, 0xF2, 0xF2), (0, 0, 0), (0x8C, 0x8C, 0x8C)
DELAY = 90  # ms per animation frame


def _rows(text):
    return [r for r in text.strip('\n').splitlines()]


def _mirror(rows):
    width = max(map(len, rows))
    return [r.ljust(width)[::-1] for r in rows]


def _transpose(rows):
    width = max(map(len, rows))
    rows = [r.ljust(width) for r in rows]
    return [''.join(r[i] for r in rows) for i in range(width)]


def _grid(n, fn):
    return [''.join(fn(x, y) for x in range(n)) for y in range(n)]


def _overlay(base, top, dx=0, dy=0):
    """Draw `top` over `base` (both lists of strings), offset by dx, dy."""
    cells = [list(r) for r in base]
    for y, row in enumerate(top):
        for x, ch in enumerate(row):
            if ch != ' ' and 0 <= y + dy < len(cells):
                line = cells[y + dy]
                if 0 <= x + dx < len(line):
                    line[x + dx] = ch
    return [''.join(r) for r in cells]


ARROW = _rows('''
#
##
###
####
#####
######
#######
####
## ##
#  +++
''')
ARROW[8] = '## +#'
ARROW[9] = '#  ++'
SHORT_ARROW = ARROW[:7]  # same tip, room underneath for a badge

IBEAM = _rows('''
#######
  ###
   #
   #
   #
   #
   #
   #
  ###
#######
''')
IBEAM = [r.center(7) for r in IBEAM]
IBEAM[4] = '   +   '
IBEAM[5] = '   +   '

HAND = _rows('''
  ++
  ##
  ##
  ##
  ## # #
  ########
 #########
 #########
  ########
   ######
''')
OPEN = _rows('''
  # # #
  # # # #
 ## # # ##
 #########
##########
##########
##########
 #########
  ++++++
   ####
''')
FIST = _rows('''
 # # # #
##########
##########
##########
##########
 ########
  ++++++
   ####
''')


def _ring(radius_in, radius_out, size=10):
    c = (size - 1) / 2

    def cell(x, y):
        d = math.hypot(x - c, y - c)
        return '#' if radius_in <= d <= radius_out else ' '
    return _grid(size, cell)


FORBIDDEN = _ring(3.4, 4.7)
FORBIDDEN = _overlay(FORBIDDEN, [''.join('+' if x + y in (9, 10) and 1 < x < 8 else ' ' for x in range(10))
                                 for y in range(10)])
FORBIDDEN = [''.join('+' if (x + y in (8, 9, 10) and 1 <= x <= 8 and 1 <= y <= 8) else ch
                     for x, ch in enumerate(row)) for y, row in enumerate(FORBIDDEN)]

MOVE = _rows('''
    ##
   ####
    ##
 #  ##  #
####++####
####++####
 #  ##  #
    ##
   ####
    ##
''')

EW = _rows('''
  #    #
 ##    ##
####++####
 ##    ##
  #    #
''')

DIAG = _grid(10, lambda x, y: '#' if (x == y or x + y <= 3 or x + y >= 15) else ' ')
DIAG = [''.join('+' if (x, y) in ((4, 4), (5, 5)) else ch for x, ch in enumerate(r)) for y, r in enumerate(DIAG)]

CROSS = _grid(9, lambda x, y: '+' if (x, y) == (4, 4) else
              '#' if ((y == 4 and (x < 3 or x > 5)) or (x == 4 and (y < 3 or y > 5))) else ' ')

CELL = _rows('''
    ##
    ##
    ##
    ##
##########
##########
    ##
    ##
    ##
    ##
''')
CELL = [''.join('+' if (x, y) in ((4, 4), (5, 4), (4, 5), (5, 5)) else ch for x, ch in enumerate(r.ljust(10)))
        for y, r in enumerate(CELL)]

QUESTION = _rows('''
 ####
##  ##
    ##
   ##
  ##
  ##

  ++
''')

def _loupe(sign):
    mid = ['#  +  #', '# +++ #', '#  +  #'] if sign == 'in' else ['#     #', '# +++ #', '#     #']
    return [' #####', '##   ##', *mid, '##   ##', ' ######', '       ##', '        ##'][:10]


def _spinner(step):
    """Eight 2x2 dots on a ring. One red head, a white tail, the rest gray."""
    spots = [(4, 0), (7, 1), (8, 4), (7, 7), (4, 8), (1, 7), (0, 4), (1, 1)]
    cells = [[' '] * 10 for _ in range(10)]
    for i, (x, y) in enumerate(spots):
        age = (step - i) % 8
        ch = '+' if age == 0 else '#' if age <= 2 else '.'
        for dy in range(2):
            for dx in range(2):
                cells[y + dy][x + dx] = ch
    return [''.join(r) for r in cells]


def _progress(step):
    frame = _overlay(_grid(10, lambda x, y: ' '), SHORT_ARROW)
    for i in range(3):
        frame = _overlay(frame, ['++' if i == step % 3 else '..'] * 2, 4 + i * 3 - 1, 8)
    return frame


# name: (frames, hotspot in artwork cells, aliases). Frames beyond one animate.
def sprites(extra_alias=True):
    badge_plus = _overlay(_overlay(_grid(10, lambda x, y: ' '), SHORT_ARROW), ['  +  ', ' +++ ', '  +  '], 5, 6)
    badge_link = _overlay(_overlay(_grid(10, lambda x, y: ' '), SHORT_ARROW), ['#+', '+#'], 6, 7)
    badge_menu = _overlay(_overlay(_grid(10, lambda x, y: ' '), SHORT_ARROW), ['+++', '', '###', '', '###'], 7, 5)
    s = {
        'default': ([ARROW], (0, 0), ['left_ptr', 'arrow', 'top_left_arrow', 'X_cursor', 'right_ptr', 'dnd-ask']),
        'text': ([IBEAM], (3, 5), ['xterm', 'ibeam']),
        'vertical-text': ([_transpose(IBEAM)], (5, 3), []),
        'pointer': ([HAND], (2, 0), ['hand1', 'hand2', 'pointing_hand', 'e29285e634086352946a0e7090d73106',
                                     '9d800788f1b08800ae810202380a0822']),
        'wait': ([_spinner(i) for i in range(8)], (4, 4), ['watch']),
        'progress': ([_progress(i) for i in range(3)], (0, 0), ['left_ptr_watch', '08e8e1c95fe2fc01f976f1e063a24ccd',
                                                                '3ecb610c1bf2410f44200f48c40d3599']),
        'crosshair': ([CROSS], (4, 4), ['cross', 'tcross', 'cross_reverse', 'diamond_cross']),
        'cell': ([CELL], (4, 4), ['plus']),
        'move': ([MOVE], (4, 4), ['fleur', 'all-scroll', 'size_all', '4498f0e0c1937ffe01fd06f973665830']),
        'grab': ([OPEN], (4, 4), ['openhand', 'hand', 'dnd-none-open']),
        'grabbing': ([FIST], (4, 4), ['closedhand', 'dnd-move', 'fcf21c00b30f7e3f83fe0dfd12e71cff']),
        'not-allowed': ([FORBIDDEN], (4, 4), ['crossed_circle', 'no-drop', 'forbidden', 'dnd-none',
                                              '03b6e0fcb3499374a867c041f52298f0']),
        'help': ([QUESTION], (3, 4), ['question_arrow', 'whats_this', 'd9ce0ab605698f320427677b458ad60b',
                                      '5c6cd98b3f3ebcb1f9c7f1c204630408']),
        'zoom-in': ([_loupe('in')], (3, 3), []),
        'zoom-out': ([_loupe('out')], (3, 3), []),
        'copy': ([badge_plus], (0, 0), ['dnd-copy', '1081e37283d90000800003c07f3ef6bf', '6407b0e94181790501fd1e167b474872']),
        'alias': ([badge_link], (0, 0), ['dnd-link', 'link', '3085a0e285b5ed0b00b1c3f2b4b5bb0d', '640fb0e74195791501fd1ed57b41487f']),
        'context-menu': ([badge_menu], (0, 0), []),
        'ew-resize': ([EW], (5, 2), ['col-resize', 'sb_h_double_arrow', 'h_double_arrow', 'split_h', 'e-resize', 'w-resize',
                                      'left_side', 'right_side', 'size_hor', '14fef782d02440884392942c11205230']),
        'ns-resize': ([_transpose(EW)], (2, 5), ['row-resize', 'sb_v_double_arrow', 'v_double_arrow', 'split_v', 'n-resize',
                                                  's-resize', 'top_side', 'bottom_side', 'size_ver',
                                                  '2870a09082c103050810ffdffffe0204']),
        'nwse-resize': ([DIAG], (4, 4), ['nw-resize', 'se-resize', 'top_left_corner', 'bottom_right_corner', 'size_fdiag',
                                          'c7088f0f3e6c8088236ef8e1e3e70000']),
        'nesw-resize': ([_mirror(DIAG)], (5, 4), ['ne-resize', 'sw-resize', 'top_right_corner', 'bottom_left_corner',
                                                   'size_bdiag', 'fcf1c3c7cd4491d801f1e1c78f100000']),
    }
    return s


def outline(rows):
    """Place the artwork on the 12-cell canvas and wrap it in a 1-cell black outline."""
    h = len(rows)
    w = max(map(len, rows))
    if h > CANVAS - 2 or w > CANVAS - 2:
        raise ValueError(f'sprite is {w}x{h}; the limit is {CANVAS - 2}x{CANVAS - 2}')
    ox, oy = (CANVAS - w) // 2, (CANVAS - h) // 2
    ink = {}
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ' ':
                ink[(x + ox, y + oy)] = ch
    out = dict(ink)
    for (x, y) in ink:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                out.setdefault((x + dx, y + dy), 'o')
    return out, ox, oy


def raster(rows, accent, size):
    """Premultiplied ARGB bytes for the sprite at `size` px (an integer multiple of 12 cells)."""
    scale = size // CANVAS
    cells, _, _ = outline(rows)
    palette = {'#': WHITE, '+': accent, '.': GRAY, 'o': BLACK}
    pix = bytearray(size * size * 4)
    for (cx, cy), ch in cells.items():
        r, g, b = palette[ch]
        px = struct.pack('<4B', b, g, r, 255)
        for y in range(cy * scale, (cy + 1) * scale):
            start = (y * size + cx * scale) * 4
            pix[start:start + 4 * scale] = px * scale
    return bytes(pix)


def hex_rgb(value):
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def xcursor(frames, hot, accent):
    """Encode an Xcursor file: every frame at every size, animated when there are several."""
    images = []
    for size in CELL_SIZES:
        scale = size // CANVAS
        for rows in frames:
            _, ox, oy = outline(rows)
            hx, hy = (hot[0] + ox + 1) * scale, (hot[1] + oy + 1) * scale
            body = struct.pack('<9I', 36, 0xfffd0002, size, 1, size, size, hx, hy, DELAY if len(frames) > 1 else 0)
            images.append((size, body + raster(rows, accent, size)))
    head = 16 + 12 * len(images)
    toc, data, pos = b'', b'', head
    for size, chunk in images:
        toc += struct.pack('<3I', 0xfffd0002, size, pos)
        data += chunk
        pos += len(chunk)
    return b'Xcur' + struct.pack('<3I', 16, 0x10000, len(images)) + toc + data


INDEX = '[Icon Theme]\nName=notheme Cursor\nComment=Pixel cursors: white with a black outline and a red accent\n'


def build_cursors(out, write_bytes, accent='#D71921'):
    """Write <out>/index.theme and <out>/cursors/*. Aliases are real copies, so they survive any copier."""
    color = hex_rgb(accent)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'index.theme').write_text(INDEX)
    for name, (frames, hot, aliases) in sprites().items():
        blob = xcursor(frames, hot, color)
        for target in (name, *aliases):
            write_bytes(out / 'cursors' / target, blob)
    return out
