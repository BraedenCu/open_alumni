import os
import json
import numpy as np
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import faiss  # Facebook AI Similarity Search

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

def get_alumni_embeddings(alumnis):
    """
    Compute embeddings for each alumni's full profile description.
    Returns a NumPy array of normalized embeddings (float32).
    """
    # Build a description for each alumni.
    descriptions = [build_profile_description(s) for s in alumnis]
    embeddings = model.encode(descriptions)
    # Normalize embeddings so that cosine similarity equals inner product.
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms
    return np.array(embeddings).astype('float32')

def build_profile_description(alumni):
    """
    Construct a full profile description by concatenating key-value pairs
    that are populated. Exclude 'name' and 'email' fields.
    """
    parts = []
    for key, value in alumni.items():
        if value is not None:
            str_val = str(value).strip()
            if key.lower() not in ["name", "email"] and str_val and str_val.lower() != "null":
                parts.append(f"{key}: {str_val}")
    return " ".join(parts)

def build_faiss_index(embeddings):
    """
    Build a FAISS index (using inner product) for the given normalized embeddings.
    """
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index

def query_faiss_index(nl_query, alumni_profiles, index, top_n=5):
    """
    Given a natural language query, compute its embedding, and query the FAISS index.
    Returns the top matching alumni as a list of 2-tuples (name, similarity score).
    """
    query_embedding = model.encode([nl_query])
    # Normalize the query embedding.
    query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
    query_embedding = query_embedding.astype('float32')
    
    distances, indices = index.search(query_embedding, top_n)
    matches = []
    for idx, score in zip(indices[0], distances[0]):
        if idx < len(alumni_profiles):
            name = alumni_profiles[idx].get("name", "Unknown")
            matches.append((name, float(score)))
    return matches

def serve_profiles_with_embeddings(nl_query, alumni_profiles, top_n=5):
    """
    Use FAISS to retrieve the top matching alumni given a natural language query.
    """
    embeddings = get_alumni_embeddings(alumni_profiles)
    index = build_faiss_index(embeddings)
    return query_faiss_index(nl_query, alumni_profiles, index, top_n)

def launch_query(nl_query):
    db = GraphDB(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    alumni_profiles = db.fetch_alumni_profiles()
    db.close()
    
    if not alumni_profiles:
        return []
    
    top_matches = serve_profiles_with_embeddings(nl_query, alumni_profiles, top_n=5)
    return top_matches

if __name__ == "__main__":
    query = input("Search Alumni: ")
    matches = launch_query(query)
    print("Top Matches:")
    for match in matches:
        print(match)