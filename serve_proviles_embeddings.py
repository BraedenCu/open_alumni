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
        # Updated query: use IS NOT NULL instead of exists(...)
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
    compute the similarity between the query embedding and each alumni's
    description embedding, and return the names of the top matching alumni.
    """
    # Compute embedding for the user's query.
    query_embedding = model.encode(nl_query)
    
    # Compute similarity scores for each alumni.
    matches = []
    for profile in alumni_profiles:
        description = profile.get("description", "")
        if not description:
            continue
        emb = model.encode(description)
        sim = cosine_similarity(query_embedding, emb)
        matches.append((profile.get("name", "Unknown"), sim))
    
    # Sort matches by similarity descending.
    matches = sorted(matches, key=lambda x: x[1], reverse=True)
    return matches[:top_n]

def main():
    nl_query = input("Enter your natural language query (e.g., 'find me investment bankers in New York who work at Goldman Sachs'): ")
    
    db = GraphDB(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    alumni_profiles = db.fetch_alumni_profiles()
    db.close()
    
    if not alumni_profiles:
        print("No alumni profiles with descriptions found in the database.")
        return
    
    top_matches = serve_profiles_with_embeddings(nl_query, alumni_profiles, top_n=5)
    
    print("\nTop matching alumni:")
    for name, sim in top_matches:
        print(f"{name} (Similarity: {sim:.3f})")

if __name__ == "__main__":
    main()