import pandas as pd
import json
from neo4j import GraphDatabase

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
    
    def add_student(self, student_info):
        """
        Merge (create or update) a 'Student' node in Neo4j based on the 'name' property.
        Additional properties are added/updated on the node.
        """
        with self.driver.session() as session:
            result = session.execute_write(self._create_student, student_info)
            return result
    
    @staticmethod
    def _create_student(tx, student_info):
        """
        The MERGE clause ensures a node with this name is created if it doesn't exist.
        Then we set/update the other properties.
        """
        # We expect 'name' to be present as the primary key for the Student node.
        name = student_info.get("name", "").strip()
        if not name:
            print("Skipping record: 'name' is missing.")
            return None
        
        query = (
            "MERGE (s:Student {name: $name}) "
            "SET s += $props "
            "RETURN s"
        )
        # We'll remove the 'name' from the properties dict so we don't overwrite the key.
        props = student_info.copy()
        props.pop("name", None)
        result = tx.run(query, name=name, props=props)
        record = result.single()
        return record[0] if record else None

def main():
    # Read the Excel file using pandas
    df = pd.read_excel(EXCEL_FILE)

    # Initialize the graph database connection
    graph_db = GraphDB(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    # Iterate through each row of the DataFrame
    for index, row in df.iterrows():
        # Build a dictionary of student properties from the Excel columns
        student_info = {
            # "Student" is used as the 'name' property in the DB
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

        # Print for debugging
        print(f"\nProcessing row {index}:")
        print(json.dumps(student_info, indent=4))
        
        # Add or update this student node in Neo4j
        node = graph_db.add_student(student_info)
        if node:
            print(f"Stored node for student: {student_info['name']}")
        else:
            print(f"Skipping row {index} due to missing or invalid name.")

    # Close the database connection
    graph_db.close()
    print("\nAll students processed and stored in the graph database.")

if __name__ == "__main__":
    main()
