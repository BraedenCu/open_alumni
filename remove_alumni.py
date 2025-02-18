from neo4j import GraphDatabase

# ====== Neo4j Connection Configuration ======
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

class GraphDB:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def remove_alumni(self, alumni_name):
        """
        Remove alumni nodes matching the provided alumni name.
        Returns the number of nodes removed.
        """
        with self.driver.session() as session:
            result = session.execute_write(self._remove_alumni_tx, alumni_name)
            return result
    
    @staticmethod
    def _remove_alumni_tx(tx, alumni_name):
        # The query uses DETACH DELETE to remove the node and all its relationships.
        query = """
        MATCH (s:alumni {name: $name})
        DETACH DELETE s
        RETURN count(s) as removed
        """
        result = tx.run(query, name=alumni_name)
        record = result.single()
        removed = record["removed"] if record else 0
        return removed

    def remove_alumnis(self, alumni_names):
        """
        Remove multiple alumnis by their names.
        """
        removed_total = 0
        for name in alumni_names:
            removed = self.remove_alumni(name)
            print(f"Removed {removed} node(s) for alumni '{name}'.")
            removed_total += removed
        return removed_total

def main():
    # Specify the list of alumni names you want to remove.
    alumnis_to_remove = ["poppy stowell-evans"]

    db = GraphDB(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    total_removed = db.remove_alumnis(alumnis_to_remove)
    db.close()
    
    print(f"Total alumnis removed: {total_removed}")

if __name__ == "__main__":
    main()