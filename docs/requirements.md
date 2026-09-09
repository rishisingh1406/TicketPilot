# Target User

TicketPilot is for the support team of a mid-level SaaS company that has documents and records covering most of the support questions they receive.

# Problem Statement

The main problem is an overload of support tasks, and a large portion of these tasks are repetitive. Handling these repetitive queries manually is costly for the company and consumes the support team's time.

Approximately 70–80% of support queries are repetitive or can be answered using the company's existing documentation. Because humans handle these queries manually, the company incurs additional support costs and customers experience unnecessary delays for simple questions.

# Product Goal

TicketPilot aims to reduce the workload of the support team by handling eligible repetitive and documentation-answerable support queries automatically. This reduces the team's work effort, lowers support costs for the company, and reduces waiting time for customers.

The goal is not to replace the support team, but to give the team leverage by automatically handling the queries that can be safely resolved without human intervention.

# Automation Target

The target is for TicketPilot to handle approximately 70–80 out of every 100 tickets that reach the support system without human intervention.

# Eligibility

Before handling a ticket automatically, TicketPilot determines whether the ticket is eligible for autonomous handling.

A ticket is eligible when it is a repetitive or straightforward question that can be reliably answered using the company's documentation and does not require human judgment or intervention.

# Escalation

Tickets that are not eligible for autonomous handling, require human judgment, involve potentially high-impact issues, or cannot be reliably answered should be sent to the human support team.

When a ticket is escalated, TicketPilot should provide the support team with the original request, a concise summary of the agent's progress, relevant information or conflicts identified, and the reason for escalation.

The customer should also be informed that the request has been transferred to the support team for further assistance.

Once a ticket has been transferred to human support, autonomous processing for that ticket should stop until the support team explicitly returns control to TicketPilot.

# Resolution Definition

A ticket is considered resolved when the customer indicates that their issue has been resolved or closes the conversation after receiving an answer.

# 70–80% Success Definition

The 70–80% target means that TicketPilot should be able to handle 70–80 tickets out of every 100 tickets that reach the support system without human intervention.

# User Workflows

## Workflow 1: Automated Support Resolution

The user asks a query, and the agent receives it. It then classifies whether the query can be resolved through document-based reasoning or should be given to the support team.

If the query can be handled by the agent, it checks the relevant documents, extracts the relevant information, processes and reasons over it, and returns a response to the user.

Before generating an autonomous answer, the agent should verify that the retrieved information provides sufficient evidence to support the answer.

If the required information is missing, insufficient, outdated, incomplete, conflicting, or cannot be reliably established, the agent should not guess and should escalate the request to the support team.

The agent may ask the customer bounded clarification questions when required information is missing and can continue processing if the customer provides the required information.

The agent should continue autonomous processing only while it is making meaningful progress toward a reliable resolution. If it cannot make sufficient progress, obtain reliable supporting evidence, or resolve the query within the defined execution limits, it should stop and escalate the query to the support team.

The agent sends the final answer to the user when the query can be reliably resolved.

## Workflow 2: Policy Question with Multiple Policies

The user asks a specific question about a policy, but multiple similar policies are present in the documents.

If the agent cannot reliably determine which policy applies, it should not choose between the policies arbitrarily.

The agent transfers the request to the support team and shows the user that it has been transferred and that the agent needs help from the support team.

If documentation is outdated, incomplete, or conflicting and the agent cannot reliably determine the authoritative information, the request should also be escalated to the support team.

## Workflow 3: Malicious Attack or Jailbreak

The user enters a jailbreak attempt or malicious query.

For the first version of TicketPilot, malicious-input detection should use defined rule-based detection.

When a jailbreak or malicious attempt is detected, TicketPilot should stop unsafe processing, mark the user's ID, immediately block the user's access to the support agent, and pass the user's ID and chat to the support team.

The agent should not continue working with the blocked user.

# Functional Requirements

* TicketPilot can take the user's query and classify it as document-based reasoning or pass it to the support team.
* TicketPilot can handle an eligible query by fetching relevant information from the RAG database and generating an answer.
* TicketPilot can verify that retrieved information provides sufficient evidence before generating an autonomous answer.
* TicketPilot can determine when to pass the query to the support team instead of handling it by itself.
* TicketPilot can transfer a task to the support team when it is not able to reliably answer.
* TicketPilot can identify multiple conflicting policies and pass the query to the support team when it cannot reliably determine which policy applies.
* TicketPilot can identify a jailbreak or malicious input and pass the query to the support team.
* TicketPilot can stop a user from using the support agent if a jailbreak or malicious input is detected according to the defined security policy.
* TicketPilot can provide the support team with a concise summary of the agent's progress when escalating a ticket.
* TicketPilot can inform the customer when their request has been transferred to the support team.
* TicketPilot can ask the customer for required missing information before escalating when clarification can help resolve the query.
* TicketPilot can reuse previously resolved answers where appropriate.
* Once a ticket is transferred to human support, TicketPilot can stop autonomous processing for that ticket until control is returned by the support team.
* TicketPilot can handle requests that are within its defined documentation-based support scope and can identify requests that are outside that scope.

