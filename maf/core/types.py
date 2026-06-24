"""Core domain types for MAF: Agent, Skill, Blueprint, Task."""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Skill:
    """A deterministic, reusable, typed function with schemas."""
    skill_id: str
    name: str
    description: str = ""
    skill_type: str = "atomic"  # atomic | composite | conditional | adaptive
    version: str = "1.0.0"
    input_schema: str = ""
    output_schema: str = ""
    error_schema: str = ""
    deterministic: bool = True
    reusable: bool = True
    atomic: bool = True
    function: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 30
    memory_limit: str = "256MB"

    def __post_init__(self):
        valid_types = {"atomic", "composite", "conditional", "adaptive"}
        if self.skill_type not in valid_types:
            raise ValueError(f"skill_type must be one of {valid_types}")


@dataclass
class Agent:
    """A typed worker with a package, skills, and optional reasoning."""
    agent_id: str
    name: str
    role: str = ""
    version: str = "1.0.0"
    skills: List[str] = field(default_factory=list)
    entry_point: str = ""
    agent_type: str = "deterministic"  # deterministic | reasoning | hybrid | meta
    reasoning: Optional[Dict[str, Any]] = None
    scripts: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        valid_types = {"deterministic", "reasoning", "hybrid", "meta"}
        if self.agent_type not in valid_types:
            raise ValueError(f"agent_type must be one of {valid_types}")


@dataclass
class Task:
    """A single invocation of a skill by an agent with specific input."""
    task_id: str
    agent_id: str
    skill_id: Optional[str] = None
    input: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timeout: int = 30


@dataclass
class Blueprint:
    """A compiled workforce program ready for execution."""
    workflow_id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    agents: List[Agent] = field(default_factory=list)
    orchestrator: Dict[str, Any] = field(default_factory=dict)
    tasks: List[Task] = field(default_factory=list)

    @classmethod
    def load(cls, path: str) -> "Blueprint":
        """Load a blueprint from a YAML file."""
        import yaml
        from pathlib import Path

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Parse agents
        agents = []
        for agent_data in data.get("agents", []):
            agents.append(Agent(
                agent_id=agent_data["agent_id"],
                name=agent_data["name"],
                role=agent_data.get("role", ""),
                version=agent_data.get("version", "1.0.0"),
                skills=agent_data.get("skills", []),
                entry_point=agent_data.get("entry_point", ""),
                agent_type=agent_data.get("type", agent_data.get("agent_type", "deterministic")),
            ))

        return cls(
            workflow_id=data["workflow_id"],
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {}),
            agents=agents,
            orchestrator=data.get("orchestrator", {}),
        )

    def compile(self) -> Dict[str, Any]:
        """Compile the blueprint into a manifest."""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "version": self.version,
            "agents": [a.agent_id for a in self.agents],
            "validated": True,
            "compiled_at": datetime.now().isoformat(),
        }
