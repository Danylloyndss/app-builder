# App Builder V1

Autonomous application-building agent: mission → specification → architecture → task graph → implementation → tests → repair → security → acceptance → delivery.

## Current target: TimePro

TimePro is the first end-to-end application used to validate the builder: a mobile-friendly digital timesheet with employee entry, automatic hour calculation, history and a manager dashboard.

## Implemented V1 capabilities

- Natural-language build mission through the web control plane.
- Deterministic product specification and architecture generation.
- Dependency-aware task graph and persistent task state.
- Project file generation and editing.
- Automated tests with bounded repair/retest loops.
- Conditional repair: successful tests do not trigger an unnecessary rebuild.
- Real security gate for obvious hard-coded secret markers.
- Mission-specific TimePro acceptance gate with seven checks.
- Durable mission memory, approvals and quality reports.
- Human-in-the-loop approval and resume flow.
- Protected POST control-plane operations via optional `APP_BUILDER_API_KEY`.
- Build concurrency protection so two missions cannot mutate the same workspace simultaneously.
- Artifact inventory and downloadable build bundle.
- Railway healthcheck, restart policy, automated tests and pre-deploy tests.
- Durable worker recovery diagnostics, resumable jobs and artifact-integrity verification before mission resume.
- GitHub Actions CI runs Python compilation and the complete unittest suite on pushes and pull requests.
- Dependency-free SQLite database adapter with transactional CRUD operations.
- TimePro persistence schema with indexes for employee and work-date queries.
- Architecture now selects a real persistence boundary for apps that require data storage.
- **Bounded model-backed Coding Agent** with structured file edits, allowlisted commands, workspace-escape protection and secret-marker rejection.
- **Executor integration**: unknown implementation tasks can now be delegated to the Coding Agent while deterministic Build Engine handlers remain the default.

## TimePro definition of done

1. Employee can enter a workday timesheet.
2. Total hours are calculated automatically from start, end and pause.
3. Invalid time ranges are rejected.
4. Submitted timesheets appear in history.
5. Manager dashboard summarizes submitted timesheets.
6. Core flow is responsive on a mobile viewport.
7. Optional fields never block submission.

## Architecture

- **Manager** — orchestration/state machine.
- **Specification Builder** — product specification.
- **Architecture Builder** — technical architecture.
- **Task Builder** — executable dependency graph.
- **Executor / Build Engine / Coding Agent** — deterministic implementation plus bounded model-backed coding.
- **Tester** — automated verification.
- **Quality Gate** — security and acceptance verification.
- **Database Adapter** — transactional persistence boundary; SQLite is the default implementation.
- **Approval Store / Policy** — human-in-the-loop safety.
- **Railway** — deployment runtime.

## Next expansion layers

- Wire the generated TimePro screens to the persistence adapter through a backend service.
- Authentication provider adapters with approval gates.
- External integrations and secret-management adapters.
- Browser/runtime integration tests.
- Multi-agent specialist execution behind the same durable state machine.
- Production release automation after human approval.

The design goal remains: continue autonomously until a genuine external action requires the human, then resume from durable state.
