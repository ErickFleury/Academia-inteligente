# Instructor evidence review and evaluation custody

Owner-authorized scope, 2026-10-24: EXT-CA-AI-02.23–25. The workspace is
`/instrutor/evidencias`, under **Revisão de evidências** in the instructor menu.
An active local Account, active Instructor employee and authenticated Instructor
role are required. No additional application role is needed.

**Owner decision, 2026-10-24:** the canonical owner approval amendment now accepts
all current sources and proposed rules through a separate project-owner registry,
because no professional reviewer is available. The workspace displays this basis
and the absence of a professional opinion. Exact hashes prevent approval of changed
versions. This does not create human judgments or modify scientific certainty,
reuse rights, excluded sources or the completeness of executable contracts.
Optional actual professional reviews continue to follow the workflow below.

## Actual review

1. Select a source, proposed rule, prescription bundle or registered public
   evaluation protocol. Read its content, source locators and missing items.
   Use **Tipo de material** to find the category. Source reading opens the
   original document in another tab; rule reading shows parameters, supporting
   links and applicable profiles; protocol reading shows public methods,
   criteria and resource budgets. An absent protocol is explicitly identified
   and must be registered under custody before it can be reviewed. JSON and
   the version hash remain under **Dados técnicos da versão (opcional)**;
   instructors need not interpret JSON to register a judgment.
   Bibliographic-only sources require consulting the original; scientific review
   does not grant rights to ingest their text or use it in RAG.
2. Choose methodological or professional review and provide the actual scope,
   method/version, competence, conflicts, domain judgments, outcome certainty
   and rationale. No scientific assessment is prefilled as approved.
3. Personally attest the work performed. Approval also requires explicit
   independence, assessed outcomes and a future review deadline. Incomplete
   executable bundles can receive change requests, but cannot be approved.
4. A different person performs the other independent function. A third person
   can record adjudication with explicit references to the conflicting reviews.
   A reviewer may explicitly supersede their own judgment in the same function;
   the original remains available in history. Concurrent replacement requests
   cannot create two current successors.

The backend records the authenticated subject, name, time and artifact hash.
The visible verifiable review reference is generated from that real record.
The prescription-bundle digest excludes only approval bookkeeping (status,
review records and deadlines); substantive rules, versions, exercise dictionary,
execution contracts and accounting changes invalidate the target. Runtime checks
reject forged, superseded, expired or differently scoped app references. A
contract deadline cannot exceed the referenced human approval deadlines.

## Evaluation custody

1. The actual custodian opens **Custódia da avaliação** and chooses the artifact
   version being evaluated. Enter the protocol, populations, methods, decision
   thresholds, repetitions and total model-call/time budgets before execution.
2. Enter only synthetic cases and the privately prepared reference judgments.
   Explicitly attest synthetic content, independence/nonexposure and the separate
   evaluation/release requirement. Exposed developer fixtures are not independent
   held-out material and must not be declared as such.
3. Submit once. Identical request retries reuse the same immutable record.
   Changed content requires a new seal. Other instructors can review the public
   frozen protocol as an artifact; they cannot retrieve its cases or references.
4. Only the authenticated custodian can explicitly open the private cases.
   Leaving the custody tab or changing sessions clears displayed private state.
   Private cases remain in PostgreSQL, outside repository fixtures and ordinary
   application logs. Public listings select metadata columns only.

This workspace registers judgments and custody. It does not run the model,
publish policy files, enable cohorts or supply release sign-off. Technical
maintainers must incorporate actual verified records into complete executable
artifacts, then perform the separately budgeted independent evaluation and obtain
the required professional and release decisions. Pilot reset refuses to erase
existing review/custody records. No real review or sealed evaluation was performed
by implementing or testing this workflow.
