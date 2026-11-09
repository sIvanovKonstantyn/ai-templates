# Attach files to settings

## User story

As an administrator, I want to attach a file to a setting, so that a setting can point to a document (a policy PDF, a certificate, a template) instead of a text value.

## Acceptance criteria

- [ ] An administrator can create or update a setting of type `FILE`.
- [ ] The file is uploaded by the admin UI directly to the upload service. The settings service never receives file bytes.
- [ ] The admin UI sends the id of the uploaded file to the settings service.
- [ ] The settings service registers the file with the storage service and keeps the returned reference id as the setting value.
- [ ] An administrator can read a setting and receive a temporary download link for the file.
- [ ] Other consumers of settings only see the reference id.

## Design notes

### Components

| Component | Responsibility |
| --- | --- |
| Admin UI | Upload dialog, direct upload to the upload service, sends `fileId` with the setting request |
| Upload service | Signs the upload, stores the bytes in object storage |
| Storage service | Registers an uploaded file for a calling service and returns a reference id |
| Document gateway | Returns a reference document that contains a short-lived signed download URL |
| Settings service | Validates the request, registers the file, stores the reference id, resolves the download link for admins |

### Flows

Create or update:
1. The admin UI uploads the file and receives `fileId`.
2. The admin UI sends the setting request with `type = FILE` and `fileId`.
3. The settings service validates the request.
4. The settings service calls the storage service with `fileId` and receives a reference id.
5. The settings service stores the reference id as the setting value.

Read with link (admin only):
1. The settings service reads the setting from the database.
2. For a `FILE` setting it asks the document gateway for the reference document of the stored reference id.
3. It returns the setting with the signed download URL in place of the value.
4. The URL expires after about five minutes. It is never stored or cached.

### Wider design (not all of it is part of the first delivery)

- Optional JSON metadata per file (category, owner, effective date) in separate tables, with a history snapshot for each setting version.
- Rollback of a `FILE` setting restores the old reference id and metadata after checking that the reference still exists.
- Idempotency key for retries, so one logical request creates one current state.
- Cache and change-event behavior for `FILE` settings.
- Client library support: a lazy `getFileUrl` helper and a `FILE` type in the model.
- Virus scanning of every uploaded file before registration.
- A separate error code for each failure (upload, registration, gateway lookup, missing reference).
- Batch endpoints stay metadata-only.
