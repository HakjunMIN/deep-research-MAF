# Deep Research Agent

An AI research agent system based on the Microsoft Agent Framework that conducts in-depth investigation into complex questions.

>[!NOTE]
> Code using the ag-ui protocol can be found in [feature/ag-ui](https://github.com/HakjunMIN/deep-research-MAF/tree/feature/ag-ui)

## Key Features

- **Multi-Agent Collaboration**: Planning, Research, Content, and Reflect agents work together to conduct research
- **Real-time Streaming**: Monitor agent progress in real-time
- **Various Search Sources**: Supports Google Search and arXiv paper search
- **Azure OpenAI Integration**: GPT-4-based reasoning and analysis

## Tech Stack

- **Backend**: Python 3.12+, FastAPI, Microsoft Agent Framework
- **Frontend**: React 18+, TypeScript, Vite, Tailwind CSS
- **AI**: Azure OpenAI (GPT-4)

## Getting Started

### Running the Backend

```bash
cd backend
uv sync
uv run python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The server runs at `http://localhost:8000`.

### Running the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.

## Environment Variables

Set the following environment variables:

- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint
- `AZURE_OPENAI_DEPLOYMENT`: Deployment name (e.g., gpt-4)
- `GOOGLE_API_KEY`: Google Search API key
- `GOOGLE_CSE_ID`: Google Custom Search Engine ID

## Usage

1. Enter a research question in the frontend
2. Agents collaborate to develop a research plan
3. Track real-time searching and analysis progress
4. Review comprehensive research results

## License

MIT