# Non-Functional Requirements

## 1. Cost Efficiency

* TicketPilot should minimize LLM usage cost while maintaining the required answer quality, safety, and response-time performance.
* The system should prefer the lowest-cost model that satisfies the required quality and latency thresholds.
* The average LLM cost for a completely resolved query should be less than ₹10 per query.
* Cost should include all LLM calls required to process and resolve the query, including retries and agent iterations.
* Reuse of previously resolved answers should help avoid unnecessary repeated LLM processing where appropriate.

## 2. Response Performance

* TicketPilot should provide responses within an acceptable time while maintaining answer quality and safety.
* The p95 end-to-end response time should be less than 30 seconds for autonomously handled queries.
* Agent retries, retrieval, reasoning, and LLM calls should be included when measuring end-to-end response time.
* The system should avoid excessive agent iterations that unnecessarily increase latency and cost.

## 3. Answer Quality and Hallucination Safety

* TicketPilot should not generate factual answers that are unsupported by reliable information from the company's available knowledge sources.
* The agent should verify that retrieved information provides sufficient evidence before generating an autonomous answer.
* When sufficient reliable evidence is unavailable, the system should prefer escalation or an explicit inability-to-answer response rather than generating an unsupported answer.
* Critical tasks should have stricter safety requirements and should not be answered autonomously when the system cannot establish sufficient confidence or supporting evidence.
* Hallucination or unsupported-answer rate should be measurable through evaluation and should remain below the defined production threshold.
* All autonomous drafts should carry citations to their supporting information.

## 4. Safe Failure Behavior

* TicketPilot should prioritize safe behavior over producing an answer when the system cannot reliably determine the correct response.
* Retrieval failures, insufficient evidence, conflicting information, outdated information, incomplete information, or low-confidence results should not cause the agent to guess.
* When reliable information cannot be established, TicketPilot should safely stop autonomous resolution and escalate the ticket to the human support team.
* The system should fail safely rather than silently returning potentially incorrect information.
* If a required dependency fails and TicketPilot cannot reliably continue processing, it should stop autonomous processing and use the defined fallback path, such as escalating the ticket to the support team.

## 5. Security and Malicious-Input Handling

* TicketPilot should remain isolated from malicious instructions, prompt-injection attempts, jailbreaks, and other malicious user activity.
* Malicious input should not be allowed to override the agent's system instructions, security policies, access controls, or tool restrictions.
* For the first version, malicious-input detection should use defined rule-based detection.
* When malicious activity is detected, TicketPilot should stop unsafe processing and apply the defined security response.
* Security events should be recorded so that they can be investigated by the support or administration team.
* User blocking or restriction should only occur according to the defined security policy rather than being decided arbitrarily by the LLM.
* TicketPilot should enforce authorization boundaries so that users cannot receive information they are not authorized to access.

## 6. Reliability

* TicketPilot should continue operating safely when individual dependencies fail, including LLM, retrieval, database, or other supporting services.
* Temporary failures should be handled using bounded retries where appropriate.
* Repeated failures should not create infinite agent loops or uncontrolled LLM costs.
* Autonomous processing should continue only while the agent is making meaningful progress toward a reliable resolution.
* If the agent cannot make sufficient progress, obtain reliable evidence, or resolve the query within the defined execution limits, it should stop and escalate.
* If a dependency failure prevents reliable resolution, the ticket should be escalated or returned through the defined fallback path.
* Excessive request volume should be limited to prevent uncontrolled resource consumption.

## 7. Observability

* TicketPilot should provide sufficient logs and metrics to understand how each ticket was processed.
* The system should be able to record important events such as classification, retrieval, LLM calls, retries, escalation, successful resolution, and security events.
* Escalation should record sufficient information for the support team to understand the customer's request, the reason for escalation, and the progress made by the agent.
* The system should provide the information necessary to measure key production metrics including:

  * autonomous resolution rate
  * successful resolution rate
  * escalation rate
  * p95 response time
  * average LLM cost per resolved query
  * unsupported-answer/hallucination rate
  * security/jailbreak detection results

## 8. Data and Privacy

