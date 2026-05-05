/** @odoo-module **/

function initChatbot() {
    const form = document.getElementById("chatbot-form");
    if (!form) return;

    const messages = document.getElementById("chatbot-messages");
    const input = document.getElementById("chatbot-input");
    const sendBtn = document.getElementById("chatbot-send");

    let activeSource = null;

    function scrollToBottom() {
        messages.scrollTop = messages.scrollHeight;
    }

    function appendBubble(html, role) {
        const div = document.createElement("div");
        div.className = `chatbot-bubble ${role}`;
        if (role === "assistant") {
            div.innerHTML = html;
        } else {
            div.textContent = html;
        }
        messages.appendChild(div);
        scrollToBottom();
        return div;
    }

    function setDisabled(disabled) {
        input.disabled = disabled;
        sendBtn.disabled = disabled;
    }

    function sendMessage(e) {
        if (e) e.preventDefault();
        const text = input.value.trim();
        if (!text || activeSource) return;

        input.value = "";
        appendBubble(text, "user");
        setDisabled(true);

        const assistantDiv = appendBubble('<span class="chatbot-typing">Thinking…</span>', "assistant");

        const url = `/chatbot/stream?message=${encodeURIComponent(text)}`;
        activeSource = new EventSource(url);

        activeSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            switch (data.type) {
                case "chunk":
                    assistantDiv.innerHTML = data.content || "";
                    scrollToBottom();
                    break;
                case "done":
                    activeSource.close();
                    activeSource = null;
                    setDisabled(false);
                    input.focus();
                    break;
                case "error":
                    assistantDiv.innerHTML = `<em style="color:red">Error: ${data.error}</em>`;
                    activeSource.close();
                    activeSource = null;
                    setDisabled(false);
                    input.focus();
                    scrollToBottom();
                    break;
            }
        };

        activeSource.onerror = () => {
            assistantDiv.innerHTML = "<em>Connection error. Please try again.</em>";
            activeSource.close();
            activeSource = null;
            setDisabled(false);
            input.focus();
        };
    }

    form.addEventListener("submit", sendMessage);
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initChatbot);
} else {
    initChatbot();
}
