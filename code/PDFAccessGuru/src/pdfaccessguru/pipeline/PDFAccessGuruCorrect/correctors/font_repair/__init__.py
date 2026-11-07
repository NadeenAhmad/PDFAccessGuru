"""
Repairs of fonts, done for the whole document at once (Phase 3c).

The first font correctors replaced fonts with an unrelated substitute, recomputed character
widths (which moves text), or deleted character tables and characters. These repairs keep
what the reader sees: text keeps its exact position (the widths in the PDF are never changed;
where needed the font program is adapted to them), and characters keep their glyphs.
"""
