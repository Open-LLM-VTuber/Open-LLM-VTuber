"""Description: This file contains the implementation of the `AsyncLLMTemplate` class.
This class is responsible for handling asynchronous interaction with OpenAI API
compatible endpoints for language generation where the language model is not
trained using a ChatML format.
"""

import requests
import json
from jinja2 import Template
from loguru import logger
from typing import AsyncIterator, List, Dict, Any

from .stateless_llm_interface import StatelessLLMInterface


TEMPLATES = {
    "LLAMA3": {
        "template": "".join(
            [
                "{{ bos_token }}",
                "{% for message in messages %}",
                "    {{ '<|start_header_id|>' + message['role'] + '<|end_header_id|>\n\n'+ message['content'] | trim + '<|eot_id|>' }}",
                "{% endfor %}",
                "{% if add_generation_prompt %}",
                "    {{ '<|start_header_id|>assistant<|end_header_id|>\n\n' }}",
                "{% endif %}",
            ]
        ),
        "eot_token": "<|eot_id|>",
    },
    "CHATML": {
        "template": "".join(
            [
                "{{ bos_token }}",
                "{% for message in messages %}",
                "    {{ '<|im_start|>' + message['role'] + '\n' + message['content'] | trim + '<|im_end|>\n' }}",
                "{% endfor %}",
                "{% if add_generation_prompt %}",
                "    {{ '<|im_start|>assistant\n' }}",
                "{% endif %}",
            ]
        ),
        "eot_token": "<|im_end|>",
    },
    "ALPACA": {
        "template": "".join(
            [
                """
{{ (messages|selectattr('role', 'equalto', 'system')|list|last).content|trim if (messages|selectattr('role', 'equalto', 'system')|list) else '' }}

{% for message in messages %}
{% if message['role'] == 'user' %}
### Instruction:
{{ message['content']|trim -}}
{% if not loop.last %}


{% endif %}
{% elif message['role'] == 'assistant' %}
### Response:
{{ message['content']|trim -}}
{% if not loop.last %}


{% endif %}
{% elif message['role'] == 'user_context' %}
### Input:
{{ message['content']|trim -}}
{% if not loop.last %}


{% endif %}
{% endif %}
{% endfor %}
{% if add_generation_prompt and messages[-1]['role'] != 'assistant' %}
### Response:
{% endif %}
        """
            ]
        ),
        "eot_token": "###",
    },
}


class AsyncLLMWithTemplate(StatelessLLMInterface):
    def __init__(
        self,
        model: str,
        base_url: str,
        llm_api_key: str = "z",
        organization_id: str = "z",
        project_id: str = "z",
        template: str = "CHATML",
        temperature: float = 1.0,
    ):
        """
        Initializes an instance of the `AsyncLLM` class.

        Parameters:
        - model (str): The model to be used for language generation.
        - base_url (str): The base URL for the OpenAI API.
        - organization_id (str, optional): The organization ID for the OpenAI API. Defaults to "z".
        - project_id (str, optional): The project ID for the OpenAI API. Defaults to "z".
        - llm_api_key (str, optional): The API key for the OpenAI API. Defaults to "z".
        - template (str, optional): The Jinja template to use. Defaults to "LLAMA3".
        - temperature (float, optional): What sampling temperature to use, between 0 and 2. Defaults to 1.0.
        """
        self.completion_url = base_url
        self.model = model
        self.temperature = temperature
        self.template = Template(TEMPLATES[template]["template"])
        self.eot_token = TEMPLATES[template]["eot_token"]
        self.prompt_headers = {
            "Authorization": llm_api_key or "Bearer your_api_key_here"
        }
        logger.info(
            f"Initialized AsyncLLM with the parameters: {self.completion_url} ({template})"
        )

    async def chat_completion(
        self, messages: List[Dict[str, Any]], system: str = None
    ) -> AsyncIterator[str]:
        """
        Generates a chat completion using the OpenAI API asynchronously.

        Parameters:
        - messages (List[Dict[str, Any]]): The list of messages to send to the API.
        - system (str, optional): System prompt to use for this completion.

        Yields:
        - str: The content of each chunk from the API response.

        Raises:
        - APIConnectionError: When the server cannot be reached
        - RateLimitError: When a 429 status code is received
        - APIError: For other API-related errors
        """
        logger.debug(f"Messages: {messages}")
        bos_token = "<|begin_of_text|>"
        stream = None
        try:
            # If system prompt is provided, add it to the messages
            messages_with_system: List[Dict[str, Any]] = messages
            if system:
                messages_with_system = [
                    {"role": "system", "content": system},
                    *messages,
                ]
            prompt = self.template.render(
                messages=messages_with_system,
                bos_token=bos_token,
                add_generation_prompt=True,
            )
            data: Dict = {
                "stream": True,
                "temperature": self.temperature,
                "prompt": prompt,
            }
            with requests.post(
                self.completion_url, headers=self.prompt_headers, json=data, stream=True
            ) as response:
                for line in response.iter_lines():
                    if line:
                        line = self._clean_raw_bytes(line)
                        next_token = self._process_line(line)
                        if next_token:
                            if next_token == self.eot_token:
                                break
                            yield next_token
        except Exception as e:
            logger.error(f"LLM API WITH TEMPLATE: Error occurred: {e}")
            logger.info(f"Base URL: {self.base_url}")
            logger.info(f"Model: {self.model}")
            logger.info(f"Messages: {messages}")
            logger.info(f"temperature: {self.temperature}")
            yield "Error calling the chat endpoint: Error occurred while generating response. See the logs for details."
        finally:
            # make sure the stream is properly closed
            # so when interrupted, no more tokens will being generated.
            if stream:
                logger.debug("Chat completion finished.")
                await stream.close()
                logger.debug("Stream closed.")

    def _clean_raw_bytes(self, line):
        line = line.decode("utf-8")
        line = line.removeprefix("data: ")
        line = json.loads(line)
        return line

    def _process_line(self, line):
        if not (("stop" in line) and (line["stop"])):
            token = line["content"]
            return token
