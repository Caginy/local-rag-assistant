let isLoading = false;

function addMessage(text, sender) {
  const container = document.getElementById("chat-container");
  const div = document.createElement("div");
  div.className = "message " + sender;
  div.innerHTML = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

async function sendQuestion(question) {
  if (isLoading) return;
  isLoading = true;

  const sendBtn = document.getElementById("send-btn");
  sendBtn.disabled = true;

  addMessage(question, "user");
  const input = document.getElementById("question-input");
  input.value = "";

  const loadingMsg = addMessage("Düşünüyorum...", "bot");

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question })
    });

    if (!response.ok) {
      throw new Error("Sunucu hatasi: " + response.status);
    }

    const data = await response.json();

    let sourcesHtml = "";
    if (data.sources && data.sources.length > 0) {
      sourcesHtml = "<div class='sources'>Kaynaklar: " +
        data.sources.map(s => `(skor: ${s.score})`).join(", ") +
        "</div>";
    }

    loadingMsg.innerHTML = data.answer + sourcesHtml;
  } catch (err) {
    loadingMsg.innerHTML = "Bir hata olustu: " + err.message;
  } finally {
    isLoading = false;
    sendBtn.disabled = false;
  }
}

function askQuestion() {
  const input = document.getElementById("question-input");
  const question = input.value.trim();
  if (question) sendQuestion(question);
}

function askQuick(question) {
  sendQuestion(question);
}

document.getElementById("question-input").addEventListener("keypress", function(e) {
  if (e.key === "Enter") askQuestion();
});