from pathlib import Path

from PIL import Image, ImageDraw

from pdfaccessguru.model.supplementary_information.table.bounding_box import BoundingBox

A4_WIDTH_PT = 595
A4_HEIGHT_PT = 842
OUTPUT_FILENAME = "rendered_table_content.png"
BOX_COLOR = "#2563EB"
LABEL_OFFSET_PT = 10


def render_rendered_table_content(
    id_to_bounding_box: dict[int, BoundingBox],
) -> Path:
    """
    Draw bounding boxes and their IDs on a DIN A4 canvas and save as PNG.

    Args:
        id_to_bounding_box: Maps element IDs to bounding boxes in pdfplumber
            page coordinates (top-left origin), as returned by
            generate_id_to_bounding_box_mapping.

    Returns:
        Path to the written PNG file in this module's directory.
    """
    output_path = Path(__file__).resolve().parent / OUTPUT_FILENAME
    image = Image.new("RGB", (A4_WIDTH_PT, A4_HEIGHT_PT), "white")
    draw = ImageDraw.Draw(image)

    for element_id, box in sorted(id_to_bounding_box.items()):
        draw.rectangle([box.x0, box.top, box.x1, box.bottom], outline=BOX_COLOR, width=1)

        label = (
            f"{element_id} ({box.x0:.1f}, {box.top:.1f}, "
            f"{box.x1:.1f}, {box.bottom:.1f})"
        )
        draw.text((box.x0, max(0, box.top - LABEL_OFFSET_PT)), label, fill=BOX_COLOR)

    image.save(output_path)
    return output_path
