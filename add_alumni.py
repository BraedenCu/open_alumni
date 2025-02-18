import json
import time
import requests
from neo4j import GraphDatabase
import os 

# ====== Configuration ======
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

API_TOKEN = os.environ.get("YALIES_KEY")
API_URL = "https://yalies.io/api/people"

def get_alumni_info(alumni_name):
    """
    Query the Yalies API for a alumni by name.
    Returns the first matching alumni's information as a dictionary.
    """
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": alumni_name,
        "page": 1,
        "page_size": 1  # Only fetch one alumni for a precise match
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            results = response.json()
            if results:
                return results[0]  # Return the first matching alumni
            else:
                print(f"No alumni found with the name '{alumni_name}'.")
                return None
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception occurred while fetching {alumni_name}: {e}")
        return None

class GraphDB:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def add_alumni(self, alumni_info, fallback_name):
        with self.driver.session() as session:
            result = session.execute_write(self._create_alumni, alumni_info, fallback_name)
            return result
    
    @staticmethod
    def _create_alumni(tx, alumni_info, fallback_name):
        # Use the "name" field if available, otherwise fallback to provided name.
        name = alumni_info.get("name") or fallback_name
        if not name:
            print("Skipping record: 'name' is missing.")
            return None
        query = (
            "MERGE (s:alumni {name: $name}) "
            "SET s += $props "
            "RETURN s"
        )
        props = alumni_info.copy()
        props.pop("name", None)
        result = tx.run(query, name=name, props=props)
        record = result.single()
        return record[0] if record else None

    def fetch_alumni_names(self):
        """
        Fetch all existing alumni names from the database.
        Returns a set of names.
        """
        with self.driver.session() as session:
            query = "MATCH (s:alumni) RETURN s.name as name"
            names = set()
            result = session.run(query)
            for record in result:
                if record["name"]:
                    names.add(record["name"])
            return names

def main():
    # List of new alumni names to add
    new_names = ["poppy stowell-evans"]

    # Initialize database connection
    db = GraphDB(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    # Fetch current alumni names from the database
    existing_names = db.fetch_alumni_names()
    
    for name in new_names:
        if name in existing_names:
            print(f"{name} already exists in the database; skipping API query.")
        else:
            print(f"Querying API for {name}...")
            info = get_alumni_info(name)
            if info:
                print(f"Adding {name} to the database...")
                db.add_alumni(info, fallback_name=name)
                # Update the existing names set to include the new entry
                existing_names.add(name)
                time.sleep(1)  # Pause to avoid API rate limits
            else:
                print(f"No data found for {name}.")
    
    db.close()
    print("Database update complete.")

if __name__ == "__main__":
    main()