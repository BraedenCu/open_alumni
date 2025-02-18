import json
import numpy as np
import networkx as nx
import math
from neo4j import GraphDatabase
from pyvis.network import Network
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
import community as community_louvain  # Louvain community detection

# ====== Neo4j Connection Configuration ======
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

# Initialize the Sentence Transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

def fetch_alumnis():
    """
    Connect to the Neo4j database and fetch all nodes with the label 'alumni'.
    Returns a list of dictionaries representing alumni properties.
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    query = "MATCH (s:alumni) RETURN s"
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
    that are populated. Only include features whose values are not None,
    not empty (or whitespace), and not the literal string 'null' (case-insensitive).
    """
    parts = []
    for key, value in alumni.items():
        if value is not None:
            str_val = str(value).strip()
            if str_val and str_val.lower() != "null":
                parts.append(f"{key}: {str_val}")
    return " ".join(parts)

def get_alumni_embeddings(alumnis):
    """
    Compute embeddings for each alumni's full profile description.
    Returns an array of embeddings.
    """
    descriptions = [build_profile_description(s) for s in alumnis]
    embeddings = model.encode(descriptions)
    return np.array(embeddings)

def cluster_alumni(embeddings, eps=0.5, min_samples=1):
    """
    Cluster alumni embeddings using DBSCAN with cosine distance.
    Returns an array of cluster labels.
    """
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine").fit(embeddings)
    return clustering.labels_

def compute_similarity(alumni1, alumni2):
    """
    Compute a dynamic similarity score between two alumnis using text embeddings.
    """
    desc1 = build_profile_description(alumni1)
    desc2 = build_profile_description(alumni2)
    
    emb1 = model.encode(desc1)
    emb2 = model.encode(desc2)
    
    cosine_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    return float(cosine_sim)

def visualize_alumnis(nodes):
    """
    Uses Pyvis to visualize alumni nodes along with edges connecting every pair of alumnis.
    Nodes are colored based on communities detected via the Louvain method. Each cluster is
    assigned a fixed center evenly distributed around a circle (like vertices of a polyhedron).
    Each node is placed near its cluster center (with a small random offset), and edges are added
    only if the normalized similarity is above a threshold. Moreover, the edge length is set inversely
    proportional to the normalized similarity score so that highly similar nodes are drawn closer together.
    """
    print("Visualizing alumni nodes...")

    net = Network(height="750px", width="100%", notebook=False)
    net.barnes_hut()

    num_nodes = len(nodes)
    if num_nodes == 0:
        print("No nodes to visualize.")
        return

    # Compute embeddings and perform clustering (for later edge filtering, we still compute similarity)
    embeddings = get_alumni_embeddings(nodes)
    dbscan_labels = cluster_alumni(embeddings, eps=0.5, min_samples=1)

    # Build a networkx graph with all nodes (without using spring layout for final positions).
    G = nx.Graph()
    for idx in range(num_nodes):
        G.add_node(idx)
    for i in range(num_nodes):
        for j in range(i+1, num_nodes):
            raw_sim = compute_similarity(nodes[i], nodes[j])
            G.add_edge(i, j, weight=raw_sim)
    
    print("Completed edge similarity computations")

    # Use Louvain community detection on the full graph to get well-defined clusters.
    partition = community_louvain.best_partition(G, weight='weight')
    # Get unique communities
    communities = list(set(partition.values()))
    communities.sort()
    num_communities = len(communities)

    # Set a radius for cluster centers; clusters will be placed evenly on a circle.
    R = 1500
    cluster_centers = {}
    for idx, community in enumerate(communities):
        theta = 2 * math.pi * idx / num_communities
        center_x = R * math.cos(theta)
        center_y = R * math.sin(theta)
        cluster_centers[community] = (center_x, center_y)
    
    # Define a color palette for communities.
    color_palette = [
        "red", "blue", "green", "orange", "purple", 
        "cyan", "magenta", "gold", "lime", "pink"
    ]

    print("Adding nodes and edges to the visualization...")

    # Add each alumni as a node with a position near its cluster center.
    for idx, node in enumerate(nodes):
        name = node.get("name")
        if not name:
            name = "unnamed"

        title = json.dumps(node, indent=2)
        community_id = partition.get(idx, 0)
        color = color_palette[community_id % len(color_palette)]
        # Get the cluster center for this node.
        center_x, center_y = cluster_centers[community_id]
        # Add a small random offset to avoid exact overlap.
        offset_x = np.random.uniform(-100, 100)
        offset_y = np.random.uniform(-100, 100)
        x = center_x + offset_x
        y = center_y + offset_y
        net.add_node(idx, label=name, title=title, group=community_id, color=color,
                     x=x, y=y, fixed={"x": False, "y": False})
    
    # Compute raw similarity scores for every pair of nodes.
    edge_data = []
    for i in range(num_nodes):
        for j in range(i+1, num_nodes):
            raw_sim = compute_similarity(nodes[i], nodes[j])
            edge_data.append((i, j, raw_sim))
    
    # Normalize similarity scores using the known raw range (approximately 0.71 to 0.86) and amplify differences.
    min_raw, max_raw = 0.71, 0.86 # Approximate range of raw similarity scores, TODO fix to a more algorithmic approach
    def normalize(sim):
        return sim ** 2

    threshold = 0.2  # Only add edges if normalized similarity is above this threshold.
    
    min_length = 100   # shortest edge when similarity is highest (norm_sim near 1)
    max_length = 10000 # longest edge when similarity is lowest (norm_sim near 0)

    print("Normalizing similarity scores and adding edges to the visualization...")
    for i, j, raw_sim in edge_data:
        norm_sim = normalize(raw_sim)
        if norm_sim >= threshold:
            # Compute edge length inversely proportional to normalized similarity.
            edge_length = max_length - (max_length - min_length) * norm_sim
            net.add_edge(i, j, value=norm_sim, label=f"{norm_sim:.2f}",
                         title=f"Similarity: {norm_sim:.2f}, Length: {edge_length:.0f}",
                         smooth={"enabled": False},
                         length=edge_length)
    
    # Set additional options to scale edge thickness visibly.
    net.set_options('''{
      "edges": {
        "scaling": {
          "min": 2,
          "max": 10,
          "label": {
            "enabled": true
          }
        },
        "color": {
          "inherit": "from"
        },
        "smooth": false
      }
    }''')
    
    net.show("./output/neo4j_alumnis.html", notebook=False)
    print("Visualization saved as 'neo4j_alumnis.html'.")

def main():
    nodes = fetch_alumnis()
    if not nodes:
        print("No alumni nodes found in the database.")
        return
    
    cap_on_visualization = 20
    print(f"Visualizing {cap_on_visualization} alumni nodes...")
    visualize_alumnis(nodes[:cap_on_visualization])

if __name__ == "__main__":
    main()