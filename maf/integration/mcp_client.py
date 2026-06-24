"""MCP Client — delegates to external Model Context Protocol servers.

Usage:
    from maf.integration import MCPClient
    client = MCPClient.from_config("integrations/llm.yaml")
    result = client.call("generate", {"prompt": "Hello"})
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


class MCPClient:
    """Client for communicating with MCP servers.
    
    Supports both stdio and HTTP transports.
    """

    def __init__(
        self,
        integration_id: str,
        protocol: str,
        config: Dict[str, Any],
    ) -> None:
        self.integration_id = integration_id
        self.protocol = protocol
        self.config = config
    
    @classmethod
    def from_config(cls, config_path: str) -> "MCPClient":
        """Create an MCP client from a YAML config file."""
        import yaml
        
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        return cls(
            integration_id=config["integration_id"],
            protocol=config["protocol"],
            config=config.get("config", {}),
        )
    
    def call(self, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server."""
        if self.protocol == "stdio":
            return self._call_stdio(tool, arguments)
        elif self.protocol in ("http", "https"):
            return self._call_http(tool, arguments)
        else:
            raise ValueError(f"Unsupported protocol: {self.protocol}")
    
    def _call_stdio(self, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool via stdio transport."""
        command = self.config.get("command")
        if not command:
            raise RuntimeError("No command specified for stdio transport")
        
        # Build the MCP request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool,
                "arguments": arguments,
            },
            "id": 1,
        }
        
        # Run the command
        result = subprocess.run(
            command,
            input=json.dumps(request),
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"MCP command failed: {result.stderr}")
        
        return json.loads(result.stdout)
    
    def _call_http(self, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool via HTTP transport."""
        import urllib.request
        
        url = self.config.get("url")
        if not url:
            raise RuntimeError("No URL specified for HTTP transport")
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool,
                "arguments": arguments,
            },
            "id": 1,
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(request).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        
        with urllib.request.urlopen(req, timeout=self.config.get("timeout", 30)) as response:
            return json.loads(response.read().decode("utf-8"))
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the MCP server is reachable."""
        try:
            if self.protocol == "stdio":
                command = self.config.get("command")
                if command:
                    result = subprocess.run(command, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"status": "healthy", "protocol": "stdio"}
            elif self.protocol in ("http", "https"):
                import urllib.request
                url = self.config.get("url")
                if url:
                    req = urllib.request.Request(url, method="GET")
                    with urllib.request.urlopen(req, timeout=5) as response:
                        if response.status == 200:
                            return {"status": "healthy", "protocol": "http"}
            return {"status": "unknown", "protocol": self.protocol}
        except Exception as e:
            return {"status": "unavailable", "reason": str(e)}
