import time
from sentence_transformers import SentenceTransformer
from langchain_ollama import OllamaEmbeddings

def run_performance_test():
    print("="*50)
    print("Embedding Generation Speed Test")
    print("="*50)

    # Generate a realistic chunk of text
    sentences = [
        f"This is an example sentence number {i} used to simulate typical document chunk sizes that would be processed by our RAG system."
        for i in range(1000)
    ]
    
    print(f"Dataset Size: {len(sentences)} sentences")
    print("\n[Loading Models...]")
    
    # 1. Initialize sentence-transformers (MiniLM)
    start = time.time()
    minilm_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
    minilm_load_time = time.time() - start
    
    # 2. Initialize Ollama (Gemma)
    start = time.time()
    # Replace 'embeddinggemma:300m' if your model identifier is different
    # Make sure your local Ollama instance is running.
    gemma_model = OllamaEmbeddings(model="embeddinggemma:300m")
    # Ping once to ensure it's loaded into memory (warm-up)
    gemma_model.embed_query("warmup")
    gemma_load_time = time.time() - start

    print(f"  -> all-MiniLM-L6-v2 (CPU memory load) took: {minilm_load_time:.2f}s")
    print(f"  -> embeddinggemma:300m (Ollama warm-up) took: {gemma_load_time:.2f}s")

    print("\n[Running Execution Test...]")

    # Run MiniLM Test
    print("Running MiniLM...")
    start = time.time()
    minilm_embeddings = minilm_model.encode(sentences)
    minilm_exec_time = time.time() - start
    
    # Run Gemma (Ollama) Test
    print("Running Gemma through Ollama...")
    start = time.time()
    gemma_embeddings = gemma_model.embed_documents(sentences)
    gemma_exec_time = time.time() - start

    # Display Results
    print("\n" + "="*50)
    print("TEST RESULTS")
    print("="*50)
    print(f"all-MiniLM-L6-v2 Execution Time:   {minilm_exec_time:.2f} seconds")
    print(f"embeddinggemma:300m Execution Time: {gemma_exec_time:.2f} seconds")
    
    speed_diff = max(minilm_exec_time, gemma_exec_time) / max(min(minilm_exec_time, gemma_exec_time), 0.0001)
    faster_model = 'all-MiniLM-L6-v2' if minilm_exec_time < gemma_exec_time else 'embeddinggemma:300m'
    
    print(f"\nConclusion: {faster_model} was ~{speed_diff:.1f}x faster on this specific hardware.")

if __name__ == "__main__":
    run_performance_test()
