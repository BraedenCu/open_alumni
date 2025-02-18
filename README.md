# Natural Language Alumni Search

## Demo

launch frontend: npm run deploy

launch API: python app.py

sample prompt: find me other yale graduates from the class of 2020 that work on public policy in washington dc

## Structure of this repository

inital_alumni_population --> popualte the neo4j database (assuming docker instance of neo4j host is running) using currently just the provided excel class lists from the Yale Office of Career Strategy

dynamic_visualize.py --> after populating the neo4j database with alumni profile nodes, compute edges between all of them and create a similarity score between all nodes in the graph. Then, display them automatically using "from pyvis.network import Network" (temporary solution)

add_alumni.py --> add specific alumni by name

remove_alumni.py --> remove specific alumni by name

view_database.py --> produce .txt file containing all information from every profile within the neo4j database, write .txt file into ./output

## Launching the information extraction script

conda create --name alumni_db python=3.8
conda activate alumni_db
pip install -r requirements.txt

## Launching the db

docker run --name neo4j -p 7687:7687 -p 7474:7474 -d neo4j:latest

docker run --name neo4j -p 7687:7687 -p 7474:7474 -e NEO4J_AUTH=none -d neo4j:latest

### Restarting db

docker stop neo4j
docker rm neo4j
docker ps -a

### Run Application

python initual_alumni_populate.py
python dynamic_visualize.py
open ./output/neo4j_alumni.html

python add_alumni.py
