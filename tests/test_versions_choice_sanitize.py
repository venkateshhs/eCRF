from eCRF_backend.versions import (
    _sanitize_entry_data_for_new_options,
    _snapshot_structural_core,
)
import unittest


class VersionChoiceSanitizeTests(unittest.TestCase):
    def test_reordering_choices_is_not_structural(self):
        old_schema = {
            "selectedModels": [
                {
                    "title": "Section",
                    "fields": [
                        {
                            "_id": "choice",
                            "label": "Choice",
                            "type": "select",
                            "options": ["A", "B", "C"],
                            "constraints": {},
                        }
                    ],
                }
            ]
        }
        new_schema = {
            "selectedModels": [
                {
                    "title": "Section",
                    "fields": [
                        {
                            "_id": "choice",
                            "label": "Choice",
                            "type": "select",
                            "options": ["C", "B", "A"],
                            "constraints": {},
                        }
                    ],
                }
            ]
        }

        self.assertEqual(
            _snapshot_structural_core(old_schema),
            _snapshot_structural_core(new_schema),
        )

    def test_actual_choice_or_constraint_change_remains_structural(self):
        base = {
            "selectedModels": [
                {
                    "title": "Section",
                    "fields": [
                        {
                            "_id": "choice",
                            "label": "Choice",
                            "type": "select",
                            "options": ["A", "B"],
                            "constraints": {},
                        }
                    ],
                }
            ]
        }
        changed_options = {
            "selectedModels": [
                {
                    "title": "Section",
                    "fields": [
                        {
                            "_id": "choice",
                            "label": "Choice",
                            "type": "select",
                            "options": ["A", "C"],
                            "constraints": {},
                        }
                    ],
                }
            ]
        }
        changed_required = {
            "selectedModels": [
                {
                    "title": "Section",
                    "fields": [
                        {
                            "_id": "choice",
                            "label": "Choice",
                            "type": "select",
                            "options": ["A", "B"],
                            "constraints": {"required": True},
                        }
                    ],
                }
            ]
        }

        base_signature = _snapshot_structural_core(base)
        self.assertNotEqual(
            base_signature,
            _snapshot_structural_core(changed_options),
        )
        self.assertNotEqual(
            base_signature,
            _snapshot_structural_core(changed_required),
        )

    def test_materialized_required_and_visibility_defaults_remain_structural(self):
        base = {
            "selectedModels": [
                {
                    "title": "Section",
                    "fields": [
                        {
                            "_id": "choice",
                            "label": "Choice",
                            "type": "select",
                            "options": ["A", "B"],
                            "constraints": {},
                        }
                    ],
                }
            ]
        }
        materialized_defaults = {
            "selectedModels": [
                {
                    "title": "Section",
                    "fields": [
                        {
                            "_id": "choice",
                            "label": "Choice",
                            "type": "select",
                            "options": ["A", "B"],
                            "constraints": {
                                "required": False,
                                "visibilityLogic": {
                                    "action": "show",
                                    "match": "all",
                                    "rules": [],
                                },
                            },
                        }
                    ],
                }
            ]
        }

        self.assertNotEqual(
            _snapshot_structural_core(base),
            _snapshot_structural_core(materialized_defaults),
        )

    def test_sanitize_changed_radio_options_in_cloned_entry_data(self):
        old_schema = {
            "selectedModels": [
                {
                    "title": "Kardiale Risikofaktoren",
                    "fields": [
                        {
                            "_id": "9cbaf516-42af-4310-a350-dd6ff4db8428",
                            "label": "Dyslipidämie",
                            "type": "radio",
                            "options": ["HDL <= 40 mg/dL", "nein"],
                            "constraints": {"allowMultiple": True},
                        }
                    ],
                }
            ]
        }
        new_schema = {
            "selectedModels": [
                {
                    "title": "Kardiale Risikofaktoren",
                    "fields": [
                        {
                            "_id": "9cbaf516-42af-4310-a350-dd6ff4db8428",
                            "label": "Dyslipidämie",
                            "type": "radio",
                            "options": ["HDL < 40 mg/dL", "nein"],
                            "constraints": {"allowMultiple": True},
                        }
                    ],
                }
            ]
        }
        data = {
            "Kardiale Risikofaktoren": {
                "9cbaf516-42af-4310-a350-dd6ff4db8428": ["HDL <= 40 mg/dL"]
            }
        }

        sanitized, changed_count = _sanitize_entry_data_for_new_options(
            data,
            old_schema,
            new_schema,
        )

        self.assertEqual(changed_count, 1)
        self.assertEqual(
            sanitized["Kardiale Risikofaktoren"]["9cbaf516-42af-4310-a350-dd6ff4db8428"],
            [],
        )

    def test_sanitize_changed_table_choice_options_in_cloned_entry_data(self):
        old_schema = {
            "selectedModels": [
                {
                    "title": "Section",
                    "fields": [
                        {
                            "_id": "table-field",
                            "label": "Table",
                            "type": "table",
                            "tableConfig": {
                                "columns": [
                                    {
                                        "id": "col-select",
                                        "label": "Select",
                                        "type": "select",
                                        "options": ["Old", "Keep"],
                                        "constraints": {"allowMultiple": True},
                                    },
                                    {
                                        "id": "col-radio",
                                        "label": "Radio",
                                        "type": "radio",
                                        "options": ["A", "B"],
                                        "constraints": {},
                                    },
                                ]
                            },
                        }
                    ],
                }
            ]
        }
        new_schema = {
            "selectedModels": [
                {
                    "title": "Section",
                    "fields": [
                        {
                            "_id": "table-field",
                            "label": "Table",
                            "type": "table",
                            "tableConfig": {
                                "columns": [
                                    {
                                        "id": "col-select",
                                        "label": "Select",
                                        "type": "select",
                                        "options": ["Keep", "New"],
                                        "constraints": {"allowMultiple": True},
                                    },
                                    {
                                        "id": "col-radio",
                                        "label": "Radio",
                                        "type": "radio",
                                        "options": ["B", "C"],
                                        "constraints": {},
                                    },
                                ]
                            },
                        }
                    ],
                }
            ]
        }
        data = {
            "Section": {
                "table-field": {
                    "rows": [
                        {"col-select": ["Old", "Keep"], "col-radio": "A"},
                        {"col-select": ["Keep"], "col-radio": "B"},
                    ]
                }
            }
        }

        sanitized, changed_count = _sanitize_entry_data_for_new_options(
            data,
            old_schema,
            new_schema,
        )

        rows = sanitized["Section"]["table-field"]["rows"]
        self.assertEqual(changed_count, 2)
        self.assertEqual(rows[0]["col-select"], ["Keep"])
        self.assertEqual(rows[0]["col-radio"], "")
        self.assertEqual(rows[1]["col-select"], ["Keep"])
        self.assertEqual(rows[1]["col-radio"], "B")

    def test_sanitize_does_not_touch_unchanged_choice_options(self):
        schema = {
            "selectedModels": [
                {
                    "title": "Section",
                    "fields": [
                        {
                            "_id": "choice",
                            "label": "Choice",
                            "type": "select",
                            "options": ["A", "B"],
                            "constraints": {},
                        }
                    ],
                }
            ]
        }
        data = {"Section": {"choice": "A"}}

        sanitized, changed_count = _sanitize_entry_data_for_new_options(data, schema, schema)

        self.assertEqual(changed_count, 0)
        self.assertEqual(sanitized, data)

    def test_sanitize_does_not_touch_reordered_choice_options(self):
        old_schema = {
            "selectedModels": [
                {
                    "title": "Section",
                    "fields": [
                        {
                            "_id": "choice",
                            "label": "Choice",
                            "type": "radio",
                            "options": ["A", "B", "C"],
                            "constraints": {"allowMultiple": True},
                        }
                    ],
                }
            ]
        }
        new_schema = {
            "selectedModels": [
                {
                    "title": "Section",
                    "fields": [
                        {
                            "_id": "choice",
                            "label": "Choice",
                            "type": "radio",
                            "options": ["C", "A", "B"],
                            "constraints": {"allowMultiple": True},
                        }
                    ],
                }
            ]
        }
        data = {"Section": {"choice": ["A", "C"]}}

        sanitized, changed_count = _sanitize_entry_data_for_new_options(
            data, old_schema, new_schema
        )

        self.assertEqual(changed_count, 0)
        self.assertEqual(sanitized, data)

    def test_sanitize_new_dominant_option_in_cloned_entry_data(self):
        old_schema = {
            "selectedModels": [
                {
                    "title": "Post-operative injuries",
                    "fields": [
                        {
                            "_id": "injuries",
                            "type": "radio",
                            "options": ["Scar", "Burn", "Amputation", "No injuries"],
                            "constraints": {"allowMultiple": True},
                        }
                    ],
                }
            ]
        }
        new_schema = {
            "selectedModels": [
                {
                    "title": "Post-operative injuries",
                    "fields": [
                        {
                            "_id": "injuries",
                            "type": "radio",
                            "options": ["Scar", "Burn", "Amputation", "No injuries"],
                            "constraints": {
                                "allowMultiple": True,
                                "dominantOptions": ["No injuries"],
                            },
                        }
                    ],
                }
            ]
        }
        data = {
            "Post-operative injuries": {
                "injuries": ["Scar", "No injuries", "Burn"]
            }
        }

        sanitized, changed_count = _sanitize_entry_data_for_new_options(
            data, old_schema, new_schema
        )

        self.assertEqual(changed_count, 1)
        self.assertEqual(
            sanitized["Post-operative injuries"]["injuries"],
            ["No injuries"],
        )


if __name__ == "__main__":
    unittest.main()
