"""Runtime execution engine for MAF.

Provides:
- EventBus: publish/subscribe event system
- BaseStateStore / MemoryStateStore: agent state persistence
- BaseAgent / Agent subclasses: executable workers
- PolicyEngine / BasePolicyEngine: governance enforcement
- Orchestrator: agent scheduling and lifecycle
- LocalRuntime: in-process execution environment
"""

import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple


# ──────────────────────────────────────────────────────────────────────────
# Event System
# ──────────────────────────────────────────────────────────────────────────

class EventBus:
    """Publish/subscribe event bus for agent communication."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._history: List[Dict[str, Any]] = []

    def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe a handler to a topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)

    def publish(self, topic: str, event: Dict[str, Any]) -> None:
        """Publish an event to a topic."""
        event["_published_at"] = datetime.now(timezone.utc).isoformat()
        event["_topic"] = topic
        self._history.append(event)
        for handler in self._subscribers.get(topic, []):
            handler(event)

    def get_history(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return published events, optionally filtered by topic."""
        if topic is None:
            return self._history.copy()
        return [e for e in self._history if e.get("_topic") == topic]


# ──────────────────────────────────────────────────────────────────────────
# State Store
# ──────────────────────────────────────────────────────────────────────────

class BaseStateStore(ABC):
    """Abstract interface for agent state persistence."""

    @abstractmethod
    def set(self, key: str, value: Any, namespace: Optional[str] = None) -> None:
        """Store a value."""
        pass

    @abstractmethod
    def get(self, key: str, namespace: Optional[str] = None) -> Any:
        """Retrieve a value."""
        pass

    @abstractmethod
    def delete(self, key: str, namespace: Optional[str] = None) -> None:
        """Delete a value."""
        pass

    @abstractmethod
    def keys(self, namespace: Optional[str] = None) -> List[str]:
        """List all keys in a namespace."""
        pass


class MemoryStateStore(BaseStateStore):
    """In-memory state store. All data is lost on restart."""

    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}

    def _ns(self, namespace: Optional[str]) -> str:
        return namespace or "default"

    def set(self, key: str, value: Any, namespace: Optional[str] = None) -> None:
        ns = self._ns(namespace)
        if ns not in self._data:
            self._data[ns] = {}
        self._data[ns][key] = value

    def get(self, key: str, namespace: Optional[str] = None) -> Any:
        ns = self._ns(namespace)
        return self._data.get(ns, {}).get(key)

    def delete(self, key: str, namespace: Optional[str] = None) -> None:
        ns = self._ns(namespace)
        if ns in self._data and key in self._data[ns]:
            del self._data[ns][key]

    def keys(self, namespace: Optional[str] = None) -> List[str]:
        ns = self._ns(namespace)
        return list(self._data.get(ns, {}).keys())


# ──────────────────────────────────────────────────────────────────────────
# Policy Engine
# ──────────────────────────────────────────────────────────────────────────

class PolicyViolationError(Exception):
    """Raised when an action violates a hard policy."""
    pass


