"""Translation Agent for the podcast application.

Translates podcast scripts into multiple languages with cultural adaptation.
"""

import json
import logging
from typing import Any, Dict, Optional

from maf.integration import KimiClient
from maf.runtime.engine import BaseAgent, ExecutionResult

logger = logging.getLogger(__name__)


class TranslationAgent(BaseAgent):
    """Agent that translates scripts with cultural and linguistic adaptation."""

    LANGUAGE_PROMPTS = {
        "en": {
            "name": "English",
            "context": "Original English script. No translation needed.",
        },
        "fr": {
            "name": "French",
            "context": "French-speaking audience (France, Quebec, Belgium, Africa). Adapt cultural references to French context. Use formal but accessible language. Maintain intellectual rigor.",
        },
        "es": {
            "name": "Spanish",
            "context": "Spanish-speaking audience (Spain, Latin America). Use neutral Spanish where possible, but adapt idioms for broad comprehension. Keep the conversational tone.",
        },
        "ta": {
            "name": "Tamil",
            "context": "Tamil-speaking audience (India, Sri Lanka, diaspora). Use formal Tamil with some modern terms. Adapt Western concepts with Tamil cultural equivalents. Ensure proper Tamil script output.",
        },
        "de": {
            "name": "German",
            "context": "German-speaking audience (Germany, Austria, Switzerland). Use standard High German. Maintain precision and intellectual depth. Adapt examples to European context.",
        },
    }

    def __init__(self, agent_id: str = "agent-005", name: str = "Translator") -> None:
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type="llm",
            skills=["translation", "cultural_adaptation", "linguistic_polishing"],
        )
        self.client = KimiClient()

    def execute(
        self,
        input: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Execute translation workflow."""
        input = input or {}
        vision = input.get("vision", "")
        episode_id = input.get("episode_id", "")
        language = input.get("language", "fr")
        script = input.get("script", "")

        if not script:
            return ExecutionResult(error="No script provided for translation", success=False)

        lang_config = self.LANGUAGE_PROMPTS.get(language, self.LANGUAGE_PROMPTS["fr"])

        # Short-circuit for English: return original script unchanged
        if language == "en":
            return ExecutionResult(
                output={
                    "episode_id": episode_id,
                    "vision": vision,
                    "language": language,
                    "language_name": lang_config["name"],
                    "translation_raw": script,
                    "translation_polished": script,
                    "cultural_notes": [],
                },
                success=True,
            )

        try:
            # Step 1: Translate with cultural adaptation
            translated = self._translate(script, language, lang_config)

            # Extract cultural notes BEFORE polishing (polish removes markers)
            cultural_notes = self._extract_cultural_notes(translated)

            # Step 2: Linguistic polishing
            polished = self._polish(translated, language, lang_config)

            output = {
                "episode_id": episode_id,
                "vision": vision,
                "language": language,
                "language_name": lang_config["name"],
                "translation_raw": translated,
                "translation_polished": polished,
                "cultural_notes": cultural_notes,
            }

            return ExecutionResult(output=output, success=True)

        except Exception as e:
            return ExecutionResult(error=str(e), success=False)

    def _translate(self, script: str, language: str, lang_config: Dict[str, Any]) -> str:
        """Translate the script with cultural context."""
        system_prompt = (
            f"You are a professional translator specializing in podcast content. "
            f"Translate the following English podcast script into {lang_config['name']}.\n\n"
            f"Audience context: {lang_config['context']}\n\n"
            "Rules:\n"
            "1. Preserve the conversational tone and intellectual depth\n"
            "2. Adapt cultural references to resonate with the target audience\n"
            "3. Keep segment markers ([SEGMENT], [PAUSE], [SFX]) intact\n"
            "4. Maintain the same approximate length and pacing\n"
            "5. Ensure names of people, places, and organizations are translated appropriately\n"
            "6. Add [CULTURAL NOTE: explanation] where significant adaptation was made\n"
            "7. Do not add or remove factual content\n"
            "8. Output ONLY the translated script, no explanations"
        )

        if len(script) > 12000:
            logger.warning(
                "Script length (%d chars) exceeds 12000 limit. Truncating to 12000 chars for translation.",
                len(script),
            )
            script = script[:12000]

        prompt = f"""Translate this podcast script into {lang_config['name']}:

{script}

Return the complete translated script."""

        response = self.client.chat(prompt, system_prompt=system_prompt)
        if response.startswith("[Kimi API Error:"):
            raise RuntimeError(f"Kimi API error during translation: {response}")
        return response

    def _polish(self, translated: str, language: str, lang_config: Dict[str, Any]) -> str:
        """Apply linguistic polishing to the translation."""
        system_prompt = (
            f"You are a linguistic editor for {lang_config['name']} podcast content. "
            "Polish the translation by:\n"
            "1. Ensuring natural flow and rhythm suitable for spoken delivery\n"
            "2. Fixing any awkward phrasing or literal translations\n"
            "3. Verifying that technical/political terms are correctly translated\n"
            "4. Ensuring the tone remains conversational and engaging\n"
            "5. Checking that all segment markers are preserved\n"
            "6. Removing any [CULTURAL NOTE] markers (keep the adapted text)\n\n"
            "Return the complete polished script."
        )

        prompt = f"""Polish this {lang_config['name']} translation:

{translated}

Return the complete polished script."""

        response = self.client.chat(prompt, system_prompt=system_prompt)
        if response.startswith("[Kimi API Error:"):
            raise RuntimeError(f"Kimi API error during polishing: {response}")
        return response

    def _extract_cultural_notes(self, text: str) -> list:
        """Extract cultural adaptation notes from the text."""
        notes = []
        for line in text.split("\n"):
            if "[CULTURAL NOTE:" in line:
                notes.append(line.strip())
        return notes
