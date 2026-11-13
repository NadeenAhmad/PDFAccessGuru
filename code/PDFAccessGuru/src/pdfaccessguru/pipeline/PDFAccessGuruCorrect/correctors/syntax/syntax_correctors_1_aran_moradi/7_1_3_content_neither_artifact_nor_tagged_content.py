from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pikepdf import Name, Pdf
import pikepdf
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi.constants import (
    PDFUA_NAMESPACE,
    RDF_NAMESPACE,
    STANDARD_TYPES,
)
from lxml import etree
from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException


# Text-showing operators (each paints glyphs, i.e. a content item).
TEXT_SHOWING_OPERATORS = ("Tj", "TJ", "'", '"')
# Path construction operators that begin a path object.
PATH_CONSTRUCTION_OPERATORS = ("m", "l", "c", "v", "y", "re", "h")
# Path-painting operators that produce a visible mark and end the path object.
PATH_PAINTING_MARK_OPERATORS = ("S", "s", "f", "F", "f*", "B", "B*", "b", "b*")
# Path-painting operators that end the path object without producing a mark.
PATH_PAINTING_NO_MARK_OPERATORS = ("n",)
# Standalone mark producers: image / form XObject invocation and shadings.
STANDALONE_MARK_OPERATORS = ("Do", "sh")

MARKED_CONTENT_BEGIN = ("BDC", "BMC")
MARKED_CONTENT_END = ("EMC",)

# Every operator that produces a content item for veraPDF rule 7.1-3.
MARK_PRODUCING_OPERATORS = (
    TEXT_SHOWING_OPERATORS
    + PATH_PAINTING_MARK_OPERATORS
    + STANDALONE_MARK_OPERATORS
)


def _begin_artifact():
    return ([Name("/Artifact")], pikepdf.Operator("BMC"))


def _end_artifact():
    return ([], pikepdf.Operator("EMC"))


def _wrap_untagged_marks(instructions):
    """
    Wrap every complete, untagged, mark-producing graphics object in an Artifact
    marked-content sequence. Content that is already inside a marked-content
    sequence (i.e. tagged as real content or already an artifact) is left
    untouched, and complete path objects / text objects are never split.
    Returns the rewritten instruction list and whether anything changed.
    """
    corrected = []
    changed = False
    depth = 0
    index = 0
    count = len(instructions)

    while index < count:
        operands, operator = instructions[index]
        name = str(operator)

        # Inside an existing marked-content sequence: keep as-is, track nesting.
        if depth > 0:
            corrected.append((operands, operator))
            if name in MARKED_CONTENT_BEGIN:
                depth += 1
            elif name in MARKED_CONTENT_END:
                depth -= 1
            index += 1
            continue

        if name in MARKED_CONTENT_BEGIN:
            corrected.append((operands, operator))
            depth += 1
            index += 1
            continue
        if name in MARKED_CONTENT_END:
            corrected.append((operands, operator))
            index += 1
            continue

        # Text object: never marked as an artifact. Text is real content until a
        # tagging step proves otherwise (e.g. a repeated running header); marking
        # it as an artifact would hide it from screen readers. It stays untagged
        # and the violation remains reported.
        if name == "BT":
            end = index
            while end < count and str(instructions[end][1]) != "ET":
                end += 1
            corrected.extend(instructions[index:end + 1])
            index = end + 1
            continue

        # Path object: collect construction operators up to the painting operator.
        if name in PATH_CONSTRUCTION_OPERATORS:
            end = index
            produces_mark = False
            while end < count:
                path_operator_name = str(instructions[end][1])
                if path_operator_name in PATH_PAINTING_MARK_OPERATORS:
                    produces_mark = True
                    break
                if path_operator_name in PATH_PAINTING_NO_MARK_OPERATORS:
                    break
                end += 1
            path_object = instructions[index:end + 1]
            if produces_mark:
                corrected.append(_begin_artifact())
                corrected.extend(path_object)
                corrected.append(_end_artifact())
                changed = True
            else:
                corrected.extend(path_object)
            index = end + 1
            continue

        # Shadings are decorative fills (backgrounds, gradients): artifact.
        if name == "sh":
            corrected.append(_begin_artifact())
            corrected.append((operands, operator))
            corrected.append(_end_artifact())
            changed = True
            index += 1
            continue

        # Images and form XObjects ("Do") are never marked as artifacts here: an
        # image may need alternative text and a form XObject may contain text.
        # Form XObjects are handled separately by _correct_form_xobjects.

        # Graphics-state or other non-mark operators: keep as-is.
        corrected.append((operands, operator))
        index += 1

    return corrected, changed