class BasePolicyEngine(ABC):
    """Abstract interface for policy enforcement."""

    @abstractmethod
    def enforce(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Check if action is allowed. Return result or raise."""
        pass

    @abstractmethod
    def get_violations(self) -> List[Dict[str, Any]]:
        """Return list of recorded violations."""
        pass


class PolicyEngine(BasePolicyEngine):
    """Policy engine with 4-level hierarchy: universal, regulatory, operational, tactical."""

    def __init__(self, policies: Optional[List[Dict[str, Any]]] = None) -> None:
        self._policies = policies or []
        self._violations: List[Dict[str, Any]] = []

    def enforce(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Check action against all policies."""
        violations = []
        for policy in self._policies:
            result = self._check_policy(action, policy)
            if result is not True:
                violations.append({
                    "policy_id": policy["id"],
                    "policy_level": policy["level"],
                    "policy_name": policy["name"],
                    "enforce": policy["enforce"],
                    "reason": str(result),
                })

        # Handle violations by level
        hard_violations = [v for v in violations if v["enforce"] == "hard"]
        if hard_violations:
            raise PolicyViolationError(
                f"Hard policy violation: {hard_violations[0]['reason']}"
            )

        # Record all violations
        self._violations.extend(violations)

        return {
            "allowed": True,
            "violations": violations,
            "warnings": [v for v in violations if v["enforce"] in ("soft", "advisory")],
        }

    def _check_policy(self, action: Dict[str, Any], policy: Dict[str, Any]) -> Any:
        """Check a single policy. Return True if allowed, or reason string if violated."""
        # Universal Level 1: Never exfiltrate credentials
        if policy["id"] == "univ_001" and action.get("data_type") == "credentials":
            if action.get("destination") == "external":
                return "Credentials cannot be transmitted externally"

        # Regulatory Level 2: GDPR data deletion
        if policy["id"] == "reg_001" and action.get("action_type") == "data_deletion":
            if action.get("delay_days", 0) > 30:
                return "Data deletion must occur within 30 days"

        # Operational Level 3: Max cost per request
        if policy["id"] == "op_001":
            cost = action.get("estimated_cost_usd", 0)
            threshold = policy.get("threshold", 5.0)
            if cost > threshold:
                return f"Cost ${cost:.2f} exceeds threshold ${threshold:.2f}"

        # Tactical Level 4: Prefer deterministic skills
        if policy["id"] == "tac_001":
            if action.get("action_type") == "skill_selection":
                if action.get("selected_type") == "llm" and action.get("deterministic_available"):
                    return "Deterministic skill is available but LLM was selected"

        return True

    def get_violations(self) -> List[Dict[str, Any]]:
        return self._violations.copy()


# ──────────────────────────────────────────────────────────────────────────
# Agent System
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class ExecutionResult:
    """Result of an agent execution."""
    output: Any = None
    error: Optional[str] = None
    trace_step: Optional[Dict[str, Any]] = None
    success: bool = True


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        agent_type: str = "deterministic",
        skills: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.agent_id = agent_id
        self.name = name
        self.agent_type = agent_type
        self.skills = skills or []
        self.config = config or {}

    @abstractmethod
    def execute(self, input: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute the agent with given input and context."""
        pass

    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this agent provides."""
        return self.skills.copy()


class SimpleAgent(BaseAgent):
    """A simple agent that echoes its input."""

    def execute(self, input: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        return ExecutionResult(
            output=input or {},
            success=True,
        )


# ──────────────────────────────────────────────────────────────────────────
# Orchestrator
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class TraceStep:
    """A single step in the execution trace."""
    step_id: str
    agent_id: str
    skill_id: Optional[str]
    action: str
    input: Dict[str, Any] = field(default_factory=dict)
    output: Any = None
    error: Optional[Dict[str, Any]] = None
    cost: Dict[str, Any] = field(default_factory=dict)
    policy_violations: List[str] = field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None


@dataclass
class RuntimeTrace:
    """Complete trace of a workforce execution."""
    trace_id: str
    workflow_id: str
    start_time: str
    end_time: Optional[str] = None
    input: Dict[str, Any] = field(default_factory=dict)
    steps: List[TraceStep] = field(default_factory=list)
    output: Any = None
    total_cost: Dict[str, Any] = field(default_factory=dict)
    performance_summary: Dict[str, Any] = field(default_factory=dict)
    governance_check: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary."""
        return {
            "trace_id": self.trace_id,
            "workflow_id": self.workflow_id,
            "timestamp": {
                "start": self.start_time,
                "end": self.end_time,
            },
            "input": self.input,
            "steps": [self._step_to_dict(s) for s in self.steps],
            "output": self.output,
            "total_cost": self.total_cost,
            "performance_summary": self.performance_summary,
            "governance_check": self.governance_check,
            "meta": self.meta,
        }

    def _step_to_dict(self, step: TraceStep) -> Dict[str, Any]:
        return {
            "step_id": step.step_id,
            "agent_id": step.agent_id,
            "skill_id": step.skill_id,
            "action": step.action,
            "input": step.input,
            "output": step.output,
            "error": step.error,
            "cost": step.cost,
            "policy_violations": step.policy_violations,
            "timestamp": {
                "start": step.start_time,
                "end": step.end_time,
            },
        }


class Orchestrator:
    """Schedules and executes agents in a workforce."""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        state_store: Optional[BaseStateStore] = None,
        policy_engine: Optional[BasePolicyEngine] = None,
    ) -> None:
        self.event_bus = event_bus or EventBus()
        self.state_store = state_store or MemoryStateStore()
        self.policy_engine = policy_engine or PolicyEngine()
        self._agents: Dict[str, BaseAgent] = {}
        self._trace: Optional[RuntimeTrace] = None

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent for execution."""
        self._agents[agent.agent_id] = agent

    def get_agent_ids(self) -> List[str]:
        """Return list of registered agent IDs."""
        return list(self._agents.keys())

    def run(
        self,
        agent_id: str,
        input: Optional[Dict[str, Any]] = None,
        skill_id: Optional[str] = None,
    ) -> ExecutionResult:
        """Run a single agent and return the result."""
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} not registered")

        agent = self._agents[agent_id]
        start_time = datetime.now(timezone.utc).isoformat()

        # Policy check
        action = {
            "action_type": "agent_execution",
            "agent_id": agent_id,
            "agent_type": agent.agent_type,
        }
        try:
            self.policy_engine.enforce(action)
        except PolicyViolationError as e:
            return ExecutionResult(
                error=str(e),
                success=False,
                trace_step=TraceStep(
                    step_id=f"step_{uuid.uuid4().hex[:8]}",
                    agent_id=agent_id,
                    skill_id=skill_id,
                    action="execute",
                    input=input or {},
                    error={"code": "POLICY_VIOLATION", "message": str(e)},
                    start_time=start_time,
                    end_time=datetime.now(timezone.utc).isoformat(),
                ),
            )

        # Execute agent
        try:
            result = agent.execute(input=input)
        except Exception as e:
            result = ExecutionResult(
                error=str(e),
                success=False,
            )

        end_time = datetime.now(timezone.utc).isoformat()

        # Build trace step
        step = TraceStep(
            step_id=f"step_{uuid.uuid4().hex[:8]}",
            agent_id=agent_id,
            skill_id=skill_id,
            action="execute",
            input=input or {},
            output=result.output,
            error={"code": "EXECUTION_ERROR", "message": result.error} if result.error else None,
            cost={"tokens": 0, "estimated_usd": 0.0},
            start_time=start_time,
            end_time=end_time,
        )
        result.trace_step = step

        return result

    def handle_agent_failure(self, agent_id: str, error: Exception) -> Dict[str, Any]:
        """Handle an agent failure gracefully."""
        return {
            "agent_id": agent_id,
            "error": str(error),
            "handled": True,
            "retry_recommended": isinstance(error, RuntimeError),
        }

    def run_workforce(
        self,
        workforce: Dict[str, Any],
        input: Optional[Dict[str, Any]] = None,
    ) -> "WorkforceResult":
        """Execute a complete workforce program."""
        trace_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc).isoformat()

        self._trace = RuntimeTrace(
            trace_id=trace_id,
            workflow_id=workforce.get("workflow_id", "unknown"),
            start_time=start_time,
            input=input or {},
            meta={
                "version": "1.3.0",
                "environment": "local",
                "policies_hash": "default",
            },
        )

        steps = []
        total_cost = {"tokens": 0, "estimated_usd": 0.0}
        output = {}

        # Run each agent in sequence
        for agent_config in workforce.get("agents", []):
            agent_id = agent_config["agent_id"]
            if agent_id not in self._agents:
                # Auto-create simple agent if not registered
                self.register_agent(SimpleAgent(agent_id=agent_id, name=agent_config.get("name", agent_id)))

            result = self.run(agent_id=agent_id, input=input)

            if result.trace_step:
                steps.append(result.trace_step)
                total_cost["tokens"] += result.trace_step.cost.get("tokens", 0)
                total_cost["estimated_usd"] += result.trace_step.cost.get("estimated_usd", 0.0)

            if result.success:
                output = result.output
            else:
                # Record failure but continue (or handle based on policy)
                pass

        end_time = datetime.now(timezone.utc).isoformat()
        duration = (datetime.fromisoformat(end_time.replace("Z", "+00:00")) - datetime.fromisoformat(start_time.replace("Z", "+00:00"))).total_seconds()

        self._trace.end_time = end_time
        self._trace.steps = steps
        self._trace.output = output
        self._trace.total_cost = total_cost
        self._trace.performance_summary = {
            "duration_seconds": duration,
            "steps_count": len(steps),
            "success_rate": sum(1 for s in steps if s.error is None) / len(steps) if steps else 0.0,
        }
        self._trace.governance_check = {
            "passed": True,
            "violations": [],
        }

        return WorkforceResult(
            output=output,
            trace=self._trace,
            success=True,
        )


@dataclass
class WorkforceResult:
    """Result of a complete workforce execution."""
    output: Any = None
    trace: Optional[RuntimeTrace] = None
    success: bool = True
    error: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────
# Local Runtime
# ──────────────────────────────────────────────────────────────────────────

class LocalRuntime:
    """In-process execution environment for MAF workloads."""

    def __init__(
        self,
        use_neo4j: bool = False,
        neo4j_uri: Optional[str] = None,
        policies: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.event_bus = EventBus()
        self.state_store = MemoryStateStore()
        self.policy_engine = PolicyEngine(policies=policies)
        self.orchestrator = Orchestrator(
            event_bus=self.event_bus,
            state_store=self.state_store,
            policy_engine=self.policy_engine,
        )
        self._cancelled = False

    def execute(
        self,
        workforce: Dict[str, Any],
        input: Optional[Dict[str, Any]] = None,
    ) -> WorkforceResult:
        """Execute a workforce program and return the result."""
        if self._cancelled:
            raise RuntimeError("Runtime has been cancelled")
        return self.orchestrator.run_workforce(workforce, input=input)

    def cancel(self) -> None:
        """Cancel the current execution."""
        self._cancelled = True

    @property
    def trace(self) -> Optional[RuntimeTrace]:
        """Return the trace of the last execution."""
        return self.orchestrator._trace
