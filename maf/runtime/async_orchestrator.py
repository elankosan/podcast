"""Async Orchestrator — enables parallel agent execution with asyncio.

Usage:
    from maf.runtime import AsyncOrchestrator
    from maf.runtime.engine import SimpleAgent
    
    orchestrator = AsyncOrchestrator()
    orchestrator.register_agent(SimpleAgent(agent_id="a1", name="Agent 1"))
    orchestrator.register_agent(SimpleAgent(agent_id="a2", name="Agent 2"))
    
    # Run agents in parallel
    results = await orchestrator.run_parallel(
        ["a1", "a2"],
        input={"query": "test"}
    )
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from maf.runtime.engine import (
    BaseAgent,
    ExecutionResult,
    Orchestrator,
    PolicyViolationError,
    RuntimeTrace,
    TraceStep,
    WorkforceResult,
)


class AsyncOrchestrator(Orchestrator):
    """Orchestrator with asyncio support for parallel agent execution.
    
    Extends the base Orchestrator with:
    - Parallel agent execution via asyncio.gather
    - Concurrent event bus operations
    - Async state store operations
    - Retry logic with exponential backoff
    """

    def __init__(
        self,
        event_bus=None,
        state_store=None,
        policy_engine=None,
        max_concurrent: int = 4,
        retry_policy: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(event_bus, state_store, policy_engine)
        self.max_concurrent = max_concurrent
        self.retry_policy = retry_policy or {
            "max_retries": 3,
            "backoff": "exponential",
            "base_delay": 1.0,
        }
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    async def run(
        self,
        agent_id: str,
        input: Optional[Dict[str, Any]] = None,
        skill_id: Optional[str] = None,
    ) -> ExecutionResult:
        """Run a single agent asynchronously."""
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
        
        # Execute with retry logic
        result = await self._execute_with_retry(agent, input, agent_id, skill_id)
        return result
    
    async def _execute_with_retry(
        self,
        agent: BaseAgent,
        input: Optional[Dict[str, Any]],
        agent_id: str,
        skill_id: Optional[str],
    ) -> ExecutionResult:
        """Execute an agent with retry logic."""
        max_retries = self.retry_policy.get("max_retries", 3)
        base_delay = self.retry_policy.get("base_delay", 1.0)
        
        last_error = None
        for attempt in range(max_retries + 1):
            start_time = datetime.now(timezone.utc).isoformat()
            try:
                # Check if agent has async execute
                if hasattr(agent, "execute_async"):
                    result = await agent.execute_async(input=input)
                else:
                    # Run synchronous execute in thread pool
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, agent.execute, input
                    )
                
                end_time = datetime.now(timezone.utc).isoformat()
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
            
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        return ExecutionResult(
            error=f"Failed after {max_retries} retries: {last_error}",
            success=False,
            trace_step=TraceStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                skill_id=skill_id,
                action="execute",
                input=input or {},
                error={"code": "RETRY_EXHAUSTED", "message": str(last_error)},
                start_time=datetime.now(timezone.utc).isoformat(),
                end_time=datetime.now(timezone.utc).isoformat(),
            ),
        )
    
    async def run_parallel(
        self,
        agent_ids: List[str],
        input: Optional[Dict[str, Any]] = None,
    ) -> List[ExecutionResult]:
        """Run multiple agents in parallel with a concurrency limit.
        
        Args:
            agent_ids: List of agent IDs to run
            input: Shared input for all agents
            
        Returns:
            List of ExecutionResult objects, one per agent
        """
        async def _run_with_semaphore(agent_id: str) -> ExecutionResult:
            async with self._semaphore:
                return await self.run(agent_id, input)
        
        tasks = [_run_with_semaphore(aid) for aid in agent_ids]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def run_workforce(
        self,
        workforce: Dict[str, Any],
        input: Optional[Dict[str, Any]] = None,
    ) -> WorkforceResult:
        """Execute a complete workforce program with async support.
        
        If the orchestrator type is "parallel", agents run concurrently.
        If "sequential", agents run one after another.
        """
        trace_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc).isoformat()
        
        self._trace = RuntimeTrace(
            trace_id=trace_id,
            workflow_id=workforce.get("workflow_id", "unknown"),
            start_time=start_time,
            input=input or {},
            meta={
                "version": "2.0.0",
                "environment": "local",
                "policies_hash": "default",
                "async": True,
            },
        )
        
        orchestrator_type = workforce.get("orchestrator", {}).get("type", "sequential")
        agent_configs = workforce.get("agents", [])
        
        # Auto-register missing agents
        for config in agent_configs:
            agent_id = config["agent_id"]
            if agent_id not in self._agents:
                from maf.runtime.engine import SimpleAgent
                self.register_agent(SimpleAgent(agent_id=agent_id, name=config.get("name", agent_id)))
        
        steps = []
        total_cost = {"tokens": 0, "estimated_usd": 0.0}
        output = {}
        
        agent_ids = [c["agent_id"] for c in agent_configs]
        
        if orchestrator_type == "parallel":
            # Run all agents in parallel
            results = await self.run_parallel(agent_ids, input)
        else:
            # Run sequentially
            results = []
            for agent_id in agent_ids:
                result = await self.run(agent_id, input)
                results.append(result)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                # Handle exceptions from gather
                step = TraceStep(
                    step_id=f"step_{uuid.uuid4().hex[:8]}",
                    agent_id="unknown",
                    skill_id=None,
                    action="execute",
                    input=input or {},
                    error={"code": "ASYNC_ERROR", "message": str(result)},
                    start_time=datetime.now(timezone.utc).isoformat(),
                    end_time=datetime.now(timezone.utc).isoformat(),
                )
                steps.append(step)
            else:
                if result.trace_step:
                    steps.append(result.trace_step)
                    total_cost["tokens"] += result.trace_step.cost.get("tokens", 0)
                    total_cost["estimated_usd"] += result.trace_step.cost.get("estimated_usd", 0.0)
                if result.success:
                    output = result.output
        
        end_time = datetime.now(timezone.utc).isoformat()
        duration = (datetime.fromisoformat(end_time.replace("Z", "+00:00")) - 
                   datetime.fromisoformat(start_time.replace("Z", "+00:00"))).total_seconds()
        
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
