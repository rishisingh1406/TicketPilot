
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




from pyexpat.errors import messages


class Agent:

    def __init__(
        self,
        system_prompt,
        user_query,
        retrieved_chunks,
        conversation_history,
        previous_tool_calls,
        previous_tool_results,
        llm
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
        self.llm = llm


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
        raise RuntimeError("Maximum iteration limit reached")

    def generate_response(self):

        messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            }
        ]

        # Add previous conversation
        messages.extend(self.conversation_history)

        # Add current user query
        messages.append(
            {
                "role": "user",
                "content": self.user_query,
            }
        )

        # Add retrieved information as isolated context
        if self.retrieved_chunks:
            retrieved_context = "\n\n".join(
                f"<retrieved_chunk>\n{chunk}\n</retrieved_chunk>"
                for chunk in self.retrieved_chunks
            )

            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Retrieved information:\n"
                        "<retrieved_context>\n"
                        f"{retrieved_context}\n"
                        "</retrieved_context>"
                    ),
                }
            )

        # Add previous tool calls and results as isolated context
        if self.previous_tool_calls:
            tool_history = []

            for tool_call, tool_result in zip(
                self.previous_tool_calls,
                self.previous_tool_results,
            ):
                tool_history.append(
                    f"<tool_call>\n{tool_call}\n</tool_call>"
                )
                tool_history.append(
                    f"<tool_result>\n{tool_result}\n</tool_result>"
                )

            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Previous tool execution history:\n"
                        "<tool_history>\n"
                        f"{chr(10).join(tool_history)}\n"
                        "</tool_history>"
                    ),
                }
            )

        # Call the LLM
        response = self.call_llm(messages)

        return response

    def call_llm(self, messages):
        return self.llm.generate(messages)

    