def _lookup_number_tree_value(number_tree, key):
    """
    Resolve a key in a PDF number tree, which stores its entries either directly
    in /Nums or spread over /Kids sub-nodes.
    """
    if not isinstance(number_tree, pikepdf.Dictionary):
        return None

    nums = number_tree.get("/Nums")
    if isinstance(nums, pikepdf.Array):
        for index in range(0, len(nums), 2):
            if int(nums[index]) == key:
                return nums[index + 1]

    kids = number_tree.get("/Kids")
    if isinstance(kids, pikepdf.Array):
        for kid in kids:
            value = _lookup_number_tree_value(kid, key)
            if value is not None:
                return value

    return None


def _mcid_parent_array(content_stream_holder, pdf):
    """
    Return the /ParentTree array that maps this content stream's MCIDs to their
    structure elements, or None when it cannot be resolved (no /StructParents, no
    /StructTreeRoot, no /ParentTree entry). None means "unknown", and every MCID
    is then treated as valid so that nothing gets reclassified on a guess.
    """
    struct_parents = content_stream_holder.get("/StructParents")
    if struct_parents is None:
        return None

    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    if not isinstance(struct_tree_root, pikepdf.Dictionary):
        return None

    parent_array = _lookup_number_tree_value(
        struct_tree_root.get("/ParentTree"), int(struct_parents)
    )
    return parent_array if isinstance(parent_array, pikepdf.Array) else None


def _marked_content_properties(operands, content_stream_holder):
    """
    Resolve the properties operand of a BDC operator. It is either an inline
    dictionary or a name referring to the /Properties entry of the content
    stream's resource dictionary.
    """
    if len(operands) < 2:
        return None

    properties = operands[1]
    if isinstance(properties, pikepdf.Dictionary):
        return properties
    if isinstance(properties, Name):
        resources = content_stream_holder.get("/Resources")
        if resources is None:
            return None
        named_properties = resources.get("/Properties")
        if named_properties is None:
            return None
        return named_properties.get(str(properties))

    return None


def _mcid_of(operands, content_stream_holder):
    """Return the /MCID of a BDC operator, or None if it carries none."""
    properties = _marked_content_properties(operands, content_stream_holder)
    if not isinstance(properties, pikepdf.Dictionary):
        return None
    mcid = properties.get("/MCID")
    return None if mcid is None else int(mcid)


def _mcid_is_dangling(mcid, parent_array):
    """
    An MCID is dangling when the structure tree does not actually refer back to
    it: either the /ParentTree array is too short, or its entry is a null.
    """
    if not 0 <= mcid < len(parent_array):
        return True
    return parent_array[mcid] is None


def _contains_tagged_marked_content(instructions, begin_index):
    """
    Whether the marked-content block starting at begin_index contains a nested
    block that is not an artifact. Such a block has to keep its tag, because
    turning its parent into an artifact would nest tagged content inside an
    artifact (rule 7.1-2).
    """
    depth = 0
    for operands, operator in instructions[begin_index:]:
        name = str(operator)
        if name in MARKED_CONTENT_BEGIN:
            depth += 1
            if depth > 1 and (not operands or str(operands[0]) != "/Artifact"):
                return True
        elif name in MARKED_CONTENT_END:
            depth -= 1
            if depth == 0:
                break
    return False


def _contains_real_content(instructions, begin_index):
    """
    Whether the marked-content block starting at begin_index shows text or paints an
    image / form XObject. Such content must not be turned into an artifact on a guess.
    """
    depth = 0
    for _, operator in instructions[begin_index:]:
        name = str(operator)
        if name in MARKED_CONTENT_BEGIN:
            depth += 1
        elif name in MARKED_CONTENT_END:
            depth -= 1
            if depth == 0:
                break
        elif name in TEXT_SHOWING_OPERATORS or name == "Do":
            return True
    return False


