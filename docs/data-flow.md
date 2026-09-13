# TicketPilot — Data Flow

## 1. Purpose

This document describes the end-to-end request lifecycle of TicketPilot.

The flow is designed around explicit boundaries between components. For each boundary, the system defines:

* What data is passed
* Data format
* Communication model
* Ownership
* Failure behavior

The system is synchronous for the current version.

---

# 2. High-Level Request Flow

```text
Client
  ↓
FastAPI
  ↓
Ticket Lifecycle
  ↓
Initial Retrieval
  ↓
Handleability Classifier
  ↓
Decision Function
  ├──────────────→ Support Team
  │
  └──────────────→ Agent Orchestrator
                         ↓
                        LLM
                         ↓
                  Structured Decision
                    ↙          ↘
              TOOL_CALL    NO_TOOL_CALL
                  ↓              ↓
                 RAG        Candidate Answer
                  ↓              ↓
               Result      Answer Validator
                  ↓              ↓
                 LLM       Valid / Invalid
                  ↓
            another action
             OR final answer
                  ↓
           Answer Validator
                  ↓
              Persist
                  ↓
               FastAPI
                  ↓
                Client
```

---

# 3. External Request

The client sends a request to a FastAPI endpoint.

### Request format

```json
{
  "user_id": "user_123",
  "message": "I was charged twice for my subscription"
}
```

The initial request contains:

* `user_id`
* `message`

### Responsibility

FastAPI is responsible for validating the external API request.

If `user_id` or `message` is missing or malformed, this is an **API boundary problem**, not an Agent system problem.

FastAPI should reject the request before it enters the agent workflow.

---

# 4. FastAPI → Ticket Lifecycle

### Data

```json
{
  "user_id": "user_123",
  "message": "I was charged twice for my subscription"
}
```

### Communication

Synchronous.

### Ownership

Ticket Lifecycle owns the ticket state.

### Responsibility

Ticket Lifecycle creates the ticket and adds the ticket identifier to the evolving ticket state.

Conceptually:

```json
{
  "user_id": "user_123",
  "message": "I was charged twice for my subscription",
  "ticket_id": "ticket_123"
}
```

The system is conceptually evolving the same ticket state by adding fields rather than creating unrelated objects at every stage.

### Failure

If ticket creation fails:

```text
Ticket Lifecycle
       ↓
Structured error/result
       ↓
FastAPI
       ↓
Client
```

FastAPI is responsible for converting the failure into the appropriate HTTP response.

---

# 5. Ticket Lifecycle → Handleability Check

After creating the ticket, the system determines whether the request can be handled by the agent.

### Data

The Handleability Check receives:

```json
{
  "message": "I was charged twice for my subscription"
}
```

Only the message is passed at this boundary.

### Communication

Synchronous.

### Ownership

* Ticket Lifecycle owns the overall ticket state.
* Handleability Check owns the handleability decision.

### Failure

If the Handleability Check fails, the ticket is escalated to the Support Team.

---

# 6. Handleability Check → Initial Retrieval

The Handleability Check needs trusted knowledge before deciding whether the agent can handle the request.

Therefore, it first performs an initial retrieval.

### Data

Input:

```json
{
  "message": "I was charged twice for my subscription"
}
```

### Communication

Synchronous.

### Ownership

Handleability Check owns this operation.

### Retrieval responsibility

Initial Retrieval searches the trusted knowledge source for information relevant to the user's message.

Conceptually:

```text
User message
     ↓
Embedding
     ↓
Vector search
     ↓
Relevant chunks
     ↓
Text + document information + metadata
```

### Retrieval result

Each retrieved result contains:

```json
{
  "chunk_text": "....",
  "document_id": "doc_123",
  "metadata": {
    "...": "..."
  }
}
```

Multiple relevant chunks may be returned.

### No relevant knowledge

If retrieval successfully executes but finds no relevant chunks, this means the system has no similar trusted knowledge for the request.

The ticket is therefore marked:

```json
{
  "handlable": false
}
```

and sent to Support.

### Retrieval system failure

If the retrieval operation itself fails, it should be retried a bounded number of times.

The exact retry count is **TBD**.

If retrieval continues to fail after the retry limit, it is treated as a retrieval/tool failure and the request should move toward Support.

---

# 7. Initial Retrieval → Handleability Classifier

After successful retrieval, the classifier receives the user's message together with the retrieved trusted knowledge.

### Data

```text
message
+
retrieved chunks
```

Conceptually:

