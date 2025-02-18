import json
from neo4j import GraphDatabase

# ====== Neo4j Connection Configuration ======
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

def fetch_all_students():
    """
    Connect to the Neo4j database and fetch all nodes with the label 'Student'.
    Returns a list of dictionaries representing student properties.
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    query = "MATCH (s:Student) RETURN s"
    students = []
    with driver.session() as session:
        result = session.run(query)
        for record in result:
            student = dict(record["s"])
            students.append(student)
    driver.close()
    return students

def write_students_to_file(students, filename="./output/students_output.txt"):
    """
    Write all student information to a text file.
    Each student's information is pretty-printed in JSON format.
    """
    with open(filename, "w", encoding="utf-8") as f:
        for student in students:
            f.write(json.dumps(student, indent=4))
            f.write("\n\n")

def main():
    students = fetch_all_students()
    if not students:
        print("No student nodes found in the database.")
        return
    write_students_to_file(students)
    print(f"Successfully wrote {len(students)} student records to './output/students_output.txt'.")

if __name__ == "__main__":
    main()