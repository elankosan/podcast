"""Multi-Agent Framework — a self-hosted, programmable workforce execution system.

MAF is a system for orchestrating teams of AI agents that can plan, execute,
verify, and improve themselves. It operates as a library, SDK, scaffold, and
sphere integration layer.
"""

__version__ = "1.3.0"
__author__ = "Selan (Elanko)"

from maf.core import Agent, Blueprint, Skill, Task
from maf.runtime import (
    AsyncOrchestrator,
    BuildLogger,
    EventBus,
    LocalRuntime,
    MemoryStateStore,
    Orchestrator,
    PolicyEngine,
    PolicyViolationError,
    RuntimeTrace,
    TraceStep,
    WorkforceResult,
)

from maf.validation import (
    StaticAnalyzer,
    TraceReporter,
    TraceValidator,
    analyze_maf_package,
)

from maf.benchmarks import BenchmarkRunner

__all__ = [
    "__version__",
    # Core domain types
    "Agent",
    "Skill",
    "Blueprint",
    "Task",
    # Runtime engine
    "LocalRuntime",
    "Orchestrator",
    "EventBus",
    "MemoryStateStore",
    "PolicyEngine",
    "PolicyViolationError",
    "RuntimeTrace",
    "TraceStep",
    "WorkforceResult",
    "BuildLogger",
    "AsyncOrchestrator",
    "BenchmarkRunner",
    # Validation tools
    "StaticAnalyzer",
    "TraceReporter",
    "TraceValidator",
    "analyze_maf_package",
]