```json
{
  "message": "I was charged twice for my subscription",
  "retrieved_chunks": [
    {
      "chunk_text": "....",
      "document_id": "doc_123",
      "metadata": {
        "...": "..."
      }
    }
  ]
}
```

### Communication

Synchronous.

### Responsibility

The LLM classifier determines whether the specific request can be handled by the system using trusted documentation.

### Definition of handlable

A request is **handlable** when the system has sufficient trusted knowledge to answer the user's specific request.

The classifier produces:

```json
{
  "handlable": true
}
```

or:

```json
{
  "handlable": false
}
```

The classifier does **not** decide the route.

Another component, the Decision Function, makes the routing decision.

### Ownership

The Handleability Classifier owns the handleability decision.

Ticket Lifecycle remains responsible for the overall ticket state.

### LLM failure

If the classifier LLM fails:

```text
Classifier LLM
      ↓
Retry
      ↓
Retry limit reached
      ↓
Support Team
```

The exact retry count is **TBD**.

### Malformed LLM response

If the classifier returns malformed output:

```text
LLM response
     ↓
Validate
     ↓
Invalid
     ↓
Retry LLM
```

Malformed output must not be accepted as a valid `handlable` value.

---

# 8. Handleability Classifier → Decision Function

The classifier has produced:

```json
{
  "handlable": true
}
```

or:

```json
{
  "handlable": false
}
```

### Communication

Synchronous.

### Responsibility

The Decision Function reads the classifier result and determines the route.

The classifier itself does not perform routing.

### Routing

```text
handlable = false
        ↓
Support Team
```

```text
handlable = true
        ↓
Agent Orchestrator
```

---

# 9. Decision Function → Agent Orchestrator

This boundary is used when:

```json
{
  "handlable": true
}
```

### Data

The Decision Function passes the client message using only the selected fields required by the Agent Orchestrator.

The message is represented as a JSON object.

Example:

```json
{
  "message": "I was charged twice for my subscription"
}
```

### Communication

Synchronous.

### Ownership

Agent Orchestrator owns agent execution.

Ticket Lifecycle continues to own the overall ticket state.

### Behavior

The Decision Function waits for the Agent Orchestrator because this boundary is synchronous.

### Failure

If the Agent Orchestrator fails before it can process the request:

```text
Agent Orchestrator
       ↓
     Retry
       ↓
  fails again
       ↓
Support Team
```

The exact retry count is **TBD**.

---

# 10. Agent Orchestrator → LLM

The Agent Orchestrator starts the agent loop by sending the query to the LLM.

### Data

JSON format.

Conceptually:

```json
{
  "query": "I was charged twice for my subscription"
}
```

The exact complete LLM input contract is **TBD**.

The agent may also need contextual information as the loop progresses, such as previous tool results and previous agent state.

---

# 11. LLM → Agent Orchestrator

The LLM does not directly execute tools.

Instead, it must return a fixed structured response that the Agent Orchestrator can validate and interpret.

The LLM is constrained to the system's predefined response format.

Currently, there are two identified outcomes.

---

## 11.1 TOOL_CALL

When the LLM needs information from the knowledge source:

```json
{
  "action": "TOOL_CALL",
  "tool": "RAG",
  "message": "duplicate subscription charge policy"
}
```

### Responsibility

The LLM decides:

* that a tool is required
* which allowed tool to use
* what message/query should be sent to that tool

The only currently allowed tool is:

```text
RAG
```

The LLM does not execute RAG itself.

The Agent Orchestrator validates the structured response and executes the requested tool.

---

## 11.2 NO_TOOL_CALL

When the LLM determines that it does not need to call RAG:

```json
{
  "action": "NO_TOOL_CALL",
  "message": "Your subscription was charged twice..."
}
```

The `message` represents the candidate answer.

It must subsequently pass through the Answer Validator before being considered the final answer.

---

# 12. Agent Orchestrator → RAG

When the LLM returns:

```json
{
  "action": "TOOL_CALL",
  "tool": "RAG",
  "message": "duplicate subscription charge policy"
}
```

the Agent Orchestrator executes the RAG tool.

### Data

JSON.

Conceptually:

```json
{
  "message": "duplicate subscription charge policy"
}
```

### Communication

Synchronous.

### Ownership

Agent Orchestrator owns the execution of the RAG tool call.

### Tool execution

```text
LLM
 ↓
TOOL_CALL
 ↓
Agent Orchestrator
 ↓
RAG
```

The query/message sent to RAG is generated by the LLM.

---

# 13. RAG → Agent Orchestrator

RAG returns retrieval results to the Agent Orchestrator.

