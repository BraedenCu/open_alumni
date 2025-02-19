'use client';

import { useState } from 'react';

export default function Home() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState('');

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setResult(null);

    try {
      const response = await fetch('http://127.0.0.1:5000/api/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        throw new Error(`Error: ${response.statusText}`);
      }

      const data = await response.json();
      console.log("API response:", data);
      if (data.error) {
        setError(data.error);
      } else if (data.matches) {
        setResult(JSON.stringify(data.matches, null, 2));
      } else {
        setError("No matching alumni found.");
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div
      style={{
        backgroundColor: "#f5f7fa",
        minHeight: "100vh",
        fontFamily: "Inter, sans-serif",
        padding: "2rem",
      }}
    >
      <header style={{ marginBottom: "2rem", textAlign: "center" }}>
        <h1 style={{ fontSize: "2.5rem", fontWeight: 600, color: "#111", marginBottom: "0.5rem" }}>
          Alumni Graph Visualization
        </h1>
        <p style={{ fontSize: "1rem", color: "#555" }}>
          Discover Yale alumni profiles and explore their connections.
        </p>
      </header>

      {/* Graph Visualization Section */}
      <section style={{ marginBottom: "2rem", borderRadius: "8px", overflow: "hidden", boxShadow: "0 2px 8px rgba(0,0,0,0.1)" }}>
        <iframe
          src="/alumni_huge.html"
          width="100%"
          height="750px"
          style={{ border: "none" }}
          title="Alumni Graph Visualization"
        />
      </section>

      {/* Query Interface Section */}
      <section
        style={{
          backgroundColor: "#fff",
          padding: "1.5rem",
          borderRadius: "8px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
        }}
      >
        <h2 style={{ fontSize: "1.75rem", marginBottom: "1rem", color: "#111" }}>Search Alumni</h2>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <input
            type="text"
            id="query"
            placeholder="e.g., find me other yale graduates from the class of 2020 who work on public policy in Washington DC"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            required
            style={{
              padding: "0.75rem",
              fontSize: "1rem",
              borderRadius: "4px",
              border: "1px solid #ddd",
            }}
          />
          <button
            type="submit"
            style={{
              padding: "0.75rem",
              fontSize: "1rem",
              borderRadius: "4px",
              backgroundColor: "#0070f3",
              color: "#fff",
              border: "none",
              cursor: "pointer",
            }}
          >
            Search
          </button>
        </form>
        {error && <p style={{ color: "red", marginTop: "1rem" }}>{error}</p>}
        {result && (
          <div style={{ marginTop: "1rem" }}>
            <h3 style={{ fontSize: "1.25rem", marginBottom: "0.5rem", color: "#111" }}>Results:</h3>
            <pre
              style={{
                backgroundColor: "#f0f0f0",
                padding: "1rem",
                borderRadius: "4px",
                overflowX: "auto",
              }}
            >
              {result}
            </pre>
          </div>
        )}
      </section>
    </div>
  );
}