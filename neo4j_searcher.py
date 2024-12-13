from neo4j import GraphDatabase
from typing import Dict, List, Optional
import logging

class Neo4jSearcher:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.logger = logging.getLogger(__name__)

    def close(self):
        self.driver.close()

    def search_topics(self, search_term: str, min_relevance: float = 0.3) -> List[Dict]:
        """
        Search for topics that match the search term using native Neo4j string operations.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (t:Topic)
                WHERE toLower(t.name) CONTAINS toLower($search)
                   OR any(word IN split(toLower($search), ' ')
                         WHERE toLower(t.name) CONTAINS word)
                WITH t, 
                     CASE 
                         WHEN toLower(t.name) = toLower($search) THEN 1.0
                         WHEN toLower(t.name) CONTAINS toLower($search) THEN 0.8
                         ELSE 0.5 
                     END as matchScore
                WHERE matchScore >= $min_relevance
                OPTIONAL MATCH (t)-[r:RELATED_TO]->(c:Concept)
                WITH t, matchScore, COUNT(DISTINCT c) as conceptCount
                RETURN {
                    topic: t.name,
                    relevance: COALESCE(t.relevance, 0.0),
                    matchScore: matchScore,
                    relatedConceptsCount: conceptCount
                } as result
                ORDER BY matchScore DESC, t.relevance DESC
            """, search=search_term, min_relevance=min_relevance)
            
            return [dict(record["result"]) for record in result]

    def get_topic_concepts(self, topic_name: str, 
                          min_weight: float = 0.3, 
                          limit: int = 20) -> Dict:
        """
        Get all concepts related to a specific topic with their relationships.
        """
        with self.driver.session() as session:
            # First verify topic exists
            topic_check = session.run("""
                MATCH (t:Topic {name: $topic})
                RETURN t.relevance as relevance
            """, topic=topic_name)
            
            topic_data = topic_check.single()
            if not topic_data:
                return {"error": f"Topic '{topic_name}' not found"}

            # Get related concepts with their relationships
            result = session.run("""
                MATCH (t:Topic {name: $topic})-[r:RELATED_TO]->(c:Concept)
                WHERE r.weight >= $min_weight
                WITH c, r
                OPTIONAL MATCH (c)-[rel:RELATED|ACTION]-(other:Concept)
                WITH c, r, 
                     COLLECT(DISTINCT {
                         otherConcept: other.name,
                         relationType: TYPE(rel),
                         relationWeight: COALESCE(rel.weight, 1.0)
                     }) as connections
                RETURN {
                    concept: c.name,
                    type: c.type,
                    topicRelationWeight: r.weight,
                    contextSimilarity: r.contextSimilarity,
                    connections: connections
                } as result
                ORDER BY r.weight DESC
                LIMIT $limit
            """, topic=topic_name, min_weight=min_weight, limit=limit)

            concepts = [dict(record["result"]) for record in result]
            
            return {
                "topic": topic_name,
                "topicRelevance": topic_data["relevance"],
                "relatedConcepts": concepts
            }

    def search_concept_network(self, topic_name: str, concept_name: str) -> Dict:
        """
        Get detailed information about a specific concept within a topic's context.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (t:Topic {name: $topic})-[r1:RELATED_TO]->(c:Concept {name: $concept})
                OPTIONAL MATCH (c)-[r2]-(connected:Concept)
                WITH c, r1, 
                     COLLECT(DISTINCT {
                         concept: connected.name,
                         type: connected.type,
                         relationshipType: TYPE(r2),
                         properties: properties(r2)
                     }) as connections
                RETURN {
                    concept: c.name,
                    type: c.type,
                    topicRelation: {
                        weight: r1.weight,
                        contextSimilarity: r1.contextSimilarity
                    },
                    connections: connections
                } as result
            """, topic=topic_name, concept=concept_name)
            
            record = result.single()
            return dict(record["result"]) if record else None

    def get_topic_statistics(self) -> Dict:
        """
        Get general statistics about topics in the knowledge graph.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (t:Topic)
                OPTIONAL MATCH (t)-[r:RELATED_TO]->(c:Concept)
                WITH t, COUNT(DISTINCT c) as conceptCount
                RETURN {
                    totalTopics: COUNT(t),
                    averageConceptsPerTopic: AVG(conceptCount),
                    topTopics: COLLECT({
                        topic: t.name,
                        conceptCount: conceptCount,
                        relevance: t.relevance
                    })[..5]
                } as stats
            """)
            
            return dict(result.single()["stats"])
