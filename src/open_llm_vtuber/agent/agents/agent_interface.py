from abc import ABC, abstractmethod
from typing import AsyncIterator, Union, Tuple, Optional
from enum import Enum
from loguru import logger
import numpy as np
import asyncio

class AgentOutputType(Enum):
    """Agent output type enumeration"""
    RAW_LLM = "raw_llm"        
    TEXT_FOR_TTS = "text_tts" 
    AUDIO_TEXT = "audio_text"      


class AgentInterface(ABC):
    """Base interface for all agent implementations"""
    
    @property
    @abstractmethod
    def output_type(self) -> AgentOutputType:
        """Return the output type of this agent"""
        pass

    @abstractmethod
    async def chat(self, prompt: str) -> Union[
        AsyncIterator[str],                    
        AsyncIterator[str],                    
        AsyncIterator[Tuple[str, str]]         
    ]:
        """
        Chat with the agent asynchronously.

        This function should be implemented by the agent.
        Input format depends on the agent's input_format:
        - TEXT: str - Text prompt
        - AUDIO: np.ndarray - Audio data

        Output format depends on the agent's output_format:
        - RAW_LLM: AsyncIterator[str] - Raw LLM output stream
        - TEXT_FOR_TTS: AsyncIterator[str] - Text ready for TTS
        - AUDIO_TEXT: AsyncIterator[Tuple[str, str]] - (audio_file_path, text) pairs
        
        Args:
            prompt: str - Input according to agent's input_format

        Returns:
            Response stream according to the agent's output_format
        """
        logger.critical("Agent: No chat function set.")
        raise ValueError("Agent: No chat function set.")

    @abstractmethod
    def handle_interrupt(self, heard_response: str) -> None:
        """
        Handle user interruption. This function will be called when the agent is interrupted by the user.

        heard_response: str
            the part of the agent's response heard by the user before interruption
        """
        logger.warning(
            """Agent: No interrupt handler set. The agent may not handle interruptions.
            correctly. The AI may not be able to understand that it was interrupted."""
        )
        pass

    @abstractmethod
    def set_memory_from_history(self, messages: list) -> None:
        """Load the agent's working memory from the message history"""
        pass

    @abstractmethod
    def clear_memory(self) -> None:
        """Clear the agent's working memory"""
        pass