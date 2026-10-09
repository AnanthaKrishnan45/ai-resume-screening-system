"""Central configuration for eligibility and scoring."""
SCORE_WEIGHTS = {
    "ai_project_depth": 40,
    "python_backend": 30,
    "cloud_fullstack": 15,
    "github": 10,
    "engineering_depth": 5,
}
PYTHON_TERMS = [
    "python", "fastapi", "django", "flask", "pandas", "numpy", "pytest",
    "scikit-learn", "pytorch", "tensorflow"
]
AI_TERMS = [
    "langchain", "langgraph", "llamaindex", "llama index", "google adk",
    "rag", "retrieval augmented generation", "vector database", "vector search",
    "embeddings", "embedding", "tool calling", "tool-calling", "multi-agent",
    "agentic", "llm", "large language model", "openai api", "transformers",
    "generative ai", "semantic search", "chromadb", "faiss", "weaviate",
    "milvus", "haystack", "autogen", "crewai"
]
