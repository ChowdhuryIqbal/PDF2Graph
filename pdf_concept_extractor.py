import PyPDF2
import spacy
import numpy as np
import pandas as pd
from collections import Counter, defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from keybert import KeyBERT
import pdfplumber
import networkx as nx
from itertools import combinations

def extract_concepts_from_pdf(pdf_path):
    """
    Extract key concepts from a PDF document, including tables, and analyze relationships.
    No Java dependency required.
    """
    # Load NLP models
    nlp = spacy.load("en_core_web_sm")
    kw_model = KeyBERT()
    
    def extract_text_and_tables(pdf_path):
        """Extract both regular text and tabular data from PDF using pdfplumber"""
        text = ""
        tables = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Extract text
                text += page.extract_text() or ""
                
                # Extract tables
                tables_on_page = page.extract_tables()
                if tables_on_page:
                    for table in tables_on_page:
                        # Convert to pandas DataFrame
                        if table:
                            cleaned_table = [[str(cell).strip() if cell is not None else "" 
                                              for cell in row] for row in table]
                            header = cleaned_table[0]
                            data = cleaned_table[1:]
                            df = pd.DataFrame(data, columns=header)
                            tables.append(df)
        
        return text, tables
    
    def process_table_content(tables):
        """Extract concepts from tabular data"""
        table_concepts = []
        column_relationships = defaultdict(list)
        
        for table in tables:
            table_text = table.to_string()
            table_concepts.extend(extract_keywords(table_text, kw_model))
            
            for col1, col2 in combinations(table.columns, 2):
                try:
                    pairs = zip(table[col1].dropna(), table[col2].dropna())
                    for val1, val2 in pairs:
                        if isinstance(val1, str) and isinstance(val2, str):
                            column_relationships[f"{col1}_{col2}"].append((val1, val2))
                except:
                    continue
        
        return table_concepts, column_relationships
    
    def extract_entities(text, nlp):
        """Extract named entities with enhanced context"""
        doc = nlp(text)
        entities = {}
        entity_contexts = defaultdict(list)
        
        for ent in doc.ents:
            if ent.label_ not in entities:
                entities[ent.label_] = []
            entities[ent.label_].append(ent.text)
            sent = ent.sent
            entity_contexts[ent.text].append(sent.text)
        
        for label in entities:
            entities[label] = dict(Counter(entities[label]))
            
        return entities, entity_contexts
    
    def analyze_relationships(doc, entities, threshold=0.5):
        """Analyze relationships between concepts using various methods"""
        relationships = defaultdict(list)
        G = nx.Graph()
        
        for sent in doc.sents:
            sent_entities = [ent.text for ent in sent.ents]
            for ent1, ent2 in combinations(sent_entities, 2):
                if ent1 != ent2:
                    G.add_edge(ent1, ent2, type='co-occurrence')
                    relationships['co-occurrence'].append((ent1, ent2))
        
        for ent1, ent2 in combinations(entities.keys(), 2):
            similarity = nlp(ent1).similarity(nlp(ent2))
            if similarity > threshold:
                G.add_edge(ent1, ent2, type='semantic', weight=similarity)
                relationships['semantic'].append((ent1, ent2, similarity))
        
        for token in doc:
            if token.dep_ in ['nsubj', 'dobj', 'pobj']:
                head = token.head.text
                dependent = token.text
                relationships['syntactic'].append((head, dependent, token.dep_))
        
        return relationships, G
    
    def extract_keywords(text, kw_model):
        keywords = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words='english',
            use_maxsum=True,
            nr_candidates=20,
            top_n=10
        )
        return dict(keywords)
    
    def extract_topics(text):
        vectorizer = TfidfVectorizer(
            max_features=20,
            stop_words='english',
            ngram_range=(1, 2)
        )
        vectors = vectorizer.fit_transform([text])
        feature_names = vectorizer.get_feature_names_out()
        scores = vectors.toarray()[0]
        
        top_indices = scores.argsort()[-10:][::-1]
        return {feature_names[i]: float(scores[i]) for i in top_indices}

    # New function for extracting concept relationships
    def extract_concept_relationships(text, nlp):
        """Extract explicit relationships between concepts using dependency parsing and semantic patterns."""
        doc = nlp(text)
        relationships = defaultdict(list)
        
        def get_subject_object_pairs(sent):
            pairs = []
            for token in sent:
                if token.pos_ == "VERB":
                    subj = None
                    obj = None
                    for child in token.children:
                        if child.dep_ in ["nsubj", "nsubjpass"]:
                            subj = child
                        elif child.dep_ in ["dobj", "pobj"]:
                            obj = child
                    if subj and obj:
                        pairs.append({
                            'subject': subj.text,
                            'verb': token.text,
                            'object': obj.text,
                            'sentence': sent.text
                        })
            return pairs

        def get_noun_chunk_relationships(sent):
            chunks = list(sent.noun_chunks)
            rels = []
            for i, chunk1 in enumerate(chunks):
                for chunk2 in chunks[i+1:]:
                    if any(token.pos_ in ["VERB", "ADP"] for token in doc[chunk1.end:chunk2.start]):
                        connecting_words = ' '.join(token.text for token in doc[chunk1.end:chunk2.start]
                                                    if token.pos_ in ["VERB", "ADP"])
                        rels.append({
                            'entity1': chunk1.text,
                            'relationship': connecting_words,
                            'entity2': chunk2.text,
                            'sentence': sent.text
                        })
            return rels

        for sent in doc.sents:
            relationships['subject_object'].extend(get_subject_object_pairs(sent))
            relationships['noun_chunks'].extend(get_noun_chunk_relationships(sent))
        
        return relationships

    try:
        text, tables = extract_text_and_tables(pdf_path)
        doc = nlp(text)
        
        table_concepts, column_relationships = process_table_content(tables)
        
        entities, entity_contexts = extract_entities(text, nlp)
        
        general_relationships, concept_graph = analyze_relationships(doc, entities)
        specific_relationships = extract_concept_relationships(text, nlp)
        
        concepts = {
            'named_entities': entities,
            'entity_contexts': entity_contexts,
            'keywords': extract_keywords(text, kw_model),
            'topics': extract_topics(text),
            'table_concepts': table_concepts,
            'column_relationships': column_relationships,
            'general_relationships': general_relationships,
            'specific_relationships': specific_relationships,
            'concept_graph': concept_graph
        }
        
        return concepts
        
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return None

