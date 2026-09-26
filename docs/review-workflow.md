# Day 7 — Reviewer UI + Human-in-the-Loop Workflow

## Objective

Close the loop with human review for cases where the agent
requires human inspection.

## Review Queue

A review item contains:

- Customer message
- Agent decision
- Agent reason
- Retrieved chunks / evidence + sources
- Agent generated answer, if available
- Failure information, if applicable
- Reviewer action
- Reviewer reason

## Agent Decisions

The final agent decision relevant to review is:

- `ANSWER`
- `ESCALATE`

Internal actions such as `TOOL_CALL` are not treated as final
review decisions.

## Reviewer Actions

The reviewer can:

- `APPROVE`
- `EDIT`
- `ESCALATE`

### Approve

If the agent produced a valid answer:

```text
APPROVE → RESOLVED