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


