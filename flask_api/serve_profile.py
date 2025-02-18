import os
import json
import numpy as np
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

# ====== Neo4j Connection Configuration ======
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

# Initialize the Sentence Transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

class GraphDB:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def fetch_alumni_profiles(self):
        """
        Fetch all alumni nodes (with at least 'name' and 'description' properties)
        from the database.
        Returns a list of dictionaries.
        """
        query = "MATCH (s:Student) WHERE s.description IS NOT NULL RETURN s"
        profiles = []
        with self.driver.session() as session:
            result = session.run(query)
            for record in result:
                node = dict(record["s"])
                if "name" in node and "description" in node:
                    profiles.append(node)
        return profiles

def cosine_similarity(vec1, vec2):
    """Compute the cosine similarity between two vectors."""
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def serve_profiles_with_embeddings(nl_query, alumni_profiles, top_n=5):
    """
    Given a natural language query and a list of alumni profiles,
    compute the cosine similarity between the query embedding and each alumni's
    description embedding. Return the top matching alumni as a list of 2-tuples:
    (name, similarity as float).
    """
    # Compute the embedding for the query.
    query_embedding = model.encode(nl_query)
    matches = []
    for profile in alumni_profiles:
        description = profile.get("description", "")
        if not description:
            continue
        emb = model.encode(description)
        sim = float(cosine_similarity(query_embedding, emb))
        matches.append((profile.get("name", "Unknown"), sim))
    
    # Sort matches by similarity descending.
    matches = sorted(matches, key=lambda x: x[1], reverse=True)
    return matches[:top_n]

def launch_query(nl_query):
    db = GraphDB(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    alumni_profiles = db.fetch_alumni_profiles()
    db.close()
    
    if not alumni_profiles:
        return []
    
    top_matches = serve_profiles_with_embeddings(nl_query, alumni_profiles, top_n=5)
    return top_matches

if __name__ == "__main__":
    # For testing from the command line
    query = input("Enter your query: ")
    matches = launch_query(query)
    print("Top Matches:")
    for match in matches:
        print(match)