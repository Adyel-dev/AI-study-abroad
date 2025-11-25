# Quick Start Guide

## Prerequisites Check

1. **Python 3.8+** installed
2. **MongoDB** running (local or cloud connection string ready)
3. **OpenAI API Key** obtained from https://platform.openai.com/

## Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
MONGODB_URI=mongodb://localhost:27017/
DB_NAME=study_germany_db
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
SECRET_KEY=your-secret-key-here-change-in-production
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
ENABLE_SCHEDULER=true
```

### 3. Initialize Database

Seed initial immigration rules:

```bash
python scripts/seed_immigration_rules.py
```

### 4. Start the Application

```bash
python app.py
```

The application will start at `http://localhost:5000`

## First Steps After Starting

### 1. Access Admin Panel

- Navigate to `/admin`
- Login with credentials from `.env` (default: admin/admin)

### 2. Sync Initial Data

In the admin panel:
- Click "Sync Universities" to fetch German universities
- (Optional) Click "Index Universities" to generate embeddings for RAG
- (Optional) Trigger programme scraping when ready

### 3. Test the Application

- Visit the home page at `/`
- Create a profile at `/profile`
- Try the AI counselor at `/counselor`
- Search universities at `/universities`
- Browse programmes at `/programmes`

## Important Notes

- **OpenAI API**: Make sure you have sufficient API credits
- **MongoDB**: Database will be created automatically on first connection
- **Uploads**: Documents are stored in `/uploads/` directory
- **Scheduler**: Background jobs run daily (universities) and weekly (programmes)

## Troubleshooting

### MongoDB Connection Error
- Check if MongoDB is running
- Verify MONGODB_URI in `.env` is correct

### OpenAI API Error
- Verify OPENAI_API_KEY is set correctly
- Check your OpenAI account has available credits

### Import Errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Activate virtual environment if using one

## Production Deployment

See `README.md` for Render.com deployment instructions.

