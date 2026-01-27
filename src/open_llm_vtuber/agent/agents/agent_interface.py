from abc import ABC, abstractmethod
from typing import AsyncIterator
from loguru import logger

from ..output_types import BaseOutput
from ..input_types import BaseInput


class AgentInterface(ABC):
    """Base interface for all agent implementations"""

    @abstractmethod
    async def chat(self, input_data: BaseInput) -> AsyncIterator[BaseOutput]:
        """
        Chat with the agent asynchronously.

        This function should be implemented by the agent.
        Output type depends on the agent's output_type:
        - SentenceOutput: For text-based responses with display and TTS text
        - AudioOutput: For direct audio output with display text and transcript

        Args:
            input_data: BaseInput - User input data

        Returns:
            AsyncIterator[BaseOutput] - Stream of agent outputs
        """
        logger.critical("Agent: No chat function set.")
        raise ValueError("Agent: No chat function set.")

    @abstractmethod
    def handle_interrupt(self, heard_response: str) -> None:
        """
        Handle user interruption. This function will be called when the agent is interrupted.

        Args:
            heard_response: str - The part of response heard before interruption
        """
        logger.warning(
            """Agent: No interrupt handler set. The agent may not handle interruptions
            correctly. The AI may not be able to understand that it was interrupted."""
        )
        pass

    @abstractmethod
    def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
        """
        Load the agent's working memory from chat history

        Args:
            conf_uid: str - Configuration ID
            history_uid: str - History ID
        """
        pass
