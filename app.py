import sqlite3
import json
import math
from flask import Flask, render_template, request, jsonify
from foundry_local_sdk import Configuration, FoundryLocalManager

app = Flask(__name__)

config = Configuration(app_name="RagAssistant")
FoundryLocalManager.initialize(config)
manager = FoundryLocalManager.instance
catalog = manager.catalog

print("Modeller yukleniyor, lutfen bekleyin...")

embed_model = catalog.get_model("qwen3-embedding-0.6b")
embed_model.download()
embed_model.load()
embed_client = embed_model.get_embedding_client()

chat_model = catalog.get_model("qwen2.5-0.5b")
chat_model.download()
chat_model.load()
chat_client = chat_model.get_chat_client()

print("Modeller hazir!")

def cosine_similarity(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    return dot / (norm1 * norm2)

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

def answer_query(question):
    top_chunks = get_top_chunks(question, top_k=2)

    best_score = top_chunks[0][0]
    if best_score < 0.55:
        return "Bu konuda elimde bilgi yok.", top_chunks

    context_text = "\n\n".join(
        [f"[Kaynak {i+1}]: {content}" for i, (score, content) in enumerate(top_chunks)]
    )

    system_prompt = (
        "Sen bir buyuk veri analistligi ders asistanisin. "
        "SADECE asagida verilen baglam metninde acikca yazan bilgiyi kullanarak Turkce cevap ver. "
        "Baglam disina CIKMA, tahmin YURUTME, uydurma bilgi VERME. "
        "Cevabinin SONUNA, hangi kaynaklari kullandigini parantez icinde belirt, ornek: (Kaynak 1). "
        "Eger baglamdaki bilgi soruyu tam olarak cevaplamiyorsa, SADECE 'Bu konuda elimde bilgi yok' yaz ve BASKA HICBIR SEY ekleme.\n\n"
        f"Baglam:\n{context_text}"
    )

    response = chat_client.complete_chat([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ])

    return response.choices[0].message.content, top_chunks

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"answer": "Lutfen bir soru yazin.", "sources": []})

    answer, top_chunks = answer_query(question)

    sources = [
        {"score": round(score, 3), "text": content[:80]}
        for score, content in top_chunks
    ]

    return jsonify({"answer": answer, "sources": sources})

if __name__ == "__main__":
    app.run(debug=False, port=5000)