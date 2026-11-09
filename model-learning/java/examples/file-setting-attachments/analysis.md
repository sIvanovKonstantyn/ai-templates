# Analysis: file-setting-attachments

The example is a generalized case. Names, services, and paths are fictional. The spec is written to follow the rules in `../../spec-writing-rules.md`, including the lessons.

Files in this folder:
- `brief.md`: the request and the design notes. The design notes describe more than the first delivery.
- `spec.md`: the spec written from it, with 7 subtasks.

## What the spec delivers

The brief describes file attachments across an admin UI, an upload service, a storage service, a document gateway, the database, rollback, cache, events, and client libraries. The spec delivers one backend slice:

1. A `FILE` setting type whose request carries a `fileId`.
2. On create and update, the service registers the file with the storage service and stores the returned reference id as the setting value.
3. A new admin endpoint that returns the setting with a temporary download link in place of the value.

## Brief to subtask

| Brief item | Subtask | Notes |
| --- | --- | --- |
| New `FILE` type | 1 | One enum value. Compile check, plus tests that assert the accepted-types message. |
| `fileId` in the request, validation | 2 | New field, two validators, validator tests with null, empty, and blank inputs. |
| Register the file with the storage service | 3 | One concrete client class. The spec pastes the endpoint contract and the properties. |
| Register on create and update | 4 | A private facade method called in both flows. The REST test base class gets a mock bean. |
| Document gateway lookup | 5 | A Feign client, a wrapper interface, a logging and retry wrapper, and the properties. |
| Admin read with download link | 6, 7 | A facade method with no cache and no rate limit, then the REST endpoint. |

## Brief content the spec does not deliver

These items are in the design notes and listed in the spec under `Out of scope`:
- Metadata tables and history snapshots.
- Rollback of `FILE` settings.
- Idempotency keys.
- Cache and change-event behavior.
- Client library support.
- Virus scanning.
- A separate error code per failure.
- Batch endpoints for `FILE` (they reject it).

## How the spec is written

- Goal: two sentences, result only.
- Subtasks run bottom up: model, validation, client, orchestration, second client, read orchestration, API.
- Each subtask: Definition (what), Recommendations (where, what to copy, negatives, tests, docs), Verification (command and pass condition).
- Reference material is inline: reference client code, the endpoint contract, the response example, the Maven block, the YAML properties.
- Reference tests are named in the subtasks that need them.
- Negative constraints are explicit: no rate limit, no caching, use the wrapper bean only.

## Gaps this kind of spec tends to have

Specs of this shape were checked against code that already existed. These gaps were found. Each one became a rule, and the example spec closes it.

| Gap | Rule | Where the example closes it |
| --- | --- | --- |
| The reference code called a different path than the contract | 28 | Subtask 3: "take the structure only" |
| A required property had no value and no default, so the service could not start | 29 | Subtask 3 and 5: properties with sources |
| No exception, error code, or log key was named for the new integration | 30 | Subtask 3 |
| A validator returned "valid" for a null value and hid a missing field | 31 | Subtask 2 |
| A shared test base class needed a mock bean for the new dependency | 32 | Subtask 4 |
| An existing test asserted the old list of accepted enum values | 33 | Subtask 1 |
| Two beans of one type (client and wrapper) | 34 | Subtask 5: `ExtendedGatewayClient` |
| `ITest` classes are excluded from the default run | 37 | Subtasks 4 and 7 |
| A wording that left a decision open | 5 | Subtask 6: the failure cases throw |
| Brief content was dropped without saying so | 3, 11 | `Out of scope` |
