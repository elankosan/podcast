"""MAF integration layer for the podcast application.

Connects the FastAPI backend to the MAF runtime for agent workforce execution.

Usage:
    from api.maf_integration import get_workforce

    workforce = get_workforce()
    result = workforce.execute_phase(
        phase="3",
        episode_id="ep_001",
        vision="Discuss AI and democracy"
    )
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from api.config import settings

try:
    from maf import Blueprint
    from maf.runtime import LocalRuntime
    from maf.runtime.build_logger import BuildLogger
    from api.agents import ResearchAgent, ScriptAgent, TranslationAgent
    MAF_AVAILABLE = True
except Exception:
    Blueprint = None
    LocalRuntime = None
    BuildLogger = None
    ResearchAgent = None
    ScriptAgent = None
    TranslationAgent = None
    MAF_AVAILABLE = False


# Module-level singleton so routers do not pay the import/build cost at module load time.
_workforce_instance: Optional["PodcastWorkforce"] = None


def get_workforce() -> "PodcastWorkforce":
    """Return the shared PodcastWorkforce instance, creating it lazily on first use."""
    global _workforce_instance
    if _workforce_instance is None:
        _workforce_instance = PodcastWorkforce()
    return _workforce_instance


class PodcastWorkforce:
    """Manages MAF workforce execution for podcast episodes."""

    # Map MAF phase numbers to the agent IDs used when registering agents.
    PHASE_AGENTS = {
        "3": "agent-003",  # Research
        "4": "agent-004",  # Script
        "5": "agent-005",  # Translation
    }

    def __init__(
        self,
        workforce_path: str = None,
        log_dir: str = None,
    ) -> None:
        self.available = MAF_AVAILABLE
        if workforce_path is None:
            workforce_path = settings.MAF_WORKFORCE_PATH
        if log_dir is None:
            log_dir = getattr(settings, "RUNTIME_LOGS_DIR", "/tmp/runtime_logs")

        self.workforce_path = Path(workforce_path)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.blueprint = None
        self.manifest = None
        self.runtime = None
        self.logger = None
        self._init_error: Optional[str] = None

        if not self.available:
            self._init_error = "MAF runtime unavailable in this deployment."
            return

        try:
            if self.workforce_path.exists() and Blueprint is not None:
                self.blueprint = Blueprint.load(str(self.workforce_path))
                self.manifest = self.blueprint.compile()

            self.runtime = LocalRuntime()

            # Register actual agents with the orchestrator
            if ResearchAgent is not None:
                self.runtime.orchestrator.register_agent(ResearchAgent())
            if ScriptAgent is not None:
                self.runtime.orchestrator.register_agent(ScriptAgent())
            if TranslationAgent is not None:
                self.runtime.orchestrator.register_agent(TranslationAgent())

            self.logger = BuildLogger(
                log_id=f"podcast_{getattr(self.blueprint, 'workflow_id', 'local')}",
                version_target="1.0.0",
                output_dir=self.log_dir,
            )
        except Exception as e:
            self.available = False
            self._init_error = str(e)

    def execute_phase(
        self,
        phase: str,
        episode_id: str,
        vision: Optional[str] = None,
        podcast_id: Optional[str] = None,
        language: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a specific MAF phase for an episode by running the right agent."""
        if not self.available:
            return {
                "success": False,
                "error": self._init_error or "MAF runtime unavailable in this deployment.",
                "episode_id": episode_id,
                "phase": phase,
            }

        agent_id = self.PHASE_AGENTS.get(phase)
        if not agent_id:
            return {
                "success": False,
                "error": f"Phase {phase} does not have a registered agent",
                "episode_id": episode_id,
                "phase": phase,
            }

        # Build input
        payload = {
            "phase": phase,
            "episode_id": episode_id,
            "podcast_id": podcast_id,
            "vision": vision or "",
            "language": language or "en",
        }
        if input_data:
            payload.update(input_data)

        # Log the step
        self.logger.start_step(
            action=f"execute_phase_{phase}",
            description=f"Execute Phase {phase} ({agent_id}) for episode {episode_id}",
            agent=agent_id,
        )

        # Execute specific agent via orchestrator
        try:
            result = self.runtime.orchestrator.run(
                agent_id=agent_id,
                input=payload,
            )

            # Complete the step
            self.logger.complete_step(
                status="success" if result.success else "failure",
                tokens_input=len(str(payload)),
                tokens_output=len(str(result.output)),
            )

            # Save trace
            if result.trace_step:
                trace_path = self.log_dir / f"trace_{episode_id}_{phase}_{result.trace_step.step_id}.json"
                with open(trace_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "episode_id": episode_id,
                        "phase": phase,
                        "agent_id": agent_id,
                        "input": payload,
                        "output": result.output,
                        "success": result.success,
                        "error": result.error,
                        "step": {
                            "step_id": result.trace_step.step_id,
                            "start_time": result.trace_step.start_time,
                            "end_time": result.trace_step.end_time,
                            "cost": result.trace_step.cost,
                            "tokens": result.trace_step.cost.get("tokens", 0) if result.trace_step.cost else 0,
                        },
                    }, f, indent=2)

            return {
                "success": result.success,
                "output": result.output,
                "trace_id": result.trace_step.step_id if result.trace_step else None,
                "episode_id": episode_id,
                "phase": phase,
                "agent_id": agent_id,
                "error": result.error,
            }

        except Exception as e:
            self.logger.complete_step(status="failure")
            return {
                "success": False,
                "error": str(e),
                "episode_id": episode_id,
                "phase": phase,
                "agent_id": agent_id,
            }

    def get_trace(self, episode_id: str, phase: str, step_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a trace by episode_id, phase, and step_id."""
        trace_path = self.log_dir / f"trace_{episode_id}_{phase}_{step_id}.json"
        if trace_path.exists():
            with open(trace_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def get_cost_report(self, episode_id: str) -> Dict[str, Any]:
        """Get cost report for an episode."""
        traces = []
        for trace_file in self.log_dir.glob("trace_*.json"):
            try:
                with open(trace_file, "r", encoding="utf-8") as f:
                    trace = json.load(f)
                    if trace.get("episode_id") == episode_id:
                        traces.append(trace)
            except Exception:
                continue

        total_cost = 0.0
        total_tokens = 0
        for trace in traces:
            cost = trace.get("step", {}).get("cost", 0)
            if isinstance(cost, dict):
                total_cost += float(cost.get("estimated_usd", 0.0) or 0.0)
                total_tokens += int(cost.get("tokens", 0) or 0)
            elif isinstance(cost, (int, float, str)):
                total_cost += float(cost or 0.0)

            tokens = trace.get("step", {}).get("tokens", 0)
            if isinstance(tokens, (int, float, str)):
                total_tokens += int(float(tokens or 0))

        return {
            "episode_id": episode_id,
            "traces_count": len(traces),
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
        }
