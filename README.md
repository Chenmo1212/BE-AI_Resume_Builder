# BE-AI_Resume_Builder

AI-powered resume optimizer backend — stateless Flask service that runs LLM pipelines on resume + job description pairs.

## Architecture: Stateless / Zero-DB

The backend is **completely stateless**. It does not connect to or require any database. All user data is managed client-side (see FE-AI_Resume_Builder).

### What the backend does
- Accepts a `POST /tasks/run` request with full context: `{ resume, task_list, ai_config }`
- Runs LangChain-based LLM pipelines to optimize resume sections
- Returns results; discards all data when the request completes
- No MongoDB, no persistent storage of any kind

### API Endpoints

#### `POST /tasks/run`
Run AI optimization on one or more resume + job pairs.

**Request body:**
```json
{
  "resume": { "basics": {...}, "work": [...], ... },
  "task_list": [{ "id": "uuid", "description": "job description text", "jobId": "optional" }],
  "ai_config": { "model": "gpt-4o", "temperature": 0.7, "api_key": "sk-...", "provider": "openai" }
}
```

**Response:**
```json
{ "message": "Task created successfully", "task_ids": ["uuid1", "uuid2"] }
```

#### `POST /tasks/results`
Poll for task completion status.

**Request body:**
```json
{ "task_ids": ["uuid1", "uuid2"] }
```

#### `POST /task/<task_id>/cancel`
Cancel a running task.

#### Deprecated (client-side storage handles these)
- `GET/POST /resumes` — resume CRUD
- `GET/POST/PUT/DELETE /job` — job CRUD

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your OPENAI_API_KEY
python app.py
```

### Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

### Security
- API key is passed per-request in `ai_config.api_key` — never stored
- No database connections required
- TLS 1.2+ required in production deployments
