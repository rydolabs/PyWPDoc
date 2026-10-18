"""Logicless/Mustache-inspired template feature."""
from .api import render_template
from .check import check_template, TemplateCheckReport, TemplateCheckIssue
from .context import ContextStack, Resolution, resolve_value, stringify_value
from .model import VariableTag
from .parser import iter_variable_tags
from .renderer import render_paragraph
from .sections import SectionTextRender, render_section_text

__all__ = [
    "VariableTag", "Resolution", "ContextStack",
    "iter_variable_tags", "resolve_value", "stringify_value",
    "render_paragraph", "render_template",
    "check_template", "TemplateCheckReport", "TemplateCheckIssue",
    "SectionTextRender", "render_section_text",
]
