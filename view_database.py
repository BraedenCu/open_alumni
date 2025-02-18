import json
from neo4j import GraphDatabase

# ====== Neo4j Connection Configuration ======
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

def fetch_all_alumnis():
    """
    Connect to the Neo4j database and fetch all nodes with the label 'alumni'.
    Returns a list of dictionaries representing alumni properties.
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    query = "MATCH (s:Student) RETURN s"
    alumnis = []
    with driver.session() as session:
        result = session.run(query)
        for record in result:
            alumni = dict(record["s"])
            alumnis.append(alumni)
    driver.close()
    return alumnis

def write_alumnis_to_file(alumnis, filename="./output/alumnis_output.txt"):
    """
    Write all alumni information to a text file.
    Each alumni's information is pretty-printed in JSON format.
    """
    with open(filename, "w", encoding="utf-8") as f:
        for alumni in alumnis:
            f.write(json.dumps(alumni, indent=4))
            f.write("\n\n")

def main():
    alumnis = fetch_all_alumnis()
    if not alumnis:
        print("No alumni nodes found in the database.")
        return
    write_alumnis_to_file(alumnis)
    print(f"Successfully wrote {len(alumnis)} alumni records to './output/alumnis_output.txt'.")

if __name__ == "__main__":
    main()