from eCRF_backend.entry_progress import calculate_overall_entry_progress


def make_study(section_count=10, fields_per_section=2):
    sections = []
    assignments = []
    for section_index in range(section_count):
        sections.append(
            {
                "id": f"section-{section_index + 1}",
                "title": f"Section {section_index + 1}",
                "fields": [
                    {
                        "id": f"section-{section_index + 1}-field-{field_index + 1}",
                        "label": f"Field {field_index + 1}",
                        "type": "text",
                    }
                    for field_index in range(fields_per_section)
                ],
            }
        )
        assignments.append([[True]])
    return {
        "selectedModels": sections,
        "assignments": assignments,
        "forms": [],
    }


def fill_sections(study_data, section_count):
    data = {}
    for section in study_data["selectedModels"][:section_count]:
        data[section["title"]] = {
            field["id"]: f"value-for-{field['id']}"
            for field in section["fields"]
        }
    return data


def empty_skips(study_data):
    return [
        [False for _field in section["fields"]]
        for section in study_data["selectedModels"]
    ]


def test_two_complete_shared_sections_do_not_mark_ten_section_visit_complete():
    study_data = make_study(section_count=10, fields_per_section=2)

    progress = calculate_overall_entry_progress(
        study_data=study_data,
        data=fill_sections(study_data, section_count=2),
        skipped_required_flags=empty_skips(study_data),
        visit_index=0,
        group_index=0,
    )

    assert progress == {
        "progress_status": "partial",
        "progress_percentage": 20,
        "progress_completed": 4,
        "progress_total": 20,
        "progress_skipped": 0,
    }


def test_all_assigned_sections_complete_marks_overall_visit_complete():
    study_data = make_study(section_count=10, fields_per_section=2)

    progress = calculate_overall_entry_progress(
        study_data=study_data,
        data=fill_sections(study_data, section_count=10),
        skipped_required_flags=empty_skips(study_data),
        visit_index=0,
        group_index=0,
    )

    assert progress["progress_percentage"] == 100
    assert progress["progress_status"] == "complete"
    assert progress["progress_completed"] == progress["progress_total"] == 20


def test_unassigned_sections_are_not_in_overall_denominator():
    study_data = make_study(section_count=10, fields_per_section=1)
    for section_index in range(5, 10):
        study_data["assignments"][section_index][0][0] = False

    progress = calculate_overall_entry_progress(
        study_data=study_data,
        data=fill_sections(study_data, section_count=2),
        skipped_required_flags=empty_skips(study_data),
        visit_index=0,
        group_index=0,
    )

    assert progress["progress_percentage"] == 40
    assert progress["progress_completed"] == 2
    assert progress["progress_total"] == 5


def test_hidden_and_empty_readonly_fields_do_not_reduce_progress():
    study_data = make_study(section_count=1, fields_per_section=1)
    controller = study_data["selectedModels"][0]["fields"][0]
    controller["id"] = "show-detail"
    controller["type"] = "radio"

    study_data["selectedModels"][0]["fields"].extend(
        [
            {
                "id": "conditional-detail",
                "label": "Conditional detail",
                "type": "text",
                "constraints": {
                    "visibilityLogic": {
                        "match": "all",
                        "action": "show",
                        "rules": [
                            {
                                "sourceFieldKey": "show-detail",
                                "operator": "eq",
                                "value": "Yes",
                            }
                        ],
                    }
                },
            },
            {
                "id": "calculated-result",
                "label": "Calculated result",
                "type": "number",
                "constraints": {"readonly": True},
            },
        ]
    )
    skips = empty_skips(study_data)

    progress = calculate_overall_entry_progress(
        study_data=study_data,
        data={"Section 1": {"show-detail": "No"}},
        skipped_required_flags=skips,
        visit_index=0,
        group_index=0,
    )

    assert progress["progress_percentage"] == 100
    assert progress["progress_completed"] == progress["progress_total"] == 1


def test_skipped_field_is_not_counted_as_completed_and_sets_skipped_status():
    study_data = make_study(section_count=1, fields_per_section=2)
    skips = empty_skips(study_data)
    skips[0][1] = True

    progress = calculate_overall_entry_progress(
        study_data=study_data,
        data=fill_sections(study_data, section_count=1),
        skipped_required_flags=skips,
        visit_index=0,
        group_index=0,
    )

    assert progress["progress_status"] == "skipped"
    assert progress["progress_percentage"] == 50
    assert progress["progress_completed"] == 1
    assert progress["progress_total"] == 2
    assert progress["progress_skipped"] == 1


def test_saved_false_checkbox_is_a_completed_no_answer():
    study_data = make_study(section_count=1, fields_per_section=1)
    checkbox = study_data["selectedModels"][0]["fields"][0]
    checkbox["type"] = "checkbox"

    progress = calculate_overall_entry_progress(
        study_data=study_data,
        data={"Section 1": {checkbox["id"]: False}},
        skipped_required_flags=empty_skips(study_data),
        visit_index=0,
        group_index=0,
    )

    assert progress["progress_percentage"] == 100
    assert progress["progress_completed"] == progress["progress_total"] == 1


def test_missing_checkbox_answer_remains_incomplete():
    study_data = make_study(section_count=1, fields_per_section=1)
    study_data["selectedModels"][0]["fields"][0]["type"] = "checkbox"

    progress = calculate_overall_entry_progress(
        study_data=study_data,
        data={},
        skipped_required_flags=empty_skips(study_data),
        visit_index=0,
        group_index=0,
    )

    assert progress["progress_percentage"] == 0
    assert progress["progress_completed"] == 0
    assert progress["progress_total"] == 1


def test_unchecked_readonly_checkbox_does_not_reduce_progress():
    study_data = make_study(section_count=1, fields_per_section=1)
    checkbox = study_data["selectedModels"][0]["fields"][0]
    checkbox["type"] = "checkbox"
    checkbox["constraints"] = {"readonly": True}

    progress = calculate_overall_entry_progress(
        study_data=study_data,
        data={"Section 1": {checkbox["id"]: False}},
        skipped_required_flags=empty_skips(study_data),
        visit_index=0,
        group_index=0,
    )

    assert progress["progress_total"] == 0
    assert progress["progress_completed"] == 0
