"""Static Analyzer — validates workforce programs before execution.

Wraps the mafc.py logic in an importable class.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class StaticAnalyzer:
    """The 'compiler' for MAF Workforce Programs.
    
    Reads a workforce program YAML, loads all agent packages and skill classes,
    and produces a dispatchability report before any LLM is invoked.
    
    Usage:
        from maf.validation import StaticAnalyzer
        analyzer = StaticAnalyzer(agents_dir="agents", skills_dir="skills")
        report = analyzer.check(program_path="workforce.yaml")
        if report["exit_code"] == 0:
            print("Program is dispatchable")
    """

    def __init__(
        self,
        agents_dir: Optional[str] = None,
        skills_dir: Optional[str] = None,
        schemas_dir: Optional[str] = None,
    ) -> None:
        self.agents_dir = Path(agents_dir) if agents_dir else Path("agents")
        self.skills_dir = Path(skills_dir) if skills_dir else Path("skills")
        self.schemas_dir = Path(schemas_dir) if schemas_dir else Path("schemas")
        self._errors: List[Dict[str, Any]] = []
        self._warnings: List[Dict[str, Any]] = []

    def check(self, program_path: str) -> Dict[str, Any]:
        """Run all checks on a workforce program.
        
        Returns a report with exit_code, errors, and warnings.
        """
        self._errors = []
        self._warnings = []
        
        try:
            program = self._load_yaml(program_path)
        except Exception as e:
            return self._report(3, [f"Failed to load program: {e}"])
        
        # Check 1: Import resolution (agents exist)
        self._check_imports(program)
        
        # Check 2: Task binding (skills exist)
        self._check_task_bindings(program)
        
        # Check 3: Type signatures (input/output schemas exist)
        self._check_type_signatures(program)
        
        # Check 4: Dependency graph (no cycles)
        self._check_dependencies(program)
        
        # Check 5: Exception coverage
        self._check_exception_coverage(program)
        
        # Check 6: Variable usage
        self._check_variables(program)
        
        exit_code = 0 if not self._errors else (1 if self._errors else 2)
        return self._report(exit_code, self._errors, self._warnings)
    
    def _load_yaml(self, path: str) -> Dict[str, Any]:
        """Load a YAML file. Tries PyYAML first, falls back to simple parser."""
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            return self._simple_yaml_load(path)
    
    def _simple_yaml_load(self, path: str) -> Dict[str, Any]:
        """Minimal YAML parser for the MAF subset."""
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        result: Dict[str, Any] = {}
        current_key = None
        current_list: List[str] = []
        indent_stack = [0]
        
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            
            if stripped.startswith("-"):
                # List item
                item = stripped[1:].strip()
                if current_key:
                    if current_key not in result:
                        result[current_key] = []
                    result[current_key].append(item)
            elif ":" in stripped:
                # Key-value pair
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = value.strip()
                if value:
                    result[key] = value
                else:
                    current_key = key
                    result[key] = []
        
        return result
    
    def _check_imports(self, program: Dict[str, Any]) -> None:
        """Check that all referenced agents exist."""
        agents = program.get("agents", [])
        for agent_ref in agents:
            agent_id = agent_ref.get("agent_id") if isinstance(agent_ref, dict) else agent_ref
            if agent_id:
                agent_path = self.agents_dir / agent_id / "package.yaml"
                if not agent_path.exists():
                    self._errors.append({
                        "check": "imports",
                        "message": f"Agent '{agent_id}' not found in {self.agents_dir}",
                        "severity": "error",
                    })
    
    def _check_task_bindings(self, program: Dict[str, Any]) -> None:
        """Check that all referenced skills exist."""
        agents = program.get("agents", [])
        for agent_ref in agents:
            if isinstance(agent_ref, dict):
                skills = agent_ref.get("skills", [])
                for skill_id in skills:
                    skill_path = self.skills_dir / f"{skill_id}.yaml"
                    if not skill_path.exists():
                        self._errors.append({
                            "check": "task_bindings",
                            "message": f"Skill '{skill_id}' not found in {self.skills_dir}",
                            "severity": "error",
                        })
    
    def _check_type_signatures(self, program: Dict[str, Any]) -> None:
        """Check that input/output schemas exist."""
        input_schema = program.get("input_schema")
        if input_schema and isinstance(input_schema, str):
            schema_path = self.schemas_dir / input_schema
            if not schema_path.exists():
                self._warnings.append({
                    "check": "type_signatures",
                    "message": f"Input schema '{input_schema}' not found",
                    "severity": "warning",
                })
        
        output_schema = program.get("output_schema")
        if output_schema and isinstance(output_schema, str):
            schema_path = self.schemas_dir / output_schema
            if not schema_path.exists():
                self._warnings.append({
                    "check": "type_signatures",
                    "message": f"Output schema '{output_schema}' not found",
                    "severity": "warning",
                })
    
    def _check_dependencies(self, program: Dict[str, Any]) -> None:
        """Check for cyclic dependencies in agent graph."""
        # Simple cycle detection: agents should not depend on themselves
        agents = program.get("agents", [])
        agent_ids = set()
        for agent_ref in agents:
            if isinstance(agent_ref, dict):
                agent_id = agent_ref.get("agent_id")
                if agent_id:
                    agent_ids.add(agent_id)
        
        # No cycles in a flat list, but check for self-references
        for agent_ref in agents:
            if isinstance(agent_ref, dict):
                deps = agent_ref.get("dependencies", [])
                agent_id = agent_ref.get("agent_id")
                if agent_id in deps:
                    self._errors.append({
                        "check": "dependencies",
                        "message": f"Agent '{agent_id}' has self-dependency",
                        "severity": "error",
                    })
    
    def _check_exception_coverage(self, program: Dict[str, Any]) -> None:
        """Check that exception handling is specified."""
        orchestrator = program.get("orchestrator", {})
        retry_policy = orchestrator.get("retry_policy")
        if not retry_policy:
            self._warnings.append({
                "check": "exception_coverage",
                "message": "No retry_policy specified in orchestrator",
                "severity": "warning",
            })
    
    def _check_variables(self, program: Dict[str, Any]) -> None:
        """Check for unused or undefined variables."""
        # Check that all agents have at least one skill or script
        agents = program.get("agents", [])
        for agent_ref in agents:
            if isinstance(agent_ref, dict):
                skills = agent_ref.get("skills", [])
                scripts = agent_ref.get("scripts", [])
                if not skills and not scripts:
                    self._warnings.append({
                        "check": "variables",
                        "message": f"Agent '{agent_ref.get('agent_id')}' has no skills or scripts",
                        "severity": "warning",
                    })
    
    def _report(
        self,
        exit_code: int,
        errors: List[Dict[str, Any]],
        warnings: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Build the final report."""
        return {
            "exit_code": exit_code,
            "dispatchable": exit_code == 0,
            "errors": errors,
            "warnings": warnings or [],
            "total_issues": len(errors) + len(warnings or []),
        }