The result contains the relevant knowledge retrieved from the trusted documentation.

Conceptually:

```json
{
  "results": [
    {
      "chunk_text": "....",
      "document_id": "doc_123",
      "metadata": {
        "...": "..."
      }
    }
  ]
}
```

The exact final response schema is **TBD**.

### Communication

Synchronous.

### Success

The retrieval result is added to the agent's current context.

The Agent Orchestrator then sends the relevant result back to the LLM.

```text
RAG
 ↓
retrieval result
 ↓
Agent Orchestrator
 ↓
LLM
```

The LLM then reasons again using the new result and decides what to do next.

---

# 14. RAG Failure Handling

A distinction is made between:

### Successful retrieval with no relevant information

```text
RAG succeeds
     ↓
No relevant chunks
```

This is a valid result, not an infrastructure failure.

### RAG execution failure

```text
RAG fails
   ↓
Retry
   ↓
Retry limit reached
```

The exact retry limit is **TBD**.

After repeated failure, the failure is returned to the LLM as part of the agent context.

The LLM then decides the next action.

The Agent Orchestrator does not automatically decide the final response solely because RAG failed.

Conceptually:

```text
RAG failure
     ↓
Retry
     ↓
Repeated failure
     ↓
Failure result
     ↓
LLM
     ↓
LLM decides next action
```

---

# 15. Agent Loop

The core Agent Orchestrator loop is:

```text
Agent Orchestrator
        ↓
       LLM
        ↓
Structured response
        ↓
   ┌────┴───────────┐
   ↓                ↓
TOOL_CALL      NO_TOOL_CALL
   ↓                ↓
  RAG          Candidate answer
   ↓                ↓
Result              │
   ↓                │
   └──────→ LLM ←───┘
              ↓
       another action
              OR
        final answer
```

The LLM can use the available context and previous results to make its next decision.

The system does not expose or depend on private chain-of-thought. What crosses the component boundary is the structured decision and the information required to continue execution.

---

# 16. Agent Execution Limits

The agent must be bounded.

The current project constraint is:

```text
Maximum agent iterations = 5
```

Tool-level retries are also bounded.

The exact tool retry limits are **TBD**.

The agent should have access to execution-state information necessary to make bounded decisions, including information such as:

* current iteration
* tool attempts
* tool failures
* elapsed/remaining execution time

The exact representation of this state is **TBD**.

---

# 17. Final Answer

When the LLM returns a `NO_TOOL_CALL` response, its message becomes a candidate final answer.

Example:

```json
{
  "action": "NO_TOOL_CALL",
  "message": "Your subscription was charged twice..."
}
```

The candidate answer is not immediately returned to the user.

It first goes through the Answer Validator.

---

# 18. Answer Validator

The Answer Validator checks whether the generated response correctly answers the user's request.

### Definition of correct

The answer is correct when it matches and correctly addresses the user's query/request.

Conceptually:

```text
Candidate Answer
       ↓
Answer Validator
       ↓
 ┌─────┴─────┐
 ↓           ↓
VALID      INVALID
 ↓           ↓
Persist     Retry /
            Escalate
```

The exact invalid-answer retry behavior is **TBD**.

---

# 19. Persistence

After the final answer has been successfully validated:

```text
Validated Answer
       ↓
Persistence
       ↓
Ticket State Updated
```

The validated result and relevant ticket state are persisted.

Ticket Lifecycle remains the owner of the overall ticket state.

The exact persistence schema is defined separately in the data/schema contracts.

---

# 20. Persistence → FastAPI → Client

After successful persistence:

```text
Validated Answer
       ↓
Persistence
       ↓
FastAPI
       ↓
HTTP Response
       ↓
Client
```

FastAPI is the external communication boundary.

The agent system does not communicate directly with the external client outside the API boundary.

---

# 21. Complete End-to-End Flow

