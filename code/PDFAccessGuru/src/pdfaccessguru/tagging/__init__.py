"""
Automatic tagging of PDFs that have no tags at all (Phase 6), built on PyMuPDF only, so it works
on every computer without extra downloads.

1. layout.py   reads each page like a person: what is a heading, a paragraph, a list item, a
               picture, a caption, a table (rows, header row, cells), a header or footer, and
               in which order it is read.
   figures.py  (1.1) groups drawings and picture pieces that belong together into one figure
               region with its labels (charts, diagrams); lines, frames and dots stay decoration.
   formulas.py (1.1) finds display equations (Formula); math inside a sentence stays text.
2. marking.py  marks every piece of the page content with the item it belongs to (MCIDs), or as
               decoration; text is never hidden.
3. builder.py  builds the tag tree (headings, paragraphs, lists, figures, tables, links inside
               the paragraph they are in) and the parent tree. A file whose tags cover almost
               none of its text (less than 5%) is tagged anew.
4. leftovers.py (1.1) in a partly tagged file, gives the content that no tag reaches its place
               in the existing tree, or marks it as decoration (headers, footers, page
               numbers, lines); the existing tags stay as they are.

The pipeline checks the result like any other fix: the pages must look the same and the text
must stay the same, otherwise the tagging is undone.
"""
