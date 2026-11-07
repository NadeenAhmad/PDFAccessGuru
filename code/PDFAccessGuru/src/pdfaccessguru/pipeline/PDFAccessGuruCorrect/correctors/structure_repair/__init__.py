"""
Group-level repairs of the structure tree: lists, tables, tables of contents and headings.

The first correctors fixed each veraPDF finding on its own: every loose list item got its own
list, every loose table cell its own row, every heading but one became a paragraph. These
helpers look at the whole group around a finding and rebuild it the way a person would:
consecutive list items form one list, cells on the same line form one row, and two headings in
one section become two sections.
"""