```text
                         CLIENT
                            │
                            │ JSON
                            │
                            ▼
                       ┌─────────┐
                       │ FastAPI │
                       └────┬────┘
                            │
                            │ user_id + message
                            ▼
                  ┌───────────────────┐
                  │ Ticket Lifecycle  │
                  │                   │
                  │ Create ticket     │
                  │ Own ticket state  │
                  └─────────┬─────────┘
                            │
                            │ message
                            ▼
                  ┌───────────────────┐
                  │ Handleability     │
                  │ Check             │
                  └─────────┬─────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Initial RAG   │
                    │ Retrieval     │
                    └───────┬───────┘
                            │
                    retrieved chunks
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Handleability        │
                 │ Classifier           │
                 │                      │
                 │ LLM → true / false  │
                 └──────────┬───────────┘
                            │
                     handlable value
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Decision Function    │
                 └──────────┬───────────┘
                            │
               ┌────────────┴────────────┐
               │                         │
        false  │                         │ true
               ▼                         ▼
       ┌──────────────┐       ┌────────────────────┐
       │ Support Team │       │ Agent Orchestrator │
       └──────────────┘       └─────────┬──────────┘
                                        │
                                        │ JSON query
                                        ▼
                                     ┌─────┐
                                     │ LLM │
                                     └──┬──┘
                                        │
                              structured response
                                        │
                           ┌────────────┴────────────┐
                           │                         │
                      TOOL_CALL                NO_TOOL_CALL
                           │                         │
                           ▼                         ▼
                         RAG                   Candidate Answer
                           │                         │
                           │ result                  │
                           ▼                         ▼
                    Agent Orchestrator       Answer Validator
                           │                         │
                           │                         │
                           ▼                         │
                          LLM                       │
                           │                         │
                           └─────── loop ────────────┘
                                                     │
                                                  VALID
                                                     │
                                                     ▼
                                                Persistence
                                                     │
                                                     ▼
                                                  FastAPI
                                                     │
                                                     ▼
                                                   CLIENT
```

---

# 22. Current Contract Decisions

| Boundary                               | Data                    | Format | Communication | Owner                            |
| -------------------------------------- | ----------------------- | ------ | ------------- | -------------------------------- |
| FastAPI → Ticket Lifecycle             | `user_id`, `message`    | JSON   | Sync          | Ticket Lifecycle                 |
| Ticket Lifecycle → Handleability       | `message`               | JSON   | Sync          | Ticket Lifecycle / Handleability |
| Handleability → Initial Retrieval      | `message`               | JSON   | Sync          | Handleability                    |
| Initial Retrieval → Classifier         | `message` + chunks      | JSON   | Sync          | Classifier                       |
| Classifier → Decision Function         | `handlable`             | JSON   | Sync          | Classifier                       |
| Decision Function → Agent Orchestrator | selected message fields | JSON   | Sync          | Agent Orchestrator               |
| Agent Orchestrator → LLM               | query                   | JSON   | Sync          | Agent Orchestrator               |
| LLM → Agent Orchestrator               | structured action       | JSON   | Sync          | Agent Orchestrator interprets    |
| Agent Orchestrator → RAG               | RAG query               | JSON   | Sync          | Agent Orchestrator               |
| RAG → Agent Orchestrator               | retrieval result        | JSON   | Sync          | Agent Orchestrator               |
| Final Answer → Validator               | candidate answer        | JSON   | Sync          | Validator                        |
| Validated Answer → Persistence         | final state/result      | TBD    | Sync          | Ticket Lifecycle                 |

---

# 23. Important Failure Distinctions

The system should distinguish between a **valid negative result** and an **execution failure**.

### No relevant knowledge

```text
Retrieval succeeds
      ↓
No relevant chunks
      ↓
handlable = false
      ↓
Support
```

### Retrieval failure

```text
Retrieval fails
      ↓
Retry
      ↓
Retry limit
      ↓
Tool failure
      ↓
LLM / Support depending on stage
```

### Valid classifier result

```text
LLM → {"handlable": false}
```

This is a valid decision, not an error.

### Malformed classifier result

```text
LLM → malformed JSON / invalid schema
                ↓
             validation
                ↓
              retry
```

This is a contract/validation failure.

### RAG tool failure

```text
RAG fails
   ↓
retry
   ↓
repeated failure
   ↓
LLM receives failure
   ↓
LLM chooses next action
```

---

# 24. Decisions Still To Be Finalized

The control flow is now substantially defined, but these contracts still need explicit decisions:

1. Exact retry count for Initial Retrieval.
2. Exact retry count for Handleability Classifier.
3. Exact retry count for Agent Orchestrator startup.
4. Exact retry count for RAG.
5. Exact schema for the complete LLM input.
6. Exact Pydantic schema for the LLM structured response.
7. Exact RAG response schema.
8. Exact agent execution-state schema.
9. Exact Answer Validator schema and invalid-answer behavior.
10. Account information flow required by the original Day 3 `parallel(retrieve, account)` requirement.
11. Security/Jailbreak branch from the Day 2 Integrity Gate.
12. Human Support/Reviewer handoff contract.
13. Persistence schema and exact state transitions.
14. Exact final FastAPI response schema.

These should be decided before treating `data-flow.md` as complete.
