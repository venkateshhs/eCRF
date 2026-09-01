from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .entry_progress import calculate_overall_entry_progress


ACTIVE = "ACTIVE"
DELETED = "DROPPED_DATA_DELETED"


def _label(item: Any, fallback: str) -> str:
    if isinstance(item, dict):
        return str(item.get("name") or item.get("title") or item.get("id") or fallback)
    text = str(item or "").strip()
    return text or fallback


def _status(subject: Any) -> str:
    if not isinstance(subject, dict):
        return ACTIVE
    return str(subject.get("status") or ACTIVE).strip().upper()


def _group_index(subject: Dict[str, Any], groups: List[Any]) -> int:
    wanted = str((subject or {}).get("group") or "").strip().lower()
    if wanted:
        for index, group in enumerate(groups):
            if _label(group, "").strip().lower() == wanted:
                return index
    return 0


def _entry_sort_key(entry: Dict[str, Any]) -> Tuple[int, str, int]:
    try:
        version = int(entry.get("form_version") or 0)
    except (TypeError, ValueError):
        version = 0
    timestamp = str(entry.get("updated_at") or entry.get("created_at") or "")
    try:
        entry_id = int(entry.get("id") or 0)
    except (TypeError, ValueError):
        entry_id = 0
    return version, timestamp, entry_id


def _latest_entries(entries: List[Dict[str, Any]]) -> Dict[Tuple[int, int, int], Dict[str, Any]]:
    latest: Dict[Tuple[int, int, int], Dict[str, Any]] = {}
    for entry in entries or []:
        try:
            key = (
                int(entry.get("subject_index")),
                int(entry.get("visit_index")),
                int(entry.get("group_index")),
            )
        except (TypeError, ValueError):
            continue
        if key not in latest or _entry_sort_key(entry) > _entry_sort_key(latest[key]):
            latest[key] = entry
    return latest


def _percent(numerator: int, denominator: int) -> int:
    return int(round((numerator / denominator) * 100)) if denominator else 0


