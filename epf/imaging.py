"""
The image pipeline: crop and enhance, dither to the panel's six colours, then
pack the result the way the firmware expects.

Everything is in-memory BytesIO. Nothing here reads the configuration - the
values arrive as arguments, so the pipeline can be exercised on its own.
"""
import io
import os
from datetime import datetime

import numpy as np
import rawpy
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

from . import dither

# So PIL can open the HEIC that iPhones produce
register_heif_opener()

# The panel's *measured* colours. Must stay in step with the pure-RGB palette
# in epf/dither.py (PURE) and the EPD_7IN3E_* codes in the firmware header.
palette = [
    (0, 0, 0),
    (255, 255, 255),
    (255, 243, 56),
    (191, 0, 0),
    (100, 64, 255),
    (67, 138, 28),
]

# This panel's colours, measured from photos of the calibration card
# (2026-10-06, two cleanest of four shots, each colour relative to the panel's
# own white so the phone's exposure and white balance cancel). Same order as
# palette. Black includes the glass's glare, as seen in use.
CALIBRATED_PALETTE = [
    (84, 69, 78),
    (255, 255, 255),
    (255, 250, 58),
    (166, 73, 69),
    (92, 115, 193),
    (111, 139, 107),
]

# Not currently consulted anywhere; /download branches on the asset's extension.
ALLOWED_EXTENSIONS = {'.jpeg', '.raw', '.jpg', '.bmp', '.dng', '.heic', '.arw',
                      '.cr2', '.dng', '.nef', '.raw'}

# The panel size; the dither and the firmware both assume it
EPD_W = 800
EPD_H = 480

# The calibration card's 3x3 grid, rows top to bottom in the panel's own
# orientation; a pair is a fine checkerboard of the two. epf/calibration.py
# reads photos of the card with the same layout.
CARD_LAYOUT = (('black', 'white', 'yellow'),
               ('red', 'blue', 'green'),
               (('black', 'white'), ('red', 'white'), ('yellow', 'blue')))

