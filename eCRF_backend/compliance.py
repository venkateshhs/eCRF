from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from math import ceil
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


def _entry_progress(
    study_data: Dict[str, Any],
    entry: Dict[str, Any],
    visit_index: int,
    group_index: int,
) -> Tuple[int, int, int, str]:
    calculated = calculate_overall_entry_progress(
        study_data=study_data,
        data=entry.get("data") or {},
        skipped_required_flags=entry.get("skipped_required_flags") or [],
        visit_index=visit_index,
        group_index=group_index,
    )
    expected = int(entry.get("progress_total") or calculated.get("progress_total") or 0)
    stored_percent = entry.get("progress_percentage")
    progress_percent = int(
        calculated.get("progress_percentage") or 0
        if stored_percent is None
        else stored_percent
    )
    progress_percent = max(0, min(100, progress_percent))
    skipped = int(
        calculated.get("progress_skipped") or 0
        if entry.get("progress_skipped") is None
        else entry.get("progress_skipped")
    )
    progress_status = str(
        entry.get("progress_status")
        or calculated.get("progress_status")
        or "none"
    ).strip().lower()
    return expected, progress_percent, skipped, progress_status


def _is_started_entry(progress_percent: int, skipped: int, progress_status: str) -> bool:
    return (
        progress_status in {"complete", "partial", "skipped"}
        or progress_percent > 0
        or skipped > 0
    )


def _parse_entry_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    month_lengths = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(value.day, month_lengths[month - 1]))


def _enrollment_plan(study_data: Dict[str, Any], first_date: date | None) -> Dict[str, Any]:
    settings = study_data.get("studySettings") or study_data.get("study_settings") or {}
    raw = settings.get("enrollmentMonitoring") or settings.get("enrollment_monitoring") or {}
    mode = str(raw.get("mode") or "none").strip().lower()
    if mode not in {"linear", "monthly"}:
        return {"configured": False, "enabled": False, "mode": "none", "planned_timeline": []}

    try:
        target_subjects = int(raw.get("target_subjects") or 0)
    except (TypeError, ValueError):
        target_subjects = 0
    try:
        duration_months = int(raw.get("duration_months") or 0)
    except (TypeError, ValueError):
        duration_months = 0

    monthly = []
    for value in raw.get("monthly_enrollments") or []:
        try:
            parsed = max(0, int(value))
        except (TypeError, ValueError):
            continue
        monthly.append(parsed)

    valid_linear = mode == "linear" and target_subjects > 0 and duration_months > 0
    valid_monthly = mode == "monthly" and bool(monthly) and sum(monthly) > 0
    if valid_monthly:
        target_subjects = sum(monthly)
        duration_months = len(monthly)
    elif not valid_linear:
        return {"configured": False, "enabled": False, "mode": "none", "planned_timeline": []}

    plan = {
        "configured": True,
        "enabled": first_date is not None,
        "waiting_for_actual": first_date is None,
        "mode": mode,
        "target_subjects": target_subjects,
        "duration_months": duration_months,
        "monthly_enrollments": monthly,
        "start_date": first_date.isoformat() if first_date else None,
        "planned_timeline": [],
    }
    if first_date is None:
        return plan

    planned_timeline = [{"date": first_date.isoformat(), "cumulative": 0}]
    if mode == "linear":
        planned_timeline.extend(
            {
                "date": _add_months(first_date, month).isoformat(),
                "cumulative": int(round(target_subjects * month / duration_months)),
            }
            for month in range(1, duration_months + 1)
        )
    else:
        cumulative = 0
        for month, value in enumerate(monthly, start=1):
            cumulative += value
            planned_timeline.append({
                "date": _add_months(first_date, month).isoformat(),
                "cumulative": cumulative,
            })
    plan["planned_timeline"] = planned_timeline

    return plan


def _planned_enrollment_on(plan: Dict[str, Any], as_of_date: date) -> int | None:
    points = plan.get("planned_timeline") or []
    if not points:
        return None
    dated_points = [
        (date.fromisoformat(point["date"]), int(point.get("cumulative") or 0))
        for point in points
    ]
    if as_of_date <= dated_points[0][0]:
        return dated_points[0][1]
    if as_of_date >= dated_points[-1][0]:
        return dated_points[-1][1]
    for (left_date, left_value), (right_date, right_value) in zip(dated_points, dated_points[1:]):
        if left_date <= as_of_date <= right_date:
            span = (right_date - left_date).days
            progress = (as_of_date - left_date).days / span if span else 1
            return int(round(left_value + (right_value - left_value) * progress))
    return dated_points[-1][1]


