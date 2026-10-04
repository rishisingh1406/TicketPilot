# TicketPilot Evaluation Metrics

## Purpose

This document defines the metrics used by the TicketPilot evaluation harness.

The evaluation harness measures whether TicketPilot produces reliable decisions and responses against a fixed 30-ticket golden dataset.

The goal is not to maximize a single score. The goal is to detect regressions across correctness, safety, evidence quality, reliability, latency, and cost.

---

## 1. Action Accuracy

### Definition

Action accuracy measures the percentage of evaluation cases where the agent's final action matches the expected action in the golden set.

The supported actions are:

* `ANSWER`
* `ESCALATE`
* `TOOL_CALL` is an intermediate action and is not treated as the final expected customer-facing action.

### Formula

`action_accuracy = correct_final_actions / total_cases`

### Why it exists

This measures whether the agent makes the correct high-level decision for each ticket.

### What can break it

* Incorrect system-prompt instructions
* Poor retrieval
* Incorrect model reasoning
* Invalid structured output
* Incorrect action parsing
* Incorrect golden-set labels

---

## 2. Structured Output Validity

### Definition

Structured-output validity measures whether the LLM response conforms to the application's `AgentLLMResponse` schema and action-specific validation rules.

A response is valid only when it can be successfully parsed and validated by Pydantic.

### Formula

`structured_output_validity = valid_structured_outputs / total_cases`

### Why it exists

TicketPilot depends on structured model output to make deterministic application decisions.

A semantically good response that violates the schema is still an engineering failure because the application cannot safely consume it.

### What can break it

* Model returns malformed JSON
* Model returns an invalid enum/tool
* Required fields are missing
* Action-specific fields contain invalid values
* Provider structured-output behavior changes
* Schema and system prompt become inconsistent

---

## 3. Escalation Precision

### Definition

Escalation precision measures how often an escalation made by the agent was actually required.

### Formula

`precision = true_positives / (true_positives + false_positives)`

Where:

* True positive = agent escalated and the golden set expected escalation
* False positive = agent escalated but the golden set expected a non-escalation action

### Why it exists

Low precision means the agent is unnecessarily sending tickets to humans.

This increases human workload and reduces automation value.

### What can break it

* Overly conservative escalation rules
* Poor retrieval
* Ambiguous system instructions
* Model misunderstanding
* Incorrect golden-set labels

---

## 4. Escalation Recall

### Definition

Escalation recall measures how many tickets that should have been escalated were actually escalated.

### Formula

`recall = true_positives / (true_positives + false_negatives)`

Where:

* True positive = agent escalated and escalation was required
* False negative = agent answered or otherwise avoided escalation when escalation was required

### Why it exists

Low recall is a safety and reliability problem.

A false negative can cause TicketPilot to answer a customer when human review was required.

### What can break it

* Missing escalation policy
* Insufficient retrieval
* Prompt-injection handling failure
* Unanswerable-question handling failure
* Model decision failure

---

## 5. Citation Correctness

### Definition

Citation correctness measures whether the sources expected by the golden set are present in the sources retrieved for the case.

### Formula

`citation_correctness = cases_with_required_source / citation_required_cases`

### Why it exists

A customer-facing answer should be grounded in the relevant knowledge-base source.

This metric verifies that the expected evidence was retrieved.

### Important limitation

Citation correctness does not prove that the generated answer is actually supported by the cited source.

A source can be retrieved but still fail to support the generated claim.

### What can break it

* Retrieval failure
* Poor embeddings
* Poor query construction
* Incorrect source metadata
* Incorrect golden-set source labels

---

## 6. Citation Faithfulness

### Definition

Citation faithfulness measures whether claims in the generated answer are actually supported by the retrieved evidence.

TicketPilot uses an LLM judge with a versioned rubric.

Current rubric:

`eval/rubrics/citation_faithfulness_v1.md`

Possible outcomes include:

* `SUPPORTED`
* `PARTIALLY_SUPPORTED`
* `UNSUPPORTED`

### Why it exists

Retrieving the correct document is not sufficient.

The generated answer must remain faithful to the information contained in that document.

### What can break it

* Hallucinated claims
* Overgeneralization
* Incorrect interpretation of retrieved evidence
* Citation pointing to a source that does not support the claim
* LLM judge failure
* Judge prompt/rubric drift

### Dependency note

The LLM judge is itself an external dependency.

A judge outage or malformed judge response must not be confused with a production-agent failure.

---

## 7. Latency

### Definition

Latency measures the wall-clock time required to evaluate one production ticket through the TicketPilot agent.

### Reported metrics

* Average latency
* P95 latency

### Why it exists

TicketPilot has an operational target of keeping customer-facing resolution latency below the defined NFR.

P95 is especially important because average latency can hide slow tail cases.

### What can break it

* Slow LLM responses
* Multiple LLM calls
* Structured-output retries
* Slow embedding generation
* Slow PostgreSQL retrieval
* Network latency
* Provider rate limiting

---

## 8. Production Cost per Ticket

### Definition

Production cost measures the estimated LLM cost incurred by TicketPilot while processing one evaluation case.

Production-agent usage is measured separately from the LLM judge cost.

### Why it exists

Evaluation cost should not be confused with production cost.

The production metric answers:

> How expensive would this agent interaction be at runtime?

### Dependency failures

* Missing token usage metadata
* Incorrect model pricing configuration
* Provider usage reporting changes
* Retry behavior increasing token consumption

---

## 9. Judge Cost

### Definition

Judge cost is the estimated cost of the LLM calls used to evaluate citation faithfulness.

It is reported separately from production cost.

### Why it exists

The judge is part of the evaluation infrastructure, not the production TicketPilot request path.

Combining the two would make production cost appear artificially high.

---

## 10. Production Errors

### Definition

A production error occurs when the production evaluation execution raises an unexpected exception that prevents normal evaluation of the case.

This is separate from structured-output validity.

For example:

* `production_error = None`
* `structured_output_valid = False`

means the application completed its evaluation flow, but the model output violated the structured-output contract.

### Why this distinction matters

A production exception and an invalid model response require different engineering fixes.

Production exception → application/infrastructure failure.

Invalid structured output → model/schema/retry reliability failure.

---

## 11. Baseline Discipline

Every baseline must record:

* Dataset name
* Dataset version
* Number of cases
* Model
* System-prompt version
* Evaluation rubric version
* Metrics
* Known limitations

Historical baselines must not be overwritten.

A new system or prompt version should create a new baseline for comparison.

---

## Interpretation Rule

No single metric represents overall quality.

TicketPilot should be evaluated across:

1. Decision correctness
2. Safety through escalation recall
3. Automation efficiency through escalation precision
4. Evidence retrieval
5. Citation faithfulness
6. Structured-output reliability
7. Latency
8. Production cost
9. Production errors

A change is considered an improvement only when it improves the target behavior without introducing unacceptable regressions elsewhere.
