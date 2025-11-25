# Study in Germany - AI Counselor MVP

A complete AI-powered counseling platform to help international students plan their studies in Germany.

## Features

- **University Search**: Browse German universities by state, search by name
- **Programme Discovery**: Find study programmes by degree type, language, field, and location
- **Immigration Helper**: Get personalized visa and residence permit advice
- **Student Profile**: Create profile, upload documents, get feasibility assessment
- **AI Counselor**: Chat with AI counselor for personalized guidance and action plans
- **Admin Panel**: Manage data, trigger scrapers, manage immigration rules

## Tech Stack

- **Backend**: Python 3, Flask
- **Database**: MongoDB
- **Frontend**: HTML, CSS, vanilla JavaScript, Bootstrap 5
- **AI**: OpenAI (ChatCompletion + Embeddings)
- **Background Jobs**: APScheduler

## Setup Instructions

### Prerequisites

- Python 3.8+
- MongoDB (local or cloud instance)
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd AI-study-abroad
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
```

5. Configure environment variables in `.env`:
```
MONGODB_URI=mongodb://localhost:27017/
DB_NAME=study_germany_db

# PRIMARY: OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free

# FALLBACK: OpenAI Configuration (required for embeddings)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
SECRET_KEY=your-secret-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
ENABLE_SCHEDULER=true
```

6. Initialize database with seed data:
```bash
python scripts/seed_immigration_rules.py
```

7. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Initial Data Setup

After starting the application:

1. Go to `/admin` and login
2. Trigger "Sync Universities" to fetch German universities from Hipolabs API
3. (Optional) Trigger "Scrape Programmes" to collect programme data
4. (Optional) Trigger "Index Universities" and "Index Programmes" to generate embeddings for RAG

## Deployment on Render.com

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set environment variables in Render dashboard:
   - `MONGODB_URI`
   - `DB_NAME`
   - `OPENAI_API_KEY`
   - `SECRET_KEY`
   - `ADMIN_USERNAME`
   - `ADMIN_PASSWORD`
   - `ENABLE_SCHEDULER=true`

4. Render will automatically use `render.yaml` for configuration
5. Add a disk volume for `/uploads` directory if needed

## Project Structure

```
project/
├── app.py                 # Main Flask application
├── config.py             # Configuration management
├── requirements.txt      # Python dependencies
├── render.yaml          # Render.com deployment config
├── api/                 # API blueprints
│   ├── universities.py
│   ├── programmes.py
│   ├── immigration.py
│   ├── profile.py
│   ├── documents.py
│   ├── assessments.py
│   ├── chat.py
│   ├── counselor.py
│   └── admin.py
├── models/              # Database models
│   └── mongo.py
├── services/            # Business logic
│   ├── assessment.py
│   ├── embeddings.py
│   └── counselor.py
├── scrapers/           # Data collection
│   ├── hipolabs_universities.py
│   └── daad_programmes.py
├── jobs/               # Background jobs
│   └── scheduler.py
├── templates/          # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── universities.html
│   ├── programmes.html
│   ├── immigration.html
│   ├── profile.html
│   ├── counselor.html
│   └── admin.html
├── static/            # Static assets
│   ├── css/
│   └── js/
├── uploads/          # Uploaded documents
└── scripts/          # Utility scripts
    └── seed_immigration_rules.py
```

## Important Disclaimers

- **Immigration Information**: All immigration and visa information is for informational purposes only and does not constitute legal advice. Always confirm with official embassies and authorities.

- **Assessments**: Feasibility assessments are informational only and do not represent admission, scholarship, or visa decisions.

- **Document Uploads**: Do not upload passports, ID cards, or bank statements. Only upload educational documents.

## License

This project is provided as-is for educational purposes.

