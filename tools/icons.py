"""Original 16px-grid notheme Pixel icons; no curves, strokes or filters."""

WHITE, RED, GRAY = '#F2F2F2', '#D71921', '#8C8C8C'
# Unthemed icons fall back to Papirus. Its Dark variant draws light glyphs for
# dark surfaces, which nearly vanish on white, so light mode uses Papirus-Light.
FALLBACK = {'dark': 'Papirus-Dark', 'light': 'Papirus-Light'}
INDEX = ('[Icon Theme]\nName=notheme Pixel\nComment=16px pixel-art icons with Nothing red accents\n'
         'Inherits={fallback},Adwaita,hicolor\nDirectories=scalable/places,scalable/apps,symbolic/places,symbolic/actions\n'
         '[scalable/places]\nSize=64\nMinSize=16\nMaxSize=256\nType=Scalable\nContext=Places\n'
         '[scalable/apps]\nSize=64\nMinSize=16\nMaxSize=256\nType=Scalable\nContext=Applications\n'
         '[symbolic/places]\nSize=16\nMinSize=8\nMaxSize=64\nType=Scalable\nContext=Places\n'
         '[symbolic/actions]\nSize=16\nMinSize=8\nMaxSize=64\nType=Scalable\nContext=Actions\n')


def pixel_svg(sprite, symbolic=False):
    rows = sprite.strip('\n').splitlines()
    width = max(map(len, rows))
    if width > 16 or len(rows) > 16:
        raise ValueError('Pixel icon exceeds the 16×16 design grid')
    left, top = (16 - width) // 2, (16 - len(rows)) // 2
    colors = {'#': WHITE, '+': WHITE if symbolic else RED, '.': WHITE if symbolic else GRAY}
    pixels = []
    for y, row in enumerate(rows):
        for x, cell in enumerate(row):
            if cell != ' ':
                pixels.append(f'<rect x="{left + x}" y="{top + y}" width="1" height="1" fill="{colors[cell]}"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" '
            'viewBox="0 0 16 16" shape-rendering="crispEdges">' + ''.join(pixels) + '</svg>')


FOLDER = '''
 ####
 #   #
 #    ######
############
#          #
#          #
#          #
#          #
#          #
############
'''
HOME = '''
     ++
    ++++
   ##  ##
  ##    ##
 ##      ##
##        ##
  #      #
  #  ##  #
  #  ##  #
  #  ##  #
  ########
'''
TERMINAL = '''
 ##########
##        ##
#          #
#  #       #
#   #      #
#    #     #
#   #      #
#  #  ++++ #
#          #
##        ##
 ##########
'''
BROWSER = '''
   ######
  ##    ##
 ##  ##  ##
##   ##   ##
# ######## #
#    ##    #
#    ++    #
# ++++++++ #
##   ++   ##
 ##  ++  ##
  ##    ##
   ######
'''
DOCUMENT = '''
 ########
 #      ##
 #      # #
 #      ####
 #         #
 #  #####  #
 #         #
 #  #####  #
 #         #
 #  +++    #
 #         #
 ###########
'''


