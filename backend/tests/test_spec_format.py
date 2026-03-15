"""Tests for the new two-part spec format (Mockup Description + OpenSpec Config)."""

import pytest


def test_extract_mockup_description():
    """Can extract Mockup Description from spec content."""
    from app.agents.dev_agent import DevAgent

    agent = DevAgent.__new__(DevAgent)  # Don't call __init__

    spec_content = """## Mockup Description

A modern dashboard app with dark theme featuring a sidebar navigation, 
metric cards grid, and data table. Primary color is cyan.

## OpenSpec Config

### Foundation
Build a Next.js 15 app with sidebar layout.
"""
    result = agent._extract_mockup_description(spec_content)
    assert "dashboard app" in result
    assert "OpenSpec Config" not in result


def test_extract_openspec_config():
    """Can extract foundation and feature prompts from OpenSpec Config."""
    from app.agents.dev_agent import DevAgent

    agent = DevAgent.__new__(DevAgent)

    spec_content = """## Mockup Description

A simple app.

## OpenSpec Config

### Foundation
Build a Next.js 15 app with dark theme, sidebar navigation, and responsive layout.

### Features
#### Feature: User Dashboard
Create a dashboard with metric cards showing real-time data.

#### Feature: Data Table
Implement a sortable, filterable data table component.
"""
    foundation, features = agent._extract_openspec_config(spec_content)
    assert "Next.js 15" in foundation
    assert len(features) == 2
    assert "metric cards" in features[0]
    assert "sortable" in features[1]


def test_extract_mockup_description_fallback():
    """Falls back to full content when no Mockup Description section."""
    from app.agents.dev_agent import DevAgent

    agent = DevAgent.__new__(DevAgent)
    result = agent._extract_mockup_description("Just plain spec content")
    assert result == "Just plain spec content"
