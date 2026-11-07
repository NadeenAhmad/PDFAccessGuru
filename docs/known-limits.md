# Known limits and ideas for later

Things we decided not to do (yet), with the reason and a rough effort, so they can be picked up later.

| What | Why it is left out | Effort (Claude Code) |
|---|---|---|
| **Text that sits only inside embedded blocks** (form XObjects): such a page is tagged as one long paragraph instead of separate headings and paragraphs. All text is still read; there are just no headings to jump between on that page. | Rare: about 3 in 200 untagged web PDFs (measured 2026-11-07). | ~3–4 h |
| **Colour contrast of text on pictures or colour gradients** is only reported ("check by eye"), not measured or fixed. | The colour behind the text is not one colour, so the contrast cannot be measured reliably. | – |
| **Report PDF in Arabic, Hindi and similar scripts**: veraPDF still reports font warnings. Screen readers read the exact text (it is stored as ActualText). | The warnings concern the shapes MuPDF draws, not the text. | – |
