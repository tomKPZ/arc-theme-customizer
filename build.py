#!/usr/bin/env python

import colorsys
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(os.path.join(SCRIPT_DIR, 'arc-theme'))
subprocess.check_output(['git', 'reset', '--hard'])

# TARGET = (0x0d/255, 0x0f/255, 0x18/255)
TARGET = (0x30 / 255, 0x01 / 255, 0x01 / 255)
ARC_BG_DARK = (0x38 / 255, 0x3c / 255, 0x4a / 255)
# ARC_BG_LIGHT = (0xf5/255, 0xf6/255, 0xf7/255)
ARC_ACCENT = '#5294e2'
TARGET_ACCENT = '#00ff00'
TARGET_FG = '#0000ff'


# Maybe make this a shift to avoid clamping?
def transfer_function(x0, y0):
    constant = x0 * (y0 - 1) / (y0 * (x0 - 1))
    return lambda x: x / (x - constant * (x - 1))


target_h, target_l, target_s = colorsys.rgb_to_hls(*TARGET)
bg_h, bg_l, bg_s = colorsys.rgb_to_hls(*ARC_BG_DARK)
transfer_l = transfer_function(bg_l, target_l)
transfer_s = transfer_function(bg_s, target_s)

THEME_H = 0.61475
THEME_S = 0.12992


def repl(m):
    m = m.group(0)
    if m == ARC_ACCENT:
        return TARGET_ACCENT
    rgb = int(m[1:], 16)
    h, l, s = colorsys.rgb_to_hls((rgb // 256 // 256) / 255,
                                  ((rgb // 256) % 256) / 255,
                                  (rgb % 256) / 255)
    if abs(h - THEME_H) > 0.05 or abs(s - THEME_S) > 0.1:
        return m
    h = target_h
    l = transfer_l(l)
    s = transfer_s(s)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    assert 0 <= r < 1
    assert 0 <= g < 1
    assert 0 <= b < 1
    r = min(255, int(r * 256))
    g = min(255, int(g * 256))
    b = min(255, int(b * 256))
    return '#%06x' % (r * 256 * 256 + g * 256 + b)


for dir, dirs, files in os.walk(os.path.join('common', 'gtk-3.0', '3.24')):
    for file in files:
        path = os.path.join(dir, file)
        contents = open(path).read()
        contents = re.sub('#[0-9a-fA-F]{6}', repl, contents)
        open(path, 'w').write(contents)

FG_COLOR_NAMES = set([
    'selected_fg_color',
    'text_color',
    'fg_color',
    'error_fg_color',
    'warning_fg_color',
    'suggested_fg_color',
    'destructive_fg_color',
])
lines = []
for line in open(
        os.path.join('common', 'gtk-3.0', '3.24', 'sass',
                     '_colors.scss')).read().split('\n'):
    if m := re.match(r'\$(\w+): (.*);$', line):
        if m.group(1) in FG_COLOR_NAMES:
            lines.append('$%s: %s;' % (m.group(1), TARGET_FG))
            continue
    lines.append(line)
open(os.path.join('common', 'gtk-3.0', '3.24', 'sass', '_colors.scss'),
     'w').write('\n'.join(lines))

subprocess.check_call(
    'sed -i "s/\(placeholder_text_color\) .*;/\\1 #{\\"\\" + mix(\$text_color, \$base_color, 50%)};/" common/gtk-3.0/3.24/sass/_colors-public.scss',
    shell=True)

#     # $warning_color: #F27835;
#     # $error_color: #FC4138;
#     # $success_color: #73d216;
#     # $destructive_color: #F04A50;
#     # $suggested_color: #4DADD4;
#     # $drop_target_color: #F08437;
#     # $dark_sidebar_bg: if($transparency == 'true', transparentize(#353945, 0.05), #353945);
#     # $dark_sidebar_fg: #BAC3CF;
#     # $entry_border: if($variant != 'dark', #cfd6e6, darken($borders_color, 0%));
#     # $wm_button_close_bg: if($variant == 'light' or $variant=='lighter', #f46067, #cc575d);
#     # $wm_button_close_hover_bg: if($variant == 'light' or $variant=='lighter', #f68086, #d7787d);
#     # $wm_button_close_active_bg: if($variant == 'light' or $variant=='lighter', #f13039, #be3841);
#     # $wm_icon_close_bg: if($variant == 'light' or $variant=='lighter', #F8F8F9 , #2f343f);
#     # $wm_button_hover_bg: if($variant == 'light' or $variant=='lighter', #fdfdfd, #454C5C);
#     # $wm_button_hover_border: if($variant == 'light' or $variant=='lighter', #D1D3DA, #262932);
#     # $wm_icon_bg: if($variant == 'light' or $variant=='lighter', #90949E, #90939B);
#     # $wm_icon_unfocused_bg: if($variant == 'light' or $variant=='lighter', #B6B8C0, #666A74);
#     # $wm_icon_hover_bg: if($variant == 'light' or $variant=='lighter', #7A7F8B, #C4C7CC);

subprocess.check_call('rm -rf build install', shell=True)
subprocess.check_call(
    'meson build --prefix="$(pwd)/install" -Dthemes=gtk3 -Dvariants=dark -Dtransprency=false -Dgtk3_version=3.24',
    shell=True)
subprocess.check_call('meson install -C build', shell=True)
