# case-e design

## Purpose

case-e is an electronic case report form and data-capture application. It lets a
study team design a study, collect structured participant data, revise the study
without losing the meaning of existing records, review progress, and export the
result.

This document describes the application model and the behaviour that must be
preserved when storage or authentication components are replaced.

## Main workflow

```text
Sign in
  -> create or open a study
  -> define groups, subjects and visits
  -> build forms from sections and fields
  -> assign sections to visits and groups
  -> publish the study
  -> enter or import participant data
  -> review, audit and export
```

Study design and data collection are separate phases. A draft can change freely.
A published definition provides the context needed to interpret collected data.

## Domain model

```text
Study
|- metadata and status
|- owner and access grants
|- groups
|- subjects
|- visits
|- forms
|  `- sections
|     `- fields and constraints
|- protocol assignments
|- template versions
|- data-entry records
|- study and participant files
|- shared links
`- audit events
```

### Study

A study is the main access, versioning and export boundary. It contains both its
definition and the data collected from that definition.

The current lifecycle states are:

- **Draft**: editable and unavailable for normal data collection.
- **Published**: available for data collection.
- **Archived**: retained but removed from the active workflow.

A revision of a published study is represented through a new template version;
it is not a separate study.

### Groups, subjects and visits

- A **group** represents a cohort, arm, site or another protocol partition.
- A **subject** is identified by a study-specific, non-identifying subject ID.
- A **visit** is a protocol collection point, not a form.

The subject, visit and group identify the data-entry context. Subject IDs must be
unique within the study and remain stable after data collection begins.

### Forms, sections and fields

A form is composed of reusable sections. A section contains fields. Fields may
define:

- type, label and stable identifier;
- required and read-only state;
- choice options, ranges, patterns and other constraints;
- conditional visibility;
- reminders and value assignments;
- calculations; and
- file or URL input settings.

The form builder stores the study definition as structured data. Different
studies can therefore define substantially different forms and constraints.

### Protocol assignments

The protocol matrix assigns sections to combinations of visit and group. An
assignment determines whether a section is expected for a subject at a
particular visit.

```text
section + visit + group -> expected data-entry section
```

This assignment is part of the versioned study definition.

## Data-entry model

A saved entry belongs to:

```text
study + subject + visit + group + template version
```

The entry contains values for the sections assigned to that context, together
with completion and skipped-required information. Files may be associated with
the study as a whole or with a subject and visit.

Authorized users can create and correct entries. Existing data is loaded before
editing. Concurrent changes must be detected rather than silently overwritten.

## Validation and form behaviour

case-e provides immediate validation in the data-entry interface. Validation
includes field types, required values, configured constraints, repeating-table
columns, conditional visibility, assignments and calculations.

The current implementation divides this work between the frontend and backend.
The frontend provides interactive behaviour, while the backend protects stored
data and study access. A future backend must not assume that browser validation
alone is sufficient because direct API submissions can bypass it.

## Versioning

Template versions preserve the definition used to collect each entry.

The main rules are:

1. A published template version with associated data must remain interpretable.
2. Structural changes create a new version when data already exists.
3. Structural changes include adding or removing fields, changing field types or
   constraints, and changing protocol assignments.
4. Older versions remain readable and exportable.
5. An entry remains linked to the template version under which it was recorded.
6. Unchanged values may be carried forward for use with a later version.
7. Exports must make version differences explicit and preserve stable columns
   where field identifiers have not changed.

Carry-forward is application behaviour, not simply a storage copy. It must be
safe for large studies and must not leave a partially migrated study after a
failure.

## Identity and permissions

case-e separates platform roles from study permissions.

Current platform roles are:

- **Administrator**
- **Principal Investigator**
- **Investigator**
- **No Access**

Study access is additive and contains three independent permissions:

- **View**
- **Add data**
- **Edit study**

The study owner and administrators have full study access. Other users receive
explicit study grants. Read-only access is represented by the **View** grant;
there is no separate Viewer platform role.

Authorization must be enforced when listing, reading and changing data. Hiding
an action in the interface is not an authorization check.

## Shared links

A shared link allows data entry without a normal case-e account. A link is
limited by:

- study;
- subject, visit and group;
- permitted sections;
- view or submission permission;
- expiry;
- maximum uses; and
- revocation state.

The submitted data uses the same study definition and storage path as an
authenticated entry. Audit information must distinguish a shared-link action
from an authenticated user action.

## Files

case-e has two file scopes:

- **Study files**, such as protocols and approvals.
- **Participant files**, associated with a subject and optionally a visit or
  field.

File content, metadata, access control and audit history must remain connected.
An exported reference is not a substitute for preserving the referenced file.

## Audit and provenance

Audit information answers:

```text
who or what changed which object, when, and how
```

Events may be study-wide or subject-specific. They cover data changes, study
changes, access changes, shared-link actions, imports, exports and controlled
deletion or dropout workflows.

The current hosted implementation combines structured application audit events
with DataLad/Git history. These histories are related but not interchangeable:
application events describe the user action, while repository history records
the resulting stored change.

## Import, export and multi-site work

case-e supports reusable study definitions and transfer of study data between
installations. The design must support:

- template export and import;
- CSV and spreadsheet import with mapping and validation;
- scoped study and data exports;
- version-aware exports;
- BIDS-oriented packages;
- audit and permitted file inclusion; and
- conflict detection when independently edited datasets are merged.

Exports are analysis or transfer artifacts. They do not replace a tested backup
of the authoritative stores.

## Current application architecture

```text
Vue frontend
    |
