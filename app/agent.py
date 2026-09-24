import json

from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from sqlalchemy.orm import Session

from app.retrieval import KnowledgeRetriever

from schemas import (
    AgentAction,
    AgentResponse,
    AllowedTool,
    RAGResult,
    RetrievedChunk,
    SearchKnowledgeInput,
    TOOL_INPUT_MODELS,
)


# ============================================================
# SEARCH_KNOWLEDGE tool
# ============================================================


def search_knowledge(
    db: Session,
    tool_input: SearchKnowledgeInput,
    retriever: KnowledgeRetriever,
) -> RAGResult:
    """
    Search the approved knowledge base using semantic retrieval.

    The LLM provides only the search query.
    Retrieval policy and database access remain application-owned.
    """

    results = retriever.retrieve_relevant_chunks(
        db=db,
        query=tool_input.query,
        top_k=5,
    )

    chunks = [
        RetrievedChunk(
            chunk_id=str(chunk.chunk_id),
            content=chunk.content,
            source=chunk.source,
            timestamp=chunk.timestamp,
            is_current=chunk.is_current,
            distance=float(distance),
        )
        for chunk, distance in results
    ]

    return RAGResult(
        query=tool_input.query,
        chunks=chunks,
    )


class Agent:

    def __init__(
        self,
        system_prompt,
        user_query,
        retrieved_chunks,
        conversation_history,
        previous_tool_calls,
        previous_tool_results,
        llm,
        db: Session,
        retriever: KnowledgeRetriever,
        tool_handlers: dict[AllowedTool, Callable] | None = None,
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

        # Database session used by tools that require persistence.
        self.db = db

        # Retrieval dependency used by SEARCH_KNOWLEDGE.
        self.retriever = retriever

        # Tool implementations are injected into the agent.
        self.tool_handlers = tool_handlers or {}

        # Latest knowledge retrieved during this agent run.
        # This is attached to the final AgentResponse.
        self.latest_retrieved_context: RAGResult | None = None

    # ============================================================
    # Agent Loop
    # ============================================================

    def run(self):

        while self.iteration <= self.max_iterations:

            # ----------------------------------------------------
            # Generate LLM response
            # ----------------------------------------------------

            response = self.generate_response()

            # ----------------------------------------------------
            # TOOL_CALL
            # ----------------------------------------------------

            if response.action == AgentAction.TOOL_CALL:

                # Check tool-call limit
                if self.tool_calls >= self.max_tool_calls:
                    raise RuntimeError(
                        "Maximum tool-call limit reached"
                    )

                # Check whether the requested tool is allowed
                if not self.is_tool_allowed(response.tool):
                    raise RuntimeError(
                        "Requested tool is not allowed"
                    )

                # Execute tool
                tool_result = self.call_tool(response)

                # Store tool call and result
                self.previous_tool_calls.append(response)
                self.previous_tool_results.append(tool_result)

                # ------------------------------------------------
                # Store latest retrieval evidence
                # ------------------------------------------------

                if isinstance(tool_result, RAGResult):
                    self.latest_retrieved_context = tool_result

                # Increment tool-call count
                self.tool_calls += 1

                # ------------------------------------------------
                # Final iteration
                # ------------------------------------------------

                if self.iteration == self.max_iterations:

                    # The tool from the final iteration has
                    # already been executed and stored.
                    #
                    # Do NOT make another LLM call.
                    return tool_result

                # ------------------------------------------------
                # Continue agent loop
                # ------------------------------------------------

                self.iteration += 1

            # ----------------------------------------------------
            # ANSWER
            # ----------------------------------------------------

            elif response.action == AgentAction.ANSWER:

                # Attach the latest retrieved evidence to the
                # final answer returned by the agent.
                return response.model_copy(
                    update={
                        "retrieved_context": (
                            self.latest_retrieved_context
                        )
                    }
                )

            # ----------------------------------------------------
            # ESCALATE
            # ----------------------------------------------------

            elif response.action == AgentAction.ESCALATE:

                return self.escalate(response)

        # --------------------------------------------------------
        # Maximum iteration limit reached
        # --------------------------------------------------------

        raise RuntimeError(
            "Maximum iteration limit reached"
        )

    # ============================================================
    # Tool Authorization
    # ============================================================

    def is_tool_allowed(
        self,
        tool: AllowedTool | None,
    ) -> bool:
        """
        Check whether the requested tool is both:

        1. A known tool defined by the schema.
        2. Actually registered with the agent.
        """

        if tool is None:
            return False

        if tool not in TOOL_INPUT_MODELS:
            return False

        if tool not in self.tool_handlers:
            return False

        return True

    # ============================================================
    # Tool Dispatch
    # ============================================================

    def call_tool(
        self,
        response: AgentResponse,
    ) -> Any:
        """
        Validate the tool input and dispatch the request
        to the registered tool handler.
        """

        if response.tool is None:
            raise RuntimeError(
                "Cannot execute tool call without a tool"
            )

        if response.tool_input is None:
            raise RuntimeError(
                "Cannot execute tool call without tool_input"
            )

        # --------------------------------------------------------
        # Find the input schema belonging to the requested tool
        # --------------------------------------------------------

        input_model = TOOL_INPUT_MODELS.get(response.tool)

        if input_model is None:
            raise RuntimeError(
                f"No input schema registered for tool: "
                f"{response.tool}"
            )

        # --------------------------------------------------------
        # Validate tool input
        # --------------------------------------------------------

        try:
            validated_input = input_model.model_validate(
                response.tool_input
            )

        except ValidationError as error:
            raise RuntimeError(
                f"Invalid input for tool {response.tool}"
            ) from error

        # --------------------------------------------------------
        # Find the actual tool implementation
        # --------------------------------------------------------

        tool_handler = self.tool_handlers.get(response.tool)

        if tool_handler is None:
            raise RuntimeError(
                f"No handler registered for tool: "
                f"{response.tool}"
            )

        # --------------------------------------------------------
        # Execute SEARCH_KNOWLEDGE
        # --------------------------------------------------------

        if response.tool == AllowedTool.SEARCH_KNOWLEDGE:

            return tool_handler(
                db=self.db,
                tool_input=validated_input,
                retriever=self.retriever,
            )

        # --------------------------------------------------------
        # Execute other tools
        # --------------------------------------------------------

        return tool_handler(validated_input)

    # ============================================================
    # LLM Response Generation
    # ============================================================

    def generate_response(self):

        # ========================================================
        # Build messages
        # ========================================================

        messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            }
        ]

        # --------------------------------------------------------
        # Conversation history
        # --------------------------------------------------------

        messages.extend(self.conversation_history)

        # --------------------------------------------------------
        # Current user query
        # --------------------------------------------------------

        messages.append(
            {
                "role": "user",
                "content": self.user_query,
            }
        )

        # ========================================================
        # Add initially retrieved chunks
        # ========================================================

        if self.retrieved_chunks:

            retrieved_context = "\n\n".join(
                (
                    "<retrieved_chunk>\n"
                    f"{self.serialize_for_prompt(chunk)}\n"
                    "</retrieved_chunk>"
                )
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

        # ========================================================
        # Add previous tool execution history
        # ========================================================

        if self.previous_tool_calls:

            tool_history = []

            for tool_call, tool_result in zip(
                self.previous_tool_calls,
                self.previous_tool_results,
            ):

                tool_history.append(
                    (
                        "<tool_call>\n"
                        f"{self.serialize_for_prompt(tool_call)}\n"
                        "</tool_call>"
                    )
                )

                tool_history.append(
                    (
                        "<tool_result>\n"
                        f"{self.serialize_for_prompt(tool_result)}\n"
                        "</tool_result>"
                    )
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

        # ========================================================
        # First LLM attempt
        # ========================================================

        try:

            response = self.call_llm(messages)

            return response

        except (json.JSONDecodeError, ValidationError):

            # ====================================================
            # One validation retry
            # ====================================================

            try:

                response = self.call_llm(messages)

                return response

            except (
                json.JSONDecodeError,
                ValidationError,
            ) as second_error:

                raise RuntimeError(
                    "LLM returned invalid structured output "
                    "after one retry"
                ) from second_error

    # ============================================================
    # Serialize Data For Prompt
    # ============================================================

    @staticmethod
    def serialize_for_prompt(
        value: Any,
    ) -> str:
        """
        Convert structured objects into predictable text
        before inserting them into the prompt.
        """

        if isinstance(value, BaseModel):

            return value.model_dump_json()

        try:

            return json.dumps(
                value,
                default=str,
            )

        except (TypeError, ValueError):

            return str(value)

    # ============================================================
    # LLM Call
    # ============================================================

    def call_llm(self, messages):

        return self.llm.generate(messages)

    # ============================================================
    # Escalation
    # ============================================================

    def escalate(
        self,
        response: AgentResponse,
    ):
        """
        Escalation implementation will be connected to the
        support handoff/persistence layer.
        """

        return response