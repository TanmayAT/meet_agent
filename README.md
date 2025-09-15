

# Hiring Interview Agent – Neha

This project provides an AI-powered **Interview Agent (Neha)**, built on LiveKit, that you can interact with in real-time. The agent joins your interview session with **< 1s latency** and supports orchestration features like transcript storage and dynamic workflows.

---

## 🎯 Features

* ⚡ **Ultra-low latency** (less than 1 second)
* 🤖 **Agent Neha** auto-dispatched into your interview session
* 📝 **Transcript storage** (in progress)
* 🔄 **Advanced orchestration** for multi-agent workflows (in progress)

---

## 🚀 Getting Started

### 1. Join the Interview Frontend

Go to the LiveKit demo page:
👉 [https://meet.livekit.io/?tab=demo](https://meet.livekit.io/?tab=demo)

Choose **Custom** when prompted.

### 2. Connection Details

* **URI:**

  ```
  wss://hiring-meet-agent-f837qv32.livekit.cloud
  ```
* **Token:**
  Generate a fresh token before every session:
  👉 [http://210.79.129.208:8000/token](http://210.79.129.208:8000/token)

⚠️ **Note:** Always use a new token for each join attempt, otherwise the connection will fail.

---

## 🧑‍💻 How It Works

1. You join the room from the LiveKit demo frontend.
2. A fresh token authenticates your session.
3. The backend dispatches **Hiring Agent Neha** into the room.
4. You interact in real-time, with sub-second latency.

---

## 🛠️ Roadmap

* [ ] Persist transcripts in storage
* [ ] Add orchestration logic for more complex interview flows
* [ ] Support multiple specialized agents

---

## 📌 Notes

* This repo focuses on backend + agent orchestration.
* Frontend for testing leverages the official [LiveKit demo](https://meet.livekit.io).

---

Would you like me to also **add setup instructions** (like how to run the backend locally with FastAPI/uvicorn + required env vars), or should this README stay **usage-only** for now?