* TicketPilot should only access information required to process the support request.
* Customer conversations and company documentation should not be exposed to unauthorized users or processes.
* Access to customer and company data should follow the application's defined authorization and security policies.
* Tenant or customer information should remain isolated so that one customer cannot receive another customer's authorized information.

## 9. Knowledge Freshness and Authority

* Company documentation used for autonomous answers should contain information that allows TicketPilot to determine its source and relevant time or version.
* When multiple relevant documents are retrieved, TicketPilot should use the available source, time, or version information to determine the appropriate information.
* If the system cannot reliably determine which information is authoritative or current, it should not guess and should escalate to the support team.

# Constraints and Scope

## Scope

* TicketPilot's autonomous handling is limited to repetitive support queries or queries that can be reliably answered using approved company documentation and records.
* TicketPilot should autonomously resolve a query only when sufficient and reliable information is available from the company's approved knowledge sources.
* Queries that require human judgment, contain conflicting or insufficient information, or cannot be reliably answered from the available knowledge sources are outside the autonomous scope and should be escalated to the human support team.
* TicketPilot should prioritize safe escalation over generating an answer when it cannot establish a reliable answer.
* TicketPilot should not act as a general-purpose support agent outside the defined documentation-based support use case.
* Requests outside the defined support scope should not be autonomously handled.

## Operational Constraints

* TicketPilot should use company-provided documentation and records as the authoritative knowledge source for autonomous answers.
* TicketPilot should not generate an answer solely because the user expects one; reliable supporting information must be available before providing a factual answer.
* Autonomous processing should have a bounded number of agent iterations and retries to prevent infinite loops, excessive latency, and uncontrolled LLM costs.
* LLM usage must remain within the defined cost constraint of less than ₹10 average LLM cost per completely resolved query.
* TicketPilot should not autonomously handle requests that require actions or decisions outside its explicitly defined capabilities.
* When required information, services, or dependencies are unavailable, TicketPilot should use the defined fallback path rather than attempting to continue indefinitely.
* Excessive request volume should be limited to prevent uncontrolled resource consumption.
* Previously resolved answers may be reused where appropriate to avoid unnecessary repeated processing.

## Out of Scope for Autonomous Resolution

* Queries requiring human judgment or decisions that cannot be reliably determined from company documentation.
* Queries where relevant company information is missing, incomplete, outdated, or conflicting.
* Requests involving multiple conflicting policies when TicketPilot cannot reliably determine which policy applies.
* Requests outside the company's supported documentation-based support use case.
* Malicious or jailbreak requests that attempt to bypass TicketPilot's instructions, security controls, or access restrictions.

# Success Criteria

## 1. Autonomous Resolution

The system autonomously resolves 70–80% of all incoming support queries without human intervention.

## 2. Answer Quality and Safety

The system should provide autonomous answers only when they are supported by reliable company information and should escalate instead of generating unsupported answers when reliable information cannot be established.

## 3. Malicious-Input Handling

The system correctly detects defined malicious or jailbreak attempts, blocks or restricts the user according to the security policy, and informs the support team for investigation.

## 4. Safe Escalation

When the system cannot reliably answer a query using the available approved knowledge, it escalates the query to the support team instead of generating an unsupported answer.

# Open Questions / Decisions

## 1. What knowledge can TicketPilot use?

**Decision:**

TicketPilot can use approved company documentation and manuals as its knowledge sources for autonomous support responses.

## 2. What should happen when the agent cannot reliably answer?

**Decision:**

When the agent is unable to reliably answer a query, it should stop autonomous processing and escalate the query to the support team.

## 3. What should happen when multiple policies conflict?

**Decision:**

When multiple policies conflict and the agent cannot reliably determine which policy applies, it should escalate the query to the support team for resolution.

## 4. What should happen during a jailbreak or malicious attempt?

**Decision:**

For the first version, malicious-input detection should use defined rule-based detection. When a jailbreak or malicious attempt is detected, TicketPilot should block the user from further use of the support agent and inform the support team about the incident.

## 5. How should agent loops be controlled?

**Decision:**

The agent should continue processing only while it is making meaningful progress toward a reliable resolution. If it cannot make sufficient progress, obtain reliable supporting evidence, or resolve the query within the defined time or execution limits, it should stop autonomous processing and escalate the query to the support team.

## 6. How should documentation freshness and conflicting information be handled?

**Decision:**

Information about the source and relevant time or version should be added as metadata when information is converted into chunks and stored in the vector store. TicketPilot can use this information to determine which information is current or authoritative. If it cannot reliably determine which information applies, it should escalate to the support team.
