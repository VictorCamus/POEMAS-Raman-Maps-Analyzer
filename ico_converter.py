"""Converteix la icona a format .ico."""
from PIL import Image

image = Image.open("POEMAS.png").convert("RGBA")

# Redimensionar mantenint la proporció
image.thumbnail((256, 256), Image.Resampling.LANCZOS)

# Crear un llenç quadrat transparent
icon = Image.new("RGBA", (256, 256), (0, 0, 0, 0))

# Centrar la imatge
position = (
    (256 - image.width) // 2,
    (256 - image.height) // 2,
)

icon.alpha_composite(image, position)

# Generar la icona amb diverses resolucions
icon.save(
    "poemas.ico",
    format="ICO",
    sizes=[
        (16, 16),
        (32, 32),
        (48, 48),
        (64, 64),
        (128, 128),
        (256, 256),
    ],
)