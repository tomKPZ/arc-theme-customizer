#!/usr/bin/env python

import colorsys
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(os.path.join(SCRIPT_DIR, 'arc-theme'))
subprocess.check_output(['git', 'reset', '--hard'])

THEME_H = 0.6148416923
THEME_S = 0.1435133077

replace_h = 0
replace_s = 0.5

def repl(m):
    m = m.group(0)
    rgb = int(m[1:], 16)
    h, l, s = colorsys.rgb_to_hls((rgb // 256 // 256)/256, ((rgb // 256) % 256)/256, (rgb % 256)/256)
    if ((h - THEME_H)**2 + (s - THEME_S)**2)**0.5 > 0.2:
        return m
    h = replace_h
    s = replace_s
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    assert 0 <= r < 1
    assert 0 <= g < 1
    assert 0 <= b < 1
    print(r, g, b)
    r = int(r * 255)
    g = int(g * 255)
    b = int(b * 255)
    return '#%06x' % (r*256*256 + g*256 + b)
    

for dir, dirs, files in os.walk(os.path.join('common', 'gtk-3.0', '3.24')):
    for file in files:
        path = os.path.join(dir, file)
        contents = open(path).read()
        contents = re.sub('#[0-9a-fA-F]{6}', repl, contents)
        open(path, 'w').write(contents)

# REPLACE = [
#     # $warning_color: #F27835;
#     # $error_color: #FC4138;
#     # $warning_fg_color: white;
#     # $error_fg_color: white;
#     # $success_color: #73d216;
#     # $destructive_color: #F04A50;
#     # $suggested_color: #4DADD4;
#     # $destructive_fg_color: white;
#     # $suggested_fg_color: white;
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

#     # text_color
#     (['5c616c', 'D3DAE3'], '0000ff'),
    
#     # base_color
#     (['ffffff', '404552'], '300000'),
#     # bg_color
#     (['F5F6F7', '383C4A'], '180000'),
#     # fg_color - same as text_color
#     # (['5c616c', 'D3DAE3'], ''),
#     # selected_fg_color - same as base_color ???
#     # (['ffffff'], ''),
#     # selected_bg_color
#     (['5294e2'], 'ff0000'),
#     # header_bg
#     (['e7e8eb', '2f343f', '2d323f'], '180000'),
#     # Asset colors
#     (['f9fafb', '353a47'], '180000'),
#     (['cfd6e6', '5b627b'], '400000'),
#     (['2d323d'], '2d0000'),
#     (['2b303b'], '2b0000'),
#     (['5f6578'], '5f0000'),
#     (['262934'], '260000'),
#     (['7a7f8b'], '7a0000'),
#     (['b9bcc2'], 'b90000'),
#     (['5f697f'], '5f0000'),
#     (['c0e3ff'], 'c00000'),
# ]

# for matches, replace_with in REPLACE:
#     for match in matches:
#         subprocess.check_call(
#             '''find common/gtk-3.0/3.24 -name "*" -type f -exec sed -i 's/'%s'/'%s'/gI' {}  \;'''
#             % (match, replace_with),
#             shell=True)

subprocess.check_call('rm -rf build install', shell=True)
subprocess.check_call('meson build --prefix=$(pwd)/install -Dthemes=gtk3 -Dvariants=dark -Dtransprency=false', shell=True)
subprocess.check_call('meson install -C build', shell=True)
