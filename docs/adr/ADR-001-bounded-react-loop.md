# ADR-001: Use a Bounded ReAct Loop

## Status

Accepted

## Context

TicketPilot needs to handle support tickets where the execution path is
not fixed. The agent may or may not need retrieval or tool execution
depending on the current ticket state, available evidence, and results
from previous actions.

A fixed chained workflow would force a predetermined execution order,
which does not fit these dynamic cases.

However, unlimited agent execution would create problems such as
uncontrolled cost, unpredictable execution, and cases where the agent
continues trying to solve a problem that should instead be handled by
the support team.

## Decision

Use a bounded ReAct-style agent loop.

The agent can dynamically decide whether to retrieve knowledge, execute
a tool, evaluate the result, take another action, produce an answer,
or stop and escalate to support.

The loop is bounded by execution limits such as maximum iterations,
time, and retries.

If the agent cannot safely resolve the ticket within those limits, the
ticket is escalated to the support team.

## Trade-offs

### Benefits

- Supports dynamic execution paths.
- Retrieval and tool usage are conditional.
- Agent can react to intermediate results.
- Prevents uncontrolled autonomous execution.
- Controls LLM and tool costs.
- Provides a defined path to human escalation.

### Costs

- Potentially higher cost than a fixed workflow.
- More difficult to debug because execution paths vary.
- Less predictable execution.
- Requires stronger observability and evaluation.

## Consequences

TicketPilot will not attempt to autonomously solve every ticket.

The system is designed to efficiently resolve tickets that can be
safely handled by the agent and escalate cases that cannot be resolved
within the defined execution boundaries.

The bounded loop becomes an explicit safety, cost, and operational
control