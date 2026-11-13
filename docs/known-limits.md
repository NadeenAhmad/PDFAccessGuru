# Known limits and ideas for later

Things we decided not to do (yet), with the reason and a rough effort, so they can be picked up later.

| What | Why it is left out | Effort (Claude Code) |
|---|---|---|
| **Text that sits only inside embedded blocks** (form XObjects): such a page is tagged as one long paragraph instead of separate headings and paragraphs. All text is still read; there are just no headings to jump between on that page. | Rare: about 3 in 200 untagged web PDFs (measured 2026-11-07). | ~3–4 h |
| **Colour contrast of text on pictures or colour gradients** is only reported ("check by eye"), not measured or fixed. | The colour behind the text is not one colour, so the contrast cannot be measured reliably. | – |
| **Report PDF in Arabic, Hindi and similar scripts**: veraPDF still reports font warnings. Screen readers read the exact text (it is stored as ActualText). | The warnings concern the shapes MuPDF draws, not the text. | – |
| **Partly tagged files: untagged table cells** become paragraphs (1.1 tags all other leftover content: text, pictures, headers and footers). | Building a table around cells that an author's tags left out needs the whole table; rare in the test files. | ~3 h |
| **Formula descriptions without an AI** read the formula's own text in words ("y equals alpha plus beta times x2"): fractions, powers and indices are not spoken as such, and symbols without a text value are left out. With an AI, the formula's picture is described. | Reading the structure of a formula needs its layout or MathML; the AI does this better. | ~1 day |
| **Charts that look like tables** (bar charts with grid lines) can stay tables, and the panels of a figure that lie far apart can become separate figures. | Telling these apart from real tables and separate figures without an AI is uncertain; 1.1 prefers leaving text readable. | ~2–3 h |
| **Without an AI, a figure's description is its caption**, taken from the nearest caption in reading order; in two-column papers this can be the caption of the neighbouring figure. The review list shows every such description. | An AI that sees the picture describes it instead. | ~1 h |
