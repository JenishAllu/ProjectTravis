
# 🤖 TRAVIS: Transformer-based AI Virtual Assistant System

A multilingual, voice-enabled AI assistant designed for financial services. TRAVIS helps customers interact via text or speech and routes sensitive queries to human agents, all while supporting multilingual translation (Telugu, Hindi, English).

---

## 🌟 Features

- 🎤 **Speech-to-Text** using OpenAI Whisper
- 🧠 **Intent Classification** using XLM-RoBERTa
- 🌐 **Translation** with NLLB (No Language Left Behind)
- 🗣️ **Text-to-Speech (TTS)** using gTTS
- 👨‍💻 **Live Chat Interface** for Agents and Customers
- 🗃️ **MongoDB Atlas** for storing messages, users, and query history
- 🌐 **Flask + Socket.IO** backend hosted with ngrok (for live demo)
- ♿ **Accessibility Features**: Keyboard and hover-based narration

---

## 📂 Project Structure

```
ProjectTravis/
├── frontend/                # HTML, CSS, JS for customer & agent interfaces
├── backend/                 # Flask API with endpoints and Socket.IO
│   ├── app.py
│   ├── models/
│   ├── utils/
│   └── ...
├── colab_outputs/           # Notebooks from Google Colab
│   ├── ml-flask-backend-2.ipynb
│   └── fine-tunning-transformers.ipynb
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### 🔧 1. Clone the Repository

```bash
git clone https://github.com/JenishAllu/ProjectTravis.git
cd ProjectTravis
```

### 📦 2. Install Requirements

```bash
pip install -r requirements.txt
```

### ⚙️ 3. Run the Flask Backend

```bash
python backend/app.py
```

> Make sure MongoDB Atlas credentials and ngrok auth token are configured.

---

## 🧪 Colab Notebooks

You can explore training, backend experimentation, and fine-tuning from the following notebooks:

### 🔹 ml-flask-backend-2.ipynb  
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JenishAllu/ProjectTravis/blob/main/colab_outputs/ml-flask-backend-2.ipynb)

### 🔹 fine-tunning-transformers.ipynb  
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JenishAllu/ProjectTravis/blob/main/colab_outputs/fine-tunning-transformers.ipynb)

---

## 🔒 Roles

- 👨‍💻 **Customer**: Can chat, speak, and get AI or human responses
- 🕵️‍♂️ **Agent**: Receives and responds to sensitive or account-related queries

---

## 💬 Tech Stack

| Component         | Technology                     |
|------------------|--------------------------------|
| Frontend         | HTML, CSS, JS                  |
| Backend          | Flask, Flask-SocketIO, PyMongo |
| NLP              | XLM-RoBERTa, NLLB, Whisper      |
| TTS              | gTTS                           |
| Database         | MongoDB Atlas                  |
| Hosting (Dev)    | Google Colab + ngrok           |

---

## 📌 Notes

- This project supports **Telugu**, **Hindi**, and **English**
- TRAVIS is designed for live demos with both AI and human agent fallback
- Accessibility is integrated for visually impaired users

---

## 🙌 Acknowledgements

- 🤗 HuggingFace for model support
- OpenAI for Whisper
- Facebook AI for NLLB
- gTTS for free text-to-speech
- Your entire team for building and training this smart assistant

---

## 📝 License

MIT License — feel free to modify and use this project with proper attribution.
