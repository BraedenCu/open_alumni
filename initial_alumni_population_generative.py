import pandas as pd
import json
import time
from neo4j import GraphDatabase
from alumni_summarization import generate_description  # Import the helper function

# ====== Excel File Configuration ======
EXCEL_FILE = "./data/2020_YC_Class_List.xlsx"  # Path to your Excel file

# ====== Neo4j Database Configuration ======
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

class GraphDB:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def add_alumni(self, alumni_info):
        """
        Merge (create or update) an alumni node in Neo4j based on the 'name' property.
        Additional properties are added/updated on the node.
        This function also generates a natural language summary using ChatGPT
        and stores it as the 'description' property.
        """
        with self.driver.session() as session:
            result = session.execute_write(self._create_alumni, alumni_info)
            return result
    
    @staticmethod
    def _create_alumni(tx, alumni_info):
        """
        Merge a node with the label 'Student' using the 'name' property as the key.
        Set/update the other properties (including the new 'description').
        """
        name = alumni_info.get("name", "").strip()
        if not name:
            print("Skipping record: 'name' is missing.")
            return None
        
        query = (
            "MERGE (s:Student {name: $name}) "
            "SET s += $props "
            "RETURN s"
        )
        props = alumni_info.copy()
        props.pop("name", None)
        result = tx.run(query, name=name, props=props)
        record = result.single()
        return record[0] if record else None

def main():
    # Read the Excel file using pandas
    df = pd.read_excel(EXCEL_FILE)

    # Initialize the graph database connection
    graph_db = GraphDB(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    # For testing, limit the number of alumni processed
    max_alumni = 1000

    # Iterate through each row of the DataFrame
    for index, row in df.iterrows():
        if index >= max_alumni:
            break
        
        # Build a dictionary of alumni properties from the Excel columns
        alumni_info_generate_description = {
            "name": str(row.get("Student", "")).strip(),
            "country": row.get("Country (if outside the U.S.)", ""),
            "us_state": row.get("U.S. State", ""),
            "city": row.get("City", ""),
            "grad_school": row.get("Graduate/Professional School", ""),
            "employer": row.get("Employer", ""),
            "industry": row.get("Industry", ""),
            "function": row.get("Function (Role)", ""),
            "major": row.get("Major", "")
        }

        # Generate the natural language summary for the alumni and add it
        description = generate_description(alumni_info_generate_description)

        ''' full alumni_info
        alumni_info = {
            "name": str(row.get("Student", "")).strip(),
            "email": row.get("Email", ""),
            "country": row.get("Country (if outside the U.S.)", ""),
            "us_state": row.get("U.S. State", ""),
            "city": row.get("City", ""),
            "grad_school": row.get("Graduate/Professional School", ""),
            "employer": row.get("Employer", ""),
            "industry": row.get("Industry", ""),
            "function": row.get("Function (Role)", ""),
            "major": row.get("Major", "")
        }
        '''
        # Now, replace all the existing description with the new one, this is all we need
        alumni_info = {
            "name": str(row.get("Student", "")).strip(),
            "email": row.get("Email", ""),
            "description": description
        }
        # alumni_info["description"] = description

        print(f"\nProcessing row {index}:")
        print(json.dumps(alumni_info, indent=4))
        
        # Add or update this alumni node in Neo4j (with the generated description).
        node = graph_db.add_alumni(alumni_info)

        if node:
            print(f"Stored node for alumni: {alumni_info['name']}")
        else:
            print(f"Skipping row {index} due to missing or invalid name.")
        
        time.sleep(0.5)  # Pause briefly to avoid rate limits.
    
    graph_db.close()
    print("\nAll alumni processed and stored in the graph database.")

if __name__ == "__main__":
    main()