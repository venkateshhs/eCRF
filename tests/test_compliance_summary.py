from datetime import datetime, timezone

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


def _entry(entry_id, subject, visit, version, data, created_at=None):
    entry = {
        "id": entry_id,
        "subject_index": subject,
        "visit_index": visit,
        "group_index": 0 if subject < 2 else 1,
        "form_version": version,
        "data": {"Clinical": data},
        "skipped_required_flags": [],
    }
    if created_at is not None:
        entry["created_at"] = created_at
    return entry


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
        "recruited_subjects": 2,
        "active_subjects": 1,
        "dropped_subjects": 1,
        "dropped_data_retained": 1,
        "dropped_data_deleted": 0,
        "dropout_percent": 50,
    }
    assert summary["compliance"]["evaluable_subjects"] == 2
    assert summary["compliance"]["started_visits"] == 2
    assert summary["compliance"]["excluded_not_started_subjects"] == 1
    assert summary["compliance"]["excluded_not_started_visits"] == 0
    assert summary["compliance"]["expected_subject_visits"] == 4
    assert summary["compliance"]["data_compliance_percent"] == 62

    baseline = summary["visit_stats"][0]
    assert baseline["expected_subjects"] == 2
    assert baseline["completed_subjects"] == 2
    assert baseline["subject_completion_percent"] == 100
    assert baseline["data_compliance_percent"] == 100

    follow_up = summary["visit_stats"][1]
    assert follow_up["partial_subjects"] == 1
    assert follow_up["not_started_subjects"] == 1
    assert follow_up["data_compliance_percent"] == 25
    assert summary["subject_visit_status"] == {
        "complete": 2,
        "partial": 1,
        "not_started": 1,
    }
    assert summary["completeness_histogram"] == [
        {"range_start": 0, "range_end": 10, "subject_count": 0},
        {"range_start": 10, "range_end": 20, "subject_count": 0},
        {"range_start": 20, "range_end": 30, "subject_count": 0},
        {"range_start": 30, "range_end": 40, "subject_count": 0},
        {"range_start": 40, "range_end": 50, "subject_count": 0},
        {"range_start": 50, "range_end": 60, "subject_count": 1},
        {"range_start": 60, "range_end": 70, "subject_count": 0},
        {"range_start": 70, "range_end": 80, "subject_count": 1},
        {"range_start": 80, "range_end": 90, "subject_count": 0},
        {"range_start": 90, "range_end": 100, "subject_count": 0},
    ]
    assert summary["completeness_threshold_curve"][80] == {
        "threshold": 80,
        "subject_count": 0,
    }
    assert summary["completeness_threshold_curve"][100] == {
        "threshold": 100,
        "subject_count": 0,
    }

    group_b = summary["group_stats"][1]
    assert group_b["recruited_subjects"] == 1
    assert group_b["evaluable_subjects"] == 1
    assert group_b["data_compliance_percent"] == 50


def test_compliance_summary_handles_empty_study():
    summary = build_compliance_summary({}, [])
    assert summary["recruitment"]["recruited_subjects"] == 0
    assert summary["compliance"]["data_compliance_percent"] == 0
    assert summary["visit_stats"] == []
    assert len(summary["completeness_histogram"]) == 10
    assert summary["completeness_threshold_curve"][80]["subject_count"] == 0


