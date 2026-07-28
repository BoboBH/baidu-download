#!/usr/bin/env python3
"""
Simple script to create a basic Windows icon file (.ico)
This creates a minimal 32x32 pixel icon for the baidu-download application
"""

import struct
import zlib

def create_simple_icon():
    """Create a simple Windows icon file"""

    # This is a minimal valid ICO file with a simple 32x32 icon
    # Using a very simple design with binary data

    # ICO header (6 bytes)
    ico_header = struct.pack('<HHH', 0, 1, 1)  # Reserved=0, Type=1 (icon), Count=1

    # Directory entry (16 bytes)
    width = 32
    height = 32
    colors = 0  # 0 means >= 8bpp
    reserved = 0
    planes = 1
    bpp = 32  # 32 bits per pixel
    size = 40 + (32 * 32 * 4) + (32 * 32 // 8)  # DIB header + pixel data + mask
    offset = 6 + 16  # After header and directory entry

    dir_entry = struct.pack('<BBBBHHII',
                            width, height, colors, reserved,
                            planes, bpp, size, offset)

    # DIB header (BITMAPINFOHEADER) (40 bytes)
    dib_header = struct.pack('<IIIHHIIIIII',
                            40,           # biSize
                            width,        # biWidth
                            height * 2,   # biHeight (double for XOR and AND masks)
                            1,            # biPlanes
                            32,           # biBitCount
                            0,            # biCompression (BI_RGB)
                            0,            # biSizeImage (uncompressed)
                            0,            # biXPelsPerMeter
                            0,            # biYPelsPerMeter
                            0,            # biClrUsed
                            0)            # biClrImportant

    # Simple pixel data - create a blue background with a white 'B' letter
    # Using BGRA format for 32bpp
    pixels = []
    for y in range(height):
        for x in range(width):
            # Simple blue background
            if y < 8 or y >= 24 or x < 8 or x >= 24:
                # Blue background
                pixels.append(struct.pack('<I', 0xFF0000FF))  # BGRA: Blue
            elif 8 <= y < 24 and 8 <= x < 24:
                # White area for 'B' letter (simplified)
                pixels.append(struct.pack('<I', 0xFFFFFFFF))  # BGRA: White
            else:
                pixels.append(struct.pack('<I', 0xFF0000FF))  # BGRA: Blue

    pixel_data = b''.join(pixels)

    # AND mask (1 bit per pixel, for transparency)
    # All zeros means fully opaque
    mask_size = width * height // 8
    and_mask = b'\x00' * mask_size

    # Combine all parts
    ico_data = ico_header + dir_entry + dib_header + pixel_data + and_mask

    return ico_data

if __name__ == "__main__":
    print("Creating Windows icon file...")
    try:
        ico_data = create_simple_icon()
        with open('baidu-download.ico', 'wb') as f:
            f.write(ico_data)
        print(f"✅ Icon created successfully: baidu-download.ico ({len(ico_data)} bytes)")
        print("This is a simple 32x32 icon with blue background and white 'B' symbol")
    except Exception as e:
        print(f"❌ Error creating icon: {e}")
        print("Note: You may need to provide a professional icon file instead")