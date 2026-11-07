from pdfaccessguru.script_evaluate_folder_and_generate_statistics import _build_final_statistics


def _entry(
    duration: float,
    before: int | None,
    after: int | None,
    by_name_before: dict[str, int] | None = None,
    by_name_after: dict[str, int] | None = None,
) -> dict:
    result = {
        "total_duration_seconds": duration,
        "violations_before_correction": before,
        "violations_after_correction": after,
    }
    if by_name_before is not None:
        result["violations_by_name_before"] = by_name_before
    if by_name_after is not None:
        result["violations_by_name_after"] = by_name_after
    return result


def test_build_final_statistics_sums_overlapping_violation_names():
    statistics = _build_final_statistics(
        {
            "a.pdf": _entry(
                1.0,
                7,
                3,
                {"id-schema-missing": 1, "missing-title": 2, "untagged": 4},
                {"id-schema-missing": 1, "untagged": 2},
            ),
            "b.pdf": _entry(
                2.0,
                10,
                7,
                {"id-schema-missing": 3, "missing-title": 1, "untagged": 6},
                {"id-schema-missing": 1, "untagged": 6},
            ),
        }
    )

    assert statistics["global"] == {
        "violations_before_correction": 17,
        "violations_after_correction": 10,
        "corrected": 7,
        "correction_rate": 0.4118,
    }
    assert statistics["violations"] == [
        {
            "name": "untagged",
            "violations_before_correction": 10,
            "violations_after_correction": 8,
            "corrected": 2,
            "correction_rate": 0.2,
        },
        {
            "name": "id-schema-missing",
            "violations_before_correction": 4,
            "violations_after_correction": 2,
            "corrected": 2,
            "correction_rate": 0.5,
        },
        {
            "name": "missing-title",
            "violations_before_correction": 3,
            "violations_after_correction": 0,
            "corrected": 3,
            "correction_rate": 1.0,
        },
    ]
    assert statistics["pdfs"] == {
        "a.pdf": {
            "total_duration_seconds": 1.0,
            "violations_before_correction": 7,
            "violations_after_correction": 3,
            "violations": [
                {
                    "name": "id-schema-missing",
                    "violations_before_correction": 1,
                    "violations_after_correction": 1,
                    "corrected": 0,
                    "correction_rate": 0.0,
                },
                {
                    "name": "untagged",
                    "violations_before_correction": 4,
                    "violations_after_correction": 2,
                    "corrected": 2,
                    "correction_rate": 0.5,
                },
                {
                    "name": "missing-title",
                    "violations_before_correction": 2,
                    "violations_after_correction": 0,
                    "corrected": 2,
                    "correction_rate": 1.0,
                },
            ],
        },
        "b.pdf": {
            "total_duration_seconds": 2.0,
            "violations_before_correction": 10,
            "violations_after_correction": 7,
            "violations": [
                {
                    "name": "untagged",
                    "violations_before_correction": 6,
                    "violations_after_correction": 6,
                    "corrected": 0,
                    "correction_rate": 0.0,
                },
                {
                    "name": "id-schema-missing",
                    "violations_before_correction": 3,
                    "violations_after_correction": 1,
                    "corrected": 2,
                    "correction_rate": 0.6667,
                },
                {
                    "name": "missing-title",
                    "violations_before_correction": 1,
                    "violations_after_correction": 0,
                    "corrected": 1,
                    "correction_rate": 1.0,
                },
            ],
        },
    }


def test_build_final_statistics_sorts_worst_rate_then_remaining_then_name():
    statistics = _build_final_statistics(
        {
            "only.pdf": _entry(
                1.0,
                18,
                18,
                {
                    "keep-many": 10,
                    "keep-few": 4,
                    "beta-zero": 2,
                    "alpha-zero": 2,
                },
                {
                    "keep-many": 10,
                    "keep-few": 4,
                    "beta-zero": 2,
                    "alpha-zero": 2,
                },
            ),
        }
    )

    expected_order = [
        "keep-many",
        "keep-few",
        "alpha-zero",
        "beta-zero",
    ]
    assert [row["name"] for row in statistics["violations"]] == expected_order
    assert [row["name"] for row in statistics["pdfs"]["only.pdf"]["violations"]] == expected_order


def test_build_final_statistics_ignores_failed_pdfs_for_rates():
    statistics = _build_final_statistics(
        {
            "ok.pdf": _entry(
                1.0,
                4,
                1,
                {"id-schema-missing": 4},
                {"id-schema-missing": 1},
            ),
            "failed.pdf": _entry(5.0, None, None),
            "timeout.pdf": _entry(300.0, None, None),
        }
    )

    assert statistics["global"] == {
        "violations_before_correction": 4,
        "violations_after_correction": 1,
        "corrected": 3,
        "correction_rate": 0.75,
    }
    assert statistics["violations"] == [
        {
            "name": "id-schema-missing",
            "violations_before_correction": 4,
            "violations_after_correction": 1,
            "corrected": 3,
            "correction_rate": 0.75,
        }
    ]
    assert statistics["pdfs"]["failed.pdf"] == {
        "total_duration_seconds": 5.0,
        "violations_before_correction": None,
        "violations_after_correction": None,
        "violations": [],
    }
    assert statistics["pdfs"]["timeout.pdf"]["violations_before_correction"] is None
    assert statistics["pdfs"]["timeout.pdf"]["violations"] == []
    assert statistics["pdfs"]["ok.pdf"]["violations"] == [
        {
            "name": "id-schema-missing",
            "violations_before_correction": 4,
            "violations_after_correction": 1,
            "corrected": 3,
            "correction_rate": 0.75,
        }
    ]


def test_build_final_statistics_all_failed_and_zero_before_have_zero_rate():
    all_failed = _build_final_statistics(
        {
            "failed.pdf": _entry(1.0, None, None),
            "timeout.pdf": _entry(2.0, None, None),
        }
    )
    assert all_failed["global"] == {
        "violations_before_correction": 0,
        "violations_after_correction": 0,
        "corrected": 0,
        "correction_rate": 0.0,
    }
    assert all_failed["violations"] == []
    assert set(all_failed["pdfs"]) == {"failed.pdf", "timeout.pdf"}
    assert all_failed["pdfs"]["failed.pdf"]["violations"] == []

    zero_before = _build_final_statistics(
        {"clean.pdf": _entry(1.0, 0, 0, {}, {})}
    )
    assert zero_before["global"]["correction_rate"] == 0.0
    assert zero_before["violations"] == []
    assert zero_before["pdfs"]["clean.pdf"]["violations_before_correction"] == 0
    assert zero_before["pdfs"]["clean.pdf"]["violations"] == []
