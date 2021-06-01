#!/usr/bin/env python

import argparse
import colorsys
import itertools
import os
import re
import shutil
import subprocess
import sys

# ----- Unthemed colors -----
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


def parse_color(color):
    assert color[0] == '#'
    return [int(color[2 * i + 1:2 * i + 3], 16) / 255 for i in range(3)]


def format_color(rgb):
    return '#%02x%02x%02x' % tuple(
        min(255, int(channel * 256)) for channel in rgb)


def lerp(x, in_min, in_max, out_min, out_max):
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;


def transfer_function(x0, y0):
    return lambda x: lerp(x, 0, x0, 0, y0) if x < x0 else lerp(x, x0, 1, y0, 1)


def sed(in_file, out_file, pattern, replace_with):
    contents = open(in_file).read()
    contents = pattern.sub(replace_with, contents)
    open(out_file, 'w').write(contents)


def is_base_color(hue, saturation):
    BASE_H = 0.61475
    BASE_S = 0.12992
    THRESH_H = 0.05
    THRESH_S = 0.20
    return abs(hue - BASE_H) < THRESH_H and abs(saturation - BASE_S) < THRESH_S


# https://www.w3.org/TR/WCAG20/#relativeluminancedef
def relative_luma(rgb):
    def channel(c):
        if c <= 0.03928:
            return c / 12.92
        return ((c + 0.055) / 1.055)**2.4

    return sum(coeff * c
               for (coeff,
                    c) in zip([0.2126, 0.7152, 0.0722], parse_color(rgb)))


# https://www.w3.org/TR/WCAG20/#contrast-ratiodef
def contrast_ratio(c1, c2):
    ratio = (relative_luma(c1) + 0.05) / (relative_luma(c2) + 0.05)
    return ratio if ratio >= 1 else 1 / ratio


def selected_fg_color():
    if (contrast_ratio(FOREGROUND, ACCENT) > contrast_ratio(BASE, ACCENT)):
        return FOREGROUND
    return BASE


def map_color(m):
    m = m.group(0)
    if m == ARC_ACCENT:
        return ACCENT

    rgb = parse_color(m)
    h, l, s = colorsys.rgb_to_hls(*rgb)
    if not is_base_color(h, s):
        return m

    target_h, target_l, target_s = colorsys.rgb_to_hls(
        *parse_color(BACKGROUND))
    bg_h, bg_l, bg_s = colorsys.rgb_to_hls(*ARC_BG)
    transfer_l = transfer_function(bg_l, target_l)
    transfer_s = transfer_function(bg_s, target_s)
    return format_color(
        colorsys.hls_to_rgb(target_h, transfer_l(l), transfer_s(s)))


def map_color_definition(m):
    if m.group(1) == 'selected_fg_color':
        return '$%s: %s;\n' % (m.group(1), selected_fg_color())
    if m.group(1) == 'base_color':
        return '$%s: %s;\n' % (m.group(1), BASE)
    if m.group(1) in NAMED_COLORS:
        return '$%s: %s;\n' % (m.group(1), NAMED_COLORS[m.group(1)])
    return m.group(0)


def rewrite_files():
    for fname in os.listdir(PATCH_DIR):
        subprocess.check_output(
            ['git', 'apply', os.path.join(PATCH_DIR, fname)])

    for file in os.listdir(SASS_DIR):
        fname = os.path.join(SASS_DIR, file)
        sed(fname, fname, COLOR_PATTERN, map_color)

    sed(COLORS_SASS_FILE, COLORS_SASS_FILE, COLOR_DEFINITION_PATTERN,
        map_color_definition)