def format_concepts(concepts):
    """Format extracted concepts and relationships for readable output."""
    output = "Extracted Concepts and Relationships:\n\n"
    output += "Named Entities:\n"
    for entity_type, entities in concepts['named_entities'].items():
        output += f"\n{entity_type}:\n"
        sorted_entities = sorted(entities.items(), key=lambda x: x[1], reverse=True)
        for entity, count in sorted_entities:
            output += f"  - {entity} ({count} occurrences)\n"
            contexts = concepts['entity_contexts'].get(entity, [])
            if contexts:
                output += f"    Context: {contexts[0][:200]}...\n"
    
    output += "\nKey Phrases (with relevance scores):\n"
    for phrase, score in concepts['keywords'].items():
        output += f"  - {phrase}: {score:.3f}\n"
    
    output += "\nTable-Specific Concepts:\n"
    for concept in concepts['table_concepts']:
        output += f"  - {concept}\n"
    
    output += "\nGeneral Relationships:\n"
    for rel_type, rels in concepts['general_relationships'].items():
        output += f"\n{rel_type.title()} Relationships:\n"
        for rel in rels[:5]:  # Show top 5 relationships of each type
            if len(rel) == 3:
                output += f"  - {rel[0]} -> {rel[1]} ({rel[2]})\n"
            else:
                output += f"  - {rel[0]} <-> {rel[1]}\n"
    
    output += "\nColumn Relationships in Tables:\n"
    for cols, pairs in concepts['column_relationships'].items():
        output += f"  - {cols.replace('_', ' <-> ')}:\n"
        for pair in pairs[:3]:  # Show top 3 examples
            output += f"    {pair[0]} <-> {pair[1]}\n"
    
    output += format_relationships(concepts['specific_relationships'])
    
    return output

def format_relationships(relationships):
    """Format the extracted relationships for readable output"""
    output = "\nExtracted Relationships:\n"
    
    if relationships.get('subject_object'):
        output += "\nSubject-Verb-Object Relationships:\n"
        for rel in relationships['subject_object']:
            output += f"• {rel['subject']} -> {rel['verb']} -> {rel['object']}\n"
            output += f"  Context: {rel['sentence']}\n"
    
    if relationships.get('noun_chunks'):
        output += "\nNoun Phrase Relationships:\n"
        for rel in relationships['noun_chunks']:
            output += f"• {rel['entity1']} -> {rel['relationship']} -> {rel['entity2']}\n"
            output += f"  Context: {rel['sentence']}\n"
    
    return output

def visualize_concept_network(concept_graph):
    """Create a visualization of the concept relationship network."""
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(concept_graph)
    nx.draw(concept_graph, pos, with_labels=True, node_color='lightblue', 
            node_size=1500, font_size=8, font_weight='bold')
    plt.title("Concept Relationship Network")
    plt.show()

