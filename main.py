import sqlite3
import json
import math
from foundry_local_sdk import Configuration, FoundryLocalManager

# 1. Yapilandirmayi baslat
config = Configuration(app_name="RagAssistant")
FoundryLocalManager.initialize(config)
manager = FoundryLocalManager.instance
catalog = manager.catalog

print("Modeller yukleniyor, lutfen bekleyin...")

# 2. Embedding modelini yukle
embed_model = catalog.get_model("qwen3-embedding-0.6b")
embed_model.download()
embed_model.load()
embed_client = embed_model.get_embedding_client()

# 3. Chat modelini yukle
chat_model = catalog.get_model("phi-3.5-mini")
chat_model.download()
chat_model.load()
chat_client = chat_model.get_chat_client()

print("Modeller hazir!\n")

# 4. Kosinus benzerligi fonksiyonu
def cosine_similarity(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    return dot / (norm1 * norm2)

# 5. En alakali chunk'lari bulan fonksiyon
def get_top_chunks(query, top_k=2):
    query_response = embed_client.generate_embeddings([query])
    query_vector = query_response.data[0].embedding

    conn = sqlite3.connect("documents.db")
    cursor = conn.cursor()
    cursor.execute("SELECT content, embedding FROM documents")
    rows = cursor.fetchall()
    conn.close()

    scored = []
    for content, embedding_json in rows:
        vector = json.loads(embedding_json)
        score = cosine_similarity(query_vector, vector)
        scored.append((score, content))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]

# 6. Retrieval + LLM'i birlestiren ana fonksiyon
def answer_query(question):
    top_chunks = get_top_chunks(question, top_k=2)

    best_score = top_chunks[0][0]
    if best_score < 0.55:
        return "Bu konuda elimde bilgi yok.", top_chunks

    context_text = "\n\n".join([f"- {content}" for score, content in top_chunks])

    system_prompt = (
        "Sen bir buyuk veri analistligi ders asistanisin. "
        "SADECE asagida verilen baglam metninde acikca yazan bilgiyi kullanarak Turkce cevap ver. "
        "Baglamda dogrudan cevaplanmamis, kismen ilgili veya dolayli bir konu varsa bile UYDURMA, YORUM KATMA, TAHMIN YURUTME. "
        "Eger baglamdaki bilgi soruyu tam olarak cevaplamiyorsa, SADECE 'Bu konuda elimde bilgi yok' yaz ve BASKA HICBIR SEY ekleme. "
        "Tarih, yil, kaynak gibi baglamda olmayan hicbir detay uydurma.\n\n"
        f"Baglam:\n{context_text}"
    )

    response = chat_client.complete_chat([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ])

    return response.choices[0].message.content, top_chunks

# 7. Interaktif CLI dongusu
print("=" * 50)
print("Buyuk Veri Analistligi RAG Asistani")
print("Cikmak icin 'exit' yazin.")
print("=" * 50)

while True:
    question = input("\nSorunuz: ").strip()

    if question.lower() in ["exit", "quit", "cikis"]:
        print("Gorusmek uzere!")
        break

    if not question:
        continue

    answer, top_chunks = answer_query(question)

    print("\n[Kullanilan kaynaklar:]")
    for score, content in top_chunks:
        print(f"  (skor: {score:.3f}) {content[:60]}...")

    print(f"\nCevap: {answer}")