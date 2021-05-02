import colorsys

for line in open('asset.txt'):
    rgb = int(line.strip(), 16)
    h, l, s = colorsys.rgb_to_hls((rgb // 256 // 256)/256, ((rgb // 256) % 256)/256, (rgb % 256)/256)
    print('%f\t%f' % (h, s))