def build_compliance_summary(
    study_data: Dict[str, Any],
    entries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build current-study recruitment and field-level compliance statistics."""
    study_data = study_data or {}
    subjects = study_data.get("subjects") if isinstance(study_data.get("subjects"), list) else []
    visits = study_data.get("visits") if isinstance(study_data.get("visits"), list) else []
    groups = study_data.get("groups") if isinstance(study_data.get("groups"), list) else []
    latest = _latest_entries(entries or [])

    statuses = [_status(subject) for subject in subjects]
    visit_stats = [
        {
            "visit_index": index,
            "visit_name": _label(visit, f"Visit {index + 1}"),
            "expected_subjects": 0,
            "completed_subjects": 0,
            "partial_subjects": 0,
            "not_started_subjects": 0,
            "progress_percent_sum": 0,
            "skipped_fields": 0,
        }
        for index, visit in enumerate(visits)
    ]
    group_stats: Dict[int, Dict[str, Any]] = {
        index: {
            "group_index": index,
            "group_name": _label(group, f"Group {index + 1}"),
            "recruited_subjects": 0,
            "evaluable_subjects": 0,
            "expected_subject_visits": 0,
            "progress_percent_sum": 0,
        }
        for index, group in enumerate(groups)
    }
    if not group_stats:
        group_stats[0] = {
            "group_index": 0,
            "group_name": "Unassigned",
            "recruited_subjects": 0,
            "evaluable_subjects": 0,
            "expected_subject_visits": 0,
            "progress_percent_sum": 0,
        }

    candidate_rows: List[Dict[str, Any]] = []
    started_subjects = set()
    started_visits = set()
    subject_groups: Dict[int, int] = {}

    for subject_index, subject in enumerate(subjects):
        subject_obj = subject if isinstance(subject, dict) else {}
        status_value = statuses[subject_index]
        group_index = _group_index(subject_obj, groups)
        if group_index not in group_stats:
            group_index = 0
        if status_value == DELETED:
            continue

        subject_groups[subject_index] = group_index

        for visit_index in range(len(visit_stats)):
            entry = latest.get((subject_index, visit_index, group_index)) or {}
            calculated_progress = calculate_overall_entry_progress(
                study_data=study_data,
                data=entry.get("data") or {},
                skipped_required_flags=entry.get("skipped_required_flags") or [],
                visit_index=visit_index,
                group_index=group_index,
            )
            expected = int(entry.get("progress_total") or calculated_progress.get("progress_total") or 0)
            if expected <= 0:
                continue
            stored_percent = entry.get("progress_percentage")
            progress_percent = int(
                calculated_progress.get("progress_percentage") or 0
                if stored_percent is None
                else stored_percent
            )
            progress_percent = max(0, min(100, progress_percent))
            skipped = int(
                calculated_progress.get("progress_skipped") or 0
                if entry.get("progress_skipped") is None
                else entry.get("progress_skipped")
            )
            progress_status = str(
                entry.get("progress_status")
                or calculated_progress.get("progress_status")
                or "none"
            ).strip().lower()

            candidate_rows.append(
                {
                    "subject_index": subject_index,
                    "visit_index": visit_index,
                    "group_index": group_index,
                    "progress_percent": progress_percent,
                    "skipped": skipped,
                    "progress_status": progress_status,
                }
            )
            if (
                progress_status in {"complete", "partial", "skipped"}
                or progress_percent > 0
                or skipped > 0
            ):
                started_subjects.add(subject_index)
                started_visits.add(visit_index)

    for subject_index in started_subjects:
        group_stat = group_stats[subject_groups[subject_index]]
        group_stat["recruited_subjects"] += 1
        group_stat["evaluable_subjects"] += 1

    recruited_statuses = [statuses[index] for index in started_subjects]
    active = sum(1 for value in recruited_statuses if value == ACTIVE)
    retained = sum(1 for value in recruited_statuses if value == "DROPPED_DATA_RETAINED")
    deleted = sum(1 for value in recruited_statuses if value == DELETED)
    dropped = sum(
        1
        for value in recruited_statuses
        if value.startswith("DROPPED_") or value.startswith("DROPOUT_")
    )

    subject_totals: Dict[int, Dict[str, int]] = {}
    distribution = {"complete": 0, "partial": 0, "not_started": 0}
    overall_progress_percent_sum = 0

    for row in candidate_rows:
        subject_index = row["subject_index"]
        visit_index = row["visit_index"]
        if subject_index not in started_subjects or visit_index not in started_visits:
            continue

        group_index = row["group_index"]
        progress_percent = row["progress_percent"]
        skipped = row["skipped"]
        progress_status = row["progress_status"]
        visit_stat = visit_stats[visit_index]
        totals = subject_totals.setdefault(
            subject_index,
            {"completed_visits": 0, "expected_visits": 0, "progress_percent_sum": 0},
        )

        visit_stat["expected_subjects"] += 1
        visit_stat["progress_percent_sum"] += progress_percent
        visit_stat["skipped_fields"] += skipped
        group_stats[group_index]["expected_subject_visits"] += 1
        group_stats[group_index]["progress_percent_sum"] += progress_percent
        totals["expected_visits"] += 1
        totals["progress_percent_sum"] += progress_percent
        overall_progress_percent_sum += progress_percent

        if progress_status == "complete" or (progress_percent >= 100 and skipped == 0):
            visit_stat["completed_subjects"] += 1
            totals["completed_visits"] += 1
            distribution["complete"] += 1
        elif (
            progress_status in {"partial", "skipped"}
            or progress_percent > 0
            or skipped > 0
        ):
            visit_stat["partial_subjects"] += 1
            distribution["partial"] += 1
        else:
            visit_stat["not_started_subjects"] += 1
            distribution["not_started"] += 1

    visit_stats = [
        stat for stat in visit_stats if stat["visit_index"] in started_visits
    ]
    for stat in visit_stats:
        stat["subject_completion_percent"] = _percent(
            stat["completed_subjects"], stat["expected_subjects"]
        )
        stat["data_compliance_percent"] = _percent(
            stat["progress_percent_sum"], stat["expected_subjects"] * 100
        )
        stat.pop("progress_percent_sum", None)

    group_rows = []
    for stat in group_stats.values():
        stat["data_compliance_percent"] = _percent(
            stat["progress_percent_sum"], stat["expected_subject_visits"] * 100
        )
        stat.pop("progress_percent_sum", None)
        group_rows.append(stat)

    expected_subject_visits = sum(row["expected_subjects"] for row in visit_stats)
    evaluable_subjects = len(started_subjects)
    subjects_with_expected_data = sum(
        1 for row in subject_totals.values() if row["expected_visits"] > 0
    )
    completed_subjects = sum(
        1
        for row in subject_totals.values()
        if row["expected_visits"] > 0 and row["completed_visits"] >= row["expected_visits"]
    )
    subject_completeness = [
        _percent(row["progress_percent_sum"], row["expected_visits"] * 100)
        for row in subject_totals.values()
        if row["expected_visits"] > 0
    ]
    completeness_histogram = []
    for lower_bound in range(0, 100, 10):
        upper_bound = lower_bound + 10
        completeness_histogram.append(
            {
                "range_start": lower_bound,
                "range_end": upper_bound,
                "subject_count": sum(
                    1
                    for value in subject_completeness
                    if lower_bound <= value < upper_bound
                    or (upper_bound == 100 and value == 100)
                ),
            }
        )
    completeness_threshold_curve = [
        {
            "threshold": threshold,
            "subject_count": sum(1 for value in subject_completeness if value >= threshold),
        }
        for threshold in range(101)
    ]

    return {
        "recruitment": {
            "recruited_subjects": len(started_subjects),
            "active_subjects": active,
            "dropped_subjects": dropped,
            "dropped_data_retained": retained,
            "dropped_data_deleted": deleted,
            "dropout_percent": _percent(dropped, len(started_subjects)),
        },
        "compliance": {
            "evaluable_subjects": evaluable_subjects,
            "started_visits": len(started_visits),
            "excluded_not_started_subjects": sum(
                1 for value in statuses if value != DELETED
            ) - evaluable_subjects,
            "excluded_not_started_visits": len(visits) - len(started_visits),
            "subjects_with_expected_data": subjects_with_expected_data,
            "completed_subjects": completed_subjects,
            "subject_completion_percent": _percent(completed_subjects, subjects_with_expected_data),
            "expected_subject_visits": expected_subject_visits,
            "data_compliance_percent": _percent(overall_progress_percent_sum, expected_subject_visits * 100),
            "skipped_fields": sum(row["skipped_fields"] for row in visit_stats),
        },
        "subject_visit_status": distribution,
        "completeness_histogram": completeness_histogram,
        "completeness_threshold_curve": completeness_threshold_curve,
        "visit_stats": visit_stats,
        "group_stats": group_rows,
    }
