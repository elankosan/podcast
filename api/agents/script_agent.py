"""Script Agent for the podcast application.

Formats research into structured podcast scripts with style enhancement.
"""

import json
import re
from typing import Any, Dict, Optional

from maf.integration import KimiClient
from maf.runtime.engine import BaseAgent, ExecutionResult


class ScriptAgent(BaseAgent):
    """Agent that formats research into a polished podcast script."""

    def __init__(self, agent_id: str = "agent-004", name: str = "Script Writer") -> None:
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type="llm",
            skills=["script_formatting", "style_enhancement", "narrative_structure"],
        )
        self.client = KimiClient()

    def execute(
        self,
        input: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Execute script formatting workflow."""
        input = input or {}
        vision = input.get("vision", "")
        episode_id = input.get("episode_id", "")

        # Get research from context or input
        research = input.get("research", input.get("synthesis", ""))

        if not vision or not research:
            return ExecutionResult(
                error="Vision and research are required for script generation",
                success=False,
            )

        try:
            # Step 1: Generate structured script
            script = self._generate_script(vision, research)

            # Step 2: Apply style enhancement
            enhanced = self._enhance_style(script, vision)

            output = {
                "episode_id": episode_id,
                "vision": vision,
                "script_raw": script,
                "script_enhanced": enhanced,
                "segments": self._extract_segments(enhanced),
            }

            return ExecutionResult(output=output, success=True)

        except Exception as e:
            return ExecutionResult(error=str(e), success=False)

    def _generate_script(self, vision: str, research: str) -> str:
        """Generate a structured podcast script from research."""
        system_prompt = (
            "You are an expert podcast script writer. You write scripts for a weekly radio show "
            "covering politics, history, economics, and philosophy. The host is knowledgeable, "
            "articulate, and engaging. Create a script with the following structure:\n\n"
            "1. INTRO (30-60 seconds): Hook the listener, introduce the topic\n"
            "2. SEGMENT 1 - Background/Context (2-3 minutes): Set the stage\n"
            "3. SEGMENT 2 - Main Discussion (5-8 minutes): Deep dive into the topic\n"
            "4. SEGMENT 3 - Counter-arguments/Alternative Views (2-3 minutes): Present nuance\n"
            "5. OUTRO (30-60 seconds): Summary and call to action\n\n"
            "Use [SEGMENT] markers, [PAUSE] for dramatic pauses, and [SFX: description] for sound effects. "
            "Write in a conversational but authoritative tone. Include specific facts, dates, and names from the research."
        )

        prompt = f"""Topic: {vision}

Research:
{research[:10000]}

Write a complete podcast script following the structure above."""

        response = self.client.chat(prompt, system_prompt=system_prompt)
        if response.startswith("[Kimi API Error:"):
            raise RuntimeError(f"Kimi API error during script generation: {response}")
        return response

    def _enhance_style(self, script: str, vision: str) -> str:
        """Apply style enhancement to the script."""
        system_prompt = (
            "You are a style editor for a prestigious podcast. Enhance the script by:\n"
            "1. Adding smooth transitions between segments\n"
            "2. Inserting rhetorical questions to engage listeners\n"
            "3. Adding [PAUSE] markers at dramatic moments\n"
            "4. Ensuring the tone is conversational yet authoritative\n"
            "5. Adding listener engagement prompts (e.g., 'Think about this...')\n"
            "6. Polishing opening hooks to be compelling\n"
            "7. Adding a memorable closing line\n\n"
            "Preserve all factual content. Return the complete enhanced script."
        )

        prompt = f"""Enhance the following podcast script:

{script}

Return the complete enhanced script with all improvements applied."""

        response = self.client.chat(prompt, system_prompt=system_prompt)
        if response.startswith("[Kimi API Error:"):
            raise RuntimeError(f"Kimi API error during style enhancement: {response}")
        return response

    def _extract_segments(self, script: str) -> list:
        """Extract segments from the script using regex to catch variations."""
        segments = []
        current_segment = {"name": "", "content": ""}

        # Pattern to catch variations like:
        # 1. INTRO, **INTRO**, INTRODUCTION, [SEGMENT: INTRO], etc.
        segment_pattern = re.compile(
            r'(?:^\s*(?:\d+\.\s*)?(?:\*\*)?(?:INTRO(?:DUCTION)?|SEGMENT\s*\d*|OUTRO)(?:\*\*)?\s*(?:[-–—]\s*.+)?)',
            re.IGNORECASE | re.MULTILINE
        )

        for line in script.split("\n"):
            line = line.strip()
            if not line:
                continue
            if segment_pattern.match(line) or line.upper().startswith("[SEGMENT") or line.upper().startswith("INTRO") or line.upper().startswith("OUTRO"):
                if current_segment["content"]:
                    segments.append(current_segment)
                current_segment = {"name": line, "content": ""}
            elif line.upper().startswith("[PAUSE]"):
                current_segment["content"] += f"\n{line}"
            elif line:
                current_segment["content"] += f"\n{line}"

        if current_segment["content"]:
            segments.append(current_segment)

        return segments
