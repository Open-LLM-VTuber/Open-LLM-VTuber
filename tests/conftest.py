"""Shared pytest setup for the Open-LLM-VTuber test suite."""

from langdetect import DetectorFactory

# langdetect samples its language profiles randomly unless a seed is fixed, so the
# detected language of a short sentence can change between runs.  Sentence
# segmentation depends on that detection, so pin it for reproducible tests.
DetectorFactory.seed = 0
