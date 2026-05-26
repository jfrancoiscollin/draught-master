"""Backend module for the strategy RAG panel.

Wires `pedagogy.prose.retrieval` (dilf) into a FastAPI route. Each
topic button on the frontend maps to a server-side "centroid" — the
mean of the embeddings of every passage matching the topic's filter
spec. Querying with the centroid surfaces the passages most
representative of the topic.

Cf. CADRAGE_STRATEGIE.md §8 (usage B: temps réel cité).
"""
