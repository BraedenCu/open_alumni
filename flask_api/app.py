from flask import Flask, request, jsonify
from flask_cors import CORS
from serve_profile import launch_query

app = Flask(__name__)
CORS(app)

@app.route('/api/query', methods=['POST'])
def query_profiles():
    print("Received a query request.")
    data = request.get_json()
    user_input = data.get("query", "")
    if not user_input:
        return jsonify({"error": "No query provided"}), 400

    try:
        print(f"Processing query: {user_input}")
        matches = launch_query(user_input)
        # Ensure that each match is a 2-tuple with similarity as a standard float.
        matches = [(name, float(sim)) for name, sim in matches]
        return jsonify({"matches": matches}), 200
    except Exception as e:
        print(f"Error processing query: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)