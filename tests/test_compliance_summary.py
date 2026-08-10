from eCRF_backend.compliance import build_compliance_summary


def _study_data():
    return {
        "subjects": [
            {"id": "SUB-001", "group": "A"},
            {"id": "SUB-002", "group": "A"},
            {"id": "SUB-003", "group": "B", "status": "DROPPED_DATA_RETAINED"},
            {"id": "SUB-004", "group": "B", "status": "DROPPED_DATA_DELETED"},
        ],
        "groups": [{"name": "A"}, {"name": "B"}],
        "visits": [{"name": "Baseline"}, {"name": "Follow-up"}],
        "selectedModels": [{
            "title": "Clinical",
            "fields": [{"id": "name"}, {"id": "age", "type": "number"}],
        }],
        "assignments": [[[True, True], [True, True]]],
    }


def _entry(entry_id, subject, visit, version, data):
    return {
        "id": entry_id,
        "subject_index": subject,
        "visit_index": visit,
        "group_index": 0 if subject < 2 else 1,
        "form_version": version,
        "data": {"Clinical": data},
        "skipped_required_flags": [],
    }


def test_compliance_summary_covers_recruitment_visits_groups_and_latest_version():
    summary = build_compliance_summary(
        _study_data(),
        [
            _entry(1, 0, 0, 1, {"name": "Old", "age": 20}),
            _entry(2, 0, 0, 2, {"name": "Latest", "age": 21}),
            _entry(3, 0, 1, 2, {"name": "Partial"}),
            _entry(4, 2, 0, 2, {"name": "Retained", "age": 40}),
            _entry(5, 3, 0, 2, {"name": "Deleted", "age": 50}),
        ],
    )

    assert summary["recruitment"] == {
        "recruited_subjects": 4,
        "active_subjects": 2,
        "dropped_subjects": 2,
        "dropped_data_retained": 1,
        "dropped_data_deleted": 1,
        "dropout_percent": 50,
    }
    assert summary["compliance"]["evaluable_subjects"] == 3
    assert summary["compliance"]["expected_subject_visits"] == 6
    assert summary["compliance"]["data_compliance_percent"] == 42

    baseline = summary["visit_stats"][0]
    assert baseline["expected_subjects"] == 3
    assert baseline["completed_subjects"] == 2
    assert baseline["subject_completion_percent"] == 67
    assert baseline["data_compliance_percent"] == 67

    follow_up = summary["visit_stats"][1]
    assert follow_up["partial_subjects"] == 1
    assert follow_up["not_started_subjects"] == 2
    assert summary["subject_visit_status"] == {
        "complete": 2,
        "partial": 1,
        "not_started": 3,
    }

    group_b = summary["group_stats"][1]
    assert group_b["recruited_subjects"] == 2
    assert group_b["evaluable_subjects"] == 1
    assert group_b["data_compliance_percent"] == 50


def test_compliance_summary_handles_empty_study():
    summary = build_compliance_summary({}, [])
    assert summary["recruitment"]["recruited_subjects"] == 0
    assert summary["compliance"]["data_compliance_percent"] == 0
    assert summary["visit_stats"] == []


def test_each_subject_visit_has_equal_weight_regardless_of_assigned_field_count():
    many_fields = [{"id": f"field-{index}"} for index in range(9)]
    study_data = {
        "subjects": [{"id": "SUB-001", "group": "A"}],
        "groups": [{"name": "A"}],
        "visits": [{"name": "Short visit"}, {"name": "Long visit"}],
        "selectedModels": [
            {"title": "Short", "fields": [{"id": "done"}]},
            {"title": "Long", "fields": many_fields},
        ],
        "assignments": [
            [[True], [False]],
            [[False], [True]],
        ],
    }
    entries = [{
        "id": 1,
        "subject_index": 0,
        "visit_index": 0,
        "group_index": 0,
        "form_version": 1,
        "data": {"Short": {"done": "yes"}},
        "skipped_required_flags": [],
    }]

    summary = build_compliance_summary(study_data, entries)

    assert summary["visit_stats"][0]["data_compliance_percent"] == 100
    assert summary["visit_stats"][1]["data_compliance_percent"] == 0
    assert summary["compliance"]["expected_subject_visits"] == 2
    assert summary["compliance"]["data_compliance_percent"] == 50


def test_saved_entry_progress_is_used_to_match_add_data_matrix():
    study_data = {
        "subjects": [{"id": "SUB-001", "group": "A"}],
        "groups": [{"name": "A"}],
        "visits": [{"name": "Visit 1"}],
        "selectedModels": [{"title": "Form", "fields": [{"id": "field"}]}],
        "assignments": [[[True]]],
    }
    entries = [{
        "id": 1,
        "subject_index": 0,
        "visit_index": 0,
        "group_index": 0,
        "form_version": 1,
        "data": {},
        "progress_status": "partial",
        "progress_percentage": 65,
        "progress_total": 20,
        "progress_skipped": 1,
    }]

    summary = build_compliance_summary(study_data, entries)

    assert summary["compliance"]["data_compliance_percent"] == 65
    assert summary["visit_stats"][0]["data_compliance_percent"] == 65
    assert summary["visit_stats"][0]["skipped_fields"] == 1
    assert summary["subject_visit_status"]["partial"] == 1
