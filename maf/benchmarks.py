"""Performance benchmarks for MAF.

Usage:
    from maf.benchmarks import BenchmarkRunner
    runner = BenchmarkRunner()
    results = runner.run_all()
    print(results.to_markdown())
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class BenchmarkResult:
    """Result of a single benchmark."""
    name: str
    duration_ms: float
    iterations: int
    throughput: float  # operations per second
    memory_mb: float = 0.0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "duration_ms": round(self.duration_ms, 2),
            "iterations": self.iterations,
            "throughput": round(self.throughput, 2),
            "memory_mb": round(self.memory_mb, 2),
            "notes": self.notes,
        }


@dataclass
class BenchmarkReport:
    """Aggregated benchmark report."""
    timestamp: str
    version: str
    results: List[BenchmarkResult] = field(default_factory=list)
    environment: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "version": self.version,
            "environment": self.environment,
            "results": [r.to_dict() for r in self.results],
        }

    def to_markdown(self) -> str:
        lines = [
            "# MAF Performance Benchmarks",
            "",
            f"**Version:** {self.version}",
            f"**Timestamp:** {self.timestamp}",
            "",
            "| Benchmark | Duration (ms) | Iterations | Throughput (ops/s) |",
            "|-----------|--------------:|-----------:|-------------------:|",
        ]
        for r in self.results:
            lines.append(
                f"| {r.name} | {r.duration_ms:.2f} | {r.iterations} | {r.throughput:.2f} |"
            )
        return "\n".join(lines)


class BenchmarkRunner:
    """Runs performance benchmarks for MAF components."""

    def __init__(self) -> None:
        self.results: List[BenchmarkResult] = []

    def benchmark_static_analyzer(self, iterations: int = 100) -> BenchmarkResult:
        """Benchmark the StaticAnalyzer.check() method."""
        from maf.validation import StaticAnalyzer
        import tempfile
        
        # Create a test workforce (use simple YAML if PyYAML not available)
        workforce_lines = [
            "workflow_id: wf_bench",
            "name: Benchmark",
            "agents:",
            "  - agent_id: test",
            "    name: Test",
            "    skills: []",
            "    type: deterministic",
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("\n".join(workforce_lines))
            path = f.name

        analyzer = StaticAnalyzer()
        start = time.perf_counter()
        for _ in range(iterations):
            analyzer.check(path)
        end = time.perf_counter()

        duration_ms = (end - start) * 1000
        return BenchmarkResult(
            name="StaticAnalyzer.check()",
            duration_ms=duration_ms,
            iterations=iterations,
            throughput=iterations / (duration_ms / 1000),
            notes="Validating a minimal workforce program",
        )

    def benchmark_local_runtime(self, iterations: int = 50) -> BenchmarkResult:
        """Benchmark the LocalRuntime.execute() method."""
        from maf.runtime import LocalRuntime

        runtime = LocalRuntime()
        workforce = {
            "workflow_id": "wf_bench",
            "agents": [{"agent_id": "test", "name": "Test"}],
        }

        start = time.perf_counter()
        for _ in range(iterations):
            runtime.execute(workforce, input={"query": "test"})
        end = time.perf_counter()

        duration_ms = (end - start) * 1000
        return BenchmarkResult(
            name="LocalRuntime.execute()",
            duration_ms=duration_ms,
            iterations=iterations,
            throughput=iterations / (duration_ms / 1000),
            notes="Executing a single-agent workforce",
        )

    def benchmark_trace_validator(self, iterations: int = 100) -> BenchmarkResult:
        """Benchmark the TraceValidator.validate() method."""
        from maf.validation import TraceValidator

        validator = TraceValidator()
        trace = {
            "trace_id": "bench-001",
            "steps": [
                {
                    "step_id": "s1",
                    "action": "plan",
                    "agent_id": "a1",
                    "timestamp": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T00:00:01Z"},
                    "cost": {"estimated_usd": 0.001},
                }
                for _ in range(10)
            ],
            "total_cost": {"estimated_usd": 0.01},
        }

        start = time.perf_counter()
        for _ in range(iterations):
            validator.validate(trace)
        end = time.perf_counter()

        duration_ms = (end - start) * 1000
        return BenchmarkResult(
            name="TraceValidator.validate()",
            duration_ms=duration_ms,
            iterations=iterations,
            throughput=iterations / (duration_ms / 1000),
            notes="Validating a 10-step trace",
        )

    def benchmark_event_bus(self, iterations: int = 1000) -> BenchmarkResult:
        """Benchmark the EventBus publish/subscribe throughput."""
        from maf.runtime import EventBus

        bus = EventBus()
        received = []
        bus.subscribe("bench", lambda e: received.append(e))

        start = time.perf_counter()
        for i in range(iterations):
            bus.publish("bench", {"id": i})
        end = time.perf_counter()

        duration_ms = (end - start) * 1000
        return BenchmarkResult(
            name="EventBus.publish()",
            duration_ms=duration_ms,
            iterations=iterations,
            throughput=iterations / (duration_ms / 1000),
            notes="Publishing events to a single subscriber",
        )

    def benchmark_policy_engine(self, iterations: int = 500) -> BenchmarkResult:
        """Benchmark the PolicyEngine.enforce() method."""
        from maf.runtime import PolicyEngine

        policies = [
            {"id": "univ_001", "level": 1, "name": "Never Exfiltrate", "statement": "...", "scope": "global", "enforce": "hard", "priority": 100},
            {"id": "op_001", "level": 3, "name": "Max Cost", "statement": "...", "scope": "exec", "enforce": "soft", "priority": 80, "threshold": 5.0},
        ]
        engine = PolicyEngine(policies=policies)
        action = {"action_type": "test"}

        start = time.perf_counter()
        for _ in range(iterations):
            engine.enforce(action)
        end = time.perf_counter()

        duration_ms = (end - start) * 1000
        return BenchmarkResult(
            name="PolicyEngine.enforce()",
            duration_ms=duration_ms,
            iterations=iterations,
            throughput=iterations / (duration_ms / 1000),
            notes="Enforcing 2 policies against a simple action",
        )

    def benchmark_state_store(self, iterations: int = 1000) -> BenchmarkResult:
        """Benchmark the MemoryStateStore get/set operations."""
        from maf.runtime import MemoryStateStore

        store = MemoryStateStore()
        start = time.perf_counter()
        for i in range(iterations):
            store.set(f"key_{i}", {"value": i})
            store.get(f"key_{i}")
        end = time.perf_counter()

        duration_ms = (end - start) * 1000
        return BenchmarkResult(
            name="MemoryStateStore.get/set",
            duration_ms=duration_ms,
            iterations=iterations,
            throughput=iterations / (duration_ms / 1000),
            notes="Alternating get and set operations",
        )

    def run_all(self) -> BenchmarkReport:
        """Run all benchmarks and return a report."""
        import platform

        results = [
            self.benchmark_static_analyzer(),
            self.benchmark_local_runtime(),
            self.benchmark_trace_validator(),
            self.benchmark_event_bus(),
            self.benchmark_policy_engine(),
            self.benchmark_state_store(),
        ]

        return BenchmarkReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="2.0.0",
            results=results,
            environment={
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "processor": platform.processor(),
            },
        )

    def save(self, path: Path) -> None:
        """Save the benchmark report to a JSON file."""
        report = self.run_all()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)
