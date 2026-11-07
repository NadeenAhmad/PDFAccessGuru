

from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.resolve_context import _split_context_path


def test_split_context_path_edge_case_empty_string():
    expected = [""]
    actual = _split_context_path("")
    assert expected == actual


def test_split_context_path_edge_case_only_one_segment():
    expected = ["document[0]"]
    actual = _split_context_path("document[0]")
    assert expected == actual

def test_split_context_path_normal_case():
    context_path = "root/document[0]/pages[0](3 0 obj PDPage)" \
    "/contentStream[0](9 0 obj PDSemanticContentStream)/content[1]{mcid:0}/contentItem[0]{mcid:0}"
    expected = ["root", 
                "document[0]", 
                "pages[0](3 0 obj PDPage)", 
                "contentStream[0](9 0 obj PDSemanticContentStream)", 
                "content[1]{mcid:0}", "contentItem[0]{mcid:0}"
                ]
    actual = _split_context_path(context_path)
    assert expected == actual

def test_split_context_path_edge_case_http_between_brackets():
    context_path = "root/document[0]/metadata[0](2 0 obj PDMetadata)/XMPPackage[0]" \
    "/Properties[6](http://purl.org/dc/elements/1.1/ - dc:title)"
    expected = ["root", 
                "document[0]", 
                "metadata[0](2 0 obj PDMetadata)", 
                "XMPPackage[0]", 
                "Properties[6](http://purl.org/dc/elements/1.1/ - dc:title)"
                ]
    actual = _split_context_path(context_path)
    assert expected == actual

def test_split_context_path_edge_case_slashed_between_round_brackets():
    context_path = "root/document[0]/metadata[0]{a/a}"
    expected = ["root", 
                "document[0]", 
                "metadata[0]{a/a}",
                ]
    actual = _split_context_path(context_path)
    assert expected == actual