def test_enrollment_monitoring_uses_first_qualifying_entry_and_includes_retained_dropouts():
    study_data = {
        "subjects": [
            {"id": "SUB-001", "group": "A", "status": "ACTIVE"},
            {"id": "SUB-002", "group": "A", "status": "ACTIVE"},
            {"id": "SUB-003", "group": "B", "status": "DROPPED_DATA_RETAINED"},
            {"id": "SUB-004", "group": "B", "status": "ACTIVE"},
            {"id": "SUB-005", "group": "B", "status": "ACTIVE"},
            {"id": "SUB-006", "group": "B", "status": "DROPPED_DATA_DELETED"},
        ],
        "groups": [{"name": "A"}, {"name": "B"}],
        "visits": [{"name": "Visit 1"}, {"name": "Visit 2"}],
        "selectedModels": [{"title": "Clinical", "fields": [{"id": "field"}]}],
        "assignments": [[[True, True], [True, True]]],
    }
    entries = [
        _entry(1, 0, 0, 1, {"field": "first"}, "2026-06-01T09:00:00Z"),
        _entry(2, 0, 1, 2, {"field": "later"}, "2026-06-15T09:00:00Z"),
        _entry(3, 1, 0, 1, {"field": "value"}, "2026-07-15T09:00:00Z"),
        _entry(4, 2, 0, 1, {"field": "retained"}, "2026-08-15T09:00:00Z"),
        _entry(5, 3, 0, 1, {"field": "value"}, "2026-09-15T09:00:00Z"),
        _entry(6, 5, 0, 1, {"field": "deleted"}, "2026-09-20T09:00:00Z"),
    ]
    entries[3]["group_index"] = 0
    entries[2]["created_at"] = "not-a-date"
    entries[2]["updated_at"] = "2026-08-15T09:00:00Z"

    summary = build_compliance_summary(
        study_data,
        entries,
        as_of=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    monitoring = summary["enrollment_monitoring"]

    assert monitoring["definition"] == "first_qualifying_data_entry"
    assert monitoring["enrolled_subjects"] == 4
    assert monitoring["configured_subjects"] == 5
    assert monitoring["first_enrollment_date"] == "2026-06-01"
    assert monitoring["last_enrollment_date"] == "2026-09-15"
    assert monitoring["timeline"][0]["total"] == 1
    assert monitoring["timeline"][-1]["total"] == 4
    assert monitoring["actual_by_group"] == [
        {"group_index": 0, "group_name": "A", "count": 2, "proportion_percent": 50},
        {"group_index": 1, "group_name": "B", "count": 2, "proportion_percent": 50},
    ]
    assert monitoring["pace"]["enrolled_last_30_days"] == 1
    assert monitoring["pace"]["enrolled_last_90_days"] == 3
    assert monitoring["pace"]["subjects_per_30_days_from_90_day_window"] == 1.0
    assert monitoring["forecast"] == {
        "available": True,
        "target_subjects": 5,
        "remaining_subjects": 1,
        "projected_completion_date": "2026-10-31",
        "monthly_pace_used": 1.0,
        "reason": None,
    }


def test_enrollment_forecast_uses_unrounded_rolling_rate():
    study_data = {
        "subjects": [{"id": f"SUB-{index:03d}", "group": "A", "status": "ACTIVE"} for index in range(1, 11)],
        "groups": [{"name": "A"}],
        "visits": [{"name": "Visit 1"}],
        "selectedModels": [{"title": "Clinical", "fields": [{"id": "field"}]}],
        "assignments": [[[True]]],
    }
    enrollment_dates = ["2026-06-01", "2026-07-15", "2026-08-01", "2026-09-01", "2026-09-15"]
    entries = [
        _entry(index, index - 1, 0, 1, {"field": "value"}, f"{entry_date}T09:00:00Z")
        for index, entry_date in enumerate(enrollment_dates, start=1)
    ]

    monitoring = build_compliance_summary(
        study_data, entries, as_of=datetime(2026, 10, 1, tzinfo=timezone.utc)
    )["enrollment_monitoring"]

    assert monitoring["pace"]["enrolled_last_90_days"] == 4
    assert monitoring["pace"]["subjects_per_30_days_from_90_day_window"] == 1.3
    assert monitoring["forecast"]["projected_completion_date"] == "2027-01-22"


def test_linear_enrollment_plan_compares_actuals_and_forecasts_to_plan_target():
    study_data = {
        "subjects": [{"id": f"SUB-{index:03d}", "group": "A", "status": "ACTIVE"} for index in range(1, 11)],
        "groups": [{"name": "A"}],
        "visits": [{"name": "Visit 1"}],
        "selectedModels": [{"title": "Clinical", "fields": [{"id": "field"}]}],
        "assignments": [[[True]]],
        "studySettings": {
            "enrollmentMonitoring": {"mode": "linear", "target_subjects": 12, "duration_months": 6}
        },
    }
    entries = [
        _entry(index, index - 1, 0, 1, {"field": "value"}, f"2026-0{index}-01T09:00:00Z")
        for index in range(1, 5)
    ]

    monitoring = build_compliance_summary(
        study_data, entries, as_of=datetime(2026, 4, 1, tzinfo=timezone.utc)
    )["enrollment_monitoring"]

    assert monitoring["plan"]["configured"] is True
    assert monitoring["plan"]["enabled"] is True
    assert monitoring["plan"]["start_date"] == "2026-01-01"
    assert monitoring["plan"]["planned_timeline"][-1] == {"date": "2026-07-01", "cumulative": 12}
    assert monitoring["planned_to_date"] == 6
    assert monitoring["variance_to_plan"] == -2
    assert monitoring["forecast"]["target_subjects"] == 12


def test_monthly_enrollment_plan_uses_incremental_targets():
    study_data = _study_data()
    study_data["studySettings"] = {
        "enrollmentMonitoring": {"mode": "monthly", "monthly_enrollments": [2, 3, 1]}
    }
    entries = [_entry(1, 0, 0, 1, {"age": 70}, "2026-01-15T09:00:00Z")]

    monitoring = build_compliance_summary(
        study_data, entries, as_of=datetime(2026, 3, 20, tzinfo=timezone.utc)
    )["enrollment_monitoring"]

    assert monitoring["plan"]["target_subjects"] == 6
    assert monitoring["plan"]["duration_months"] == 3
    assert monitoring["plan"]["planned_timeline"] == [
        {"date": "2026-01-15", "cumulative": 0},
        {"date": "2026-02-15", "cumulative": 2},
        {"date": "2026-03-15", "cumulative": 5},
        {"date": "2026-04-15", "cumulative": 6},
    ]
    assert monitoring["planned_to_date"] == 5
    assert monitoring["variance_to_plan"] == -4


def test_enrollment_plan_is_preserved_while_waiting_for_first_actual_entry():
    study_data = _study_data()
    study_data["studySettings"] = {
        "enrollmentMonitoring": {"mode": "linear", "target_subjects": 20, "duration_months": 8}
    }

    monitoring = build_compliance_summary(
        study_data, [], as_of=datetime(2026, 3, 20, tzinfo=timezone.utc)
    )["enrollment_monitoring"]

    assert monitoring["plan"] == {
        "configured": True,
        "enabled": False,
        "waiting_for_actual": True,
        "mode": "linear",
        "target_subjects": 20,
        "duration_months": 8,
        "monthly_enrollments": [],
        "start_date": None,
        "planned_timeline": [],
    }


def test_untouched_subjects_and_future_visits_are_excluded_from_scope():
    many_fields = [{"id": f"field-{index}"} for index in range(9)]
    study_data = {
        "subjects": [
            {"id": "SUB-001", "group": "A"},
            {"id": "SUB-002", "group": "A"},
        ],
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

    assert summary["compliance"]["evaluable_subjects"] == 1
    assert summary["compliance"]["started_visits"] == 1
    assert summary["compliance"]["excluded_not_started_subjects"] == 1
    assert summary["compliance"]["excluded_not_started_visits"] == 1
    assert len(summary["visit_stats"]) == 1
    assert summary["visit_stats"][0]["visit_name"] == "Short visit"
    assert summary["visit_stats"][0]["data_compliance_percent"] == 100
    assert summary["compliance"]["expected_subject_visits"] == 1
    assert summary["compliance"]["data_compliance_percent"] == 100


def test_recruitment_and_dropout_only_use_subjects_with_started_data():
    study_data = {
        "subjects": [
            {"id": "SUB-001", "status": "ACTIVE"},
            {"id": "SUB-002", "status": "DROPPED_DATA_RETAINED"},
            {"id": "SUB-003", "status": "ACTIVE"},
            {"id": "SUB-004", "status": "DROPPED_DATA_RETAINED"},
        ],
        "visits": [{"name": "Visit 1"}],
        "selectedModels": [{"title": "Form", "fields": [{"id": "field"}]}],
        "assignments": [[[True]]],
    }
    entries = [
        {
            "id": 1,
            "subject_index": 0,
            "visit_index": 0,
            "group_index": 0,
            "form_version": 1,
            "data": {"Form": {"field": "active data"}},
        },
        {
            "id": 2,
            "subject_index": 1,
            "visit_index": 0,
            "group_index": 0,
            "form_version": 1,
            "data": {"Form": {"field": "retained data"}},
        },
    ]

    summary = build_compliance_summary(study_data, entries)

    assert summary["recruitment"] == {
        "recruited_subjects": 2,
        "active_subjects": 1,
        "dropped_subjects": 1,
        "dropped_data_retained": 1,
        "dropped_data_deleted": 0,
        "dropout_percent": 50,
    }


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


def test_unstarted_cells_inside_the_active_subject_visit_scope_count_as_gaps():
    study_data = {
        "subjects": [{"id": "SUB-001"}, {"id": "SUB-002"}],
        "visits": [{"name": "Visit 1"}, {"name": "Visit 2"}],
        "selectedModels": [{"title": "Form", "fields": [{"id": "field"}]}],
        "assignments": [[[True], [True]]],
    }
    entries = [
        {
            "id": 1,
            "subject_index": 0,
            "visit_index": 0,
            "group_index": 0,
            "form_version": 1,
            "data": {"Form": {"field": "done"}},
        },
        {
            "id": 2,
            "subject_index": 1,
            "visit_index": 1,
            "group_index": 0,
            "form_version": 1,
            "data": {"Form": {"field": "done"}},
        },
    ]

    summary = build_compliance_summary(study_data, entries)

    assert summary["compliance"]["evaluable_subjects"] == 2
    assert summary["compliance"]["started_visits"] == 2
    assert summary["compliance"]["expected_subject_visits"] == 4
    assert summary["compliance"]["data_compliance_percent"] == 50
    assert summary["subject_visit_status"] == {
        "complete": 2,
        "partial": 0,
        "not_started": 2,
    }