FastAPI application layer
    |-- authentication and sessions
    |-- authorization
    |-- study workflow and validation
    |-- versioning and carry-forward
    |-- shared-link enforcement
    |-- audit and export orchestration
    |
    |-- relational database
    `-- filesystem or DataLad/git-annex storage
```

The local profile uses SQLite and local filesystem storage. The hosted profile
uses PostgreSQL and DataLad-backed study storage, with git-annex/RIA available
for file content and remote persistence.

In the current hosted storage model:

- draft study content is held in the relational database;
- published study content and entry data are written to the study dataset;
- template-version records remain available through the database;
- user, session, status and permission records are relational; and
- DataLad history supplements the application audit trail.

## Target integrated architecture

The intended Cerebra integration is:

```text
case-e frontend
    |-- Forgejo: login, identity and team membership
    |-- Dump Things: study metadata and submitted records
    `-- Forgejo/git-annex: schemas and file content
```

The target is to retain the case-e study-design and data-entry interface while
removing the separate case-e database and general application backend where the
required behaviour can be provided safely by shared services.

Forgejo authentication using Authorization Code with PKCE and team-based role
mapping has been tested. This replaces local login, but it does not by itself
replace study versioning, validation, shared links, provisioning, curation,
export or audit semantics.

A trusted component may still be required for operations that cannot safely be
performed by a browser, including:

- creating Dump Things collections with an administrator credential;
- creating or changing Forgejo teams;
- issuing and checking patient links;
- enforcing study-specific writes in a shared collection;
- automatic curation; and
- long-running version migration or export work.

Such a component does not have to be the current case-e backend, but its
responsibilities must be explicit.

## Required invariants

Any replacement architecture must preserve these rules:

1. A study definition determines which data may be collected.
2. Every entry has an unambiguous study, subject, visit, group and version.
3. Historical entries remain interpretable after the study changes.
4. Users cannot discover or modify studies outside their access.
5. Write authorization and validation are enforced outside the browser when
   they protect stored data.
6. Shared links grant only their declared scope and lifetime.
7. Study files and participant files retain their scope and permissions.
8. Audit history retains actor, time, action and affected object.
9. Partial provisioning, migration and curation failures are recoverable.
10. Configuration supplies deployment URLs, collection names and permission
    mappings; they are not fixed in application code.

## Open design decisions

The following decisions are still required for the Forgejo and Dump Things
integration:

1. One collection per organization, one per study, or a hybrid model.
2. Generic case-e schema or generated schema per study.
3. Enforcement point for study-specific validation.
4. Enforcement point for study-specific write authorization.
5. Representation of template versions and carry-forward.
6. Incoming, automatically curated or directly curated submissions.
7. Provisioning owner for collections, teams and repositories.
8. Storage and authorization model for both file scopes.
9. Study-level export and analytics mechanism.
10. Session, refresh-token and logout policy for the browser application.

## Related decisions and issues

- [#25: Investigation schema](https://github.com/venkateshhs/eCRF/issues/25)
- [#47: Investigator access model](https://github.com/venkateshhs/eCRF/issues/47)
- [#51: Study versioning rules](https://github.com/venkateshhs/eCRF/issues/51)
- [#57: Dump Things investigation](https://github.com/venkateshhs/eCRF/issues/57)
- [#64: Audit trail](https://github.com/venkateshhs/eCRF/issues/64)
- [#80: Study access management](https://github.com/venkateshhs/eCRF/issues/80)
- [#88: Multi-site merge](https://github.com/venkateshhs/eCRF/issues/88)
- [#118: Inactivity logout](https://github.com/venkateshhs/eCRF/issues/118)
- [#124: Audit protection and export](https://github.com/venkateshhs/eCRF/issues/124)
