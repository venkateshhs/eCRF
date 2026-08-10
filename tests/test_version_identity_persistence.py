from eCRF_backend.versions import normalize_study_data_ids


def _schema(*, include_notes=True, ids=False):
    fields = [
        {"name": "assessment_date", "label": "Assessment Date", "type": "date"},
        {"name": "site_code", "label": "Site Code", "type": "text"},
    ]
    if include_notes:
        fields.append({"name": "notes", "label": "Notes", "type": "textarea"})

    schema = {
        "selectedModels": [
            {
                "title": "Visit Information",
                "fields": fields,
            }
        ]
    }
    if ids:
        schema["selectedModels"][0]["_id"] = "section-v1"
        for field in schema["selectedModels"][0]["fields"]:
            field["_id"] = f"field-{field['name']}"
    return schema


def test_new_study_ids_are_generated_once_and_preserved():
    normalized = normalize_study_data_ids(_schema())
    section = normalized["selectedModels"][0]

    assert section["_id"]
    assert all(field["_id"] for field in section["fields"])
    assert normalize_study_data_ids(normalized) == normalized


def test_legacy_idless_study_inherits_latest_snapshot_ids():
    reference = _schema(ids=True)
    normalized = normalize_study_data_ids(_schema(), reference)

    section = normalized["selectedModels"][0]
    assert section["_id"] == "section-v1"
    assert [field["_id"] for field in section["fields"]] == [
        "field-assessment_date",
        "field-site_code",
        "field-notes",
    ]


def test_version_edit_preserves_retained_ids_and_only_new_fields_get_new_ids():
    reference = _schema(ids=True)
    edited = _schema(include_notes=False)
    edited["selectedModels"][0]["fields"].append(
        {"name": "investigator_comment", "label": "Investigator Comment", "type": "text"}
    )

    normalized = normalize_study_data_ids(edited, reference)
    fields = {
        field["name"]: field["_id"]
        for field in normalized["selectedModels"][0]["fields"]
    }

    assert normalized["selectedModels"][0]["_id"] == "section-v1"
    assert fields["assessment_date"] == "field-assessment_date"
    assert fields["site_code"] == "field-site_code"
    assert fields["investigator_comment"]
    assert fields["investigator_comment"] not in {
        "field-assessment_date",
        "field-site_code",
        "field-notes",
    }


def test_reference_id_replaces_regenerated_id_for_same_field_identity():
    reference = _schema(ids=True)
    edited = _schema(include_notes=False)
    edited["selectedModels"][0]["_id"] = "replacement-section"
    edited["selectedModels"][0]["fields"][0]["_id"] = "replacement-assessment"

    normalized = normalize_study_data_ids(edited, reference)

    assert normalized["selectedModels"][0]["_id"] == "section-v1"
    assert normalized["selectedModels"][0]["fields"][0]["_id"] == "field-assessment_date"


def test_ambiguous_duplicate_names_do_not_inherit_the_wrong_reference_id():
    reference = {
        "selectedModels": [
            {
                "_id": "section-v1",
                "title": "Section",
                "fields": [
                    {"_id": "first", "name": "value", "label": "Value"},
                    {"_id": "second", "name": "value", "label": "Value"},
                ],
            }
        ]
    }
    incoming = {
        "selectedModels": [
            {"title": "Section", "fields": [{"name": "value", "label": "Value"}]}
        ]
    }

    normalized = normalize_study_data_ids(incoming, reference)
    field_id = normalized["selectedModels"][0]["fields"][0]["_id"]

    assert field_id not in {"first", "second"}


def test_new_duplicate_name_does_not_reuse_an_existing_field_id():
    reference = {
        "selectedModels": [
            {
                "_id": "section-v1",
                "title": "Section",
                "fields": [{"_id": "existing", "name": "value", "label": "Value"}],
            }
        ]
    }
    incoming = {
        "selectedModels": [
            {
                "_id": "section-v1",
                "title": "Section",
                "fields": [
                    {"_id": "existing", "name": "value", "label": "Value"},
                    {"_id": "new-field", "name": "value", "label": "Value"},
                ],
            }
        ]
    }

    normalized = normalize_study_data_ids(incoming, reference)
    field_ids = [field["_id"] for field in normalized["selectedModels"][0]["fields"]]

    assert field_ids == ["existing", "new-field"]
