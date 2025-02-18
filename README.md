# Natural Language Alumni Search

## Structure of this repository

inital_alumni_population --> popualte the neo4j database (assuming docker instance of neo4j host is running) using currently just the provided excel class lists from the Yale Office of Career Strategy

dynamic_visualize.py --> after populating the neo4j database with alumni profile nodes, compute edges between all of them and create a similarity score between all nodes in the graph. Then, display them automatically using "from pyvis.network import Network" (temporary solution)

add_alumni.py --> add specific alumni by name

remove_alumni.py --> remove specific alumni by name

view_database.py --> produce .txt file containing all information from every profile within the neo4j database, write .txt file into ./output