"""Research Agent for the podcast application.

Uses Kimi API + web search to research topics and synthesize findings.
"""

import json
from typing import Any, Dict, Optional

from maf.integration import KimiClient
from maf.runtime.engine import BaseAgent, ExecutionResult


class ResearchAgent(BaseAgent):
    """Agent that researches a topic and produces structured findings."""

    def __init__(self, agent_id: str = "agent-003", name: str = "Researcher") -> None:
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type="llm",
            skills=["synthesis", "fact_checking"],
        )
        self.client = KimiClient()

    def execute(
        self,
        input: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Execute research workflow."""
        input = input or {}
        vision = input.get("vision", "")
        episode_id = input.get("episode_id", "")

        if not vision:
            return ExecutionResult(error="No vision provided", success=False)

        try:
            # Step 1: Synthesize topic with Kimi (web search can be added later)
            synthesis = self._synthesize(vision)

            # Step 2: Extract structured data
            structured = self._extract_structure(synthesis)

            output = {
                "episode_id": episode_id,
                "vision": vision,
                "synthesis": synthesis,
                "structured": structured,
            }

            return ExecutionResult(output=output, success=True)

        except Exception as e:
            return ExecutionResult(error=str(e), success=False)

    def _synthesize(self, vision: str) -> str:
        """Use Kimi to synthesize research on the topic."""
        system_prompt = (
            "You are a research analyst for a political/history/economics podcast. "
            "Produce a comprehensive research brief with: "
            "1) Key facts and data, 2) Main arguments and perspectives, 3) Context and background, "
            "4) Notable quotes or statistics, 5) Potential angles for the podcast. "
            "Be factual, flag any controversial claims, and note where sources would be needed."
        )

        prompt = f"""Research topic: {vision}

Please produce a structured research brief covering the key aspects of this topic. Include historical context, current developments, main stakeholder perspectives, and potential angles for a podcast discussion."""

        response = self.client.chat(prompt, system_prompt=system_prompt)
        if response.startswith("[Kimi API Error:"):
            raise RuntimeError(f"Kimi API error during synthesis: {response}")
        return response

    def _extract_structure(self, synthesis: str) -> Dict[str, Any]:
        """Extract structured data from synthesis text."""
        lines = synthesis.split("\n")
        sections = {
            "key_facts": [],
            "arguments": [],
            "context": [],
            "quotes": [],
            "angles": [],
        }
        current_section = None

        for line in lines:
            line = line.strip()
            lower = line.lower()
            if "key fact" in lower or "fact" in lower:
                current_section = "key_facts"
            elif "argument" in lower or "perspective" in lower:
                current_section = "arguments"
            elif "context" in lower or "background" in lower:
                current_section = "context"
            elif "quote" in lower or "statistic" in lower:
                current_section = "quotes"
            elif "angle" in lower:
                current_section = "angles"
            elif line and current_section and line[0] in "-•*123456789":
                sections[current_section].append(line.lstrip("-•*123456789. "))

        return sections