def _artifact_dangling_mcid_blocks(instructions, content_stream_holder, parent_array):
    """
    Reclassify every marked-content block whose /MCID is not reachable through the
    /ParentTree as an artifact. Such a block claims to be real content, but no
    structure element refers back to it, so the content is unreachable for
    assistive technology and veraPDF keeps reporting rule 7.1-3 for it.
    Only blocks that are not nested inside another marked-content sequence are
    rewritten, so that the result never becomes an artifact inside tagged content
    (rule 7.1-1) or tagged content inside an artifact (rule 7.1-2).
    Returns the rewritten instruction list and whether anything changed.
    """
    if parent_array is None:
        return instructions, False

    corrected = list(instructions)
    changed = False
    depth = 0

    for index, (operands, operator) in enumerate(instructions):
        name = str(operator)

        if name in MARKED_CONTENT_END:
            depth = max(0, depth - 1)
            continue
        if name not in MARKED_CONTENT_BEGIN:
            continue

        is_top_level = depth == 0
        depth += 1

        if not is_top_level or name != "BDC":
            continue
        if operands and str(operands[0]) == "/Artifact":
            continue

        mcid = _mcid_of(operands, content_stream_holder)
        if mcid is None or not _mcid_is_dangling(mcid, parent_array):
            continue
        if _contains_tagged_marked_content(instructions, index):
            continue
        if _contains_real_content(instructions, index):
            # Text or images whose structure link is broken need a structure repair,
            # not an artifact: leave them and keep the violation reported.
            continue

        corrected[index] = _begin_artifact()
        changed = True

    return corrected, changed


def _corrected_instructions_for(content_stream_holder, pdf):
    """
    Compute the artifact-wrapped instructions for a page or form XObject content
    stream, or None if nothing needs to change.
    """
    instructions = list(pikepdf.parse_content_stream(content_stream_holder))
    operator_names = [str(operator) for _, operator in instructions]

    if not any(name in MARK_PRODUCING_OPERATORS for name in operator_names):
        return None

    # Fully untagged streams are no longer enclosed as one big Artifact (that hid all
    # text from screen readers). Every stream goes through the same rules: only
    # decorative paths and shadings become artifacts; text and images stay untagged.
    corrected, changed = _wrap_untagged_marks(instructions)
    parent_array = _mcid_parent_array(content_stream_holder, pdf)
    corrected, dangling_changed = _artifact_dangling_mcid_blocks(
        corrected, content_stream_holder, parent_array
    )
    return corrected if changed or dangling_changed else None


def _write_back(content_stream_holder, corrected_instructions, pdf):
    """
    Persist the corrected instructions. A form XObject IS a content stream and is
    rewritten in place; a page holds its content in the /Contents entry.
    """
    data = pikepdf.unparse_content_stream(corrected_instructions)
    if isinstance(content_stream_holder, pikepdf.Stream):
        content_stream_holder.write(data)
    else:
        content_stream_holder["/Contents"] = pdf.make_stream(data)


def _forms_drawn_inside_tagged_content(pdf) -> set:
    """
    Form XObjects (and the forms they draw) that some page draws inside a tagged marked-content
    sequence. Their content belongs to that tag, so nothing inside them may become an artifact:
    the same form is often also drawn untagged elsewhere, and marking its inside as an artifact
    there would put an artifact inside tagged content here (rule 7.1-2; found on a real file).
    """
    found: set = set()

    def add_with_nested(form, depth=0) -> None:
        if form.objgen in found or depth > 10:
            return
        found.add(form.objgen)
        resources = form.get("/Resources")
        xobjects = resources.get("/XObject") if isinstance(resources, pikepdf.Dictionary) else None
        for nested in (xobjects.values() if isinstance(xobjects, pikepdf.Dictionary) else []):
            if isinstance(nested, pikepdf.Stream) and nested.get("/Subtype") == pikepdf.Name.Form:
                add_with_nested(nested, depth + 1)

    def scan(owner, resources, seen) -> None:
        xobjects = resources.get("/XObject") if isinstance(resources, pikepdf.Dictionary) else None
        tagged_depth = 0
        stack: list[bool] = []
        try:
            operations = pikepdf.parse_content_stream(owner)
        except Exception:
            return
        for operands, operator in operations:
            name = str(operator)
            if name in MARKED_CONTENT_BEGIN:
                tagged = name == "BDC" and len(operands) > 1 and _mcid_of(operands, owner) is not None
                stack.append(tagged)
                tagged_depth += tagged
            elif name in MARKED_CONTENT_END and stack:
                tagged_depth -= stack.pop()
            elif name == "Do" and isinstance(xobjects, pikepdf.Dictionary):
                form = xobjects.get(str(operands[0]))
                if not isinstance(form, pikepdf.Stream) or form.get("/Subtype") != pikepdf.Name.Form:
                    continue
                if tagged_depth:
                    add_with_nested(form)
                elif form.objgen not in seen:
                    seen.add(form.objgen)
                    scan(form, form.get("/Resources") or resources, seen)

    seen: set = set()
    for page in pdf.pages:
        scan(page, page.obj.get("/Resources"), seen)
    return found


