import os
from app.core.config import settings
from app.services.rag_service import F1StrategistEngine

def main():
    print("🤖 Initializing Pit Wall AI Strategist...")
    
    # 🔍 DIAGNOSTIC CHECK: Print the key length and its last 4 characters
    key = settings.HF_TOKEN
    if key:
        print(f"📡 Loaded API Key: Length={len(key)} | Ends with='...{key[-4:]}'")
    else:
        print("❌ Loaded API Key: None (Empty String)")
        
    engine = F1StrategistEngine()
    # ... rest of your code remains the same
    
    # 2. Check for the target file
    pdf_path = "f1_rules.pdf"
    if not os.path.exists(pdf_path):
        print(f"❌ Error: Could not find '{pdf_path}' in the root directory.")
        print("Please place a sample PDF there and name it 'f1_rules.pdf'")
        return

    # 3. Feed the document into ChromaDB (Step 1 & 2 of RAG)
    # Note: You only need to run ingestion ONCE per document, as it saves to disk!
    print("\n--- Phase 1: Ingesting Data into Vector DB ---")
    engine.ingest_f1_document(pdf_path)
    
    # 4. Query the engine (Step 3 & 4 of RAG)
    print("\n--- Phase 2: Testing AI Retrieval Knowledge ---")
    
    # Change this question to match something specific inside your PDF!
    question = "What are the core regulations or key takeaways mentioned in this document?"
    
    print(f"🤔 Question: {question}")
    print("⏳ Searching Vector DB and generating answer...")
    
    answer = engine.query_assistant(question)
    
    print("\n🏎️ AI Strategist Response:")
    print(answer)

if __name__ == "__main__":
    main()