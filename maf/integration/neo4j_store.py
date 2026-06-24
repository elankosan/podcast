"""Neo4j State Store — persists agent state to a Neo4j graph database.

Usage:
    from maf.integration import Neo4jStateStore
    store = Neo4jStateStore(uri="bolt://localhost:7687", auth=("neo4j", "password"))
    store.set("key", "value", namespace="session1")
    value = store.get("key", namespace="session1")
"""

from typing import Any, Dict, List, Optional

from maf.runtime import BaseStateStore


class Neo4jStateStore(BaseStateStore):
    """State store backed by Neo4j.
    
    Requires the neo4j Python package:
        pip install neo4j>=5.0.0
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        auth: tuple = ("neo4j", "password"),
        database: str = "maf",
    ) -> None:
        self.uri = uri
        self.auth = auth
        self.database = database
        self._driver: Optional[Any] = None
        self._connected = False
        
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(uri, auth=auth)
            self._connected = True
        except ImportError:
            self._connected = False
        except Exception:
            self._connected = False
    
    def _ensure_connection(self) -> None:
        """Ensure the Neo4j connection is available."""
        if not self._connected:
            raise RuntimeError(
                "Neo4j is not available. Install with: pip install neo4j>=5.0.0\n"
                "Or use MemoryStateStore for local-only operation."
            )
    
    def set(self, key: str, value: Any, namespace: Optional[str] = None) -> None:
        """Store a value in Neo4j."""
        self._ensure_connection()
        ns = namespace or "default"
        
        with self._driver.session(database=self.database) as session:
            session.run(
                """
                MERGE (n:State {namespace: $ns, key: $key})
                SET n.value = $value, n.updated_at = datetime()
                """,
                ns=ns, key=key, value=json.dumps(value)
            )
    
    def get(self, key: str, namespace: Optional[str] = None) -> Any:
        """Retrieve a value from Neo4j."""
        self._ensure_connection()
        ns = namespace or "default"
        
        with self._driver.session(database=self.database) as session:
            result = session.run(
                "MATCH (n:State {namespace: $ns, key: $key}) RETURN n.value AS value",
                ns=ns, key=key
            )
            record = result.single()
            if record:
                import json
                return json.loads(record["value"])
            return None
    
    def delete(self, key: str, namespace: Optional[str] = None) -> None:
        """Delete a value from Neo4j."""
        self._ensure_connection()
        ns = namespace or "default"
        
        with self._driver.session(database=self.database) as session:
            session.run(
                "MATCH (n:State {namespace: $ns, key: $key}) DELETE n",
                ns=ns, key=key
            )
    
    def keys(self, namespace: Optional[str] = None) -> List[str]:
        """List all keys in a namespace."""
        self._ensure_connection()
        ns = namespace or "default"
        
        with self._driver.session(database=self.database) as session:
            result = session.run(
                "MATCH (n:State {namespace: $ns}) RETURN n.key AS key",
                ns=ns
            )
            return [record["key"] for record in result]
    
    def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver:
            self._driver.close()
            self._connected = False
    
    def health_check(self) -> Dict[str, Any]:
        """Check if Neo4j is reachable."""
        if not self._connected:
            return {"status": "unavailable", "reason": "driver_not_initialized"}
        try:
            with self._driver.session() as session:
                result = session.run("RETURN 1 AS n")
                record = result.single()
                if record and record["n"] == 1:
                    return {"status": "healthy", "uri": self.uri}
                return {"status": "degraded", "reason": "unexpected_response"}
        except Exception as e:
            return {"status": "unavailable", "reason": str(e)}


import json
