"""Export the code-native foundation mark. Development only: requires Pillow."""
from pathlib import Path
import re
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'static'
PATHS = [
 ('#ffffff', 'M48 78 C43 74 18 58 18 39 C18 21 39 18 48 32 C57 18 78 21 78 39 C78 58 53 74 48 78 Z'),
 ('#2e7054', 'M46 63 L50 63 L50 40 L46 40 Z'),
 ('#2e7054', 'M48 53 C34 55 28 44 29 35 C42 34 50 42 48 53 Z'),
 ('#e8b951', 'M48 45 C48 33 58 28 68 29 C69 40 59 48 48 45 Z'),
]
svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96"><rect width="96" height="96" rx="22" fill="#2e7054"/>'
svg += ''.join(f'<path fill="{color}" d="{path}"/>' for color, path in PATHS) + '</svg>\n'
(STATIC / 'favicon.svg').write_text(svg)

def points(path):
    tokens = re.findall(r'[MCLZ]|-?\d+(?:\.\d+)?', path)
    out, current, i = [], (0, 0), 0
    while i < len(tokens):
        command = tokens[i]; i += 1
        if command in ('M', 'L'):
            current = tuple(map(float, tokens[i:i+2])); i += 2; out.append(current)
        elif command == 'C':
            values = list(map(float, tokens[i:i+6])); i += 6
            start = current; a, b, end = values[:2], values[2:4], values[4:]
            for n in range(1, 49):
                t = n / 48
                out.append(tuple((1-t)**3*start[k]+3*(1-t)**2*t*a[k]+3*(1-t)*t*t*b[k]+t**3*end[k] for k in (0,1)))
            current = tuple(end)
    return out

scale = 16
master = Image.new('RGBA', (96*scale, 96*scale))
draw = ImageDraw.Draw(master)
draw.rounded_rectangle((0,0,96*scale-1,96*scale-1), radius=22*scale, fill='#2e7054')
for color, path in PATHS:
    draw.polygon([(x*scale,y*scale) for x,y in points(path)], fill=color)
for name, size in [('favicon.png',96),('foundation-logo.png',512),('apple-touch-icon.png',180)]:
    master.resize((size,size), Image.Resampling.LANCZOS).save(STATIC/name)
master.resize((256,256), Image.Resampling.LANCZOS).save(STATIC/'favicon.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
