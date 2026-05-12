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
