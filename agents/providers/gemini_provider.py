from google import genai
from google.genai import types


class GeminiProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
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
        contents: list = []
        if file_bytes is not None:
            contents.append(types.Part.from_bytes(data=file_bytes, mime_type=media_type))
        contents.append(user_message)

        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[
                    types.Tool(
                        function_declarations=[
                            types.FunctionDeclaration(
                                name=tool_name,
                                description=tool_description,
                                parameters=self._build_schema(tool_parameters),
                            )
                        ]
                    )
                ],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode="ANY",
                        allowed_function_names=[tool_name],
                    )
                ),
            ),
        )

        fc = next(
            (
                p.function_call
                for p in response.candidates[0].content.parts
                if p.function_call and p.function_call.name == tool_name
            ),
            None,
        )
        if fc is None:
            raise ValueError(f"Gemini ({self._model}) did not call tool '{tool_name}'")

        return dict(fc.args)

    def call_and_maybe_use_tool(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
    ) -> tuple[str | None, str | None, dict | None]:
        user_message = messages[-1]["content"] if messages else ""
        return self.call_plain(system_prompt, user_message), None, None

    def continue_after_tool(
        self,
        system_prompt: str,
        messages: list[dict],
        tool_name: str,
        tool_input: dict,
        tool_result: str,
    ) -> str:
        user_message = messages[-1]["content"] if messages else ""
        return self.call_plain(
            system_prompt,
            f"{user_message}\n\nThe {tool_name} action completed: {tool_result}",
        )

    def call_plain(self, system_prompt: str, user_message: str) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=user_message,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
        )
        return response.text

    def _build_schema(self, schema: dict) -> types.Schema:
        """Convert a standard JSON Schema dict to a google.genai Schema object."""
        type_map = {
            "string": types.Type.STRING,
            "number": types.Type.NUMBER,
            "integer": types.Type.INTEGER,
            "boolean": types.Type.BOOLEAN,
            "array": types.Type.ARRAY,
            "object": types.Type.OBJECT,
        }

        raw_type = schema.get("type", "string")
        if isinstance(raw_type, list):
            raw_type = next((t for t in raw_type if t != "null"), "string")

        kwargs: dict = {"type": type_map.get(raw_type, types.Type.STRING)}

        if "description" in schema:
            kwargs["description"] = schema["description"]
        if "required" in schema:
            kwargs["required"] = schema["required"]
        if "properties" in schema:
            kwargs["properties"] = {
                k: self._build_schema(v) for k, v in schema["properties"].items()
            }
        if "items" in schema:
            kwargs["items"] = self._build_schema(schema["items"])

        return types.Schema(**kwargs)