def build_icons(root, write, mode='dark'):
    write(root / 'index.theme', INDEX.replace('{fallback}', FALLBACK.get(mode, FALLBACK['dark'])))
    apps = [
        (['org.gnome.Nautilus', 'nautilus', 'system-file-manager', 'file-manager'],
         FOLDER.replace(' ####', ' ++++', 1)),
        (['brave-browser', 'brave-browser-stable', 'brave', 'brave_brave', 'com.brave.Browser'], '''
 ##      ##
############
##        ##
 # ##  ## #
 #  #  #  #
 #   ##   #
 ##  ++  ##
  # ++++ #
  ## ++ ##
   #    #
    ####
     ##
'''),
        (['code', 'code_code', 'visual-studio-code', 'com.visualstudio.code', 'vscode'], '''
         ##
        # #
 ##    #  #
 # #  #   #
  # ##    #
   ##     #
   ##     #
  # ##    #
 # #  #   #
 ##    #  #
        # #
         ++
'''),
        (['org.gnome.Terminal', 'gnome-terminal', 'utilities-terminal', 'org.gnome.Console',
          'kgx', 'kitty', 'Alacritty', 'com.mitchellh.ghostty'], TERMINAL),
        (['org.gnome.Settings', 'gnome-control-center', 'preferences-system',
          'org.gnome.tweaks', 'org.gnome.Extensions', 'com.mattjakeman.ExtensionManager'], '''
    ####
 ## #  # ##
 # ##  ## #
 ##      ##
##   ++   ##
#   +  +   #
#   +  +   #
##   ++   ##
 ##      ##
 # ##  ## #
 ## #  # ##
    ####
'''),
        (['firefox', 'firefox_firefox', 'org.mozilla.firefox', 'google-chrome',
          'google-chrome-stable', 'chromium', 'chromium-browser', 'org.chromium.Chromium',
          'web-browser'], BROWSER),
        (['org.gnome.TextEditor', 'org.gnome.gedit', 'gedit', 'accessories-text-editor',
          'org.gnome.Evince', 'evince', 'x-office-document'], DOCUMENT),
        (['org.gnome.Software', 'snap-store', 'snap-store_snap-store', 'software-store'], '''
    ++++
   +    +
   +    +
############
#          #
#          #
#    ##    #
#   ####   #
#   ####   #
#    ##    #
#          #
############
'''),
    ]
    for aliases, sprite in apps:
        for name in aliases:
            write(root / f'scalable/apps/{name}.svg', pixel_svg(sprite))

    # Small badges distinguish folder types without subpixel linework.
    badges = {
        'folder': [], 'folder-open': [(8, 5), (9, 5)],
        'folder-documents': [(7, 5), (8, 5), (7, 6), (7, 7), (8, 7)],
        'folder-download': [(8, 4), (8, 5), (8, 6), (7, 6), (9, 6), (8, 7)],
        'folder-music': [(7, 5), (8, 5), (9, 5), (7, 6), (9, 6), (6, 7), (8, 7)],
        'folder-pictures': [(6, 7), (7, 6), (8, 7), (9, 6), (10, 7)],
        'folder-videos': [(7, 5), (7, 6), (8, 6), (7, 7)],
        'folder-desktop': [(6, 5), (7, 5), (8, 5), (9, 5), (6, 6), (9, 6), (7, 7), (8, 7)],
        'folder-publicshare': [(6, 5), (9, 5), (7, 6), (8, 6), (6, 7), (9, 7)],
        'folder-templates': [(7, 5), (8, 5), (7, 6), (8, 6), (7, 7), (8, 7)],
    }
    for name, badge in badges.items():
        rows = [list(row.ljust(12)) for row in FOLDER.strip('\n').splitlines()]
        rows[0][2] = '+'
        rows[0][3] = '+'
        for x, y in badge:
            rows[y][x] = '+'
        sprite = '\n'.join(''.join(row) for row in rows)
        write(root / f'scalable/places/{name}.svg', pixel_svg(sprite))
        write(root / f'symbolic/places/{name}-symbolic.svg', pixel_svg(sprite, symbolic=True))
    write(root / 'scalable/places/user-home.svg', pixel_svg(HOME))
    write(root / 'symbolic/places/user-home-symbolic.svg', pixel_svg(HOME, symbolic=True))
    # Nautilus uses user-desktop, not folder-desktop, for the XDG desktop folder.
    for alias, target in {'user-desktop': 'folder-desktop', 'folder-downloads': 'folder-download',
                          'folder-remote': 'folder-publicshare', 'folder-saved-search': 'folder-documents'}.items():
        write(root / f'scalable/places/{alias}.svg', (root / f'scalable/places/{target}.svg').read_text())
        write(root / f'symbolic/places/{alias}-symbolic.svg', (root / f'symbolic/places/{target}-symbolic.svg').read_text())
    for name in ('user-trash', 'user-trash-full'):
        sprite = '''
    ++++
    +  +
############
 #        #
 # # ## # #
 # # ## # #
 # # ## # #
 # # ## # #
 #        #
  ########
'''
        if name.endswith('full'):
            sprite = sprite.replace(' #        #', ' # ++++++ #')
        write(root / f'scalable/places/{name}.svg', pixel_svg(sprite))
        write(root / f'symbolic/places/{name}-symbolic.svg', pixel_svg(sprite, symbolic=True))
    grid = '\n'.join('##   ##   ##' if y % 5 < 2 else '' for y in range(12))
    write(root / 'symbolic/actions/view-app-grid-symbolic.svg', pixel_svg(grid, symbolic=True))
