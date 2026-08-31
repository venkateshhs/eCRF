# case-e

**case-e** is an electronic case report form (eCRF) and electronic data capture
(EDC) application for designing research studies, collecting structured
subject/visit data, monitoring completion, preserving an audit history, and
exporting analysis-ready study packages.

The application supports a lightweight local workstation profile and a hosted
server profile. It is developed by the Biomarker Development Group at INM-7,
Forschungszentrum Jülich.

## Start here

| Resource | Link |
| --- | --- |
| Hosted case-e application | [https://ecrf.inm7.de/login](https://ecrf.inm7.de/login) |
| Complete user and administrator documentation | [https://biomarker-development-at-inm7.github.io/case-e-docs/](https://biomarker-development-at-inm7.github.io/case-e-docs/) |
| Documentation source repository | [Biomarker-Development-at-INM7/case-e-docs](https://github.com/Biomarker-Development-at-INM7/case-e-docs) |
| Application source repository | [Biomarker-Development-at-INM7/eCRF](https://github.com/Biomarker-Development-at-INM7/eCRF) |
| Application issues | [Issue tracker](https://github.com/Biomarker-Development-at-INM7/eCRF/issues) |

The standalone documentation contains detailed, screenshot-based workflows for
every major function. If the published documentation is not available yet, see
[View the documentation locally](#view-the-documentation-locally).

## Hosted access and collaboration

To evaluate or collaborate using the managed service:

1. Open the [hosted login page](https://ecrf.inm7.de/login).
2. Select **Create account** and register a user.
3. A self-registered account initially receives the platform role
   **Investigator**. Registration does not automatically grant access to an
   existing study or permission to create a study.
4. Contact **Prof. Jürgen Dukart** to discuss the study and arrange the
   appropriate collaboration, platform role, and study-level access.
5. After access is granted, open an existing study or begin designing a new
   study with Principal Investigator or Administrator permissions.

**Collaboration contact:**

- Prof. Jürgen Dukart
- Biomarker Development Group, INM-7, Forschungszentrum Jülich
- [j.dukart@fz-juelich.de](mailto:j.dukart@fz-juelich.de?subject=case-e%20collaboration)
- [Research group website](https://www.fz-juelich.de/en/inm/inm-7/research-groups/biomarker-development)

When requesting collaboration, include the institution, study purpose,
approximate number of users and subjects, expected data types, timeline, and
whether the request concerns a new or existing study. Never email passwords,
participant data, clinical files, password-reset tokens, or active shared links.

## Major capabilities

### Study creation and lifecycle

- Create studies from scratch or import reusable definitions and supported
  study data.
- Configure metadata, groups/cohorts, subjects, subject-ID patterns, group
  assignments, visits, and forms through a guided workflow.
- Map form sections to visits and study groups through the Schedule of
  Assessments/protocol matrix.
- Work in draft, publish an approved design, and create controlled revisions
  while retaining template-version context.
- Maintain study-level documents, descriptions, assignments, and access grants.

### Form and section design

- Build forms from standard clinical sections, custom fields, saved templates,
  or supported Biomedical Investigation Ontology (OBI) concepts.
- Arrange forms as reusable sections and fields.
- Save complete forms or selected sections as reusable design templates.
- Rearrange, copy, edit, collapse, expand, and remove form components.
- Preview and test the design before publishing it to a study.

Supported custom field types include text, text area, number, checkbox, radio
group, dropdown/select, date, time, file upload or URL reference, slider/Likert
scale, and repeating table.

### Field settings and validation

Common field settings include labels, placeholders, help text, required and
read-only states, defaults, and controlled field-type conversion. Type-specific
constraints include:

- text length, regular-expression patterns, and transformations;
- numeric minimum, maximum, step, integer-only, and digit limits;
- date/time formats, ranges, and defaults;
- ordered choice options, multi-selection, and dominant choices such as *None*;
- slider/Likert ranges, steps, labels, and marks;
- file formats, size guidance, upload/link behavior, multiple files, and BIDS
  modality metadata; and
- typed repeating-table columns and row validation.

### Conditional logic, reminders, assignments, and calculations

- Show or hide fields using one or more conditions combined with AND or OR.
- Use type-aware equality, text, numeric, date/time, empty, and between rules.
- Display value-triggered guidance or outlier reminders during data entry.
- Assign literal values to read-only targets with ordered first-match behavior
  and optional overwrite handling.
- Build and validate numeric expressions using fields, arithmetic, functions,
  constants, and scored choice/checkbox inputs.
- Select strict or zero-based blank handling and write results to calculated
  read-only fields.
- Detect invalid symbols, target conflicts, incompatible values, and potential
  circular dependencies.

### Subjects, visits, and data collection

- Navigate data collection through a subject-by-visit matrix.
- Filter visits, subjects, and active/retained/deleted dropout states.
- Track visible data points, required/skipped values, validation errors, and
  completion percentage in real time.
- Navigate directly to remaining incomplete or invalid fields.
- Save a complete available form entry for one subject and visit.
- Copy supported values from a previous visit for review.
- Add, copy, edit, and remove repeating-table rows.
- Attach permitted files or approved URL references.
- Import CSV, XLSX, and XLS through mapping, preview, warning/error review, and
  validated commit steps.
- Detect concurrent edits and surface conflicts for deliberate resolution.

### Sharing and collaboration

- Grant study-specific **View**, **Add data**, and **Edit study** permissions.
- Create scoped data-entry links for permitted subjects, visits, and sections.
- Create authorized bulk links for subjects in the same group.
- Set link expiry and use counts, monitor access, revoke links, and export link
  information to CSV.
- Keep platform roles separate from study permissions: registration alone does
  not provide access to a study.

### Users, permissions, and account recovery

- Platform roles include Investigator, Principal Investigator, Viewer, and
  Administrator, with study permissions applied separately.
- Administrators manage users and roles; study owners and authorized
  administrators manage study grants.
- Password changes revoke existing sessions.
- Optional email recovery uses masked-email confirmation and a time-limited,
  single-use reset link; it is disabled until SMTP is configured and validated.
- Apply least privilege and test each role with non-production data.

### Review, oversight, audit, and dropout

- Review version-aware data in a grouped, sortable, filterable table.
- Monitor recruitment, retention, data coverage, complete subjects, partial
  visits, skipped required fields, visit performance, and group comparison.
- Inspect study-level and subject-level audit events and structured changes.
- Record controlled subject dropout with data retained or active data deleted.
  Retained dropouts become read-only; deletion requires additional confirmation
  and does not erase independent exports or backups.

### Export and reproducibility

- Export complete selected-version data as CSV or Excel-compatible XLS.
- Export reusable JSON study templates and supported scoped subsets.
- Download a BIDS-oriented study ZIP with dataset metadata, participants,
  human-labelled eCRF data, templates, and permitted files.
- Create custom packages scoped by version, subject, group, visit, files,
  templates, and audit content.
- Combine template versions while preserving stable columns for unchanged
  identifiers.
- Download a template-and-CSV merge bundle for transfer to another study.
- Use DataLad/RIA-backed history in the configured server profile.

Exports are analytical or transfer artifacts; they are not substitutes for a
tested recovery backup of the database, study/file storage, configuration, and
DataLad/RIA history.

## Run locally from source

### Prerequisites

- Python 3.11 or a compatible recent Python 3 release
- Node.js and npm
- Git

### Quickstart

```bash
git clone https://github.com/Biomarker-Development-at-INM7/eCRF.git
cd eCRF

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

cd eCRF_frontend
npm ci
npm run build
cd ..

python server.py
```

If the browser does not open automatically, visit
[http://127.0.0.1:8000/login](http://127.0.0.1:8000/login).

On a new local data directory, the evaluation bootstrap account is:

```text
Username: admin
Password: Admin123!
```

Change this password immediately through **User Management → Change Password**.
The local defaults are only for evaluation on one workstation. Do not expose
the local launcher to a network and do not retain the default password.

The local launcher binds to `127.0.0.1:8000`, uses SQLite, stores the database
and study files in the selected data directory, disables DataLad/git-annex, and
opens a browser unless `ECRF_OPEN_BROWSER=0`. On macOS and Windows, the first
launch asks for a data folder when none is configured.

Set `ECRF_DATA_DIR` to choose the data directory without the folder dialog:

| Item | Location |
| --- | --- |
| SQLite database | `<data-dir>/ecrf.db` |
| Study datasets and files | `<data-dir>/bids_datasets` |
| Launcher configuration | `<application-dir>/ecrf_config.json` |

## Build the desktop bundle

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt

cd eCRF_frontend
npm ci
npm run build
cd ..

pyinstaller -y ecrf.spec
```

The result is written below `dist/`. Move the complete bundle, not selected
internal files. It uses the same local profile, storage selection, SQLite
database, and bootstrap behavior as `python server.py`.

## Hosted/server deployment

Production deployments should use the server profile, PostgreSQL, explicit
secrets, exact HTTPS CORS origins, persistent file storage, and a configured
DataLad RIA store where study-write history is required.

The supplied Docker Compose stack includes PostgreSQL 16, case-e, Apache,
persistent runtime/database volumes, and a file-based RIA store.

```bash
cd deploy/docker

# Create .env with the required server values listed below.
chmod 600 .env

# Replace every placeholder and insecure default before continuing.
docker compose up -d --build
docker compose ps
./scripts/smoke-test.sh http://localhost:8080
```

Important server variables include:

- `ECRF_ENV=production` and `ECRF_PROFILE=server`
- `ECRF_DATABASE_URL`, `ECRF_SECRET_KEY`, and `ECRF_CORS_ALLOW_ORIGINS`
- `ECRF_DATA_DIR`, `BIDS_ROOT`, and `ECRF_TEMPLATES_DIR`
- `ECRF_BOOTSTRAP_ADMIN` and the `ECRF_ADMIN_*` values
- `ECRF_DATALAD_MODE`, `ECRF_DATALAD_RIA_URL`, and
  `ECRF_DATALAD_PUSH_ON_SAVE`
- `ECRF_DATALAD_REQUIRE_RIA_FOR_WRITES`

Never use example database/admin passwords or secret keys in a shared
deployment. Do not expose PostgreSQL port 5432 publicly. Back up the database,
runtime data, and RIA storage consistently and test restoration.

See the [complete deployment guide](https://biomarker-development-at-inm7.github.io/case-e-docs/deployment.html)
for Docker, systemd/Apache, HTTPS, SMTP recovery, validation, and operations.

## Configure email password recovery

Password recovery is disabled by default. Start with
`deploy/password-reset.env.example`, configure the public HTTPS origin and an
approved SMTP relay/account, then restart case-e. Never commit SMTP passwords.

```bash
ECRF_PASSWORD_RESET_ENABLED=1
ECRF_FRONTEND_BASE_URL=https://ecrf.example.org
ECRF_SMTP_HOST=smtp.example.org
ECRF_SMTP_PORT=587
ECRF_SMTP_USERNAME=casee@example.org
ECRF_SMTP_PASSWORD=replace-with-a-secret
ECRF_SMTP_STARTTLS=1
ECRF_SMTP_SSL=0
ECRF_MAIL_FROM=casee@example.org
```

Test delivery, public routing, expiry, single use, rate limits, and session
revocation with a non-privileged account before enabling recovery for users.

## Verify an installation

```bash
python -m eCRF_backend.preflight
curl -fsS http://127.0.0.1:8000/health
```

For the supplied Linux service:

```bash
sudo systemctl status casee
sudo journalctl -u casee -n 200 --no-pager
```

## View the documentation locally

The complete Sphinx documentation is maintained in the separate
[`case-e-docs`](https://github.com/Biomarker-Development-at-INM7/case-e-docs) repository.

```bash
git clone https://github.com/Biomarker-Development-at-INM7/case-e-docs.git
cd case-e-docs

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

sphinx-build -E -W --keep-going -b html docs docs/_build/html
python3 -m http.server 8080 --directory docs/_build/html
```

Open [http://127.0.0.1:8080/](http://127.0.0.1:8080/) and stop the server with
`Ctrl+C`.

## Security, privacy, and validation

Software availability does not establish that an installation is suitable for
a regulated or production study.

- Do not enter real participant data until design, permissions, validation,
  hosting, backups, recovery, and organizational approvals are reviewed.
- Do not put participant information, credentials, active shared links, tokens,
  production logs, or secrets in public issues.
- Use HTTPS, unique secrets, least privilege, protected backups, and an approved
  incident-response process.
- Validate every field, rule, protocol assignment, role, import, export, and
  recovery path against the intended protocol.
- Independently assess applicable GCP, GDPR, HIPAA, 21 CFR Part 11,
  institutional, and jurisdictional requirements.

This material is informational software guidance, not medical, clinical,
legal, regulatory, information-security, or compliance advice.

## Support

- Documentation: [case-e-docs issues](https://github.com/Biomarker-Development-at-INM7/case-e-docs/issues)
- Application bugs/features: [application issue tracker](https://github.com/Biomarker-Development-at-INM7/eCRF/issues)
- Hosted access/collaboration: [Prof. Jürgen Dukart](mailto:j.dukart@fz-juelich.de?subject=case-e%20collaboration)
- Security/privacy/production incidents: use the responsible organization's
  approved private incident channel.

Bug reports should include the case-e version/build, deployment type, sanitized
reproduction steps, expected and actual behavior, and exact error message.

## Authorship and maintenance

**Documentation author and maintainer:**
[Venkatesh Hariharapura Shivashankar](https://github.com/Biomarker-Development-at-INM7)

Software and documentation contribution history is recorded in the respective
Git repositories.

## AI-generation disclosure

This README and the linked case-e documentation site were generated entirely by
ChatGPT. This statement is provided expressly for transparency and legal
attribution. ChatGPT and OpenAI are not the author, maintainer, publisher,
operator, sponsor, or legal guarantor of case-e. The named human maintainer is
responsible for reviewing, accepting, publishing, correcting, and versioning
the documentation.

AI-generated material can contain errors or omissions. If documentation
conflicts with validated behavior, stop the affected workflow and ask the
maintainer or deployment administrator to resolve the discrepancy before
continuing regulated or production activity.

## License

case-e is distributed under the [MIT License](LICENSE).
