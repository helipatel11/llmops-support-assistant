from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings


# Load documents
loader = DirectoryLoader(
    "llm/docs",
    glob="**/*.txt"
)

documents = loader.load()

print(f"Loaded {len(documents)} documents")


# Split documents
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

texts = text_splitter.split_documents(documents)

print(f"Created {len(texts)} chunks")


# Ollama embeddings
embedding = OllamaEmbeddings(
    model="llama3"
)


# Store vectors
vectordb = Chroma.from_documents(
    documents=texts,
    embedding=embedding,
    persist_directory="llm/chroma_db"
)

vectordb.persist()

print("ChromaDB created successfully.")