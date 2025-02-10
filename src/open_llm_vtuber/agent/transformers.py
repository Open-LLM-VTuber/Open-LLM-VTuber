from typing import AsyncIterator, Tuple, Callable, List
from functools import wraps
from .output_types import Actions, SentenceOutput
from ..live2d_model import Live2dModel
from ..config_manager import TTSPreprocessorConfig
from ..utils.sentence_divider import SentenceDivider
from ..utils.sentence_divider import SentenceWithTags, TagState
from ..utils.tts_preprocessor import tts_filter as filter_text
from loguru import logger


def sentence_divider(
    faster_first_response: bool = True,
    segment_method: str = "pysbd",
    valid_tags: List[str] = None,
):
    """
    Decorator that transforms token stream into sentences with tags

    Args:
        faster_first_response: bool - Whether to enable faster first response
        segment_method: str - Method for sentence segmentation
        valid_tags: List[str] - List of valid tags to process
    """

    def decorator(
        func: Callable[..., AsyncIterator[str]],
    ) -> Callable[..., AsyncIterator[SentenceWithTags]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> AsyncIterator[SentenceWithTags]:
            divider = SentenceDivider(
                faster_first_response=faster_first_response,
                segment_method=segment_method,
                valid_tags=valid_tags or [],
            )
            token_stream = func(*args, **kwargs)
            async for sentence in divider.process_stream(token_stream):
                yield sentence

        return wrapper

    return decorator


def actions_extractor(live2d_model: Live2dModel):
    """
    Decorator that extracts actions from sentences
    """

    def decorator(
        func: Callable[..., AsyncIterator[SentenceWithTags]],
    ) -> Callable[..., AsyncIterator[Tuple[SentenceWithTags, Actions]]]:
        @wraps(func)
        async def wrapper(
            *args, **kwargs
        ) -> AsyncIterator[Tuple[SentenceWithTags, Actions]]:
            sentence_stream = func(*args, **kwargs)
            async for sentence in sentence_stream:
                actions = Actions()
                # Only extract emotions for non-tag text
                if not any(
                    tag.state in [TagState.START, TagState.END] for tag in sentence.tags
                ):
                    expressions = live2d_model.extract_emotion(sentence.text)
                    if expressions:
                        actions.expressions = expressions
                yield sentence, actions

        return wrapper

    return decorator


def display_processor():
    """
    Decorator that processes text for display.
    Handles think tag by adding parentheses.
    """

    def decorator(
        func: Callable[..., AsyncIterator[Tuple[SentenceWithTags, Actions]]],
    ) -> Callable[..., AsyncIterator[Tuple[SentenceWithTags, str, Actions]]]:
        @wraps(func)
        async def wrapper(
            *args, **kwargs
        ) -> AsyncIterator[Tuple[SentenceWithTags, str, Actions]]:
            stream = func(*args, **kwargs)

            async for sentence, actions in stream:
                display = sentence.text
                # Handle think tag states
                for tag in sentence.tags:
                    if tag.name == "think":
                        if tag.state == TagState.START:
                            display = "("  # Start of think content
                        elif tag.state == TagState.END:
                            display = ")"  # End of think content
                yield sentence, display, actions

        return wrapper

    return decorator


def tts_filter(
    tts_preprocessor_config: TTSPreprocessorConfig = None,
):
    """
    Decorator that filters text for TTS.
    Skips TTS for think tag content.
    """

    def decorator(
        func: Callable[..., AsyncIterator[Tuple[SentenceWithTags, str, Actions]]],
    ) -> Callable[..., AsyncIterator[SentenceOutput]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> AsyncIterator[SentenceOutput]:
            sentence_stream = func(*args, **kwargs)
            config = tts_preprocessor_config or TTSPreprocessorConfig()

            async for sentence, display, actions in sentence_stream:
                # Skip TTS for think tags and their content
                if any(tag.name == "think" for tag in sentence.tags):
                    tts = ""
                else:
                    tts = filter_text(
                        text=display,
                        remove_special_char=config.remove_special_char,
                        ignore_brackets=config.ignore_brackets,
                        ignore_parentheses=config.ignore_parentheses,
                        ignore_asterisks=config.ignore_asterisks,
                        ignore_angle_brackets=config.ignore_angle_brackets,
                    )

                logger.debug(f"display: {display}")
                logger.debug(f"tts: {tts}")

                yield SentenceOutput(
                    display_text=display,
                    tts_text=tts,
                    actions=actions,
                )

        return wrapper

    return decorator
