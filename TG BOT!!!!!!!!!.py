import io
import os

from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = ""

FONT_PATHS = [
    "font.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def load_font(size):
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    lines, line = [], ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if draw.textlength(test, font=font) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def add_text(image_bytes, text):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    width, height = img.size

    size = max(20, width // 10)
    while True:
        font = load_font(size)
        lines = wrap_text(draw, text, font, width * 0.9)
        line_h = size * 1.2
        if len(lines) * line_h <= height * 0.4 or size <= 16:
            break
        size -= 2

    y = height - len(lines) * line_h - height * 0.04
    for line in lines:
        line_w = draw.textlength(line, font=font)
        draw.text(
            ((width - line_w) / 2, y),
            line,
            font=font,
            fill="white",
            stroke_width=max(1, size // 12),
            stroke_fill="black",
        )
        y += line_h

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=95)
    out.seek(0)
    return out


async def send_result(update, context, file_id, text):
    tg_file = await context.bot.get_file(file_id)
    data = bytes(await tg_file.download_as_bytearray())
    await update.message.reply_photo(add_text(data, text))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Пришли фото с подписью, и я напишу её на картинке. "
        "Или пришли фото без подписи, и я спрошу текст."
    )


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]  # самое большое разрешение
    caption = update.message.caption
    if caption:
        await send_result(update, context, photo.file_id, caption)
    else:
        context.user_data["photo_id"] = photo.file_id
        await update.message.reply_text("Теперь напиши текст для фотографии.")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_id = context.user_data.pop("photo_id", None)
    if not photo_id:
        await update.message.reply_text("Сначала пришли фото.")
        return
    await send_result(update, context, photo_id, update.message.text)


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling()


if __name__ == "__main__":
    main()
