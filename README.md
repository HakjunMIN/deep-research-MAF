# Deep Research Agent

An AI research agent system based on the Microsoft Agent Framework that performs in-depth investigations for complex questions.

>[!NOTE]
> Code using the ag-ui protocol is available on [feature/ag-ui](https://github.com/HakjunMIN/deep-research-MAF/tree/feature/ag-ui)

## Key Features

- **Multi-Agent Collaboration**: Planning, Research, Content, and Reflect agents work together to conduct research
- **Real-Time Streaming**: Monitor agent progress in real time
- **Various Search Sources**: Supports Google Search and arXiv paper searches
- **Azure OpenAI Integration**: Inference and analysis based on GPT-4

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
