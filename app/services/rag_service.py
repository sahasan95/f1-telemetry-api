import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

# Clean native local Ollama integration drivers
from langchain_ollama import OllamaEmbeddings, ChatOllama

# Core Retrieval Chains
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# Points to a fresh version path to bypass any stuck file handles completely
DB_DIR = os.path.join(os.getcwd(), "chroma_db_local")

class F1StrategistEngine:
    def __init__(self):
        print("⚡ Booting Local Vector Engine (nomic-embed-text)...")
        self.embeddings = OllamaEmbeddings(
            model="nomic-embed-text"
        )
        
        print("⚡ Initializing Local Brain (phi3)...")
        self.llm = ChatOllama(
            model="phi3",
            temperature=0
        )
        
    def ingest_f1_document(self, file_path: str):
        """Slices PDF and indexes text vectors into local ChromaDB for free."""
        print(f"🔄 Starting local ingestion for: {file_path}")
        
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = text_splitter.split_documents(documents)
        
        vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=DB_DIR
        )
        print(f"✅ Successfully vectorized {len(chunks)} chunks locally into ChromaDB.")
        return vector_store

    def query_assistant(self, user_question: str) -> str:
        """Retrieves matching local vectors and prompts the offline local LLM."""
        vector_store = Chroma(persist_directory=DB_DIR, embedding_function=self.embeddings)
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        
        system_prompt = (
            "You are an elite Formula 1 Pit Wall Strategy Engineer. "
            "Analyze the provided race data or regulations context carefully to answer the question. "
            "If you do not know the answer based on the context, state that you lack sufficient data.\n\n"
            "Context:\n{context}"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])
        
        question_answer_chain = create_stuff_documents_chain(self.llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        
        response = rag_chain.invoke({"input": user_question})
        return response["answer"]