Target user 

 TicketPilot is for the support team of a mid-level SaaS company that has documents and records covering most of the support questions they receive.

Problem statement 

The main problem is an overload of support tasks, and a large portion of these tasks are repetitive. Handling these repetitive queries manually is costly for the company and consumes the support team's time.

Approximately 70–80% of support queries are repetitive or can be answered using the company's existing documentation. Because humans handle these queries manually, the company incurs additional support costs and customers experience unnecessary delays for simple questions.

Product goal

TicketPilot aims to reduce the workload of the support team by handling eligible repetitive and documentation-answerable support queries automatically. This reduces the team's work effort, lowers support costs for the company, and reduces waiting time for customers.

The goal is not to replace the support team, but to give the team leverage by automatically handling the queries that can be safely resolved without human intervention.


Automation target

The target is for TicketPilot to handle approximately 70–80 out of every 100 tickets that reach the support system without human intervention.

Eligibility

Before handling a ticket automatically, TicketPilot determines whether the ticket is eligible for autonomous handling.

A ticket is eligible when it is a repetitive or straightforward question that can be reliably answered using the company's documentation and does not require human judgment or intervention.


Escalation

Tickets that are not eligible for autonomous handling, require human judgment, involve potentially high-impact issues, or cannot be reliably answered should be sent to the human support team.


Resolution definition

A ticket is considered resolved when the customer indicates that their issue has been resolved or closes the conversation after receiving an answer.

70–80% success definition

The 70–80% target means that TicketPilot should be able to handle 70–80 tickets out of every 100 tickets that reach the support system without human intervention.



Workflow 1: Automated Support Resolution

The user asks a query, and the agent receives it. It then classifies whether the query can be resolved through document-based reasoning or should be given to the support team.

If the query can be handled by the agent, it checks the relevant documents, takes out the relevant information, processes and reasons over it, and returns a response to the user.

The loop continues until the query is resolved or the agent determines that it cannot resolve the issue. If the loop has run multiple times without resolving the issue, the request should be moved to the support team.

The agent sends the final answer to the user.


Workflow 2: Policy Question with Multiple Policies

The user asks a specific question about a policy, but multiple similar policies are present in the documents. The agent has to give control to the support team.

The agent cannot choose between the policies because multiple policies are telling the same thing, and the agent is not able to decide which policy it should select.

The agent transfers the request to the support team first, and then shows the user that it has been transferred and that the agent needs help from the support team.


Workflow 3: Malicious Attack or Jailbreak

The user enters a jailbreak attempt or jailbreak query. The agent then marks the user's ID and immediately blocks the user's access.

The user should be blocked, and their ID and chat should be passed to the support team. The agent should not work with the user.


Functional Requirements

* Can stop a user from using the support agent if a jailbreak is found.
* Can transfer the task to the support team if it is not able to answer.
* Can take the user's query and classify it as document-based reasoning or pass it to the support team.
* Can handle the user's query by fetching the document from the RAG database and then generating the answer.
* Can determine when to pass the query to the support team instead of handling it by itself.
* Can identify multiple policies and pass the query to the support team when this situation occurs.
* Can identify a jailbreak and pass the query to the support team.


Non - functional requirements 

llm cost should be lowest by maintaining the performance by choosing the lowest cost model with performance level performance like good accuracy and speed cost less than 10 ruppe per complete query resultion avg 

reponse time for agent fast balancing with accuracy no hallicination p95 < 30 seconds

agent should not hallicinate in case of it should give controlt to system or tell difrecly 

TicketPilot should prioritize safe behavior over generating a response when reliable information is not available. by trackign and blocking the mallicious user 

agent should not be affected by mallicous activity of user and handel it safely 

if not enough data transfer to support team 



Non-Functional Requirements

1. Cost Efficiency

* TicketPilot should minimize LLM usage cost while maintaining the required answer quality, safety, and response-time performance.
* The system should prefer the lowest-cost model that satisfies the required quality and latency thresholds.
* The average LLM cost for a completely resolved query should be less than ₹10 per query
* Cost should include all LLM calls required to process and resolve the query, including retries and agent iterations.

2. Response Performance

* TicketPilot should provide responses within an acceptable time while maintaining answer quality and safety.
* The p95 end-to-end response time should be less than 30 seconds for autonomously handled queries.
* Agent retries, retrieval, reasoning, and LLM calls should be included when measuring end-to-end response time.
* The system should avoid excessive agent iterations that unnecessarily increase latency and cost.

3. Answer Quality and Hallucination Safety

* TicketPilot should not generate factual answers that are unsupported by reliable information from the company's available knowledge sources.
* When sufficient reliable evidence is unavailable, the system should prefer escalation or an explicit inability-to-answer response rather than generating an unsupported answer.
* Critical tasks should have stricter safety requirements and should not be answered autonomously when the system cannot establish sufficient confidence or supporting evidence.
* Hallucination/unsupported-answer rate should be measurable through evaluation and should remain below the defined production threshold.

4. Safe Failure Behavior

* TicketPilot should prioritize safe behavior over producing an answer when the system cannot reliably determine the correct response.
* Retrieval failures, insufficient evidence, conflicting information, or low-confidence results should not cause the agent to guess.
* When reliable information cannot be established, TicketPilot should safely stop autonomous resolution and escalate the ticket to the human support team.
* The system should fail safely rather than silently returning potentially incorrect information.

5. Security and Malicious-Input Handling

* TicketPilot should remain isolated from malicious instructions, prompt-injection attempts, jailbreaks, and other malicious user activity.
* Malicious input should not be allowed to override the agent's system instructions, security policies, access controls, or tool restrictions.
* When malicious activity is detected, TicketPilot should stop unsafe processing and apply the defined security response.
* Security events should be recorded so that they can be investigated by the support/administration team.
* User blocking or restriction should only occur according to the defined security policy rather than being decided arbitrarily by the LLM.

6. Reliability

* TicketPilot should continue operating safely when individual dependencies fail, including LLM, retrieval, database, or other supporting services.
* Temporary failures should be handled using bounded retries where appropriate.
* Repeated failures should not create infinite agent loops or uncontrolled LLM costs.
* If a dependency failure prevents reliable resolution, the ticket should be escalated or returned through the defined fallback path.

7. Observability

* TicketPilot should provide sufficient logs and metrics to understand how each ticket was processed.
* The system should be able to record important events such as classification, retrieval, LLM calls, retries, escalation, successful resolution, and security events.
* The system should provide the information necessary to measure key production metrics including:

  * autonomous resolution rate
  * successful resolution rate
  * escalation rate
  * p95 response time
  * average LLM cost per resolved query
  * unsupported-answer/hallucination rate
  * security/jailbreak detection results

8. Data and Privacy

* TicketPilot should only access information required to process the support request.
* Customer conversations and company documentation should not be exposed to unauthorized users or processes.
* Access to customer and company data should follow the application's defined authorization and security policies.
