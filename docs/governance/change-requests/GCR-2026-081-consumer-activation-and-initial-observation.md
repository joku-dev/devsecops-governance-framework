# GCR-2026-081: Consumer activation and initial observation

## Classification and source

This is an operational publication under the accepted GCR-2026-080 consumer
contract, plus a pending personal remediation request. It introduces no source
document, policy, baseline, role or enforcement change.

The maintainer personally posted operating acceptance in central PR #101,
comment `5698945870`, at `2026-09-16T14:15:04Z`. The protected-main workflow
`35107314433` captured the actual GitHub response at `14:16:03Z` and opened
PR #102. Its capture binds the unchanged implementation and approved scope.
The acceptance record remains unchanged when the proposal is extended below.

## Actual first observation

Consumer PR #6 records the confirmed roles and evidence boundary. Its mainline
commit `5da284d0a3e7d526df644266451206e09084a556` produced architecture run
`35107862511` and CI run `35107861865`. Feedback and observability declarations
remain `reviewed`; all gates remain report-only.

Using the accepted implementation and actual GitHub GETs, the local CLI appended
the first observation to the same activation proposal at `2026-09-16T14:21:30Z`.
The artifact observation time is `14:20:45Z`. Full source bytes and provider
metadata are retained and the selected policy was independently recalculated.
The required PR guard re-fetches the new source and operating consent using
the configured repository secret before merge.

The outcome is one open `operation_readiness` finding with B5/P11 source
messages, not two marker findings. No old diagnostic candidate is promoted.
The general consumer-result indexes and GRS-002 history are separate.

## Pending decision and validation

`consumer-operation/action-requests/00000001.json` binds receipt
`transaction:a54f246ad4bd302f2df4ac68451839ae4ace023075c8290a278547d32b0232a2`
at revision 1. Its plan names `joku-dev`, the feedback/observability evidence
work, personal progress and closure requirements, and a proposed deadline of
23 September 2026, 23:59:59 Europe/Berlin. The statement is prepared for PR #102;
it is not posted or accepted by automation. There are zero action records.

The empty-observation regression test now explicitly injects an empty ledger
instead of assuming the repository forever contains no real observations.
Runtime implementation fingerprints are unchanged.
The consumer store's local append locks and unpublished temporary files now
use the same ignore rules as the original lifecycle store. A publisher test
checks that these files cannot obstruct or enter a normal operational proposal.
Validate with the pinned
full suite, independent provider recheck, strict documentation build and all
required GitHub checks. The maintainer's standing scoped review exception
applies to the technical publication; normal review protection is restored
after merge.
