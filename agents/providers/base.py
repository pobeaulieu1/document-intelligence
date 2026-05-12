from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """
    Common interface for all LLM providers.

    Supports both document-grounded calls (Agent 1: extraction) and text-only
    calls (Agent 2: enrichment). Pass file_bytes=None for text-only calls.
    """

    def call_with_tool(
        self,
        system_prompt: str,
        user_message: str,
        tool_name: str,
        tool_description: str,
        tool_parameters: dict,
        file_bytes: bytes | None = None,
        media_type: str | None = None,
    ) -> dict:
        """
        Send a message to the model with forced tool use and return the tool arguments.

        Args:
            system_prompt:    Task instructions for the model.
            user_message:     The user-turn message accompanying the file or data.
            tool_name:        Name of the tool the model must call.
            tool_description: Human-readable description of the tool.
            tool_parameters:  JSON Schema object describing the tool's parameters.
            file_bytes:       Raw bytes of an image or PDF. None for text-only calls.
            media_type:       MIME type (e.g. "image/jpeg", "application/pdf").

        Returns:
            A plain Python dict containing the tool call arguments.
        """
        ...

    def call_plain(self, system_prompt: str, user_message: str) -> str:
        """Send a plain text prompt and return the model's text response."""
        ...

    def call_and_maybe_use_tool(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
    ) -> tuple[str | None, str | None, dict | None]:
        """
        Send a conversation with optional tools available.
        messages: list of {"role": "user"|"assistant", "content": str}
        Returns (text, None, None) if the model responded with text.
        Returns (None, tool_name, tool_input) if the model called a tool.
        """
        ...

    def continue_after_tool(
        self,
        system_prompt: str,
        messages: list[dict],
        tool_name: str,
        tool_input: dict,
        tool_result: str,
    ) -> str:
        """Send a tool result back to the model and return its follow-up text."""
        ...
