import re
from typing import List, Tuple, AsyncIterator, Optional, Union, Dict, Any
import pysbd
from loguru import logger
from langdetect import detect
from enum import Enum
from dataclasses import dataclass

# Constants for additional checks
COMMAS = [
    ",",
    "،",
    "，",
    "、",
    "፣",
    "၊",
    ";",
    "΄",
    "‛",
    "।",
    "﹐",
    "꓾",
    "⹁",
    "︐",
    "﹑",
    "､",
    "،",
]

END_PUNCTUATIONS = [".", "!", "?", "。", "！", "？", "...", "。。。"]
ABBREVIATIONS = [
    "Mr.",
    "Mrs.",
    "Dr.",
    "Prof.",
    "Inc.",
    "Ltd.",
    "Jr.",
    "Sr.",
    "e.g.",
    "i.e.",
    "vs.",
    "St.",
    "Rd.",
    "Dr.",
]

# Set of languages directly supported by pysbd
SUPPORTED_LANGUAGES = {
    "am",
    "ar",
    "bg",
    "da",
    "de",
    "el",
    "en",
    "es",
    "fa",
    "fr",
    "hi",
    "hy",
    "it",
    "ja",
    "kk",
    "mr",
    "my",
    "nl",
    "pl",
    "ru",
    "sk",
    "ur",
    "zh",
}


def detect_language(text: str) -> str:
    """
    Detect text language and check if it's supported by pysbd.
    Returns None for unsupported languages.
    """
    try:
        detected = detect(text)
        return detected if detected in SUPPORTED_LANGUAGES else None
    except Exception as e:
        logger.debug(f"Language detection failed, language not supported by pysdb: {e}")
        return None


def is_complete_sentence(text: str) -> bool:
    """
    Check if text ends with sentence-ending punctuation and not abbreviation.

    Args:
        text: Text to check

    Returns:
        bool: Whether the text is a complete sentence
    """
    text = text.strip()
    if not text:
        return False

    if any(text.endswith(abbrev) for abbrev in ABBREVIATIONS):
        return False

    return any(text.endswith(punct) for punct in END_PUNCTUATIONS)


def contains_comma(text: str) -> bool:
    """
    Check if text contains any comma.

    Args:
        text: Text to check

    Returns:
        bool: Whether the text contains a comma
    """
    return any(comma in text for comma in COMMAS)


def comma_splitter(text: str) -> Tuple[str, str]:
    """
    Process text and split it at the first comma.
    Returns the split text (including the comma) and the remaining text.

    Args:
        text: Text to split

    Returns:
        Tuple[str, str]: (split text with comma, remaining text)
    """
    if not text:
        return [], ""

    for comma in COMMAS:
        if comma in text:
            split_text = text.split(comma, 1)
            # Return first part with the comma
            return split_text[0].strip() + comma, split_text[1].strip()
    return text, ""


def has_punctuation(text: str) -> bool:
    """
    Check if the text is a punctuation mark.

    Args:
        text: Text to check

    Returns:
        bool: Whether the text is a punctuation mark
    """
    for punct in COMMAS + END_PUNCTUATIONS:
        if punct in text:
            return True
    return False


def contains_end_punctuation(text: str) -> bool:
    """
    Check if text contains any sentence-ending punctuation.

    Args:
        text: Text to check

    Returns:
        bool: Whether the text contains ending punctuation
    """
    return any(punct in text for punct in END_PUNCTUATIONS)


def segment_text_by_regex(text: str) -> Tuple[List[str], str]:
    """
    Segment text into complete sentences using regex pattern matching.
    More efficient but less accurate than pysbd.

    Args:
        text: Text to segment into sentences

    Returns:
        Tuple[List[str], str]: (list of complete sentences, remaining incomplete text)
    """
    if not text:
        return [], ""

    complete_sentences = []
    remaining_text = text.strip()

    # Create pattern for matching sentences ending with any end punctuation
    escaped_punctuations = [re.escape(p) for p in END_PUNCTUATIONS]
    pattern = r"(.*?(?:[" + "|".join(escaped_punctuations) + r"]))"

    while remaining_text:
        match = re.search(pattern, remaining_text)
        if not match:
            break

        end_pos = match.end(1)
        potential_sentence = remaining_text[:end_pos].strip()

        # Skip if sentence ends with abbreviation
        if any(potential_sentence.endswith(abbrev) for abbrev in ABBREVIATIONS):
            remaining_text = remaining_text[end_pos:].lstrip()
            continue

        complete_sentences.append(potential_sentence)
        remaining_text = remaining_text[end_pos:].lstrip()

    return complete_sentences, remaining_text


