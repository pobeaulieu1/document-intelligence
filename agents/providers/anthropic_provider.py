import base64

import anthropic


class AnthropicProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key or None)
        self._model = model

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
        user_content: list[dict] = []

        if file_bytes is not None:
            b64 = base64.standard_b64encode(file_bytes).decode()
            if media_type == "application/pdf":
                user_content.append({
                    "type": "document",
                    "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
                })
            else:
                user_content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64},
                })

        user_content.append({"type": "text", "text": user_message})

        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[
                {
                    "name": tool_name,
                    "description": tool_description,
                    "input_schema": tool_parameters,
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
            messages=[{"role": "user", "content": user_content}],
        )

        tool_block = next((b for b in response.content if b.type == "tool_use"), None)
        if tool_block is None:
            raise ValueError(f"Anthropic ({self._model}) did not call tool '{tool_name}'")

        return tool_block.input
