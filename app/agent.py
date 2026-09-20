
"""
INITIALIZE AGENT

    Receive:
        - system prompt / agent instructions
        - user query
        - initially retrieved chunks
        - conversation history
        - previous tool calls and results

    Set:
        iteration = 1
        tool_calls = 0
        max_iterations = 5
        max_tool_calls = 5


WHILE iteration <= max_iterations:

    ┌─────────────────────────────────────┐
    │ Send current agent state to the LLM │
    └──────────────────┬──────────────────┘
                       ↓

    LLM returns structured AgentResponse
                       ↓

    Validate AgentResponse against schema
                       │
              ┌────────┴────────┐
              │                 │
            VALID             INVALID
              │                 │
              │            Retry LLM once
              │                 ↓
              │            Validate again
              │                 │
              │          ┌──────┴──────┐
              │          │             │
              │        VALID         INVALID
              │          │             │
              │          │       Fail execution
              │          │       and raise error
              │          │
              └──────────┴───────────────


    IF AgentResponse.action == TOOL_CALL:

        Check whether requested tool is allowed

            IF tool is not allowed:
                Fail execution
                and raise error

        Check tool-call limit

            IF tool_calls >= max_tool_calls:
                Terminate agent execution
                Do not execute another tool call

            ELSE:
                Execute requested tool

                Store:
                    - tool name
                    - tool input
                    - tool result

                tool_calls = tool_calls + 1


                IF iteration == max_iterations:
                    Terminate agent execution

                    # The tool from iteration 5 has already
                    # been executed and its result stored.
                    # Do NOT send the result back to the LLM.
                    # Do NOT start iteration 6.

                ELSE:
                    iteration = iteration + 1

                    Continue loop
                    with updated agent state


    IF AgentResponse.action == ANSWER:

        Validate/store final answer
        Return answer to user

        Terminate agent execution


    IF AgentResponse.action == ESCALATE:

        Collect:
            - conversation history
            - relevant agent execution history
            - relevant tool calls/results
            - escalation information

        Send case to support team

        Terminate agent execution


END LOOP

"""


class Agent:

    def __init__(
        self,
        system_prompt,
        user_query,
        retrieved_chunks,
        conversation_history,
        previous_tool_calls,
        previous_tool_results,
    ):
        self.system_prompt = system_prompt
        self.user_query = user_query
        self.retrieved_chunks = retrieved_chunks
        self.conversation_history = conversation_history
        self.previous_tool_calls = previous_tool_calls
        self.previous_tool_results = previous_tool_results

        self.iteration = 1
        self.tool_calls = 0
        self.max_iterations = 5
        self.max_tool_calls = 5

    def run(self):

        while self.iteration <= self.max_iterations:

            # Generate LLM response
            response = self.generate_response()

            # Decide what the LLM wants to do
            if response.action == "TOOL_CALL":

                # Check tool-call limit
                if self.tool_calls >= self.max_tool_calls:
                    raise RuntimeError("Maximum tool-call limit reached")

                # Check whether the requested tool is allowed
                if not self.is_tool_allowed(response.tool):
                    raise RuntimeError("Requested tool is not allowed")

                # Execute tool
                tool_result = self.call_tool(response)

                # Store tool call and result
                self.previous_tool_calls.append(response)
                self.previous_tool_results.append(tool_result)

                # Increment tool-call count
                self.tool_calls += 1

                # Current iteration is complete.
                # If this was iteration 5, the while condition
                # will prevent another LLM call.
                self.iteration += 1

            elif response.action == "ANSWER":

                # Return answer to user
                return response

            elif response.action == "ESCALATE":

                # Send conversation/execution context to support
                return self.escalate(response)

        # Maximum iteration limit reached
        raise RuntimeError("Maximum agent iteration limit reached")

    