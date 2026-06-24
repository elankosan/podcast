"""Build Logger — tracks costs and events during framework construction.

This is the meta-observability layer: it records every step of building the
framework itself, with token costs, time, and feedback loops. It is used by
the Test Agent, Review Agent, and Cost Agent to provide feedback on the
build process.

Usage:
    from maf.runtime import BuildLogger
    logger = BuildLogger(log_id="implog_001", budget_usd=50.0)
    
    with logger.step("create_file", agent="executor", description="Create __init__.py"):
        # ... do work ...
        pass  # Cost is estimated automatically
    
    logger.record_feedback(
        step_id="step_001",
        agent="test_agent",
        status="pass",
        score=0.95
    )
    
    report = logger.get_phase_report("phase2")
    print(report.phase_cost)
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class StepCost:
    """Cost of a single build step."""
    tokens_input: int = 0
    tokens_output: int = 0
    estimated_usd: float = 0.0
    model: str = "unknown"
    
    @property
    def tokens_total(self) -> int:
        return self.tokens_input + self.tokens_output
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "tokens_total": self.tokens_total,
            "estimated_usd": self.estimated_usd,
            "model": self.model,
        }


@dataclass
class BuildStep:
    """A single step in the build process."""
    step_id: str
    action: str  # create_file, edit_file, run_test, review, etc.
    description: str = ""
    agent: str = "executor"
    files_affected: List[str] = field(default_factory=list)
    status: str = "pending"  # success, failure, partial, skipped
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: float = 0.0
    step_cost: StepCost = field(default_factory=StepCost)
    feedback: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action": self.action,
            "description": self.description,
            "agent": self.agent,
            "files_affected": self.files_affected,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "step_cost": self.step_cost.to_dict(),
            "feedback": self.feedback,
        }


@dataclass
class PhaseCost:
    """Aggregated cost for a build phase."""
    tokens_input: int = 0
    tokens_output: int = 0
    estimated_usd: float = 0.0
    
    @property
    def tokens_total(self) -> int:
        return self.tokens_input + self.tokens_output
    
    def add(self, cost: StepCost) -> None:
        self.tokens_input += cost.tokens_input
        self.tokens_output += cost.tokens_output
        self.estimated_usd += cost.estimated_usd
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "tokens_total": self.tokens_total,
            "estimated_usd": self.estimated_usd,
        }


@dataclass
class BuildPhase:
    """A phase in the build process (e.g., Phase 2: Packaging)."""
    phase_id: str
    name: str
    description: str = ""
    status: str = "pending"  # pending, in_progress, completed, failed, skipped, deferred
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    steps: List[BuildStep] = field(default_factory=list)
    phase_cost: PhaseCost = field(default_factory=PhaseCost)
    feedback_summary: Dict[str, Any] = field(default_factory=dict)
    
    def add_step(self, step: BuildStep) -> None:
        self.steps.append(step)
        self.phase_cost.add(step.step_cost)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "steps": [s.to_dict() for s in self.steps],
            "phase_cost": self.phase_cost.to_dict(),
            "feedback_summary": self.feedback_summary,
        }


class BuildLogger:
    """Logs the implementation of the MAF framework with cost tracking."""
    
    # Default cost model: $0.002 per 1K tokens (rough estimate for mid-tier LLM)
    DEFAULT_COST_PER_1K_TOKENS = 0.002
    
    def __init__(
        self,
        log_id: Optional[str] = None,
        version_target: str = "2.0.0",
        budget_usd: Optional[float] = None,
        budget_tokens: Optional[int] = None,
        output_dir: Optional[Path] = None,
    ) -> None:
        self.log_id = log_id or f"implog_{uuid.uuid4().hex[:8]}"
        self.version_target = version_target
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.completed_at: Optional[str] = None
        
        self.budget_usd = budget_usd
        self.budget_tokens = budget_tokens
        self.consumed_usd = 0.0
        self.consumed_tokens = 0
        
        self.phases: Dict[str, BuildPhase] = {}
        self.current_phase: Optional[str] = None
        self.current_step: Optional[str] = None
        
        self.adaptive_adjustments: List[Dict[str, Any]] = []
        self.output_dir = output_dir or Path(".")
        
        self._step_stack: List[BuildStep] = []
    
    def start_phase(self, phase_id: str, name: str, description: str = "") -> BuildPhase:
        """Start a new build phase."""
        phase = BuildPhase(
            phase_id=phase_id,
            name=name,
            description=description,
            status="in_progress",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self.phases[phase_id] = phase
        self.current_phase = phase_id
        return phase
    
    def complete_phase(self, phase_id: str, status: str = "completed") -> None:
        """Complete a build phase."""
        if phase_id in self.phases:
            self.phases[phase_id].status = status
            self.phases[phase_id].completed_at = datetime.now(timezone.utc).isoformat()
        if self.current_phase == phase_id:
            self.current_phase = None
    
    def start_step(
        self,
        action: str,
        description: str = "",
        agent: str = "executor",
        files_affected: Optional[List[str]] = None,
        estimated_tokens_input: int = 0,
        estimated_tokens_output: int = 0,
    ) -> BuildStep:
        """Start a new build step. Returns the step object."""
        step_id = f"step_{len(self._get_all_steps()) + 1:03d}"
        step = BuildStep(
            step_id=step_id,
            action=action,
            description=description,
            agent=agent,
            files_affected=files_affected or [],
            status="in_progress",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._step_stack.append(step)
        self.current_step = step_id
        return step
    
    def complete_step(
        self,
        status: str = "success",
        tokens_input: int = 0,
        tokens_output: int = 0,
        estimated_usd: Optional[float] = None,
        model: str = "unknown",
    ) -> BuildStep:
        """Complete the current build step with cost."""
        if not self._step_stack:
            raise RuntimeError("No step in progress")
        
        step = self._step_stack.pop()
        step.status = status
        step.completed_at = datetime.now(timezone.utc).isoformat()
        
        # Calculate duration
        if step.started_at:
            start = datetime.fromisoformat(step.started_at.replace("Z", "+00:00"))
            end = datetime.now(timezone.utc)
            step.duration_seconds = (end - start).total_seconds()
        
        # Calculate cost
        if estimated_usd is None:
            total_tokens = tokens_input + tokens_output
            estimated_usd = (total_tokens / 1000) * self.DEFAULT_COST_PER_1K_TOKENS
        
        step.step_cost = StepCost(
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            estimated_usd=estimated_usd,
            model=model,
        )
        
        # Add to current phase
        if self.current_phase and self.current_phase in self.phases:
            self.phases[self.current_phase].add_step(step)
        
        # Update totals
        self.consumed_usd += estimated_usd
        self.consumed_tokens += tokens_input + tokens_output
        
        self.current_step = None
        return step
    
    def record_feedback(
        self,
        step_id: str,
        agent: str,  # "test_agent", "review_agent", "cost_agent"
        status: str,
        **kwargs: Any,
    ) -> None:
        """Record feedback from an agent on a specific step."""
        for phase in self.phases.values():
            for step in phase.steps:
                if step.step_id == step_id:
                    if "feedback" not in step.__dict__:
                        step.feedback = {}
                    step.feedback[agent] = {
                        "status": status,
                        **kwargs,
                    }
                    return
        raise ValueError(f"Step {step_id} not found")
    
    def record_phase_feedback(
        self,
        phase_id: str,
        test_passed: bool,
        review_approved: bool,
        cost_within_budget: bool,
        recommendations: Optional[List[str]] = None,
    ) -> None:
        """Record aggregated feedback for an entire phase."""
        if phase_id not in self.phases:
            raise ValueError(f"Phase {phase_id} not found")
        self.phases[phase_id].feedback_summary = {
            "test_passed": test_passed,
            "review_approved": review_approved,
            "cost_within_budget": cost_within_budget,
            "recommendations": recommendations or [],
        }
    
    def adjust_plan(
        self,
        triggered_by: str,
        original_plan: str,
        adjusted_plan: str,
        reason: str,
    ) -> None:
        """Record an adaptive plan adjustment based on feedback."""
        self.adaptive_adjustments.append({
            "adjustment_id": f"adj_{len(self.adaptive_adjustments) + 1:03d}",
            "triggered_by": triggered_by,
            "original_plan": original_plan,
            "adjusted_plan": adjusted_plan,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    def get_phase_report(self, phase_id: str) -> Dict[str, Any]:
        """Get a report for a specific phase."""
        if phase_id not in self.phases:
            return {}
        phase = self.phases[phase_id]
        return {
            "phase_id": phase.phase_id,
            "name": phase.name,
            "status": phase.status,
            "steps_count": len(phase.steps),
            "phase_cost": phase.phase_cost.to_dict(),
            "feedback_summary": phase.feedback_summary,
        }
    
    def get_total_cost(self) -> PhaseCost:
        """Get total cost across all phases."""
        total = PhaseCost()
        for phase in self.phases.values():
            total.tokens_input += phase.phase_cost.tokens_input
            total.tokens_output += phase.phase_cost.tokens_output
            total.estimated_usd += phase.phase_cost.estimated_usd
        return total
    
    def is_over_budget(self) -> bool:
        """Check if build is over budget."""
        if self.budget_usd is not None and self.consumed_usd > self.budget_usd:
            return True
        if self.budget_tokens is not None and self.consumed_tokens > self.budget_tokens:
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the entire log to a dictionary."""
        total = self.get_total_cost()
        return {
            "log_id": self.log_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "version_target": self.version_target,
            "phases": [p.to_dict() for p in self.phases.values()],
            "total_cost": total.to_dict(),
            "budget": {
                "allocated_usd": self.budget_usd,
                "consumed_usd": self.consumed_usd,
                "remaining_usd": (self.budget_usd - self.consumed_usd) if self.budget_usd else None,
                "allocated_tokens": self.budget_tokens,
                "consumed_tokens": self.consumed_tokens,
                "remaining_tokens": (self.budget_tokens - self.consumed_tokens) if self.budget_tokens else None,
            },
            "adaptive_adjustments": self.adaptive_adjustments,
            "meta": {
                "version": "1.3.0",
                "environment": "local",
                "builder": "MAF Self-Build System",
            },
        }
    
    def save(self, path: Optional[Path] = None) -> Path:
        """Save the log to a JSON file."""
        if path is None:
            path = self.output_dir / f"{self.log_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path
    
    def _get_all_steps(self) -> List[BuildStep]:
        """Get all steps across all phases."""
        steps = []
        for phase in self.phases.values():
            steps.extend(phase.steps)
        return steps
    
    def __enter__(self) -> "BuildLogger":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.save()
