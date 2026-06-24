"""Sphere integration for the podcast application.

Syncs podcast data to the Neo4j knowledge graph for cross-episode research and topic tracking.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

from maf.integration import Neo4jStateStore


class PodcastSphereSync:
    """Syncs podcast episodes, topics, and research to the sphere knowledge graph."""

    def __init__(self) -> None:
        self.store = Neo4jStateStore(
            uri=os.environ.get("NEO4J_URI", "bolt://neo4j:7687"),
            auth=(
                os.environ.get("NEO4J_USER", "neo4j"),
                os.environ.get("NEO4J_PASSWORD", "password"),
            ),
        )

    def sync_episode(
        self,
        episode_id: str,
        podcast_id: str,
        title: str,
        vision: str,
        research_output: Optional[Dict[str, Any]] = None,
        script_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Sync an episode and its research to the sphere graph."""
        try:
            # Create episode node
            self._run_query(
                """
                MERGE (e:Episode {id: $episode_id})
                SET e.title = $title, e.vision = $vision, e.updated_at = datetime()
                """,
                episode_id=episode_id, title=title, vision=vision,
            )

            # Create podcast node and relationship
            self._run_query(
                """
                MERGE (p:Podcast {id: $podcast_id})
                MERGE (e:Episode {id: $episode_id})
                MERGE (p)-[:HAS_EPISODE]->(e)
                """,
                podcast_id=podcast_id, episode_id=episode_id,
            )

            # Extract and create topic nodes from vision
            topics = self._extract_topics(vision)
            for topic in topics:
                self._run_query(
                    """
                    MERGE (t:Topic {name: $topic})
                    MERGE (e:Episode {id: $episode_id})
                    MERGE (e)-[:COVERS]->(t)
                    """,
                    topic=topic, episode_id=episode_id,
                )

            # Store research findings
            if research_output:
                structured = research_output.get("structured", {})
                for fact in structured.get("key_facts", []):
                    self._run_query(
                        """
                        MERGE (f:Fact {content: $fact})
                        MERGE (e:Episode {id: $episode_id})
                        MERGE (e)-[:CONTAINS]->(f)
                        """,
                        fact=fact[:500], episode_id=episode_id,
                    )

                for argument in structured.get("arguments", []):
                    self._run_query(
                        """
                        MERGE (a:Argument {content: $argument})
                        MERGE (e:Episode {id: $episode_id})
                        MERGE (e)-[:PRESENTS]->(a)
                        """,
                        argument=argument[:500], episode_id=episode_id,
                    )

            return {"success": True, "topics_synced": len(topics), "episode_id": episode_id}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def query_related_episodes(self, topic: str) -> List[Dict[str, Any]]:
        """Find episodes related to a given topic."""
        try:
            result = self._run_query(
                """
                MATCH (t:Topic)<-[:COVERS]-(e:Episode)-[:HAS_EPISODE]-(p:Podcast)
                WHERE t.name CONTAINS $topic OR e.vision CONTAINS $topic
                RETURN e.id AS episode_id, e.title AS title, e.vision AS vision,
                       p.id AS podcast_id, collect(t.name) AS topics
                LIMIT 10
                """,
                topic=topic,
            )
            return [dict(record) for record in result]
        except Exception as e:
            return []

    def get_episode_knowledge(self, episode_id: str) -> Dict[str, Any]:
        """Get all knowledge connected to an episode."""
        try:
            records = self._run_query(
                """
                MATCH (e:Episode {id: $episode_id})
                OPTIONAL MATCH (e)-[:COVERS]->(t:Topic)
                OPTIONAL MATCH (e)-[:CONTAINS]->(f:Fact)
                OPTIONAL MATCH (e)-[:PRESENTS]->(a:Argument)
                RETURN e.title AS title, e.vision AS vision,
                       collect(DISTINCT t.name) AS topics,
                       collect(DISTINCT f.content) AS facts,
                       collect(DISTINCT a.content) AS arguments
                """,
                episode_id=episode_id,
            )
            record = records[0] if records else None
            if record:
                return dict(record)
            return {}
        except Exception as e:
            return {"error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Check sphere connectivity."""
        return self.store.health_check()

    def _run_query(self, query: str, **params) -> List[Any]:
        """Run a Cypher query against Neo4j and consume records inside the session."""
        if not self.store._connected:
            raise RuntimeError("Neo4j not connected")
        with self.store._driver.session(database=self.store.database) as session:
            return list(session.run(query, **params))

    def _extract_topics(self, vision: str) -> List[str]:
        """Extract key topics from a vision string, preserving multi-word phrases and short acronyms."""
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "about",
            "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "must", "shall", "can", "need", "dare",
            "ought", "used", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they",
            "me", "him", "her", "us", "them", "my", "your", "his", "its", "our", "their", "what", "which",
            "who", "whom", "whose", "where", "when", "why", "how", "all", "each", "every", "both", "few",
            "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than",
            "too", "very", "just", "now", "then", "here", "there", "up", "down", "out", "off", "over", "under",
            "again", "further", "once", "during", "before", "after", "above", "below", "between", "through",
            "into", "from", "by", "as", "if", "because", "until", "while", "although", "though", "unless",
            "since", "whether", "however", "therefore", "moreover", "nevertheless", "nonetheless",
            "meanwhile", "otherwise", "instead", "likewise", "similarly", "consequently", "furthermore",
            "hence", "thus", "accordingly", "subsequently", "notably", "particularly", "especially",
            "specifically", "generally", "usually", "often", "sometimes", "rarely", "never", "always",
            "frequently", "occasionally", "regularly", "constantly", "repeatedly", "daily", "weekly",
            "monthly", "yearly", "recently", "currently", "previously", "formerly", "originally",
            "initially", "finally", "eventually", "ultimately", "instantly", "immediately", "suddenly",
            "gradually", "slowly", "quickly", "rapidly", "briefly", "shortly", "long", "much", "many",
            "little", "less", "least", "fewer", "fewest", "lot", "lots", "plenty", "several", "various",
            "numerous", "countless", "abundant", "scarce", "sparse", "dense", "thick", "thin", "wide",
            "narrow", "deep", "shallow", "high", "low", "tall", "short", "big", "small", "large", "huge",
            "tiny", "massive", "immense", "vast", "major", "minor", "main", "primary", "secondary",
            "tertiary", "initial", "final", "first", "last", "second", "third", "next", "previous",
            "following", "preceding", "subsequent", "prior", "earlier", "later", "new", "old", "young",
            "ancient", "modern", "contemporary", "current", "past", "future", "present", "recent",
            "distant", "near", "close", "far", "away", "apart", "together", "alone", "single", "double",
            "triple", "multiple", "various", "different", "similar", "same", "opposite", "reverse",
            "inverse", "contrary", "despite", "regardless", "notwithstanding", "although", "though",
            "whereas", "while", "whilst", "whereby", "wherein", "whereupon", "whereafter", "wherever",
            "whenever", "whatever", "whoever", "whichever", "however", "whatever", "whatsoever",
            "whosoever", "whomsoever", "whichsoever", "whensoever", "wheresoever", "howsoever",
            "whysoever", "wherefore", "therefore", "whereat", "thereat", "wherein", "therein",
            "whereon", "thereon", "whereof", "thereof", "whereby", "thereby", "whereto", "thereto",
            "whereunto", "thereunto", "wherewith", "therewith", "wherefrom", "therefrom", "wherewithal",
            "therewithal", "hereabout", "thereabout", "whereabout", "hereafter", "thereafter",
            "wherebefore", "therebefore", "herein", "therein", "wherein", "hereinto", "thereinto",
            "whereinto", "hereof", "thereof", "whereof", "hereon", "thereon", "whereon", "hereto",
            "thereto", "whereto", "hereunder", "thereunder", "whereunder", "hereupon", "thereupon",
            "whereupon", "herewith", "therewith", "wherewith", "herewithal", "therewithal",
            "wherewithal",
        }

        # Extract multi-word phrases in quotes
        phrases = re.findall(r'"([^"]{3,50})"', vision)
        candidates = phrases[:]

        # Extract capitalized multi-word phrases (proper nouns)
        words = vision.split()
        i = 0
        while i < len(words):
            w = words[i].strip(",.!?;:()[]")
            if w and w[0].isupper() and w.lower() not in stopwords and len(w) > 2:
                phrase = [w]
                j = i + 1
                while j < len(words):
                    next_w = words[j].strip(",.!?;:()[]")
                    if next_w and (next_w[0].isupper() or next_w.lower() in {"of", "the", "and"}):
                        phrase.append(next_w)
                        j += 1
                    else:
                        break
                candidates.append(" ".join(phrase))
                i = j
            else:
                i += 1

        # Extract single meaningful words (length > 2, not > 3)
        for w in words:
            w_clean = w.strip(",.!?;:()[]").lower()
            if w_clean and w_clean not in stopwords and len(w_clean) > 2:
                if w_clean not in [c.lower() for c in candidates]:
                    candidates.append(w_clean)

        # Deduplicate preserving case of first occurrence
        seen = set()
        unique = []
        for c in candidates:
            key = c.lower()
            if key not in seen:
                seen.add(key)
                unique.append(c)

        return unique[:10]
