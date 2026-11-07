from .common import (
    CouldNotCorrectDetectedViolationException,
    DetectedViolation,
    Pdf,
    _replace_nth_occurrence,
    corrector,
    pikepdf,
)


@corrector("form-xobject-mcids-multi-referenced")
def correct_form_xobject_mcids_multi_referenced(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.20-2

    Violation description:
    A Form XObject containing MCIDs is referenced more than once.

    Correction strategy:
    Duplicate the affected Form XObject for every use after the first one and
    rewrite later /Do operators to point to the clones. This ensures that no
    single MCID-bearing Form XObject object is reused multiple times.
    """
    affected_element = detected_violation.affected_element

    if not hasattr(affected_element, "keys") or not hasattr(affected_element, "read_bytes"):
        raise CouldNotCorrectDetectedViolationException("form-xobject-mcids-multi-referenced")

    occurrence_counter = 0
    clone_counter = 1

    for page in pdf.pages:
        page_dict = page.obj
        resources = page_dict.get("/Resources")
        if not isinstance(resources, pikepdf.Dictionary):
            continue

        xobjects = resources.get("/XObject")
        if not isinstance(xobjects, pikepdf.Dictionary):
            continue

        for original_name in list(xobjects.keys()):
            xobject = xobjects.get(original_name)
            if xobject != affected_element:
                continue

            content_stream = page_dict.get("/Contents")
            if content_stream is None or not hasattr(content_stream, "read_bytes"):
                continue

            content_text = content_stream.read_bytes().decode("latin1", errors="ignore")
            pattern = f"{original_name} Do"
            occurrences_on_page = content_text.count(pattern)

            if occurrences_on_page == 0:
                continue

            updated_content = content_text
            for local_occurrence_index in range(occurrences_on_page):
                if occurrence_counter == 0:
                    occurrence_counter += 1
                    continue

                clone_name = f"/FmClone{clone_counter}"
                clone_counter += 1

                cloned_xobject = pdf.make_stream(xobject.read_bytes()) # type: ignore
                for key in xobject.keys(): # type: ignore
                    if key in ["/Length", "/Filter"]:
                        continue
                    cloned_xobject[key] = xobject.get(key) # type: ignore

                xobjects[clone_name] = cloned_xobject
                replacement = f"{clone_name} Do"
                updated_content = _replace_nth_occurrence(
                    updated_content,
                    pattern,
                    replacement,
                    local_occurrence_index,
                )
                occurrence_counter += 1

            page_dict["/Contents"] = pdf.make_stream(updated_content.encode("latin1"))

    if occurrence_counter <= 1:
        raise CouldNotCorrectDetectedViolationException("form-xobject-mcids-multi-referenced")