def segment_text_by_pysbd(text: str) -> Tuple[List[str], str]:
    """
    Segment text into complete sentences and remaining text.
    Uses pysbd for supported languages, falls back to regex for others.

    Args:
        text: Text to segment into sentences

    Returns:
        Tuple[List[str], str]: (list of complete sentences, remaining incomplete text)
    """
    if not text:
        return [], ""

    try:
        # Detect language
        lang = detect_language(text)

        if lang is not None:
            # Use pysbd for supported languages
            segmenter = pysbd.Segmenter(language=lang, clean=False)
            sentences = segmenter.segment(text)

            if not sentences:
                return [], text

            # Process all but the last sentence
            complete_sentences = []
            for sent in sentences[:-1]:
                sent = sent.strip()
                if sent:
                    complete_sentences.append(sent)

            # Handle the last sentence
            last_sent = sentences[-1].strip()
            if is_complete_sentence(last_sent):
                complete_sentences.append(last_sent)
                remaining = ""
            else:
                remaining = last_sent

        else:
            # Use regex for unsupported languages
            return segment_text_by_regex(text)

        logger.debug(
            f"Processed sentences: {complete_sentences}, Remaining: {remaining}"
        )
        return complete_sentences, remaining

    except Exception as e:
        logger.error(f"Error in sentence segmentation: {e}")
        # Fallback to regex on any error
        return segment_text_by_regex(text)


class TagState(Enum):
    """State of a tag in text"""

    START = "start"  # <tag>
    INSIDE = "inside"  # text between tags
    END = "end"  # </tag>
    SELF_CLOSING = "self"  # <tag/>
    NONE = "none"  # no tag


@dataclass
class TagInfo:
    """Information about a tag"""

    name: str
    state: TagState

    def __str__(self) -> str:
        """String representation of tag info"""
        if self.state == TagState.NONE:
            return "none"
        return f"{self.name}:{self.state.value}"


@dataclass
class SentenceWithTags:
    """A sentence with its tag information, supporting nested tags"""

    text: str
    tags: List[TagInfo]  # List of tags from outermost to innermost


