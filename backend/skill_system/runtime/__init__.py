"""Pure Skill Executor and deterministic built-in fake skills."""

from .fake_skills import (
    MOCK_PAPER_SEARCH,
    MOCK_SUMMARY,
    mock_paper_search,
    mock_summary,
    register_fake_skills,
)
from .skill_executor import SkillExecutor

__all__ = [
    "MOCK_PAPER_SEARCH",
    "MOCK_SUMMARY",
    "SkillExecutor",
    "mock_paper_search",
    "mock_summary",
    "register_fake_skills",
]
