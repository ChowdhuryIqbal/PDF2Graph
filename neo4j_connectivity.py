from neo4j import GraphDatabase
import os
from neo4j.exceptions import ServiceUnavailable, AuthError
from dotenv import load_dotenv

load_dotenv()


# Fetch environment variables
uri = os.environ.get("NEO4J_URI")
user = os.environ.get("NEO4J_USERNAME")
password = os.environ.get("NEO4J_PASSWORD")

# Validate environment variables
if not uri or not user or not password:
    raise ValueError("Missing one or more required environment variables: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD")

# Initialize driver
driver = GraphDatabase.driver(uri, auth=(user, password))

try:
    with driver.session() as session:
        result = session.run("RETURN 'Connection Successful' AS message")
        for record in result:
            print(record["message"])
except AuthError as e:
    print(f"Authentication Error: {e}")
except ServiceUnavailable as e:
    print(f"Service Unavailable: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    driver.close()
