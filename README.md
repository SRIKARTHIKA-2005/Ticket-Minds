# OmniChat - Multilingual Customer Support Platform

OmniChat is a real-time, cloud-deployable customer support ticket and chat system. It enables clients and support engineers to communicate seamlessly across different languages (Spanish, Tamil, Hindi, French, German, and English). 

The platform features a modern dark-themed Discord + WhatsApp hybrid interface, automatic language detection and translation, and optional AI-based sentiment and priority classification with local keyword-matching fallbacks.

---

## 🚀 Key Features

- **Role-Based Access Control**: Separate dashboards and routing policies for clients and support engineers.
- **Auto-Translation Pipeline**: Google Translate API integration (via `deep-translator`) translates client messages to English and engineer replies back to the client's language.
- **Language Detection**: Automatically determines client native language using `langdetect`.
- **Discord + WhatsApp Layout**: Clean dark UI showing ticket prioritization, sentiment badges, and translation toggle in bubbles.
- **Optional AI Insights**: Integrates with local Ollama Llama 3 model for ticket classification, with a local rule-based keyword-matching fallback if Ollama is offline.
- **Persistent Cloud Deploy Ready**: Configured for backend hosting on **Render** (using SQLite persistent disks) and frontend hosting on **Vercel**.

---

## 📂 Project Structure

```plaintext
multilingual_support_translator/
│
├── backend/
│   ├── main.py              # FastAPI app routing & database seeding
│   ├── config.py            # Environment settings parser
│   ├── database.py          # SQLAlchemy SQLite connection setup
│   ├── models.py            # SQLAlchemy models (User, Ticket, Message)
│   ├── schemas.py           # Pydantic validation schemas
│   ├── auth.py              # JWT authentication & native bcrypt hashing
│   └── translator_service.py # Translation, lang detection, & AI pipeline
│
├── frontend/
│   ├── src/
│   │   ├── components/      # UI elements & custom scrollbars
│   │   ├── pages/           # Login, Signup, ClientDashboard, EngineerDashboard
│   │   ├── context/         # AuthContext for React state & JWT retention
│   │   ├── utils/           # api.js fetching client wrapper
│   │   ├── App.jsx          # Route guards & dashboard routers
│   │   ├── index.css        # Tailwind imports & style directives
│   │   └── main.jsx
│   ├── package.json         # React & UI dependencies
│   ├── tailwind.config.js   # Tailwind v3 setup
│   ├── postcss.config.js    # PostCSS configs
│   ├── vercel.json          # SPA routing config for Vercel
│   └── vite.config.js       # Vite React compile configs
│
├── database/                # Local SQLite persistence directory
│   └── support.db           # SQLite DB file (generated on startup)
│
├── render.yaml              # Render blueprint deployment specification
├── requirements.txt         # Python backend dependencies
├── .env.example             # Environment template
└── test_api.py              # Automated API verification suite
```

---

## 🔑 Demo Quick-Login Credentials

On startup, the backend database is automatically seeded with these demo users to make testing immediate:

| Username | Password | Role | Native Language |
| :--- | :--- | :--- | :--- |
| **arun** | `password123` | Client | Tamil (தமிழ்) |
| **juan** | `password123` | Client | Spanish (Español) |
| **engineer** | `admin123` | Support Engineer | English (EN) |

---

## 🛠️ Local Installation & Setup

### Prerequisites
- Python 3.9+
- Node.js 18+
- (Optional) [Ollama](https://ollama.com/) with `llama3` pulled for advanced AI analysis.

---

### Step 1: Backend Setup
1. Navigate to the root directory and create a virtual environment:
   ```bash
   python -m venv venv
   # Activate on Windows:
   venv\Scripts\activate
   # Activate on macOS/Linux:
   source venv/bin/activate
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment variables file:
   ```bash
   copy .env.example .env
   ```
4. Start the FastAPI server:
   ```bash
   python -m uvicorn backend.main:app --reload --port 8000
   ```
   - API interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Step 2: Frontend Setup (Two Options)

#### Option A: React + Tailwind CSS Frontend
1. Open a new terminal window, navigate to the `frontend/` directory, and install npm packages:
   ```bash
   cd frontend
   npm install
   ```
2. Start the Vite React development server:
   ```bash
   npm run dev
   ```
   - Web application: http://localhost:5173

#### Option B: Streamlit Frontend
1. Open a new terminal window (ensure your python environment is active), and run:
   ```bash
   streamlit run frontend/app.py
   ```
   - Web application: http://localhost:8501

---

## 🧪 Running Integration Tests

To verify that the authentication, translation pipeline, and REST contracts function correctly:
1. Ensure the backend FastAPI server is running on `http://127.0.0.1:8000`.
2. Open a new terminal and run:
   ```bash
   python test_api.py
   ```

---

## 🌍 Cloud Deployment Instructions

### 1. Backend Deployment (Render)
1. Push this project to a **GitHub** repository.
2. In the Render Dashboard, select **New** -> **Blueprint**.
3. Link your GitHub repository. Render will automatically parse `render.yaml` and configure:
   - Web Service starting: `uvicorn backend.main:app`
   - A persistent SSD volume mounted to `/data` (sizes 1 GB, storing `/data/support.db` permanently).
   - Auto-generated `JWT_SECRET`.

### 2. Frontend Deployment (Vercel)
1. Log in to Vercel, click **Add New** -> **Project**.
2. Import your GitHub repository, setting the **Root Directory** to `frontend`.
3. Set the **Framework Preset** to `Vite`.
4. Add the following **Environment Variable**:
   - `VITE_API_URL`: The URL pointing to your Render backend API service (e.g., `https://my-backend-app.onrender.com`).
5. Click **Deploy**. Vercel will build the frontend, and compile all SPA routing routes via `vercel.json`.
