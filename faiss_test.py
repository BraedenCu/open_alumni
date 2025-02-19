import sys
import json
import numpy as np
import networkx as nx
import math
from neo4j import GraphDatabase
from pyvis.network import Network
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
import community as community_louvain  # Louvain community detection
import faiss  # For fast similarity search

# ====== Neo4j Connection Configuration ======
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

# Initialize the Sentence Transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

def fetch_alumnis():
    """
    Connect to the Neo4j database and fetch all nodes with the label 'Student'.
    Returns a list of dictionaries representing alumni properties.
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    query = "MATCH (s:Student) RETURN s"
    nodes = []
    with driver.session() as session:
        result = session.run(query)
        for record in result:
            node_props = dict(record["s"])
            nodes.append(node_props)
    driver.close()
    return nodes

def build_profile_description(alumni):
    """
    Construct a full profile description by concatenating key-value pairs
    that are populated. Only include fields (except 'name' and 'email') that
    are not None, not empty, and not the literal 'null' (case-insensitive).
    """
    parts = []
    for key, value in alumni.items():
        if value is not None:
            str_val = str(value).strip()
            if key.lower() not in ["name", "email"] and str_val and str_val.lower() != "null":
                parts.append(f"{key}: {str_val}")
    return " ".join(parts)

def get_alumni_embeddings(alumnis):
    """
    Compute embeddings for each alumni's full profile description.
    Returns a NumPy array of embeddings.
    """
    descriptions = [build_profile_description(s) for s in alumnis]
    embeddings = model.encode(descriptions)
    # Normalize embeddings so that inner product equals cosine similarity.
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms
    return np.array(embeddings).astype('float32')

def cluster_alumni(embeddings, eps=0.5, min_samples=1):
    """
    Cluster alumni embeddings using DBSCAN with cosine distance.
    Returns an array of cluster labels.
    """
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine").fit(embeddings)
    return clustering.labels_

def compute_similarity(alumni1, alumni2):
    """
    Compute a dynamic similarity score between two alumni using text embeddings.
    """
    desc1 = build_profile_description(alumni1)
    desc2 = build_profile_description(alumni2)
    emb1 = model.encode(desc1)
    emb2 = model.encode(desc2)
    cosine_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    return float(cosine_sim)

# ---------- FAISS Integration Functions ----------

def build_faiss_index(embeddings):
    """
    Build and return a FAISS index (using inner product) for the provided embeddings.
    Assumes embeddings are normalized.
    """
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index

def query_faiss_index(nl_query, alumni_profiles, index, top_n=5):
    """
    Given a natural language query, compute its embedding, and query the FAISS index.
    Returns the top_n alumni matches as a list of tuples (name, similarity score).
    """
    query_embedding = model.encode([nl_query])
    # Normalize the query embedding.
    query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
    query_embedding = query_embedding.astype('float32')
    
    distances, indices = index.search(query_embedding, top_n)
    # distances represent the inner product (cosine similarity for normalized vectors).
    matches = []
    for idx, score in zip(indices[0], distances[0]):
        # Ensure idx is valid
        if idx < len(alumni_profiles):
            name = alumni_profiles[idx].get("name", "Unknown")
            matches.append((name, float(score)))
    return matches

# ---------- Graph Visualization Functions (Existing) ----------

def visualize_alumnis(nodes):
    """
    Uses Pyvis to visualize alumni nodes with a deterministic layout.
    Nodes are colored based on communities detected via Louvain.
    Edges are added with lengths inversely proportional to the normalized similarity.
    """
    print("Visualizing alumni nodes...")

    net = Network(height="750px", width="100%", notebook=False)
    net.barnes_hut()

    num_nodes = len(nodes)
    if num_nodes == 0:
        print("No nodes to visualize.")
        return

    # Compute embeddings and clustering.
    embeddings = get_alumni_embeddings(nodes)
    dbscan_labels = cluster_alumni(embeddings, eps=0.5, min_samples=1)

    # Build a NetworkX graph to compute a deterministic layout.
    G = nx.Graph()
    for idx in range(num_nodes):
        G.add_node(idx)
    for i in range(num_nodes):
        for j in range(i+1, num_nodes):
            raw_sim = compute_similarity(nodes[i], nodes[j])
            G.add_edge(i, j, weight=raw_sim)
    
    print("Completed edge similarity computations")

    # Use Louvain community detection.
    partition = community_louvain.best_partition(G, weight='weight')
    communities = list(set(partition.values()))
    communities.sort()
    num_communities = len(communities)

    # Set cluster centers evenly on a circle.
    R = 1500
    cluster_centers = {}
    for idx, community in enumerate(communities):
        theta = 2 * math.pi * idx / num_communities
        center_x = R * math.cos(theta)
        center_y = R * math.sin(theta)
        cluster_centers[community] = (center_x, center_y)
    
    # Define a color palette.
    color_palette = [
        "red", "blue", "green", "orange", "purple", 
        "cyan", "magenta", "gold", "lime", "pink"
    ]

    print("Adding nodes and edges to the visualization...")
    # Add nodes with positions near cluster centers.
    for idx, node in enumerate(nodes):
        name = node.get("name")
        if not name:
            name = f"Student {idx}"
        title = json.dumps(node, indent=2)
        community_id = partition.get(idx, 0)
        color = color_palette[community_id % len(color_palette)]
        center_x, center_y = cluster_centers[community_id]
        offset_x = np.random.uniform(-100, 100)
        offset_y = np.random.uniform(-100, 100)
        x = center_x + offset_x
        y = center_y + offset_y
        net.add_node(idx, label=name, title=title, group=community_id, color=color,
                     x=x, y=y, fixed={"x": False, "y": False})
    
    # Compute raw similarity scores.
    edge_data = []
    for i in range(num_nodes):
        for j in range(i+1, num_nodes):
            raw_sim = compute_similarity(nodes[i], nodes[j])
            edge_data.append((i, j, raw_sim))
    
    # Normalize similarity scores and compute edge lengths.
    # Assume raw similarity is in a rough range [0.71, 0.86]
    min_raw, max_raw = 0.71, 0.86
    def normalize(sim):
        norm = (sim - min_raw) / (max_raw - min_raw) if max_raw != min_raw else sim
        return norm ** 2

    threshold = 0.2
    min_length = 100
    max_length = 10000
    print("Normalizing similarity scores and adding edges...")
    for i, j, raw_sim in edge_data:
        norm_sim = normalize(raw_sim)
        if norm_sim >= threshold:
            edge_length = max_length - (max_length - min_length) * norm_sim
            net.add_edge(i, j, value=norm_sim, label=f"{raw_sim:.2f}",
                         title=f"Similarity: {norm_sim:.2f}, Length: {edge_length:.0f}",
                         smooth={"enabled": False},
                         length=edge_length)
    
    net.set_options('''{
      "edges": {
        "scaling": {
          "min": 2,
          "max": 30,
          "label": { "enabled": true }
        },
        "color": { "inherit": "from" },
        "smooth": false
      }
    }''')
    
    output_path = "./output/output.html"  # Ensure the output folder exists.
    net.show(output_path, notebook=False)
    print(f"Visualization saved as '{output_path}'.")

def main():
    nodes = fetch_alumnis()
    if not nodes:
        print("No alumni nodes found in the database.")
        return
    
    # For demonstration, cap the number of nodes visualized.
    cap_on_visualization = 20
    print(f"Visualizing {cap_on_visualization} alumni nodes...")
    visualize_alumnis(nodes[:cap_on_visualization])
    
    # --- FAISS Integration for Querying Specific Alumni ---
    # Build FAISS index over alumni embeddings.
    embeddings = get_alumni_embeddings(nodes)
    index = build_faiss_index(embeddings)
    
    # Example: Query for a very specific prompt.
    sample_query = "find me New Yorkers who graduated from Yale and work in investment banking at Goldman Sachs"
    print(f"\nRunning FAISS query for: '{sample_query}'")
    # Query FAISS index.
    query_embedding = model.encode([sample_query])
    query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
    query_embedding = query_embedding.astype('float32')
    top_n = 5
    distances, indices = index.search(query_embedding, top_n)
    
    print("\nTop FAISS Matches:")
    for idx, score in zip(indices[0], distances[0]):
        if idx < len(nodes):
            name = nodes[idx].get("name", "Unknown")
            print(f"{name} (Similarity: {score:.3f})")

if __name__ == "__main__":
    main()