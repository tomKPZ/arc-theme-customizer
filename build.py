#!/usr/bin/env python

import colorsys
import itertools
import os
import re
import subprocess
import sys

import config

# ----- Unthemed colors -----
# $warning_color: #F27835;
# $error_color: #FC4138;
# $success_color: #73d216;
# $destructive_color: #F04A50;
# $suggested_color: #4DADD4;
# $drop_target_color: #F08437;
# $dark_sidebar_bg: if($transparency == 'true', transparentize(#353945, 0.05), #353945);
# $dark_sidebar_fg: #BAC3CF;
# $entry_border: if($variant != 'dark', #cfd6e6, darken($borders_color, 0%));
# $wm_button_close_bg: if($variant == 'light' or $variant=='lighter', #f46067, #cc575d);
# $wm_button_close_hover_bg: if($variant == 'light' or $variant=='lighter', #f68086, #d7787d);
# $wm_button_close_active_bg: if($variant == 'light' or $variant=='lighter', #f13039, #be3841);
# $wm_icon_close_bg: if($variant == 'light' or $variant=='lighter', #F8F8F9 , #2f343f);
# $wm_button_hover_bg: if($variant == 'light' or $variant=='lighter', #fdfdfd, #454C5C);
# $wm_button_hover_border: if($variant == 'light' or $variant=='lighter', #D1D3DA, #262932);
# $wm_icon_bg: if($variant == 'light' or $variant=='lighter', #90949E, #90939B);
# $wm_icon_unfocused_bg: if($variant == 'light' or $variant=='lighter', #B6B8C0, #666A74);
# $wm_icon_hover_bg: if($variant == 'light' or $variant=='lighter', #7A7F8B, #C4C7CC);

GTK_VERSION = '3.24'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CWD = os.path.join(SCRIPT_DIR, 'arc-theme')
os.chdir(CWD)

PATCH_DIR = os.path.join(SCRIPT_DIR, 'patches')
GTK3_DIR = os.path.join(CWD, 'common', 'gtk-3.0', GTK_VERSION)
COLORS_SASS_FILE = os.path.join(GTK3_DIR, 'sass', '_colors.scss')
BUILD_DIR = os.path.join(CWD, 'build')
INSTALL_DIR = os.path.join(BUILD_DIR, 'install')

subprocess.check_output(['git', 'reset', '--hard'])
for fname in os.listdir(PATCH_DIR):
    subprocess.check_output(['git', 'apply', os.path.join(PATCH_DIR, fname)])

ARC_BG_DARK = '#383c4a'
ARC_BG_LIGHT = '#f5f6f7'
ARC_ACCENT = '#5294e2'


def parse_color(color):
    color = color.lstrip('#')
    return [int(color[2 * i:2 * i + 2], 16) / 255 for i in range(3)]


def format_color(rgb):
    return '#%02x%02x%02x' % tuple(
        min(255, int(channel * 256)) for channel in rgb)


def luma(color):
    return colorsys.rgb_to_hls(*parse_color(color))[1]


# Maybe make this a shift to avoid clamping?
def transfer_function(x0, y0):
    if y0 in (0, 1):
        return lambda _: y0
    constant = x0 * (y0 - 1) / (y0 * (x0 - 1))
    return lambda x: x / (x - constant * (x - 1))


if luma(config.FOREGROUND) > luma(config.BACKGROUND):
    ARC_BG = parse_color(ARC_BG_DARK)
    THEME_VARIANT = 'dark'
else:
    ARC_BG = parse_color(ARC_BG_LIGHT)
    THEME_VARIANT = 'lighter'

target_h, target_l, target_s = colorsys.rgb_to_hls(
    *parse_color(config.BACKGROUND))
bg_h, bg_l, bg_s = colorsys.rgb_to_hls(*ARC_BG)
transfer_l = transfer_function(bg_l, target_l)
transfer_s = transfer_function(bg_s, target_s)


def is_base_color(hue, saturation):
    BASE_H = 0.61475
    BASE_S = 0.12992
    THRESH_H = 0.05
    THRESH_S = 0.10
    return abs(hue - BASE_H) < THRESH_H and abs(saturation - BASE_S) < THRESH_S


def map_color(m):
    m = m.group(0)
    if m == ARC_ACCENT:
        return config.ACCENT
    rgb = parse_color(m)
    h, l, s = colorsys.rgb_to_hls(*rgb)
    if not is_base_color(h, s):
        return m
    return format_color(
        colorsys.hls_to_rgb(target_h, transfer_l(l), transfer_s(s)))


COLOR_PATTERN = re.compile(r'#[0-9a-fA-F]{6}')
for dir, dirs, files in os.walk(GTK3_DIR):
    for file in files:
        path = os.path.join(dir, file)
        contents = open(path).read()
        contents = COLOR_PATTERN.sub(map_color, contents)
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
COLOR_DEFINITION_PATTERN = re.compile(r'\$(\w+): (.*);')


def map_color_definition(m):
    if m.group(1) in FG_COLOR_NAMES:
        return '$%s: %s;\n' % (m.group(1), config.FOREGROUND)
    return m.group(0)


colors_sass = open(COLORS_SASS_FILE).read()
colors_sass = COLOR_DEFINITION_PATTERN.sub(map_color_definition, colors_sass)
open(COLORS_SASS_FILE, 'w').write(colors_sass)

subprocess.check_call(['rm', '-rf', BUILD_DIR])
subprocess.check_call([
    'meson',
    'build',
    '--prefix=' + INSTALL_DIR,
    '-Dthemes=gtk3',
    '-Dgtk3_version=' + GTK_VERSION,
    '-Dvariants=' + THEME_VARIANT,
    '-Dtransparency=false',
])
subprocess.check_call(['meson', 'install', '-C', 'build'])
subprocess.check_call([
    'ln', '-sf',
    os.path.join(INSTALL_DIR, 'share', 'themes',
                 'Arc-%s-solid' % THEME_VARIANT.capitalize()),
    os.path.join(SCRIPT_DIR, 'Arc-Base16')
])
