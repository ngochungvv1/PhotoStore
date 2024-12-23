import random
import string
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np


# def add_watermark(image_path, watermark_text):
#     image = Image.open(image_path).convert("RGBA")  # Chế độ RGBA cho ảnh gốc
#
#     # Tạo một ảnh mới với chế độ RGBA để thêm watermark
#     txt = Image.new("RGBA", image.size, (255, 255, 255, 0))  # Ảnh trong suốt
#     draw = ImageDraw.Draw(txt)
#     font = ImageFont.truetype("arial.ttf", 40)
#     draw.text((10, 10), watermark_text, fill=(255, 255, 255, 128), font=font)
#
#     # Thêm watermark vào ảnh
#     watermarked = Image.alpha_composite(image, txt)
#
#     # Lưu ảnh dưới dạng PNG (vì PNG hỗ trợ alpha channel)
#     watermarked_path = image_path.replace('.jpg', '_watermarked.png')
#
#     # Nếu muốn lưu ảnh dưới dạng JPEG, cần chuyển chế độ sang RGB (không có alpha channel)
#     watermarked_rgb = watermarked.convert("RGB")  # Chuyển từ RGBA sang RGB
#     watermarked_rgb.save(watermarked_path.replace('.png', '.jpg'), 'JPEG')  # Lưu dưới dạng JPEG
#
#     return watermarked_path
def add_logo_watermark(image_path, logo_path):
    image = Image.open(image_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    # Đặt kích thước của logo
    logo.thumbnail((100, 100), Image.LANCZOS)

    # Vị trí của logo ở góc dưới bên phải
    image_width, image_height = image.size
    logo_width, logo_height = logo.size
    position = (image_width - logo_width - 10, image_height - logo_height - 10)

    # Chèn logo lên ảnh chính
    image.paste(logo, position, logo)

    # Trả về đối tượng ảnh
    return image.convert("RGB")  # Chuyển đổi sang RGB để lưu dưới dạng JPEG


def add_text_watermark(image_path, text):
    image = Image.open(image_path).convert("RGBA")

    # Tạo lớp trong suốt để vẽ văn bản lên đó
    txt_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)

    # Sử dụng font tùy chỉnh
    try:
        font = ImageFont.truetype("arial.ttf", 50)
    except IOError:
        font = ImageFont.load_default()

    # # Thêm văn bản ở vị trí dưới cùng bên phải
    # text_bbox = draw.textbbox((0, 0), text, font=font)
    # text_width = text_bbox[2] - text_bbox[0]
    # text_height = text_bbox[3] - text_bbox[1]
    # position = (image.size[0] - text_width - 10, image.size[1] - text_height - 10)

    # # Vẽ văn bản lên lớp trong suốt với độ mờ
    # draw.text(position, text, fill=(255, 255, 255, 128), font=font)

    # # Hợp nhất lớp văn bản với ảnh gốc
    # watermarked_image = Image.alpha_composite(image, txt_layer)

    # Tính toán vị trí của từng văn bản
    text1_bbox = draw.textbbox((0, 0), text, font=font)
    text1_width = text1_bbox[2] - text1_bbox[0]
    text1_height = text1_bbox[3] - text1_bbox[1]
    position1 = (10, 10)

    text2_bbox = draw.textbbox((0, 0), text, font=font)
    text2_width = text2_bbox[2] - text2_bbox[0]
    text2_height = text2_bbox[3] - text2_bbox[1]
    position2 = ((image.size[0] - text2_width) // 2, (image.size[1] - text2_height) // 2)

    text3_bbox = draw.textbbox((0, 0), text, font=font)
    text3_width = text3_bbox[2] - text3_bbox[0]
    text3_height = text3_bbox[3] - text3_bbox[1]
    position3 = (image.size[0] - text3_width - 10, image.size[1] - text3_height - 10)

    # Vẽ văn bản lên lớp trong suốt với độ mờ
    draw.text(position1, text, fill=(255, 255, 255, 128), font=font)
    draw.text(position2, text, fill=(255, 255, 255, 128), font=font)
    draw.text(position3, text, fill=(255, 255, 255, 128), font=font)

    # Hợp nhất lớp văn bản với ảnh gốc
    watermarked_image = Image.alpha_composite(image, txt_layer)

    # Trả về đối tượng ảnh
    return watermarked_image.convert("RGB")  # Chuyển đổi sang RGB để lưu dưới dạng JPEG

def generate_random_text(length=6):
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for _ in range(length))
#------------------------------------------------------------------------------------------
def embed_watermark(image, watermark):
    """
    Nhúng watermark vào ảnh gốc bằng phương pháp LSB.

    - image: Ảnh gốc (Pillow Image object).
    - watermark: Ảnh watermark (Pillow Image object, đã được resize).

    Returns:
        Ảnh đã nhúng watermark (Pillow Image object).
    """
    # Resize watermark để phù hợp với kích thước ảnh gốc
    watermark_resized = watermark.resize((image.width, image.height), Image.Resampling.LANCZOS)

    # Chuyển đổi ảnh sang mảng numpy
    image_array = np.array(image)
    watermark_array = np.array(watermark_resized)

    # Nhúng watermark vào bit cuối cùng của kênh màu xanh (blue channel)
    watermarked_array = image_array.copy()
    watermarked_array[..., 2] = (image_array[..., 2] & 0b11111110) | watermark_array

    return Image.fromarray(watermarked_array)


def extract_watermark(watermarked_image):
    """
    Trích xuất watermark từ ảnh đã được nhúng.

    - watermarked_image: Ảnh đã nhúng watermark (Pillow Image object).

    Returns:
        Ảnh watermark được trích xuất (Pillow Image object).
    """
    # Chuyển đổi ảnh sang mảng numpy
    watermarked_array = np.array(watermarked_image)

    # Lấy watermark từ bit cuối cùng của kênh màu xanh (blue channel)
    extracted_watermark = (watermarked_array[..., 2] & 0b00000001) * 255

    return Image.fromarray(extracted_watermark)