def build():
    if not os.path.isdir(BUILD_DIR):
        subprocess.check_call([
            'meson',
            'build',
            '-Dthemes=gtk3',
            '-Dgtk3_version=' + GTK_VERSION,
            '-Dvariants=dark,lighter',
            '-Dtransparency=false',
        ])
        subprocess.check_call(['ninja', '-C', BUILD_DIR])
    shutil.rmtree(ARC_CUSTOM_DIR, ignore_errors=True)
    os.makedirs(ASSETS_DIR)
    procs = [subprocess.Popen(['sassc', GTK_MAIN_FILE, GTK_CSS_FILE])]
    for fname in os.listdir(SVG_DIR):
        if m := SVG_PATTERN.fullmatch(fname):
            sed(os.path.join(SVG_DIR, fname), os.path.join(ASSETS_DIR, fname),
                COLOR_PATTERN, map_color)
            ofname = m.group(1) + '@2.svg'
            procs.append(
                subprocess.Popen([
                    'rsvg-convert', '-x', '2', '-y', '2', '-f', 'svg',
                    os.path.join(ASSETS_DIR, fname), '-o',
                    os.path.join(ASSETS_DIR, ofname)
                ]))
    for proc in procs:
        assert not proc.wait()


parser = argparse.ArgumentParser(description='Build a customized Arc theme')
parser.add_argument('config_file', type=argparse.FileType('r'))
args = parser.parse_args()

exec(args.config_file.read())

GTK_VERSION = '3.24'

ARC_BG_DARK = '#383c4a'
ARC_BG_LIGHT = '#f5f6f7'
ARC_ACCENT = '#5294e2'
if relative_luma(FOREGROUND) > relative_luma(BASE):
    ARC_BG = parse_color(ARC_BG_DARK)
    THEME_VARIANT = 'dark'
else:
    ARC_BG = parse_color(ARC_BG_LIGHT)
    THEME_VARIANT = 'lighter'

FG_COLOR_NAMES = [
    'text_color',
    'fg_color',
]

NAMED_COLORS = {
    'text_color': FOREGROUND,
    'fg_color': FOREGROUND,
    'warning_color': WARNING_COLOR,
    'error_color': ERROR_COLOR,
    'warning_fg_color': WARNING_FG_COLOR,
    'error_fg_color': ERROR_FG_COLOR,
    'success_color': SUCCESS_COLOR,
    'destructive_color': DESTRUCTIVE_COLOR,
    'suggested_color': SUGGESTED_COLOR,
    'destructive_fg_color': DESTRUCTIVE_FG_COLOR,
    'suggested_fg_color': SUGGESTED_FG_COLOR,
    'drop_target_color': DROP_TARGET_COLOR,
}

COLOR_PATTERN = re.compile(r'#[0-9a-fA-F]{6}')
COLOR_DEFINITION_PATTERN = re.compile(r'\$(\w+): (.*);')
SVG_PATTERN = re.compile(r'(.*)\.svg')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CWD = os.path.join(SCRIPT_DIR, 'arc-theme')
PATCH_DIR = os.path.join(SCRIPT_DIR, 'patches')
GTK_DIR = os.path.join(CWD, 'common', 'gtk-3.0', GTK_VERSION)
ASSETS_SVG_FILE = os.path.join(GTK_DIR, 'assets.svg')
ASSETS2_SVG_FILE = os.path.join(GTK_DIR, 'assets2.svg')
SASS_DIR = os.path.join(GTK_DIR, 'sass')
COLORS_SASS_FILE = os.path.join(SASS_DIR, '_colors.scss')
GTK_MAIN_FILE = os.path.join(SASS_DIR, 'gtk-solid-%s.scss' % THEME_VARIANT)
BUILD_DIR = os.path.join(CWD, 'build')
SVG_DIR = os.path.join(BUILD_DIR, 'common', 'gtk-3.0')
ARC_CUSTOM_DIR = os.path.join(SCRIPT_DIR, 'Arc-' + THEME_SUFFIX)
THEME_DIR = os.path.join(ARC_CUSTOM_DIR, 'gtk-3.0')
ASSETS_DIR = os.path.join(THEME_DIR, 'assets')
GTK_CSS_FILE = os.path.join(THEME_DIR, 'gtk.css')

os.chdir(CWD)
rewrite_files()
build()
subprocess.check_output(['git', 'reset', '--hard'])
