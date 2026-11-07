
import io
import json

import pikepdf
import pytest

from pdfaccessguru.model.supplementary_information.table.bounding_box import BoundingBox
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collectors_3_robin_hart import (
    v7_2_t09_td_not_contained_tr as collector_module,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collectors_3_robin_hart.v7_2_t09_td_not_contained_tr import (
    aggregate_bounding_boxes,
    collect_supplementary_information_7_2_t09,
    find_page_number_from_page_element,
    generate_id_to_bounding_box_mapping,
    generate_id_to_mcids_mapping,
    generate_id_to_table_elements_mapping,
    render_id_to_bounding_box_mapping_json,
    render_table_json,
    retrieve_bounding_boxs_of_mcid,
)
from test.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collectors_3_robin_hart.render_rendered_table_content import render_rendered_table_content
from test.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.test_utils import generate_resource_path

# Define utility methods

def _make_struct(tag: str, children: list | None = None) -> pikepdf.Dictionary:
    element = pikepdf.Dictionary({"/S": pikepdf.Name(tag)})
    if children is not None:
        element["/K"] = pikepdf.Array(children)
    return element


def _tag_of(element: pikepdf.Object) -> str:
    tag = element.get("/S")
    assert tag is not None
    return str(tag)


def _open_corpus_table_element():
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t09-fail-a.pdf")
    pdf = pikepdf.open(pdf_path)
    table_element = pdf.Root.get("/StructTreeRoot").get("/K").get("/K")  # type: ignore
    if table_element is None:
        pdf.close()
        pytest.fail("Table element not found")
    return pdf, table_element


EXPECTED_CORPUS_TABLE_JSON = {
    "ID": 0,
    "tag": "/Table",
    "children": [
        {
            "ID": 1,
            "tag": "/THead",
            "children": [
                {
                    "ID": 2,
                    "tag": "/TR",
                    "children": [
                        {"ID": 3, "tag": "/TH"},
                        {"ID": 4, "tag": "/TH"},
                    ],
                }
            ],
        },
        {
            "ID": 5,
            "tag": "/TBody",
            "children": [
                {"ID": 6, "tag": "/TD"},
                {"ID": 7, "tag": "/TD"},
            ],
        },
        {
            "ID": 8,
            "tag": "/TBody",
            "children": [
                {
                    "ID": 9,
                    "tag": "/TR",
                    "children": [
                        {"ID": 10, "tag": "/TD"},
                        {"ID": 11, "tag": "/TD"},
                    ],
                }
            ],
        },
        {
            "ID": 12,
            "tag": "/TFoot",
            "children": [
                {
                    "ID": 13,
                    "tag": "/TR",
                    "children": [
                        {"ID": 14, "tag": "/TD"},
                        {"ID": 15, "tag": "/TD"},
                    ],
                }
            ],
        },
    ],
}


# Start of test cases

def test_find_page_number_returns_index_for_corpus_page_element():
    pdf, table_element = _open_corpus_table_element()
    with pdf:
        page_element = table_element.get("/Pg")
        assert page_element is not None
        assert find_page_number_from_page_element(page_element, pdf) == 0


def test_find_page_number_returns_correct_index_for_multi_page_pdf():
    pdf = pikepdf.new()
    pdf.add_blank_page()
    pdf.add_blank_page()

    assert find_page_number_from_page_element(pdf.pages[0].obj, pdf) == 0
    assert find_page_number_from_page_element(pdf.pages[1].obj, pdf) == 1


def test_find_page_number_raises_when_page_element_not_in_pdf():
    pdf = pikepdf.new()
    pdf.add_blank_page()
    orphan_page = pdf.make_indirect(pikepdf.Dictionary({"/Type": pikepdf.Name("/Page")}))

    with pytest.raises(Exception, match="Could not find page number"):
        find_page_number_from_page_element(orphan_page, pdf)


def test_generate_id_mapping_standard_table_hierarchy():
    td = _make_struct("/TD")
    th = _make_struct("/TH")
    tr = _make_struct("/TR", [td, th])
    tbody = _make_struct("/TBody", [tr])
    table = _make_struct("/Table", [tbody])

    mapping = generate_id_to_table_elements_mapping(table)

    assert len(mapping) == 5
    assert mapping[0] == table
    assert mapping[1] == tbody
    assert mapping[2] == tr
    assert mapping[3] == td
    assert mapping[4] == th    
    assert [_tag_of(mapping[i]) for i in range(5)] == [
        "/Table",
        "/TBody",
        "/TR",
        "/TD",
        "/TH",
    ]


def test_generate_id_mapping_td_directly_under_tbody():
    td1 = _make_struct("/TD")
    td2 = _make_struct("/TD")
    tbody = _make_struct("/TBody", [td1, td2])
    table = _make_struct("/Table", [tbody])

    mapping = generate_id_to_table_elements_mapping(table)

    assert len(mapping) == 4
    assert mapping[0] == table
    assert mapping[1] == tbody
    assert mapping[2] == td1
    assert mapping[3] == td2


def test_generate_id_mapping_skips_irrelevant_tags():
    span = _make_struct("/Span")
    td = _make_struct("/TD")
    tr = _make_struct("/TR", [td, span])
    tbody = _make_struct("/TBody", [tr])
    caption = _make_struct("/Caption")
    table = _make_struct("/Table", [caption, tbody])

    mapping = generate_id_to_table_elements_mapping(table)

    assert len(mapping) == 4
    assert mapping[0] == table
    assert mapping[1] == tbody
    assert mapping[2] == tr
    assert mapping[3] == td
    assert caption not in mapping.values()
    assert span not in mapping.values()


def test_generate_id_to_mcids_mapping_corpus_table_has_eight_keys():
    pdf, table_element = _open_corpus_table_element()
    with pdf:
        id_to_table_elements = generate_id_to_table_elements_mapping(table_element)
        id_to_mcids_mapping = generate_id_to_mcids_mapping(id_to_table_elements)
        # TODO: Check if the mapping is correct
        assert len(id_to_mcids_mapping) == 8


def test_aggregate_bounding_boxes_combines_boxes():
    box_a = BoundingBox(x0=10, top=20, x1=40, bottom=60)
    box_b = BoundingBox(x0=50, top=10, x1=70, bottom=35)

    result = aggregate_bounding_boxes([box_a, box_b])

    assert result == BoundingBox(x0=10, top=10, x1=70, bottom=60)


def test_retrieve_bounding_boxs_of_mcid_corpus_mcid_11():
    pdf, table_element = _open_corpus_table_element()
    with pdf:
        pdf_bytes = io.BytesIO()
        pdf.save(pdf_bytes)
        boxes = retrieve_bounding_boxs_of_mcid(11, 0, pdf_bytes)

    assert len(boxes) == 11
    aggregated = aggregate_bounding_boxes(boxes)
    assert aggregated.x0 == pytest.approx(142.8)
    assert aggregated.top == pytest.approx(59.992, abs=0.01)
    assert aggregated.x1 == pytest.approx(220.068, abs=0.01)
    assert aggregated.bottom == pytest.approx(71.992, abs=0.01)


def test_generate_id_to_bounding_box_mapping_corpus_table():
    pdf, table_element = _open_corpus_table_element()
    with pdf:
        pdf_snapshot = io.BytesIO()
        pdf.save(pdf_snapshot)

        id_to_table_elements = generate_id_to_table_elements_mapping(table_element)
        id_to_bbox_mapping = generate_id_to_bounding_box_mapping(
            id_to_table_elements, 0, pdf_snapshot
        )
    # TODO: Check if the mapping is correct
    print(id_to_bbox_mapping)
    render_rendered_table_content(id_to_bbox_mapping)

    assert len(id_to_bbox_mapping) == 8
    assert set(id_to_bbox_mapping.keys()) == {3, 4, 6, 7, 10, 11, 14, 15}
    for bbox in id_to_bbox_mapping.values():
        assert bbox.x1 > bbox.x0
        assert bbox.bottom > bbox.top


def test_render_id_to_bounding_box_mapping_json_rounds_to_three_decimal_places():
    mapping = {
        3: BoundingBox(x0=142.80001, top=59.99249, x1=220.06801, bottom=71.99201),
        11: BoundingBox(x0=1.23456, top=2.34567, x1=3.45678, bottom=4.56789),
    }

    actual = render_id_to_bounding_box_mapping_json(mapping)
    expected = (
        '{"3": {"x0": 142.8, "top": 59.992, "x1": 220.068, "bottom": 71.992}, '
        '"11": {"x0": 1.235, "top": 2.346, "x1": 3.457, "bottom": 4.568}}'
    )

    assert actual == expected


def test_render_table_json_corpus_table():
    pdf, table_element = _open_corpus_table_element()
    with pdf:
        id_to_table_elements = generate_id_to_table_elements_mapping(table_element)
        result = render_table_json(table_element, id_to_table_elements)

    print(json.dumps(json.loads(result), indent=4))

    assert json.loads(result) == EXPECTED_CORPUS_TABLE_JSON


def test_collect_supplementary_information_7_2_t09() :
    pdf, table_element = _open_corpus_table_element()
    with pdf:
        veraPdf_violation = VeraPdfViolation(
            rule_id="7.2-9",
            clause="7.2",
            test_number="9",
            description="description",
            context="root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](19 0 obj SEDocument Document)/K[0](30 0 obj SETable Table)/K[1](47 0 obj SETBody TBody)/K[0](34 0 obj SETD TD)",
            message="message",
        )
        supplementary_information = collect_supplementary_information_7_2_t09(veraPdf_violation, pdf, table_element['/K'][1]['/K'][0])
        #Todo: implement assertion