"""Create a simple camera icon for the application"""
from PIL import Image, ImageDraw

# Create 256x256 image with transparent background
size = 256
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Colors
body_color = (50, 50, 50, 255)  # Dark gray camera body
lens_color = (30, 30, 30, 255)  # Darker lens
lens_ring = (100, 100, 100, 255)  # Gray lens ring
highlight = (80, 80, 80, 255)  # Highlight
flash_color = (200, 200, 200, 255)  # Flash

# Camera body (rounded rectangle)
margin = 30
body_top = 70
body_bottom = 210
draw.rounded_rectangle(
    [margin, body_top, size - margin, body_bottom],
    radius=20,
    fill=body_color
)

# Viewfinder bump on top
draw.rounded_rectangle(
    [80, 45, 140, 75],
    radius=8,
    fill=body_color
)

# Flash
draw.rounded_rectangle(
    [170, 50, 210, 70],
    radius=5,
    fill=flash_color
)

# Lens outer ring
lens_center = (size // 2, 140)
lens_radius = 55
draw.ellipse(
    [lens_center[0] - lens_radius, lens_center[1] - lens_radius,
     lens_center[0] + lens_radius, lens_center[1] + lens_radius],
    fill=lens_ring
)

# Lens inner
inner_radius = 45
draw.ellipse(
    [lens_center[0] - inner_radius, lens_center[1] - inner_radius,
     lens_center[0] + inner_radius, lens_center[1] + inner_radius],
    fill=lens_color
)

# Lens highlight
highlight_radius = 35
draw.ellipse(
    [lens_center[0] - highlight_radius, lens_center[1] - highlight_radius,
     lens_center[0] + highlight_radius, lens_center[1] + highlight_radius],
    fill=(40, 40, 40, 255)
)

# Lens reflection (small white circle)
draw.ellipse([100, 115, 115, 130], fill=(255, 255, 255, 100))

# Save as ICO with multiple sizes
img_sizes = []
for s in [16, 32, 48, 64, 128, 256]:
    img_sizes.append(img.resize((s, s), Image.Resampling.LANCZOS))

img_sizes[0].save(
    'camera_icon.ico',
    format='ICO',
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    append_images=img_sizes[1:]
)

print("Icon created: camera_icon.ico")