def _correct_form_xobjects(container, visited, pdf, tagged_forms=None):
    """
    Recursively wrap untagged marks inside every form XObject reachable from the
    given page/XObject via its /Resources /XObject dictionary. Forms that are drawn inside
    tagged content somewhere are left alone (see _forms_drawn_inside_tagged_content).
    """
    if tagged_forms is None:
        tagged_forms = _forms_drawn_inside_tagged_content(pdf)
    resources = container.get("/Resources")
    if resources is None:
        return
    xobjects = resources.get("/XObject")
    if xobjects is None:
        return

    for key in list(xobjects.keys()):
        xobject = xobjects[key]

        objgen = getattr(xobject, "objgen", None)
        if objgen is not None:
            if objgen in visited:
                continue
            visited.add(objgen)

        if str(xobject.get("/Subtype")) != "/Form":
            continue
        if objgen in tagged_forms:
            continue

        corrected = _corrected_instructions_for(xobject, pdf)
        if corrected is not None:
            xobject.write(pikepdf.unparse_content_stream(corrected))

        _correct_form_xobjects(xobject, visited, pdf, tagged_forms)


_RETAG_CHECKED: dict[int, tuple] = {}


def _retag_if_nearly_untagged(pdf: Pdf) -> bool:
    """Tag the whole file anew if its tags cover less than 5% of its text (checked once per file)."""
    from pdfaccessguru.pipeline.reporting.writer import report_info, report_review
    from pdfaccessguru.tagging.builder import tag_document

    tree = pdf.Root.get("/StructTreeRoot")
    if not isinstance(tree, pikepdf.Dictionary) or tree.get("/K") is None:
        return False                       # no tags at all: that is the job of the 7.1-11 fix
    key = (len(pdf.pages), pdf.pages[0].obj.objgen if len(pdf.pages) else None)
    if _RETAG_CHECKED.get(id(pdf)) == key:
        return False
    _RETAG_CHECKED.clear()
    _RETAG_CHECKED[id(pdf)] = key
    result = tag_document(pdf)
    if not result.pages:
        return False
    old = f"{result.replaced_share * 100:.0f}%" if result.replaced_share is not None else "none"
    report_info(f"The tags of this file covered almost none of its text ({old}), so the file was tagged anew "
                f"automatically on {result.pages} page(s).")
    report_review("Tags were added automatically. Please check the reading order and the headings once, "
                  "for example with the tags panel of your PDF program or with a screen reader.")
    return True


def _tag_leftover_content(pdf: Pdf) -> None:
    """In a partly tagged file, give the content that no tag reaches its place (1.1, once per file)."""
    from pdfaccessguru.pipeline.reporting.writer import report_debug, report_info, report_review
    from pdfaccessguru.tagging.leftovers import tag_leftovers

    try:
        result = tag_leftovers(pdf)
    except Exception as error:                 # never stop the other fixes of this rule
        report_debug(f"The untagged content could not be tagged: {error}")
        return
    if not result.changed:
        return
    kinds = ", ".join(f"{count} {tag}" for tag, count in sorted(result.elements.items()) if count)
    parts = []
    if kinds:
        parts.append(f"new elements {kinds}")
    if result.artifacts:
        parts.append(f"{result.artifacts} header, footer, page number or decoration piece(s) marked as decoration")
    if result.linked:
        parts.append(f"{result.linked} element(s) outside the tag tree linked into it")
    where = f" on {result.pages} page(s)" if result.pages else ""
    report_info(f"Content that no tag reached was tagged{where}: {'; '.join(parts)}.")
    report_review("Untagged content was added to the existing tags automatically. Please check its place in the "
                  "reading order and the headings once, for example with the tags panel of your PDF program.")