def _build_enrollment_monitoring(
    study_data: Dict[str, Any],
    entries: List[Dict[str, Any]],
    statuses: List[str],
    groups: List[Any],
    as_of: datetime | None,
) -> Dict[str, Any]:
    subjects = study_data.get("subjects") if isinstance(study_data.get("subjects"), list) else []
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    as_of_date = now.date()

    group_rows = [
        {"group_index": index, "group_name": _label(group, f"Group {index + 1}")}
        for index, group in enumerate(groups)
    ]
    if not group_rows:
        group_rows = [{"group_index": 0, "group_name": "Unassigned"}]

    earliest_by_subject: Dict[int, Dict[str, Any]] = {}
    qualifying_without_date = set()
    for entry in entries or []:
        try:
            subject_index = int(entry.get("subject_index"))
            visit_index = int(entry.get("visit_index"))
        except (TypeError, ValueError):
            continue
        try:
            entry_group_index = int(entry.get("group_index"))
        except (TypeError, ValueError):
            entry_group_index = -1
        if subject_index < 0 or subject_index >= len(subjects):
            continue
        if statuses[subject_index] == DELETED:
            continue
        subject = subjects[subject_index] if isinstance(subjects[subject_index], dict) else {}
        subject_group_index = _group_index(subject, groups)
        if subject_group_index < 0 or subject_group_index >= len(group_rows):
            subject_group_index = 0
        progress_group_index = entry_group_index
        if progress_group_index < 0 or progress_group_index >= len(group_rows):
            progress_group_index = subject_group_index

        expected, progress_percent, skipped, progress_status = _entry_progress(
            study_data, entry, visit_index, progress_group_index
        )
        if expected <= 0 or not _is_started_entry(progress_percent, skipped, progress_status):
            continue

        entry_time = _parse_entry_datetime(entry.get("created_at"))
        if entry_time is None:
            entry_time = _parse_entry_datetime(entry.get("updated_at"))
        if entry_time is None:
            qualifying_without_date.add(subject_index)
            continue
        current = earliest_by_subject.get(subject_index)
        if current is None or entry_time < current["timestamp"]:
            earliest_by_subject[subject_index] = {
                "subject_index": subject_index,
                "timestamp": entry_time,
                "date": entry_time.date(),
                "group_index": subject_group_index,
            }

    qualifying_without_date.difference_update(earliest_by_subject)
    events = sorted(
        (event for event in earliest_by_subject.values() if event["date"] <= as_of_date),
        key=lambda event: (event["date"], event["subject_index"]),
    )
    events_by_date: Dict[date, List[Dict[str, Any]]] = {}
    for event in events:
        events_by_date.setdefault(event["date"], []).append(event)

    cumulative_groups = [0] * len(group_rows)
    timeline = []
    for event_date in sorted(events_by_date):
        for event in events_by_date[event_date]:
            cumulative_groups[event["group_index"]] += 1
        total = sum(cumulative_groups)
        timeline.append({
            "date": event_date.isoformat(),
            "total": total,
            "groups": [
                {
                    **group,
                    "count": cumulative_groups[group["group_index"]],
                    "proportion_percent": _percent(cumulative_groups[group["group_index"]], total),
                }
                for group in group_rows
            ],
        })

    enrolled_total = len(events)
    configured_subjects = sum(1 for status_value in statuses if status_value != DELETED)
    first_date = events[0]["date"] if events else None
    last_date = events[-1]["date"] if events else None
    plan = _enrollment_plan(study_data, first_date)
    history_days = (as_of_date - first_date).days + 1 if first_date else 0
    last_30_cutoff = as_of_date - timedelta(days=29)
    last_90_cutoff = as_of_date - timedelta(days=89)
    enrolled_last_30 = sum(1 for event in events if event["date"] >= last_30_cutoff)
    enrolled_last_90 = sum(1 for event in events if event["date"] >= last_90_cutoff)
    pace_30 = round(enrolled_last_30, 1)
    pace_90_exact = enrolled_last_90 / 3
    pace_90 = round(pace_90_exact, 1)

    forecast_target = int(plan.get("target_subjects") or configured_subjects) if plan.get("enabled") else configured_subjects
    forecast = {
        "available": False,
        "target_subjects": forecast_target,
        "remaining_subjects": max(0, forecast_target - enrolled_total),
        "projected_completion_date": None,
        "monthly_pace_used": None,
        "reason": "insufficient_history",
    }
    remaining = forecast["remaining_subjects"]
    if forecast_target <= enrolled_total:
        forecast["reason"] = "current_roster_complete"
    elif history_days >= 30 and enrolled_last_90 >= 3 and pace_90_exact > 0:
        projected_days = ceil(remaining / (pace_90_exact / 30))
        forecast.update({
            "available": True,
            "projected_completion_date": (as_of_date + timedelta(days=projected_days)).isoformat(),
            "monthly_pace_used": pace_90,
            "reason": None,
        })

    actual_by_group = []
    for group in group_rows:
        count = cumulative_groups[group["group_index"]]
        actual_by_group.append({
            **group,
            "count": count,
            "proportion_percent": _percent(count, enrolled_total),
        })

    planned_to_date = None
    variance_to_plan = None
    if plan.get("enabled"):
        planned_to_date = _planned_enrollment_on(plan, as_of_date)
        variance_to_plan = enrolled_total - planned_to_date

    return {
        "definition": "first_qualifying_data_entry",
        "as_of": as_of_date.isoformat(),
        "enrolled_subjects": enrolled_total,
        "configured_subjects": configured_subjects,
        "first_enrollment_date": first_date.isoformat() if first_date else None,
        "last_enrollment_date": last_date.isoformat() if last_date else None,
        "subjects_missing_entry_date": len(qualifying_without_date),
        "pace": {
            "enrolled_last_30_days": enrolled_last_30,
            "enrolled_last_90_days": enrolled_last_90,
            "subjects_per_30_days": pace_30,
            "subjects_per_30_days_from_90_day_window": pace_90,
        },
        "plan": plan,
        "planned_to_date": planned_to_date,
        "variance_to_plan": variance_to_plan,
        "forecast": forecast,
        "actual_by_group": actual_by_group,
        "timeline": timeline,
    }


def build_compliance_summary(
    study_data: Dict[str, Any],
    entries: List[Dict[str, Any]],
    as_of: datetime | None = None,
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
            expected, progress_percent, skipped, progress_status = _entry_progress(
                study_data, entry, visit_index, group_index
            )
            if expected <= 0:
                continue

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
            if _is_started_entry(progress_percent, skipped, progress_status):
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
        "enrollment_monitoring": _build_enrollment_monitoring(
            study_data, entries, statuses, groups, as_of
        ),
    }