class SentenceDivider:
    def __init__(
        self,
        faster_first_response: bool = True,
        segment_method: str = "pysbd",
        valid_tags: List[str] = None,
    ):
        """
        Initialize the SentenceDivider.

        Args:
            faster_first_response: Whether to split first sentence at commas
            segment_method: Method for segmenting sentences
            valid_tags: List of valid tag names to detect
        """
        self.faster_first_response = faster_first_response
        self.segment_method = segment_method
        self.valid_tags = valid_tags or ["think"]
        self._is_first_sentence = True
        self._buffer = ""
        # Replace active_tags dict with a stack to handle nesting
        self._tag_stack = []

    def _get_current_tags(self) -> List[TagInfo]:
        """
        Get all current active tags from outermost to innermost.

        Returns:
            List[TagInfo]: List of active tags
        """
        return [TagInfo(tag.name, TagState.INSIDE) for tag in self._tag_stack]

    def _get_current_tag(self) -> Optional[TagInfo]:
        """
        Get the current innermost active tag.

        Returns:
            TagInfo if there's an active tag, None otherwise
        """
        return self._tag_stack[-1] if self._tag_stack else None

    def _extract_tag(self, text: str) -> Tuple[Optional[TagInfo], str]:
        """
        Extract the first tag from text if present.
        Handles nested tags by maintaining a tag stack.

        Args:
            text: Text to check for tags

        Returns:
            Tuple of (TagInfo if tag found else None, remaining text)
        """
        # Find the first occurrence of any tag
        first_tag = None
        first_pos = len(text)
        tag_type = None
        matched_tag = None

        # Check for self-closing tags
        for tag in self.valid_tags:
            pattern = f"<{tag}/>"
            match = re.search(pattern, text)
            if match and match.start() < first_pos:
                first_pos = match.start()
                first_tag = match
                tag_type = TagState.SELF_CLOSING
                matched_tag = tag

        # Check for opening tags
        for tag in self.valid_tags:
            pattern = f"<{tag}>"
            match = re.search(pattern, text)
            if match and match.start() < first_pos:
                first_pos = match.start()
                first_tag = match
                tag_type = TagState.START
                matched_tag = tag

        # Check for closing tags
        for tag in self.valid_tags:
            pattern = f"</{tag}>"
            match = re.search(pattern, text)
            if match and match.start() < first_pos:
                first_pos = match.start()
                first_tag = match
                tag_type = TagState.END
                matched_tag = tag

        if not first_tag:
            return None, text

        # Handle the found tag
        if tag_type == TagState.START:
            # Push new tag onto stack
            self._tag_stack.append(TagInfo(matched_tag, TagState.START))
        elif tag_type == TagState.END:
            # Verify matching tags
            if not self._tag_stack or self._tag_stack[-1].name != matched_tag:
                logger.warning(f"Mismatched closing tag: {matched_tag}")
            else:
                self._tag_stack.pop()

        return (TagInfo(matched_tag, tag_type), text[first_tag.end() :].lstrip())

    async def _process_buffer(self) -> AsyncIterator[SentenceWithTags]:
        """
        Process the current buffer, yielding complete sentences with tags.
        This is now an async generator.
        It consumes processed parts from self._buffer.
        """
        processed_something = True  # Flag to loop until no more processing can be done
        while processed_something:
            processed_something = False
            original_buffer_len = len(self._buffer)

            if not self._buffer.strip():
                break

            # Find the next tag position
            next_tag_pos = len(self._buffer)
            tag_pattern_found = None
            for tag in self.valid_tags:
                patterns = [f"<{tag}>", f"</{tag}>", f"<{tag}/>"]
                for pattern in patterns:
                    pos = self._buffer.find(pattern)
                    if pos != -1 and pos < next_tag_pos:
                        next_tag_pos = pos
                        tag_pattern_found = pattern  # Store the found pattern

            if next_tag_pos == 0:
                # Tag is at the start of buffer
                tag_info, remaining = self._extract_tag(self._buffer)
                if tag_info:
                    processed_text = self._buffer[
                        : len(self._buffer) - len(remaining)
                    ].strip()
                    # Yield the tag itself, represented as a SentenceWithTags
                    yield SentenceWithTags(text=processed_text, tags=[tag_info])
                    self._buffer = remaining
                    processed_something = True
                    continue  # Restart processing loop for the remaining buffer

            elif next_tag_pos < len(self._buffer):
                # Tag is in the middle - process text before tag first
                text_before_tag = self._buffer[:next_tag_pos]
                current_tags = self._get_current_tags()
                processed_segment = ""

                # Process complete sentences in text before tag
                if contains_end_punctuation(text_before_tag):
                    sentences, remaining_before = self._segment_text(text_before_tag)
                    for sentence in sentences:
                        if sentence.strip():
                            yield SentenceWithTags(
                                text=sentence.strip(),
                                tags=current_tags or [TagInfo("", TagState.NONE)],
                            )
                    # The part consumed includes sentences + what's left before the tag
                    processed_segment = text_before_tag
                    self._buffer = self._buffer[len(processed_segment) :]
                    processed_something = True
                    continue  # Restart processing loop

                elif text_before_tag.strip() and tag_pattern_found:
                    # No sentence end, but content exists AND we found a tag pattern after it.
                    # We can yield this segment because the tag provides a boundary.
                    yield SentenceWithTags(
                        text=text_before_tag.strip(),
                        tags=current_tags or [TagInfo("", TagState.NONE)],
                    )
                    self._buffer = self._buffer[len(text_before_tag) :]
                    processed_something = True
                    continue  # Restart processing loop
                # --- If no tag found after text_before_tag, we wait for more input or end punctuation ---

                # Process the tag itself if we haven't continued
                tag_info, remaining_after_tag = self._extract_tag(self._buffer)
                if tag_info:
                    processed_tag_text = self._buffer[
                        : len(self._buffer) - len(remaining_after_tag)
                    ].strip()
                    yield SentenceWithTags(text=processed_tag_text, tags=[tag_info])
                    self._buffer = remaining_after_tag
                    processed_something = True
                    continue  # Restart processing loop

            # No tags found or tag is not at the beginning/middle of processable segment
            # Process normal text if buffer has changed or punctuation exists
            if original_buffer_len > 0:
                current_tags = self._get_current_tags()

                # Handle first sentence with comma if enabled
                if (
                    self._is_first_sentence
                    and self.faster_first_response
                    and contains_comma(self._buffer)
                ):
                    sentence, remaining = comma_splitter(self._buffer)
                    if sentence.strip():
                        yield SentenceWithTags(
                            text=sentence.strip(),
                            tags=current_tags or [TagInfo("", TagState.NONE)],
                        )
                        self._buffer = remaining
                        self._is_first_sentence = False
                        processed_something = True
                        continue  # Restart processing loop

                # Process normal sentences based on end punctuation
                if contains_end_punctuation(self._buffer):
                    sentences, remaining = self._segment_text(self._buffer)
                    if sentences:  # Only process if segmentation yielded sentences
                        self._buffer = remaining
                        self._is_first_sentence = False
                        processed_something = True
                        for sentence in sentences:
                            if sentence.strip():
                                yield SentenceWithTags(
                                    text=sentence.strip(),
                                    tags=current_tags or [TagInfo("", TagState.NONE)],
                                )
                        continue  # Restart processing loop

            # If we reached here without processing anything, break the loop
            if not processed_something:
                break

    async def _flush_buffer(self) -> AsyncIterator[SentenceWithTags]:
        """
        Process and yield all remaining content in the buffer at the end of the stream.
        """
        logger.debug(f"Flushing remaining buffer: '{self._buffer}'")
        # First, run _process_buffer to yield any standard sentences/tags
        async for sentence in self._process_buffer():
            yield sentence

        # After processing standard structures, if anything is left, yield it as a final fragment
        if self._buffer.strip():
            logger.debug(
                f"Yielding final fragment from buffer: '{self._buffer.strip()}'"
            )
            current_tags = self._get_current_tags()
            yield SentenceWithTags(
                text=self._buffer.strip(),
                tags=current_tags or [TagInfo("", TagState.NONE)],
            )
            self._buffer = ""  # Clear buffer after flushing

    async def process_stream(
        self, segment_stream: AsyncIterator[Union[str, Dict[str, Any]]]
    ) -> AsyncIterator[Union[SentenceWithTags, Dict[str, Any]]]:
        """
        Process a stream of tokens (strings) and dictionaries.
        Yields complete sentences with tags (SentenceWithTags) or dictionaries directly.

        Args:
            segment_stream: An async iterator yielding strings or dictionaries.

        Yields:
            Union[SentenceWithTags, Dict[str, Any]]: Complete sentences/tags or original dictionaries.
        """
        self._full_response = []
        self.reset()  # Ensure state is clean

        async for item in segment_stream:
            if isinstance(item, dict):
                # Before yielding the dict, process and yield any complete sentences formed so far
                async for sentence in self._process_buffer():
                    self._full_response.append(
                        sentence.text
                    )  # Track for complete response
                    yield sentence
                # Now yield the dictionary
                yield item
            elif isinstance(item, str):
                self._buffer += item
                # Process the buffer incrementally as string chunks arrive
                async for sentence in self._process_buffer():
                    self._full_response.append(
                        sentence.text
                    )  # Track for complete response
                    yield sentence
            else:
                logger.warning(
                    f"SentenceDivider received unexpected type: {type(item)}"
                )

        # After the stream finishes, flush any remaining text in the buffer
        async for sentence in self._flush_buffer():
            self._full_response.append(sentence.text)
            yield sentence

    @property
    def complete_response(self) -> str:
        """Get the complete response accumulated so far"""
        return "".join(self._full_response)

    def _segment_text(self, text: str) -> Tuple[List[str], str]:
        """Segment text using the configured method"""
        if self.segment_method == "regex":
            return segment_text_by_regex(text)
        return segment_text_by_pysbd(text)

    def reset(self):
        """Reset the divider state for a new conversation"""
        self._is_first_sentence = True
        self._buffer = ""
        self._tag_stack = []