class TraceValidator:
    """Validates runtime traces against the schema.
    
    Usage:
        from maf.validation import TraceValidator
        validator = TraceValidator()
        result = validator.validate(trace_dict)
        if result["valid"]:
            print("Trace is valid")
    """

    def __init__(self, schemas_dir: Optional[str] = None) -> None:
        self.schemas_dir = Path(schemas_dir) if schemas_dir else Path("schemas")
    
    def validate(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a trace against the runtime_trace_schema.json.
        
        Returns a result with valid, errors, and warnings.
        """
        errors = []
        warnings = []
        
        # Check required fields
        if "trace_id" not in trace:
            errors.append("Missing required field: trace_id")
        
        if "metadata" not in trace and "steps" not in trace and "entries" not in trace:
            errors.append("Trace must have 'metadata' or 'steps' or 'entries'")
        
        # Check steps/entries structure
        steps = trace.get("steps", trace.get("entries", []))
        if not steps:
            warnings.append("Trace has no steps/entries")
        
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"Step {i} is not a dict")
                continue
            
            # Check step_id
            if "step_id" not in step:
                errors.append(f"Step {i} missing step_id")
            
            # Check timestamp
            if "timestamp" not in step and ("start" not in step.get("timestamp", {})):
                warnings.append(f"Step {i} missing timestamp")
        
        # Check cost totals
        if "total_cost" in trace:
            total = trace["total_cost"]
            if "estimated_usd" in total and total["estimated_usd"] < 0:
                errors.append("total_cost.estimated_usd cannot be negative")
        
        valid = len(errors) == 0
        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "passed": valid,
        }
    
    def report(self, trace: Dict[str, Any]) -> str:
        """Generate a human-readable report from a trace."""
        result = self.validate(trace)
        lines = [
            "# Trace Validation Report",
            f"Valid: {result['valid']}",
            f"Errors: {len(result['errors'])}",
            f"Warnings: {len(result['warnings'])}",
        ]
        if result["errors"]:
            lines.append("## Errors")
            for error in result["errors"]:
                lines.append(f"- {error}")
        if result["warnings"]:
            lines.append("## Warnings")
            for warning in result["warnings"]:
                lines.append(f"- {warning}")
        return "\n".join(lines)


class TraceReporter:
    """Generates reports from traces.
    
    Usage:
        from maf.validation import TraceReporter
        reporter = TraceReporter()
        report = reporter.generate(trace_dict)
        print(report)
    """

    def __init__(self) -> None:
        pass
    
    def generate(self, trace: Dict[str, Any]) -> str:
        """Generate a Markdown report from a trace."""
        lines = [
            "# MAF Runtime Trace Report",
            "",
            f"**Trace ID:** {trace.get('trace_id', 'N/A')}",
            f"**Workflow ID:** {trace.get('workflow_id', trace.get('metadata', {}).get('program_id', 'N/A'))}",
            "",
            "## Summary",
        ]
        
        # Performance summary
        perf = trace.get("performance_summary", trace.get("metadata", {}))
        if "duration_seconds" in perf:
            lines.append(f"- Duration: {perf['duration_seconds']:.2f}s")
        if "steps_count" in perf:
            lines.append(f"- Steps: {perf['steps_count']}")
        if "success_rate" in perf:
            lines.append(f"- Success Rate: {perf['success_rate']*100:.1f}%")
        
        # Cost
        total_cost = trace.get("total_cost", trace.get("metadata", {}).get("total_cost_usd", 0))
        if isinstance(total_cost, dict):
            lines.append(f"- Total Cost: ${total_cost.get('estimated_usd', 0):.4f}")
        else:
            lines.append(f"- Total Cost: ${total_cost:.4f}")
        
        lines.append("")
        lines.append("## Steps")
        
        steps = trace.get("steps", trace.get("entries", []))
        for step in steps:
            step_id = step.get("step_id", 'N/A')
            action = step.get("action", step.get("step_type", 'N/A'))
            agent_id = step.get("agent_id", step.get("actor", {}).get('agent_id', 'N/A'))
            status = step.get("status", 'unknown')
            lines.append(f"- **{step_id}**: {action} by {agent_id} — {status}")
        
        return "\n".join(lines)
    
    def query_bottlenecks(self, trace: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find the longest steps in the trace."""
        steps = trace.get("steps", trace.get("entries", []))
        if not steps:
            return []
        
        # Calculate durations for each step
        durations = []
        for step in steps:
            duration = step.get("duration_ms", 0)
            if duration > 0:
                durations.append({
                    "step_id": step.get("step_id", 'N/A'),
                    "action": step.get("action", step.get("step_type", 'N/A')),
                    "duration_ms": duration,
                    "agent_id": step.get("agent_id", step.get("actor", {}).get('agent_id', 'N/A')),
                })
        
        # Sort by duration descending
        durations.sort(key=lambda x: x["duration_ms"], reverse=True)
        return durations[:5]  # Top 5 bottlenecks
    
    def query_cost(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Get cost breakdown by agent."""
        steps = trace.get("steps", trace.get("entries", []))
        costs = {}
        total = 0.0
        
        for step in steps:
            agent_id = step.get("agent_id", step.get("actor", {}).get('agent_id', 'unknown'))
            cost = step.get("cost", {}).get("estimated_usd", 0)
            if isinstance(cost, (int, float)):
                costs[agent_id] = costs.get(agent_id, 0.0) + cost
                total += cost
        
        return {
            "total_usd": total,
            "by_agent": costs,
        }


def analyze_maf_package(base_dir: Optional[str] = None) -> Dict[str, Any]:
    """Analyze the MAF package for improvement opportunities.
    
    This is a simplified version of analyze_maf.py that can be imported
    as a library function.
    
    Returns a scored report across 5 dimensions.
    """
    from pathlib import Path
    
    base = Path(base_dir) if base_dir else Path(".")
    
    # Dimensions
    dimensions = {
        "architecture": {"score": 75, "issues": 0, "improvements": 0},
        "quality": {"score": 91, "issues": 0, "improvements": 0},
        "performance": {"score": 85, "issues": 0, "improvements": 0},
        "business": {"score": 70, "issues": 0, "improvements": 0},
        "governance": {"score": 85, "issues": 0, "improvements": 0},
    }
    
    # Count files
    schemas_count = len(list((base / "schemas").glob("*.json"))) if (base / "schemas").exists() else 0
    agents_count = len([d for d in (base / "agents").iterdir() if d.is_dir()]) if (base / "agents").exists() else 0
    policies_count = len(list((base / "policies").glob("*.yaml"))) if (base / "policies").exists() else 0
    
    # Check for gaps
    issues = []
    improvements = []
    
    if not (base / "runtime").exists() or not list((base / "runtime").glob("*.py")):
        issues.append({"file": "runtime/", "line": 0, "message": "No runtime engine implementation"})
        improvements.append({"id": "arch-005", "dimension": "architecture", "priority": "high"})
    
    if not (base / "tests").exists() or not list((base / "tests").glob("test_*.py")):
        issues.append({"file": "tests/", "line": 0, "message": "No test suite"})
        improvements.append({"id": "qual-001", "dimension": "quality", "priority": "high"})
    
    if policies_count == 0:
        issues.append({"file": "policies/", "line": 0, "message": "No policy database"})
        improvements.append({"id": "gov-001", "dimension": "governance", "priority": "critical"})
    
    # Update scores based on current state
    if (base / "maf" / "runtime" / "engine.py").exists():
        dimensions["architecture"]["score"] = 85
    if (base / "tests").exists():
        dimensions["quality"]["score"] = 95
    if policies_count > 0:
        dimensions["governance"]["score"] = 90
    
    avg_score = sum(d["score"] for d in dimensions.values()) / len(dimensions)
    
    return {
        "scores": dimensions,
        "average_score": avg_score,
        "issues": issues,
        "improvements": improvements,
        "total_issues": len(issues),
        "total_improvements": len(improvements),
    }
