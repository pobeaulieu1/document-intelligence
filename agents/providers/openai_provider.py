import base64
import json

from openai import OpenAI


class OpenAIProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key, max_retries=6)
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
        user_content: list = []

        if file_bytes is not None and media_type != "application/pdf":
            b64 = base64.standard_b64encode(file_bytes).decode()
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{b64}"},
            })

        user_content.append({"type": "text", "text": user_message})

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_description,
                    "parameters": tool_parameters,
                },
            }],
            tool_choice={"type": "function", "function": {"name": tool_name}},
        )

        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            raise ValueError(f"OpenAI ({self._model}) did not call tool '{tool_name}'")

        return json.loads(tool_calls[0].function.arguments)

    def call_plain(self, system_prompt: str, user_message: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content

    def call_and_maybe_use_tool(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
    ) -> tuple[str | None, str | None, dict | None]:
        openai_tools = [{
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        } for t in tools]
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        response = self._client.chat.completions.create(
            model=self._model,
            messages=full_messages,
            tools=openai_tools,
            tool_choice="auto",
        )
        msg = response.choices[0].message
        if msg.tool_calls:
            call = msg.tool_calls[0]
            return None, call.function.name, json.loads(call.function.arguments)
        return msg.content, None, None

    def continue_after_tool(
        self,
        system_prompt: str,
        messages: list[dict],
        tool_name: str,
        tool_input: dict,
        tool_result: str,
    ) -> str:
        full_messages = (
            [{"role": "system", "content": system_prompt}]
            + list(messages)
            + [
                {"role": "assistant", "content": None, "tool_calls": [{
                    "id": "call_0",
                    "type": "function",
                    "function": {"name": tool_name, "arguments": json.dumps(tool_input)},
                }]},
                {"role": "tool", "tool_call_id": "call_0", "content": tool_result},
            ]
        )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=full_messages,
        )
        return response.choices[0].message.content
