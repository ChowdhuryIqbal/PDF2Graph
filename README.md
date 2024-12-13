# PDF2Graph: Extracting and Visualizing Knowledge Graphs from PDFs

**PDF2Graph** is a tool that extracts concepts and relationships from PDF documents and visualizes them using Neo4j knowledge graphs. The project uses NLP techniques to identify named entities, key phrases, topics, and relationships, which are then uploaded to a Neo4j database for interactive exploration.

---

## Table of Contents

1. [Features](#features)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Neo4j Configuration](#neo4j-configuration)
6. [Commands](#commands)
7. [Sample Workflow](#sample-workflow)

---

## Features

- Extracts **concepts**, **key phrases**, and **topics** from PDFs.
- Analyzes **relationships** between concepts using NLP techniques.
- Stores extracted data in a **Neo4j knowledge graph**.
- Provides tools for **querying and visualizing** knowledge graphs.
- Supports **table extraction** and **relationship analysis**.

---

## Requirements

- **Python 3.8+**
- **Neo4j Community Edition**
- **Java** (for Neo4j)
- Dependencies:
  - `PyPDF2`
  - `spacy`
  - `pdfplumber`
  - `keybert`
  - `scikit-learn`
  - `networkx`
  - `neo4j`
  - `dotenv`

Install dependencies via pip:

```bash
pip install -r requirements.txt
```

## Installation
1. Create a Virtual Environment:
```bash
python -m venv venv
```
2. Activate the Virtual Environment:

- Windows:
```bash
.\venv\Scripts\activate
```

- Linux/Mac:
```bash
source venv/bin/activate
```

3. Install Dependencies:
```bash
pip install -r requirements.txt
```

4. Neo4j Installation (Local):

Download the Neo4j Community Edition from the official website. For Azure Neo4J can be found inside the Azure Marketplace to be hosted as a service (running on a virtual machine incurring costs)

```bash
neo4j windows-service install
neo4j console
```
## Usage
1. Command-Line Execution
```bash
python main.py --folder <path_to_pdf_folder> --neo4j_uri <neo4j_uri> --neo4j_user <neo4j_username> --neo4j_password <neo4j_password>
```
- Example:
```bash
python main.py --folder "./pdfs" --neo4j_uri "bolt://localhost:7687" --neo4j_user "neo4j" --neo4j_password "YourPassword"
```

## Neo4j Configuration
1. Start Neo4j Service:
```bash
neo4j console
```

2. Access Neo4j Browser:

Open the following URL in your browser:
```bash
http://localhost:7474/
```

3. Login Credentials:

- Username: neo4j
- Password: Set during initial setup

4. Delete Existing Nodes (if needed):

```bash
MATCH (n) DETACH DELETE n;
```

## Commands

- Activate Virtual Environment:
```bash
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/Mac
```
- Deactivate Virtual Environment:
```bash
deactivate
```

## Sample Workflow
1. Extract Concepts from PDFs and Upload to Neo4j:
```bash
python main.py --folder "./pdfs" --neo4j_uri "bolt://localhost:7687" --neo4j_user "neo4j" --neo4j_password "YourPassword"
```

2. Verify Neo4j Connection:
```bash
python neo4j_connectivity.py
```

3. Query Neo4j Graph:

- Search topics:
```python
from neo4j_searcher import Neo4jSearcher
searcher = Neo4jSearcher("bolt://localhost:7687", "neo4j", "YourPassword")
print(searcher.search_topics("sample topic"))
searcher.close()
```
