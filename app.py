import ollama
import chromadb
from chromadb.utils import embedding_functions

# 1. 初始化資料庫 (存放在記憶體，適合測試)
client = chromadb.Client()
collection = client.get_or_create_collection(name="pi_docs")

# 2. 準備知識庫資料
documents = [
    "Raspberry Pi 5 有 4GB 和 8GB RAM 版本。",
    "Pi 5 的處理器是 Broadcom BCM2712，速度比 Pi 4 快 2-3 倍。",
    "在 Pi 5 上運行 LLM 建議使用主動散熱器以避免降頻。",
    "Ollama 是一個在邊緣裝置運行大型語言模型的工具。"
]

# 將資料存入向量資料庫 (自動使用 nomic-embed-text 進行 Embedding)
for i, d in enumerate(documents):
    # 這裡手動呼叫 ollama 取得 embedding 並存入
    response = ollama.embeddings(model="nomic-embed-text", prompt=d)
    collection.add(
        ids=[str(i)],
        embeddings=[response['embedding']],
        documents=[d]
    )

def simple_rag(query):
    print(f"\n🔍 使用者問題: {query}")

    # Step A: 檢索 (Retrieval) - 找出最相關的前 2 條資訊
    query_emb = ollama.embeddings(model="nomic-embed-text", prompt=query)['embedding']
    results = collection.query(query_embeddings=[query_emb], n_results=2)
    context = " ".join(results['documents'][0])
    
    # Step B: Reranking (重排序邏輯)
    # 註：在小型 RAG 中，檢索結果不多時可跳過，或用 Cross-Encoder 模型處理。
    # 這裡我們直接將最相關的 context 餵給 LLM。

    # Step C: 生成 (Generation)
    prompt = f"請根據以下資訊回答問題：\n資訊：{context}\n問題：{query}\n答案："
    
    output = ollama.generate(model="llama3.2:3b", prompt=prompt)
    return output['response']

# 測試運行
answer = simple_rag("Raspberry Pi 5 的處理器是什麼？")
print(f"🤖 AI 回答: {answer}")