@corrector("content-neither-artifact-nor-tagged-content")
def correct_content_neither_artifact_nor_tagged_content(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.1-3
    Violation description: Content is neither marked as Artifact nor tagged as real content
    Correction strategy:
    Content ends up unclassified in two different ways, so the correction runs in
    two passes.

    Rule: only decorative content becomes an artifact. Text and images are real
    content until a tagging step proves otherwise; they stay untagged and the
    violation remains reported ("needs tagging"), because marking them as artifacts
    would hide them from screen readers. (Until 2026-11 untagged text was marked as
    an artifact, which hid 99.82% of the text in the evaluated theses.)

    Pass 1 - untagged decorative items:
    Untagged path objects (lines, rules, boxes, backgrounds) and shadings that are
    not inside a marked-content sequence are wrapped in "/Artifact BMC ... EMC".
    Existing tags are kept, tagged content is never nested inside an artifact and
    path objects are never split. Text objects and image / form XObjects are left
    untouched.
    Before correction:
    ...
    re
    f
    ...
    After correction:
    /Artifact BMC
        re
        f
    EMC
    ...

    Pass 2 - dangling MCIDs:
    Being inside a marked-content sequence is not enough: a block such as
    "/P <</MCID 95>> BDC" only counts as real content when the structure tree
    actually refers back to that MCID. The link is checked by resolving the
    content stream's /StructParents through the /StructTreeRoot's /ParentTree and
    looking up the MCID in the resulting array. When the array is too short there
    or holds a null, nothing in the structure tree points at the content, it is
    unreachable for assistive technology, and veraPDF keeps reporting rule 7.1-3.
    Such a block is reclassified as an artifact only if it contains no text and no
    image / form XObject (i.e. purely decorative drawing).
    Before correction:
    /P <</MCID 95>> BDC   % but /ParentTree[95] is null
        0 0 100 2 re f
    EMC
    After correction:
    /Artifact BMC
        0 0 100 2 re f
    EMC

    Only blocks that are not nested inside another marked-content sequence are
    reclassified, and only when they contain no nested tagged content, so the
    result never becomes an artifact inside tagged content (rule 7.1-1) or tagged
    content inside an artifact (rule 7.1-2). When the /ParentTree cannot be
    resolved at all (no /StructParents, no /StructTreeRoot), every MCID is treated
    as valid and pass 2 changes nothing, rather than reclassifying content on a
    guess.

    The page content stream and every form XObject it references (which have their
    own content streams) are corrected by both passes.

    Untagged text and images, and dangling blocks that contain them, are not
    touched by the two passes. They need the structure tree to be built or
    repaired: a file with almost no tags is tagged anew (tagging/builder.py); in a
    partly tagged file, tagging/leftovers.py (1.1) runs first and gives them new
    structure elements in reading order (or marks running headers, footers and
    page numbers as artifacts). What it cannot place safely stays reported.
    """

    affected_element = detected_violation.affected_element

    # A file whose tags cover almost none of its text (e.g. only a template's title page) is
    # tagged anew as a whole (Phase 6); that marks all its content at once.
    if _retag_if_nearly_untagged(pdf):
        return
    # In a partly tagged file the content that no tag reaches gets its place in the existing
    # tree (text, pictures, unknown MCIDs) or becomes decoration (headers, footers, page
    # numbers, lines); done for the whole file at the first page (1.1).
    _tag_leftover_content(pdf)

    try:
        corrected_instructions = _corrected_instructions_for(affected_element, pdf)
    except Exception as e:
        raise CouldNotCorrectDetectedViolationException("content-neither-artifact-nor-tagged-content") from e

    if corrected_instructions is not None:
        _write_back(affected_element, corrected_instructions, pdf)

    _correct_form_xobjects(affected_element, set(), pdf)