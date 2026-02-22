#!python
#
# Aaron Eppert (2026)
#
import os
import sys
import random
import argparse
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


class BingoCardGenerator:
    def __init__(
        self, size: int = 5, free_space_text: str = "FREE SPACE", title: str = ""
    ):
        self.size: int = size
        self.free_space_text: str = free_space_text
        self.cell_size: int = 110  # Slightly larger for better readability
        self.margin: int = 40
        self.inset: int = 10
        self.title: str = title

    def get_image_files(self, directory: str) -> list[str]:
        """Scans directory for valid image extensions."""
        valid_ext = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff")
        files = [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.lower().endswith(valid_ext)
        ]
        return files

    def load_and_prepare_image(self, image_path: str) -> Image.Image:
        """Loads, resizes, and converts image for the grid."""
        try:
            # Open image and convert to RGB (handles RGBA/P modes)
            img = Image.open(image_path).convert("RGBA")

            # Create a square thumbnail to fit the grid cell nicely
            # We use Image.thumbnail to maintain aspect ratio
            img_copy = img.copy()
            img_copy.thumbnail(
                (self.cell_size - self.inset, self.cell_size - self.inset),
                Image.Resampling.LANCZOS,
            )

            # Create a white background to paste the image onto (prevents transparency issues in PDF)
            bg = Image.new("RGB", (self.cell_size, self.cell_size), (255, 255, 255))
            # Center the image
            offset = (
                (self.cell_size - img_copy.width) // 2,
                (self.cell_size - img_copy.height) // 2,
            )
            bg.paste(
                img_copy, offset, mask=img_copy.split()[3]
            )  # Use alpha channel as mask

            return bg
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            return self._create_placeholder("Err")

    def _create_placeholder(
        self, text: str, color: tuple = (200, 200, 200)
    ) -> Image.Image:
        """Helper to create a placeholder image for text or missing files."""
        img = Image.new("RGB", (self.cell_size, self.cell_size), color)
        d = ImageDraw.Draw(img)

        # Try to load a nice font
        font_size = 20
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        text_w = d.textlength(text, font=font)
        text_h = font_size  # rough estimate
        position = ((self.cell_size - text_w) // 2, (self.cell_size - text_h) // 2)

        d.text(position, text, fill="black", font=font)
        return img

    def generate_single_card(self, items: list[str], output_filename: str):
        """Generates one Bingo card PDF."""
        total_cells = self.size * self.size

        content: list[str] = []

        # Add valid images first
        for item in items:
            if os.path.isfile(item):
                content.append(self.load_and_prepare_image(item))
            else:
                content.append(self._create_placeholder(str(item)[:15]))

        # Fill remaining spots if needed
        if len(content) < total_cells:
            count = 1
            while len(content) < total_cells:
                # Create a numbered placeholder
                txt = f"Slot {len(content) + 1}"
                content.append(self._create_placeholder(txt))
                count += 1

        # Randomize and Handle Free Space
        # Remove the middle spot from the pool to put Free Space there
        middle_index = total_cells // 2

        # Pop the item currently in the middle (it will be replaced by Free Space)
        _ = content.pop(middle_index)

        # Shuffle the remaining items
        random.shuffle(content)

        # Insert Free Space in the middle
        free_space_img = self._create_placeholder(
            self.free_space_text, color=(255, 255, 255)
        )
        content.insert(middle_index, free_space_img)

        # Construct the Final Grid (PIL Image)
        card_width = (
            (self.size * self.cell_size) + (2 * self.margin) + ((self.size - 1) * 2)
        )
        card_height = (
            (self.size * self.cell_size)
            + (2 * self.margin)
            + ((self.size - 1) * 2)
            + 60
        )  # Extra space for title

        final_card = Image.new("RGB", (card_width, card_height), (255, 255, 255))
        draw = ImageDraw.Draw(final_card)

        # Draw Border
        draw.rectangle(
            [(0, 0), (card_width - 1, card_height - 1)], outline="black", width=4
        )

        # Draw Grid
        for row in range(self.size):
            for col in range(self.size):
                index = row * self.size + col
                img_data = content[index]

                # Calculate position with gaps
                x = self.margin + col * (self.cell_size + 2)
                y = self.margin + 40 + row * (self.cell_size + 2)  # +40 for title space

                final_card.paste(img_data, (x, y))

                # Draw Grid Lines
                draw.rectangle(
                    [(x, y), (x + self.cell_size, y + self.cell_size)],
                    outline="black",
                    width=2,
                )

        # Add Title
        if len(self.title) > 0:
            try:
                title_font = ImageFont.truetype("arialbd.ttf", 48)
            except:
                title_font = ImageFont.load_default()

            title_w = draw.textlength(self.title, font=title_font)
            draw.text(
                ((card_width - title_w) // 2, 10),
                self.title,
                fill="black",
                font=title_font,
            )

        # 5. Convert to PDF
        temp_img_path = "temp_pdf_interim.jpg"
        final_card.save(temp_img_path)

        c = canvas.Canvas(output_filename, pagesize=letter)
        # Scale to fit letter paper
        c.drawImage(temp_img_path, 0, 0, width=letter[0], height=letter[1])
        _ = c.save()

        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

        return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate Bingo Cards from a directory of images."
    )
    _ = parser.add_argument(
        "-d",
        "--directory",
        type=str,
        default=".",
        help="Directory containing images (default: current directory)",
    )
    _ = parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=1,
        help="Number of unique cards to generate (default: 1)",
    )
    _ = parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="bingo_card",
        help="Base filename for output PDFs (default: bingo_card)",
    )
    _ = parser.add_argument(
        "-s",
        "--size",
        type=int,
        choices=[4, 5],
        default=5,
        help="Grid size (4x4 or 5x5, default: 5x5)",
    )
    _ = parser.add_argument(
        "-f",
        "--free-space",
        type=str,
        default="FREE SPACE",
        help="Text for the center free space cell",
    )
    _ = parser.add_argument(
        "-t", "--title", type=str, default="", help="Title for Bingo Cards"
    )

    args = parser.parse_args()

    # Validate directory
    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' not found.")
        sys.exit(1)

    # Get images
    image_files = BingoCardGenerator(size=args.size).get_image_files(args.directory)

    if not image_files:
        print(
            f"No images found in {args.directory}. Generating cards with text placeholders only."
        )

    print(f"Found {len(image_files)} images. Generating {args.number} card(s)...")

    generator = BingoCardGenerator(
        size=args.size, free_space_text=args.free_space, title=args.title
    )

    for i in range(1, args.number + 1):
        # Create a unique seed for this card based on the index to ensure different layouts
        random.seed()  # Reset seed to true random for each card

        # Shuffle a copy of the list for this specific card
        current_pool = image_files.copy()
        random.shuffle(current_pool)

        output_filename = f"{args.output}_{i}.pdf"
        generator.generate_single_card(current_pool, output_filename)
        print(f"Generated: {output_filename}")

    print(f"Completed - {args.number} created.")


if __name__ == "__main__":
    main()
