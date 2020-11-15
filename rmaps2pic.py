#!/usr/bin/env python3

import os
import sys
import argparse
import sqlite3
import itertools

from PIL import Image, ImageDraw
from io import BytesIO

ENOERR          = 0

TILE_WIDTH      = 256
TILE_HEIGHT     = 256

def progressBar(i, max):
    n_bar = 40 # size of progress bar
    j= i/max
    sys.stdout.write(f"\rProgress: [{'=' * int(n_bar * j):{n_bar}s}] {int(100 * j)}%")
    if (j == 1.0): sys.stdout.write("\n")
    sys.stdout.flush()

def main():

    parser = argparse.ArgumentParser(description='''Extracts the map layer to a simple TIFF file.''')
    parser.add_argument('--zoom', metavar='<level>', type=str,
                        help='''map level to parse''')
    parser.add_argument('--format', metavar='<format>', type=str,
                        help='''resulted image format (JPEG, TIFF)''', default='JPEG')
    parser.add_argument('--compression', metavar='<type>', type=str,
                        help="resulted image compresstion type, i.e. \'fiff_deflate'\'", default='')
    parser.add_argument('--quality', metavar='<value>', type=str,
                        help='''resulted image compression quality [default :100]''', default=100)
    parser.add_argument('from_filename', metavar='<file>', type=str,
                        help='''input .sqlitedb file ('xyz'-formatted)''')
    args = parser.parse_args()

    if(not os.path.isfile(args.from_filename)):
        rc = os.errno.ENOENT
        print("Failed to open file: {}. {}".format(args.from_filename, os.strerror(rc)))
        sys.exit(rc)

    db = sqlite3.connect(args.from_filename)
    cursor = db.cursor()

    if args.zoom is None:
        print('----------------------------------------')
        print('Level | Number of tiles')
        print('----------------------------------------')
        for level_ix in range(0, 20):
            for row in cursor.execute('SELECT COUNT(*) FROM tiles WHERE z={}'.format(level_ix)):
                if (row[0] > 0):
                    print("{:5} | {}".format(level_ix, row[0]))
        print('----------------------------------------')
        args.zoom = input('\nSelect map level to extract: [0-20]: ')

    # map of tile's 'x':[y,...] values
    tiles_map = {}

    cursor.execute('SELECT x,y,z FROM tiles WHERE z={}'.format(args.zoom)) 
    for row in cursor:
        x = row[0]
        y = row[1]
        if x in tiles_map:
            tiles_map[x].append(y)
        else:
            tiles_map[x] = []

    if not tiles_map:
        print("Map layer {} is empty, no tiles in database.".format(args.zoom))
        sys.exit(ENOERR)

    size_x = len(tiles_map.keys())
    size_y = max([len(y) for x,y in tiles_map.items()]) 

    image_width = size_x * TILE_WIDTH
    image_height = size_y * TILE_HEIGHT

    for row in cursor.execute('SELECT COUNT(*) FROM tiles WHERE z={}'.format(args.zoom)):
        print("Number of tiles: {}, {}x{} ".format(row[0], image_width, image_height))

    image = Image.new('RGB', (image_width, image_height), color = 'white')

    # tiles position
    # TBD: no checks for missed tiles
    tiles_pos = []
    for x, y in tiles_map.items():
        tiles_pos.append({'x': x, 'y': y})

    progress = 0
    for x, y in itertools.product(range(size_x), range(size_y)):
        for row in cursor.execute('SELECT image FROM tiles WHERE x={} AND y={} AND z={}'.format(tiles_pos[x]['x'], tiles_pos[x]['y'][y], args.zoom)):
            tile = Image.open(BytesIO(row[0]))
            image.paste(tile, (x * TILE_WIDTH, y * TILE_HEIGHT))
            progress += 1
            progressBar(progress, size_x * size_y)
            

    image.save('out_l{}.{}'.format(args.zoom, args.format.lower()), format=args.format, compression=args.compression, quality=args.quality)

    db.close()

if __name__ == '__main__':
    main()