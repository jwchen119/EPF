# -*- coding: utf-8 -*-

import numpy as np
from PIL import Image, ImageFilter

EPD_W = 1200
EPD_H = 1600


def load_scaled(image, angle, display_mode='fit', blur_radius=30):
    if isinstance(image, str):
        img = Image.open(image)
    else:
        img = image.copy()

    img = img.convert('RGB')
    img = img.rotate(angle, expand=True)

    orig_ratio = img.width / img.height
    epd_ratio = EPD_W / EPD_H

    if display_mode == 'fill':
        # fill branch — UNCHANGED
        if orig_ratio > epd_ratio:
            new_height = EPD_H
            new_width = int(new_height * orig_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            left = (new_width - EPD_W) // 2
            img = img.crop((left, 0, left + EPD_W, EPD_H))
        else:
            new_width = EPD_W
            new_height = int(new_width / orig_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            top = (new_height - EPD_H) // 2
            img = img.crop((0, top, EPD_W, top + EPD_H))
    else:
        # fit branch — blurred fill background
        blur_radius = max(1, min(100, int(blur_radius)))

        # Step 1: compute fill-scale dimensions for background
        if orig_ratio > epd_ratio:
            # landscape image → fit-height → pillarbox (bars left/right)
            bg_height = EPD_H
            bg_width = int(bg_height * orig_ratio)
        else:
            # portrait/square image → fit-width → letterbox (bars top/bottom)
            bg_width = EPD_W
            bg_height = int(bg_width / orig_ratio)

        # Step 2: resize to fill-scale (guarantee full coverage)
        bg_img = img.resize(
            (max(bg_width, EPD_W), max(bg_height, EPD_H)),
            Image.Resampling.LANCZOS,
        )

        # Step 3: center-crop to exact display size
        left = (bg_img.width - EPD_W) // 2
        top = (bg_img.height - EPD_H) // 2
        bg_img = bg_img.crop((left, top, left + EPD_W, top + EPD_H))

        # Step 4: apply Gaussian blur
        bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        # Step 5: fit-scale the sharp image (original logic)
        if orig_ratio > epd_ratio:
            new_width = EPD_W
            new_height = int(new_width / orig_ratio)
        else:
            new_height = EPD_H
            new_width = int(new_height * orig_ratio)

        sharp_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Step 6: paste sharp image centered onto blurred background
        offset = ((EPD_W - new_width) // 2, (EPD_H - new_height) // 2)
        bg_img.paste(sharp_img, offset)
        return bg_img

    return img


def convert_image(input_image, preview_path=None, dithering_strength=1.0):
    rgb_image = input_image.copy().convert('RGB')

    palette = [
        0,
        0,
        0,
        255,
        255,
        255,
        255,
        216,
        0,
        229,
        57,
        53,
        0,
        76,
        255,
        29,
        185,
        84,
    ]

    palette += (768 - len(palette)) * [0]
    pal_image = Image.new('P', (1, 1))
    pal_image.putpalette(palette)

    dither = Image.Dither.FLOYDSTEINBERG if dithering_strength and dithering_strength > 0 else Image.Dither.NONE
    output_image = rgb_image.quantize(palette=pal_image, dither=dither).convert('RGB')
    return np.array(output_image, dtype=np.uint8)
