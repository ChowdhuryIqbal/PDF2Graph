from neo4j import GraphDatabase
import spacy
from collections import defaultdict

class Neo4jConnector:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.nlp = spacy.load("en_core_web_sm")

    def close(self):
        self.driver.close()

    def _find_topic_concept_relationships(self, topics, entity_contexts):
        """Find relationships between topics and concepts based on context."""
        relationships = defaultdict(list)
        
        # Create a mapping of entities to their contexts
        entity_text = {entity: ' '.join(contexts) 
                      for entity, contexts in entity_contexts.items()}
        
        for topic, relevance in topics.items():
            topic_doc = self.nlp(topic)
            
            for entity, context in entity_text.items():
                # Skip if entity or context is empty
                if not entity or not context:
                    continue
                    
                # Calculate context relevance
                context_doc = self.nlp(context)
                topic_context_similarity = topic_doc.similarity(context_doc)
                
                # If the topic appears in the entity's context or there's significant semantic similarity
                if (topic.lower() in context.lower() or 
                    entity.lower() in topic.lower() or 
                    topic_context_similarity > 0.3):  # Threshold for semantic similarity
                    
                    # Calculate relationship strength
                    strength = (topic_context_similarity + relevance) / 2
                    relationships[topic].append({
                        'entity': entity,
                        'strength': strength,
                        'context_similarity': topic_context_similarity
                    })
        
        return relationships

    def add_nodes_and_relationships(self, concepts):
        with self.driver.session() as session:
            # Add nodes for each entity in concepts
            for entity_type, entities in concepts['named_entities'].items():
                for entity in entities:
                    session.run("MERGE (n:Concept {name: $name, type: $type})", 
                                name=entity, type=entity_type)

            # Add topic nodes and relationships
            topic_concept_rels = self._find_topic_concept_relationships(
                concepts['topics'], 
                concepts['entity_contexts']
            )

            # Create topic nodes with their relevance scores
            for topic, relevance in concepts['topics'].items():
                # Create topic node
                session.run("""
                    MERGE (t:Topic {name: $name})
                    SET t.relevance = $relevance
                """, name=topic, relevance=relevance)
                
                # Create relationships with related concepts
                for rel in topic_concept_rels[topic]:
                    session.run("""
                        MATCH (t:Topic {name: $topic})
                        MATCH (c:Concept {name: $entity})
                        MERGE (t)-[r:RELATED_TO]->(c)
                        SET r.type = 'topic_association',
                            r.weight = $strength,
                            r.contextSimilarity = $context_similarity
                    """, topic=topic, 
                         entity=rel['entity'],
                         strength=rel['strength'],
                         context_similarity=rel['context_similarity'])

            # Add relationships between topics based on shared concepts
            session.run("""
                MATCH (t1:Topic)-[r1:RELATED_TO]->(c:Concept)<-[r2:RELATED_TO]-(t2:Topic)
                WHERE t1 <> t2
                WITH t1, t2, AVG(r1.weight + r2.weight) as strength, COUNT(c) as shared
                WHERE shared > 0
                MERGE (t1)-[r:RELATED_TO]->(t2)
                SET r.type = 'topic_similarity',
                    r.weight = strength,
                    r.shared_concepts = shared
            """)

            # Add general relationships
            for rel_type, rels in concepts['general_relationships'].items():
                for rel in rels:
                    if len(rel) == 3:  # if semantic or weighted relationship
                        session.run("""
                            MATCH (a:Concept {name: $entity1}), (b:Concept {name: $entity2})
                            MERGE (a)-[r:RELATED {type: $rel_type, weight: $weight}]->(b)
                        """, entity1=rel[0], entity2=rel[1], rel_type=rel_type, weight=rel[2])
                    else:
                        session.run("""
                            MATCH (a:Concept {name: $entity1}), (b:Concept {name: $entity2})
                            MERGE (a)-[r:RELATED {type: $rel_type}]->(b)
                        """, entity1=rel[0], entity2=rel[1], rel_type=rel_type)

            # Add specific relationships
            for rel_type, rels in concepts['specific_relationships'].items():
                if rel_type == 'subject_object':
                    for rel in rels:
                        session.run("""
                            MATCH (a:Concept {name: $subject}), (b:Concept {name: $object})
                            MERGE (a)-[r:ACTION {type: 'subject_object', verb: $verb}]->(b)
                        """, subject=rel['subject'], verb=rel['verb'], object=rel['object'])
                elif rel_type == 'noun_chunks':
                    for rel in rels:
                        session.run("""
                            MATCH (a:Concept {name: $entity1}), (b:Concept {name: $entity2})
                            MERGE (a)-[r:RELATED {type: 'noun_chunk', relation: $relationship}]->(b)
                        """, entity1=rel['entity1'], relationship=rel['relationship'], entity2=rel['entity2'])

            # Column relationships from tables
            for cols, pairs in concepts['column_relationships'].items():
                col1, col2 = cols.split("_")
                for pair in pairs:
                    session.run("""
                        MERGE (a:Concept {name: $entity1, type: $col1})
                        MERGE (b:Concept {name: $entity2, type: $col2})
                        MERGE (a)-[r:RELATED {type: 'column_relationship', relation: $relation}]->(b)
                    """, entity1=pair[0], entity2=pair[1], col1=col1, col2=col2, relation=f"{col1} <-> {col2}")
