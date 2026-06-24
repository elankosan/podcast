"""MAF integration layer for the podcast application.

Connects the FastAPI backend to the MAF runtime for agent workforce execution.

Usage:
    from api.maf_integration import PodcastWorkforce
    
    workforce = PodcastWorkforce()
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

from maf import Blueprint
from maf.runtime import LocalRuntime
from maf.runtime.build_logger import BuildLogger

from api.agents import ResearchAgent, ScriptAgent, TranslationAgent


class PodcastWorkforce:
    """Manages MAF workforce execution for podcast episodes."""
    
    def __init__(
        self,
        workforce_path: str = None,
        log_dir: str = "runtime_logs",
    ) -> None:
        if workforce_path is None:
            workforce_path = str(Path(__file__).parent.parent / "workforce.yaml")
        self.workforce_path = Path(workforce_path)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Load the blueprint
        self.blueprint = Blueprint.load(str(self.workforce_path))
        self.manifest = self.blueprint.compile()
        
        # Initialize runtime
        self.runtime = LocalRuntime()
        
        # Register actual agents with the orchestrator
        self.runtime.orchestrator.register_agent(ResearchAgent())
        self.runtime.orchestrator.register_agent(ScriptAgent())
        self.runtime.orchestrator.register_agent(TranslationAgent())
        
        # Initialize build logger
        self.logger = BuildLogger(
            log_id=f"podcast_{self.blueprint.workflow_id}",
            version_target="1.0.0",
            output_dir=self.log_dir,
        )
    
    def execute_phase(
        self,
        phase: str,
        episode_id: str,
        vision: Optional[str] = None,
        podcast_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a specific MAF phase for an episode by running the right agent."""
        
        # Phase -> Agent ID mapping
        PHASE_AGENTS = {
            "3": "agent-003",  # Research
            "4": "agent-004",  # Script
            "5": "agent-005",  # Translation
        }
        
        agent_id = PHASE_AGENTS.get(phase)
        if not agent_id:
            return {
                "success": False,
                "error": f"Phase {phase} does not have a registered agent",
                "episode_id": episode_id,
                "phase": phase,
            }
        
        # Build input
        input_data = {
            "phase": phase,
            "episode_id": episode_id,
            "podcast_id": podcast_id,
            "vision": vision or "",
            "language": language or "en",
        }
        
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
                input=input_data,
            )
            
            # Complete the step
            self.logger.complete_step(
                status="success" if result.success else "failure",
                tokens_input=len(str(input_data)),
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
                        "input": input_data,
                        "output": result.output,
                        "success": result.success,
                        "error": result.error,
                        "step": {
                            "step_id": result.trace_step.step_id,
                            "start_time": result.trace_step.start_time,
                            "end_time": result.trace_step.end_time,
                        },
                    }, f, indent=2)
            
            return {
                "success": result.success,
                "output": result.output,
                "trace_id": result.trace_step.step_id if result.trace_step else None,
                "episode_id": episode_id,
                "phase": phase,
                "agent_id": agent_id,
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
        # Find all traces for this episode
        traces = []
        for trace_file in self.log_dir.glob("trace_*.json"):
            with open(trace_file, "r", encoding="utf-8") as f:
                trace = json.load(f)
                if trace.get("episode_id") == episode_id:
                    traces.append(trace)
        
        total_cost = 0.0
        total_tokens = 0
        for trace in traces:
            cost = trace.get("step", {}).get("cost", 0)
            if cost is None:
                cost = 0.0
            total_cost += float(cost)
            tokens = trace.get("step", {}).get("tokens", 0)
            if tokens is None:
                tokens = 0
            total_tokens += int(tokens)
        
        return {
            "episode_id": episode_id,
            "traces_count": len(traces),
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
        }
