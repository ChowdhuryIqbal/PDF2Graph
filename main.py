'''
 python -m venv ./venv
 .\concept\Scripts\activate
 deactivate

admin password: YourPasswordGoesHere

neo4jBrowserURL:
http://node-qelxxxxxxn2bo.australiaeast.cloudapp.azure.com:7474/

username: 
neo4j

-- local windows install
down load .zip of the community edition
go the bin folder of the installation (it runs on JVM, install java for windows)

neo4j windows-service install

start the service by running: neo4j console

enter the urI: with same username and password: neo4j
and setup a new password

>> Delete nodes in the graph db: 
MATCH (n)
DETACH DELETE n;
'''

import argparse
import logging
from pathlib import Path
from pdf_concept_extractor import extract_concepts_from_pdf
from neo4j_integration import Neo4jConnector
import json
import sys

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    return logging.getLogger(__name__)

def process_pdfs_in_folder(folder_path, neo4j_uri, neo4j_user, neo4j_password):
    """
    Process all PDFs in a folder and update the Neo4j knowledge graph.

    Args:
        folder_path: Path to the folder containing PDF files.
        neo4j_uri: Neo4j database URI.
        neo4j_user: Neo4j username.
        neo4j_password: Neo4j password.
    """
    logger = setup_logging()
    folder = Path(folder_path)
    
    if not folder.exists() or not folder.is_dir():
        logger.error(f"Invalid folder path: {folder_path}")
        sys.exit(1)
    
    pdf_files = list(folder.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in the folder: {folder_path}")
        sys.exit(1)
    
    # Connect to Neo4j
    neo4j_conn = Neo4jConnector(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
    
    try:
        for pdf_file in pdf_files:
            logger.info(f"Processing PDF: {pdf_file.name}")
            
            # Extract concepts from the PDF
            concepts = extract_concepts_from_pdf(pdf_file)
            
            if not concepts:
                logger.warning(f"Failed to extract concepts from: {pdf_file.name}")
                continue
            
            # Upload to Neo4j
            try:
                neo4j_conn.add_nodes_and_relationships(concepts)
                logger.info(f"Data successfully uploaded for: {pdf_file.name}")
            except Exception as e:
                logger.error(f"Failed to upload data for {pdf_file.name}: {e}", exc_info=True)
    finally:
        neo4j_conn.close()

def main(folder=None, neo4j_uri=None, neo4j_user=None, neo4j_password=None):
    """
    Main function to process PDFs and update the Neo4j knowledge graph.

    Args:
        folder: Path to folder containing PDFs.
        neo4j_uri: Neo4j database URI.
        neo4j_user: Neo4j username.
        neo4j_password: Neo4j password.
    """
    logger = setup_logging()
    
    if not folder or not neo4j_uri or not neo4j_user or not neo4j_password:
        logger.error("Missing required arguments.")
        sys.exit(1)

    try:
        process_pdfs_in_folder(folder, neo4j_uri, neo4j_user, neo4j_password)
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process PDFs in a folder and update the Neo4j knowledge graph."
    )
    parser.add_argument("--folder", type=str, required=True, help="Path to the folder containing PDF files.")
    parser.add_argument("--neo4j_uri", type=str, default="bolt://localhost:7687", help="URI of the Neo4j database.")
    parser.add_argument("--neo4j_user", type=str, default="neo4j", help="Neo4j username.")
    parser.add_argument("--neo4j_password", type=str, required=True, help="Neo4j password.")
    
    args = parser.parse_args()

    main(
        folder=args.folder,
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password
    )