def load_scaled(image, angle, display_mode='fit'):
    """
    Rotate, then letterbox ('fit') or centre-crop ('fill') to the panel size.
    Moved here unchanged from the former cpy.pyx, where it was plain Python anyway.
    """
    img = image.copy()
    img = img.convert('RGB')
    img = img.rotate(angle, expand=True)

    orig_ratio = img.width / img.height
    epd_ratio = EPD_W / EPD_H
    if display_mode == 'fill':
        if orig_ratio > epd_ratio:
            # Too wide: crop the sides
            new_height = EPD_H
            new_width = int(new_height * orig_ratio)
            img = img.resize((new_width, new_height), Image.LANCZOS)
            left = (new_width - EPD_W) // 2
            img = img.crop((left, 0, left + EPD_W, EPD_H))
        else:
            # Too tall: crop top and bottom
            new_width = EPD_W
            new_height = int(new_width / orig_ratio)
            img = img.resize((new_width, new_height), Image.LANCZOS)
            top = (new_height - EPD_H) // 2
            img = img.crop((0, top, EPD_W, top + EPD_H))
        return img

    if orig_ratio > epd_ratio:
        new_width = EPD_W
        new_height = int(new_width / orig_ratio)
    else:
        new_height = EPD_H
        new_width = int(new_height * orig_ratio)
    img = img.resize((new_width, new_height), Image.LANCZOS)
    bg = Image.new('RGB', (EPD_W, EPD_H), (255, 255, 255))
    bg.paste(img, ((EPD_W - new_width) // 2, (EPD_H - new_height) // 2))
    return bg

def calibration_card():
    """
    A 3x3 grid in the panel's own orientation, to photograph and measure what
    the panel really shows:

        black            white             yellow
        red              blue              green
        black/white 50%  red/white 50%     yellow/blue 50%

    The bottom row is fine checkerboards; their measured colour, compared with
    the mean of the two solid colours, shows how the dots mix to the eye.
    Returned as an RGB array of the six pure colours, ready to pack.
    """
    pure = {'black': (0, 0, 0), 'white': (255, 255, 255), 'yellow': (255, 255, 0),
            'red': (255, 0, 0), 'blue': (0, 0, 255), 'green': (0, 255, 0)}
    card = np.zeros((EPD_H, EPD_W, 3), dtype=np.uint8)
    yy, xx = np.mgrid[0:EPD_H, 0:EPD_W]
    checker = (yy + xx) % 2 == 0
    for r, row in enumerate(CARD_LAYOUT):
        for c, cell in enumerate(row):
            y0, y1 = r * EPD_H // 3, (r + 1) * EPD_H // 3
            x0, x1 = c * EPD_W // 3, (c + 1) * EPD_W // 3
            if isinstance(cell, tuple):
                a, b = (np.array(pure[name], dtype=np.uint8) for name in cell)
                block = np.where(checker[y0:y1, x0:x1, None], a, b)
            else:
                block = np.array(pure[cell], dtype=np.uint8)
            card[y0:y1, x0:x1] = block
    return card

def depalette_image(pixels, palette):
    palette_array = np.array(palette)
    diffs = np.sqrt(np.sum((pixels[:, :, None, :] - palette_array[None, None, :, :]) ** 2, axis=3))
    indices = np.argmin(diffs, axis=2)
    indices[indices > 3] += 1  # Simulate the code from the C
    return indices

def scale_img_in_memory(image, rotation=270, display_mode='fill', enhanced=1.0,
                        contrast=1.0, strength=1.0, dither_mode='classic',
                        target_width=800, target_height=480, bg_color=(255, 255, 255),
                        panel_palette=None, dot_gain=None, correction=None):
    """
    Rotate, fit or crop to the panel, enhance, then dither. Returns a BytesIO BMP.

    target_width/target_height only affect the (currently disabled) date overlay;
    the panel size itself is fixed by EPD_W and EPD_H.

    :param image: PIL Image object
    :param rotation: rotation angle (0, 90, 180, 270)
    :param display_mode: 'fit' to letterbox, 'fill' to centre-crop
    :param enhanced: saturation, via PIL ImageEnhance.Color
    :param contrast: contrast, via PIL ImageEnhance.Contrast
    :param strength: scales the Floyd-Steinberg error diffusion (classic only)
    :param dither_mode: see epf/dither.py
    :param panel_palette: the panel's colours, for every dither but classic
    :param dot_gain: the panel's dot gain, default dither.DOT_GAIN
    :param correction: classic_cc's adjustments, see dither.dither()
    :return: BytesIO object
    """

    # Get data from EXIF
    try:
        exif = image._getexif()
        if exif:
            # EXIF time tag is 36867
            date_time = exif.get(36867)
            if not date_time:
                # Alternative time tag is 306
                date_time = exif.get(306)
        else:
            date_time = None
    except:
        date_time = None

    # Read correct photo orientation from EXIF
    image = ImageOps.exif_transpose(image)

    img = load_scaled(image, rotation, display_mode)
    # Enhance color and contrast
    enhanced_img = ImageEnhance.Color(img).enhance(enhanced)
    enhanced_img = ImageEnhance.Contrast(enhanced_img).enhance(contrast)

    # Palette definition (matching previous quantization logic)
    palette = [
        0, 0, 0,         # Black
        255, 255, 255,   # White
        255, 255, 0,    # Yellow
        255, 0, 0,       # Deep Red
        0, 0, 255,    # Blue
        0, 255, 0      # Green
    ]

    # Prepare palette image (similar to previous code)
    e = len(palette)
    assert e > 0, "Palette unexpectedly short"
    assert e <= 768, "Palette unexpectedly long"
    assert e % 3 == 0, "Palette not multiple of 3, so not RGB"

    # Create temporary palette image
    pal_image = Image.new("P", (1, 1))

    # Zero-pad palette to 768 values
    palette += (768 - e) * [0]
    pal_image.putpalette(palette)

    # Quantize image
    # output_img = enhanced_img.convert("RGB").quantize(
    #     palette=pal_image,
    #     dither=Image.Dither.FLOYDSTEINBERG
    # ).convert("RGB")

    output_img = dither.dither(enhanced_img, dither_mode, strength,
                               panel_palette or CALIBRATED_PALETTE,
                               dither.DOT_GAIN if dot_gain is None else dot_gain, correction)
    output_img = Image.fromarray(output_img, mode="RGB")

    # Add date if available
    if date_time:
        draw = ImageDraw.Draw(output_img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except:
            font = ImageFont.load_default()

        # Format the date
        try:
            try:
                dt = datetime.strptime(date_time, "%Y:%m:%d %H:%M:%S")
                formatted_time = dt.strftime("%Y/%m/%d")
            except ValueError:
                dt = datetime.strptime(date_time, "%Y.%m.%d")
                formatted_time = dt.strftime("%Y/%m/%d")
        except:
            formatted_time = date_time

        def draw_text_with_background(draw, text, font, text_color=(255, 255, 255), bg_color=(0, 0, 0)):
            # Calculate rotated width/height
            if rotation in [90, 270]:
                img_width, img_height = target_height, target_width  # width and height swapped
            else:
                img_width, img_height = target_width, target_height

            # Set text position
            if rotation == 0:  # no rotation
                position = (img_width - 200, img_height - 40)
            elif rotation == 90:  # 90 degrees clockwise (actually counterclockwise)
                position = (img_height - 30, 30)
            elif rotation == 180:  # 180 degrees
                position = (img_width -200 , img_height - 40)
            elif rotation == 270:  # 270 degrees clockwise (actually counterclockwise)
                position = (30, img_width - 30)

            # Get text bounding box
            text_bbox = draw.textbbox((0, 0), text, font=font)  # use (0, 0) to get text size
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            padding = 5

            # Set text position and background rectangle bounds
            if rotation == 0:  # no rotation, bottom right
                position = (img_width - text_width - 40, img_height - text_height - 40)
                rect_coords = [
                    position[0] - padding,  # Top left X
                    position[1] - padding,  # Top left Y
                    position[0] + text_width + padding,  # Bottom right X
                    position[1] + text_height + padding  # Bottom right Y
                ]
            elif rotation == 90:  # 90 degrees, top right
                position = (img_height - text_height - 40, 40)
                rect_coords = [
                    position[0] - padding,  # Top left X
                    position[1] - padding,  # Top left Y
                    position[0] + text_height + padding,  # Bottom right X
                    position[1] + text_width + padding   # Bottom right Y
                ]
            elif rotation == 180:  # 180 degrees, top left
                position = (40, 40)
                rect_coords = [
                    position[0] - padding,  # Top left X
                    position[1] - padding,  # Top left Y
                    position[0] + text_width + padding,  # Bottom right X
                    position[1] + text_height + padding  # Bottom right Y
                ]
            elif rotation == 270:  # 270 degrees, bottom left
                position = (40, img_width - text_width - 40)
                rect_coords = [
                    position[0] - padding,  # Top left X
                    position[1] - padding,  # Top left Y
                    position[0] + text_height + padding,  # Bottom right X
                    position[1] + text_width + padding   # Bottom right Y
                ]

            # Draw rectangular background
            draw.rectangle(rect_coords, fill=bg_color)

            # Create text based on the rotation of image
            if rotation == 0:
                draw.text(position, text, fill=text_color, font=font)
            else:
                # Create a new image to draw rotated text
                rotated_text = Image.new("RGB", (text_width, text_height), (255, 255, 255))  # white background
                rotated_draw = ImageDraw.Draw(rotated_text)
                rotated_draw.text((0, 0), text, fill=text_color, font=font)

                # Rotate text image
                rotated_text = rotated_text.rotate(rotation, expand=True, resample=Image.BICUBIC)

                # Calculate where rotated text should be pasted
                if rotation == 90:
                    # 90 degree rotation, display in top right
                    output_img.paste(rotated_text, (position[1], position[0]))
                elif rotation == 180:
                    # 180 degree rotation, display in top left
                    output_img.paste(rotated_text, (position[0], position[1]))
                elif rotation == 270:
                    # 270 degree rotation, display in bottom left
                    output_img.paste(rotated_text, (position[1], position[0]))

        # Drawing the text on forground (WIP)
        # draw_text_with_background(draw, formatted_time, font)

    # Save image into ram
    img_io = io.BytesIO()
    output_img.save(img_io, 'BMP')
    img_io.seek(0)
    return img_io

def convert_to_c_code_in_memory(image_data):
    """ Pack the dithered image as the C-array text the firmware streams """
    pixels = np.array(image_data)

    indices = depalette_image(pixels, palette)

    # Two 4-bit indices per byte; an odd last column gets a zero partner,
    # as the old per-pixel loop did
    indices = indices.astype(np.uint8)
    if indices.shape[1] % 2:
        indices = np.pad(indices, ((0, 0), (0, 1)))
    packed = ((indices[:, 0::2] << 4) | indices[:, 1::2]).reshape(-1)

    # "XX," per byte, 16 bytes to a line, then "};" - built as one byte array
    # instead of 192,000 string writes (about 4 ms rather than 300+)
    hex_digits = np.frombuffer(b'0123456789ABCDEF', dtype=np.uint8)
    text = np.empty((packed.size, 3), dtype=np.uint8)
    text[:, 0] = hex_digits[packed >> 4]
    text[:, 1] = hex_digits[packed & 15]
    text[:, 2] = ord(',')
    text = text.reshape(-1)
    full = (packed.size // 16) * 48
    body = np.empty(full // 48 * 49, dtype=np.uint8)
    lines = body.reshape(-1, 49)
    lines[:, :48] = text[:full].reshape(-1, 48)
    lines[:, 48] = ord('\n')
    out = body.tobytes() + text[full:].tobytes() + b'};\n'

    output_bytes = io.BytesIO(out)
    output_bytes.seek(0)
    return output_bytes

def pack_bmp_for_panel(bmp_io):
    """ Open a BMP produced by scale_img_in_memory and pack it for the firmware """
    bmp_io.seek(0)
    return convert_to_c_code_in_memory(Image.open(bmp_io))

# Every RAW extension rawpy is asked to handle by name. The list is not
# exhaustive - a camera missing from it is caught by the fallback in open_asset.
RAW_SUFFIXES = ('.raw', '.dng', '.arw', '.cr2', '.cr3', '.nef', '.nrw', '.orf',
                '.raf', '.rw2', '.pef', '.srw', '.sr2', '.3fr', '.erf', '.iiq')

def _open_raw(data):
    """ A PIL image from RAW bytes, whatever the file is called """
    data.seek(0)
    with rawpy.imread(data) as raw:
        return Image.fromarray(raw.postprocess(use_camera_wb=True, use_auto_wb=False))

def open_asset(data, original_path):
    """ A PIL image from downloaded bytes, decoding RAW and HEIC as needed """
    lowered = (original_path or '').lower()
    if lowered.endswith(RAW_SUFFIXES):
        return _open_raw(data)
    if lowered.endswith('.heic'):
        return Image.open(data).convert("RGB")
    try:
        image = Image.open(data)
    except UnidentifiedImageError:
        # PIL reports the BytesIO object rather than the file, which says nothing
        # about what went wrong. The usual cause is a RAW file from a camera not
        # in RAW_SUFFIXES, so try the decoder that does not go by the name, and
        # otherwise name the asset that cannot be shown.
        try:
            return _open_raw(data)
        except Exception as error:
            raise ValueError(
                f"Unsupported image format: {original_path or 'unknown file'}") from error
    # Image.open only reads the header. Decoding now means a truncated or damaged
    # file fails here, where the caller can fall back to the preview, rather than
    # halfway through the pipeline.
    image.load()
    return image

def open_preview(data):
    """ A PIL image from Immich's preview rendering, which is always JPEG or WebP """
    image = Image.open(data)
    image.load()
    return image

# --- unused by the server, kept from the original ---------------------------

def convert_raw_or_dng_to_jpg(input_file_path, output_dir):
    """Convert RAW or DNG files to JPG using rawpy."""
    with rawpy.imread(input_file_path) as raw:
        rgb = raw.postprocess(use_camera_wb=True, use_auto_wb=False)
        base_name = os.path.splitext(os.path.basename(input_file_path))[0]
        jpg_file_path = os.path.join(output_dir, f"{base_name}.jpg")
        Image.fromarray(rgb).save(jpg_file_path, 'JPEG')
        return jpg_file_path

def convert_heic_to_jpg(input_file_path, output_dir):
    """Convert heic files to JPG using rawpy."""
    img = Image.open(input_file_path)
    img = img.convert("RGB")
    base_name = os.path.splitext(os.path.basename(input_file_path))[0]
    jpg_file_path = os.path.join(output_dir, f"{base_name}.jpg")
    img.save(jpg_file_path, "JPEG", quality=95)
    return jpg_file_path
