# We want to add a natural language paragraph summary of each alumni to the database given the spreadsheet containing the alumni data. The summary should be stored as a new property on the alumni node in the database. We want a natural language summary of the profiles so that our text embedding similarity score will be more accurate and meaningful (vs just using textual embedding comparison on raw values). The summary should be generated using the following template: (Name)lives in (City). They work at (company). At Yale they majored in (major). They did/did not go to graduate school, if so they went to (graduate school name). They work in the (industry) industry as a (job function).

# The summary should be generated for each alumni based on the data in the spreadsheet. If any of the fields are missing, they should be skipped in the summary. The summary should be stored in the database as a new property called "description". Implement the function add_alumni_description in the GraphDB class to achieve this. The function should take the alumni_info dictionary and return the updated alumni node with the description property added. You can assume that the alumni_info dictionary will contain the same keys as in the main function. The description should be generated according to the template provided above. You can use the following helper function to generate the description: def generate_description(alumni_info):     name = alumni_info.get("name", "")     city = alumni_info.get("city", "")     employer = alumni_info.get("employer", "")     grad_school = alumni_info.get("grad_school", "")     major = alumni_info.get("major", "")     industry = alumni_info.get("industry", "")     function = alumni_info.get("function", "")     description = f"{name} lives in {city}. They work at {employer}."     if grad_school:         description += f" At Yale they majored in {major}. They went to {grad_school}."     else:         description += f" At Yale they majored in {major}. They did not go to graduate school."     description += f" They work in the {industry} industry as a {function}."     return description You can assume that the GraphDB class has already

'''Alumni information is in the following form:
    {
        "country": NaN,
        "major": "Psychology",
        "city": "Madison",
        "function": "Project Management",
        "grad_school": NaN,
        "name": "Abigail Calnen Hopkins",
        "employer": "Epic Systems Corporation",
        "industry": "Healthcare/Pharmaceutical/Biotech/Global Health",
        "us_state": "Wisconsin",
        "email": "abhops@gmail.com"
    }
'''

# the natural language summaries should be created with chatgpt api. We do this so that, when we inevitably add many more fields, we can easily update the summary generation without having to rewrite anything! Also, do not worry about the database population as we handle that in the initial_alumni_populate.py file. All we are worried about is defining functions that will be used in that file, when given a line of data for a specific person, we generate a paragraph output. That is all we are doing in this file

# the database is already defined and created in initial_alumni_add
import os
from openai import OpenAI
import openai
import json
from neo4j import GraphDatabase

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Set your OpenAI API key (ensure this is set in your environment)
#if not openai.api_key:
#    raise ValueError("Please set your OPENAI_API_KEY environment variable.")

def get_completion(prompt):
    """
    Generate a completion from OpenAI's ChatCompletion API using the new syntax.
    """
    response = client.chat.completions.create(model="gpt-3.5-turbo",  # or "gpt-4" if available and desired
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7,
    max_tokens=150)
    return response.choices[0].message.content.strip()

def generate_description(alumni_info):
    """
    Generates a natural language summary for an alumni profile using the provided template.
    If fields are missing, they are skipped.
    
    Template:
    (Name) lives in (City). They work at (company). At Yale they majored in (major).
    They did/did not go to graduate school, if so they went to (graduate school name).
    They work in the (industry) industry as a (job function).
    """
    # Build the prompt with the alumni_info in JSON
    prompt = (
        "Generate a natural language summary for the following alumni profile using this template:\n\n"
        "\"<Name> lives in <City>. They work at <company>. At Yale they majored in <major>. "
        "They did/did not go to graduate school, if so they went to <graduate school name>. "
        "They work in the <industry> industry as a <job function>.\"\n\n"
        "Skip any field that is missing.\n\n"
        "Alumni profile data:\n" + json.dumps(alumni_info, indent=2)
    )
    return get_completion(prompt)

class GraphDB:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def add_alumni_description(self, alumni_info):
        """
        Generates a natural language description for an alumni profile using the ChatGPT API,
        then updates the corresponding node in the database with a new property "description".
        The node is matched using the 'name' property.
        Returns the updated node.
        """
        description = generate_description(alumni_info)
        alumni_info["description"] = description
        name = alumni_info.get("name", "").strip()
        if not name:
            print("Skipping record: no valid name provided.")
            return None
        query = (
            "MATCH (s:Student {name: $name}) "
            "SET s.description = $description "
            "RETURN s"
        )
        with self.driver.session() as session:
            result = session.execute_write(self._update_description, name, description)
            return result

    @staticmethod
    def _update_description(tx, name, description):
        result = tx.run(
            query="""
                MATCH (s:Student {name: $name})
                SET s.description = $description
                RETURN s
            """,
            name=name, description=description
        )
        record = result.single()
        return record[0] if record else None