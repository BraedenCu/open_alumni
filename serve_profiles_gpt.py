# Now, we want to create a test script that when we manually provide a natural language prompt, we receive a response with the profiles that most closely match what the prompt is requesting (for example, find me investment bankers in new york that work at goldman sachs) then print out the names of the alumni that match that criteria or score a high similarity score with users who have similar profiles.

# first, using a prompt from the user, give gpt access to all the alumni profiles by fine tuning it with the alumni profiles. Then, it should be able to instantly serve up the profiles that best match the prompt given by the user.

# thus, we need a function for finetuning our gpt. Another function for using that finetuned gpt to serve up the profiles that best match the prompt given by the user. And finally a last function to take natural language prompt as input and return the profiles that chatgpt serves up.

import os
import json
from neo4j import GraphDatabase
from openai import OpenAI
import openai

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ====== Neo4j Connection Configuration ======
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

class GraphDB:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def fetch_alumni_profiles(self):
        """
        Fetch all alumni nodes (with at least 'name' and 'description') from the database.
        Returns a list of dictionaries.
        """
        query = "MATCH (s:Student) RETURN s"
        profiles = []
        with self.driver.session() as session:
            result = session.run(query)
            for record in result:
                node = dict(record["s"])
                if "name" in node and "description" in node:
                    profiles.append(node)
        return profiles

def fine_tune_gpt(alumni_profiles):
    """
    Simulate fine-tuning GPT with the alumni profiles by constructing a context string.
    For each profile, we include its name and description. This context is later injected
    into the system prompt for serving user queries.
    """
    context_lines = []
    for profile in alumni_profiles:
        name = profile.get("name", "Unknown")
        description = profile.get("description", "")
        context_lines.append(f"{name}: {description}")
    context = "\n".join(context_lines)
    return context

def serve_profiles(nl_prompt, alumni_context):
    """
    Given a natural language prompt and the alumni context string, generate a response
    using the ChatGPT API that returns the names of alumni that best match the query.
    """
    system_prompt = (
        "You are an expert at matching alumni profiles to user queries. You are specifically good as providing precise matches. You specifically match keywords from the user's prompt to keywords in alumni profiles."
        "Below is a list of alumni profiles (each line contains the alumni's name and a short description). "
        "Based on the user's query, return only the names of the alumni that best match and an explanation of why they were selected. Be sure to only serve up profiles that are relevant to the user query."
        "Separate the names with commas.\n\n"
        "Alumni Profiles:\n" + alumni_context
    )

    user_prompt = f"User Query: {nl_prompt}\n\nReturn only the names of the best matching alumni which share direct keywords with the user prompt."

    response = client.chat.completions.create(model="gpt-3.5-turbo",  # Use the cost-effective model.
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    temperature=0.0,
    max_tokens=150)
    return response.choices[0].message.content.strip()

def main():
    nl_query = "find me investment bankers in New York who work at Goldman Sachs. Only show me bankers that work at goldman sachs in your response.'"

    pre_prompt = "I need you to find the exact alumni profile that MOST matches the following criteria, answer using only there name and email. User Prompt is as follows, use all context provided previously to inform the best match response: "

    prompt = pre_prompt + nl_query

    # Connect to Neo4j and fetch alumni profiles.
    db = GraphDB(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    alumni_profiles = db.fetch_alumni_profiles()
    db.close()

    if not alumni_profiles:
        print("No alumni profiles found in the database.")
        return

    # Build the GPT context string from alumni profiles.
    alumni_context = fine_tune_gpt(alumni_profiles)

    # Get the response from GPT.
    result = serve_profiles(prompt, alumni_context)

    print("\nMatching Alumni:")
    print(result)

if __name__ == "__main__":
    main()