# -*- coding: utf-8 -*-

from PIL import Image
import numpy as np


EPD_W = 1200
EPD_H = 1600


def load_scaled(image, angle, display_mode='fit'):
    if isinstance(image, str):
        img = Image.open(image)
    else:
        img = image.copy()

    img = img.convert('RGB')
    img = img.rotate(angle, expand=True)

    orig_ratio = img.width / img.height
    epd_ratio = EPD_W / EPD_H

    if display_mode == 'fill':
        if orig_ratio > epd_ratio:
            new_height = EPD_H
            new_width = int(new_height * orig_ratio)
            img = img.resize((new_width, new_height), Image.LANCZOS)
            left = (new_width - EPD_W) // 2
            img = img.crop((left, 0, left + EPD_W, EPD_H))
        else:
            new_width = EPD_W
            new_height = int(new_width / orig_ratio)
            img = img.resize((new_width, new_height), Image.LANCZOS)
            top = (new_height - EPD_H) // 2
            img = img.crop((0, top, EPD_W, top + EPD_H))
    else:
        if orig_ratio > epd_ratio:
            new_width = EPD_W
            new_height = int(new_width / orig_ratio)
        else:
            new_height = EPD_H
            new_width = int(new_height * orig_ratio)

        img = img.resize((new_width, new_height), Image.LANCZOS)
        bg = Image.new('RGB', (EPD_W, EPD_H), (255, 255, 255))
        offset = ((EPD_W - new_width) // 2, (EPD_H - new_height) // 2)
        bg.paste(img, offset)
        return bg

    return img


def convert_image(input_image, preview_path=None, dithering_strength=1.0):
    rgb_image = input_image.copy().convert('RGB')

    palette = [
        0, 0, 0,
        255, 255, 255,
        255, 216, 0,
        229, 57, 53,
        0, 76, 255,
        29, 185, 84,
    ]

    palette += (768 - len(palette)) * [0]
    pal_image = Image.new('P', (1, 1))
    pal_image.putpalette(palette)

    dither = Image.Dither.FLOYDSTEINBERG if dithering_strength and dithering_strength > 0 else Image.Dither.NONE
    output_image = rgb_image.quantize(palette=pal_image, dither=dither).convert('RGB')
    return np.array(output_image, dtype=np.uint8)