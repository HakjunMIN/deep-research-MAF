# Deep Research Agent

Microsoft Agent Framework 기반의 AI 리서치 에이전트 시스템으로, 복잡한 질문에 대한 심층 조사를 수행합니다. 프론트와 백엔드 프로토콜은 AG-UI를 사용합니다.

## 주요 기능

- **Multi-Agent 협업**: Planning, Research, Content, Reflect 에이전트가 협력하여 연구 수행
- **실시간 스트리밍**: 에이전트 진행 상황을 실시간으로 확인 (AG-UI 프로토콜)
- **다양한 검색 소스**: Google Search, arXiv 논문 검색 지원
- **Azure OpenAI 통합**: GPT-4 기반 추론 및 분석

## 기술 스택

- **Backend**: Python 3.12+, FastAPI, Microsoft Agent Framework
- **Frontend**: React 18+, TypeScript, Vite, Tailwind CSS
- **AI**: Azure OpenAI (GPT-4)

## 시작하기

### 1. 환경 설정

백엔드 디렉토리에 `.env` 파일을 생성하고 필요한 환경 변수를 설정합니다 (아래 환경 변수 섹션 참조).

### 2. Frontend 빌드

```bash
cd frontend
npm install
npm run build
```

빌드된 파일은 자동으로 `backend/static` 폴더에 복사됩니다.

### 3. Backend 실행

```bash
cd backend
uv sync
uv run python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

애플리케이션은 `http://localhost:8000`에서 실행됩니다.

## AG-UI 스트리밍

이 프로젝트는 **AG-UI 프로토콜(Server-Sent Events, SSE)** 기반 스트리밍을 지원합니다.

- 스트리밍 엔드포인트: `POST /agui` (요청 헤더 `Accept: text/event-stream`)
- 프론트엔드 UI는 `/agui`를 통해 툴 콜 진행 상황과 최종 답변 텍스트를 스트리밍으로 수신합니다.

참고: 동기/레거시 API 엔드포인트(`/research`, `/research/stream`)도 함께 제공됩니다.

### Frontend 개발 모드 (선택사항)

프론트엔드 개발 시에만 별도 개발 서버를 실행할 수 있습니다:

```bash
cd frontend
npm run dev
```

개발 서버는 `http://localhost:5173`에서 실행되며, 백엔드 API는 `http://localhost:8000`을 호출합니다.

## 환경 변수

다음 환경 변수를 설정해야 합니다:

- `AZURE_OPENAI_API_KEY`: Azure OpenAI API 키
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI 엔드포인트
- `AZURE_OPENAI_DEPLOYMENT_NAME`: 배포 이름 (예: gpt-4o)
- `AZURE_OPENAI_API_VERSION`: API 버전 (선택, 기본값 있음)
- `GOOGLE_API_KEY`: Google Search API 키
- `GOOGLE_CSE_ID`: Google Custom Search Engine ID

프론트엔드에서 API 주소를 분리하고 싶다면 아래도 사용할 수 있습니다:

- `VITE_API_URL`: 백엔드 베이스 URL (예: `http://localhost:8000`, 기본값은 same-origin)

## 사용 방법

1. 브라우저에서 `http://localhost:8000` 접속
2. 연구하고 싶은 질문 입력
3. 에이전트들이 협력하여 연구 계획 수립
4. 실시간으로 검색 및 분석 과정 확인
5. 종합된 연구 결과 확인

## 배포

Azure Container Apps에 배포할 수 있습니다. 자세한 내용은 [DEPLOYMENT.md](DEPLOYMENT.md)를 참조하세요.

## 라이선스

MIT
