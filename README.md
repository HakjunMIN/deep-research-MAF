# Deep Research Agent

Microsoft Agent Framework 기반의 AI 리서치 에이전트 시스템으로, 복잡한 질문에 대한 심층 조사를 수행합니다.

>[!NOTE]
> ag-ui 프로토콜을 사용한 코드는 [feature/ag-ui](https://github.com/HakjunMIN/deep-research-MAF/tree/feature/ag-ui)

## 주요 기능

- **Multi-Agent 협업**: Planning, Research, Content, Reflect 에이전트가 협력하여 연구 수행
- **실시간 스트리밍**: 에이전트 진행 상황을 실시간으로 확인
- **다양한 검색 소스**: Google Search, arXiv 논문 검색 지원
- **Azure OpenAI 통합**: GPT-4 기반 추론 및 분석

#기술 스택

- **Backend**: Python 3.12+, FastAPI, Microsoft Agent Framework
- **Frontend**: React 18+, TypeScript, Vite, Tailwind CSS
- **AI**: Azure OpenAI (GPT-4)

# 시작하기

### Backend 실행

```bash
cd backend
uv sync
uv run python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

서버는 `http://localhost:8000`에서 실행됩니다.

### Frontend 실행

```bash
cd frontend
npm install
npm run dev
```

프론트엔드는 `http://localhost:5173`에서 실행됩니다.

## 환경 변수

다음 환경 변수를 설정해야 합니다:

- `AZURE_OPENAI_API_KEY`: Azure OpenAI API 키
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI 엔드포인트
- `AZURE_OPENAI_DEPLOYMENT`: 배포 이름 (예: gpt-4)
- `GOOGLE_API_KEY`: Google Search API 키
- `GOOGLE_CSE_ID`: Google Custom Search Engine ID

## 사용 방법

1. 프론트엔드에서 연구하고 싶은 질문 입력
2. 에이전트들이 협력하여 연구 계획 수립
3. 실시간으로 검색 및 분석 과정 확인
4. 종합된 연구 결과 확인

## 라이선스

MIT


## 테스트 문서

이 프로젝트는 백엔드와 프론트엔드에 대한 포괄적인 단위 테스트 커버리지를 지원합니다.

### Backend Testing
- 프레임워크: **pytest**, **pytest-asyncio**, **pytest-mock**
- 커버리지 명령어:
  ```bash
  cd backend
  uv run pytest --cov=src --cov-report=term-missing
  ```
- 최소 코드 커버리지: **70%**

### Frontend Testing
- 프레임워크: **Vitest**, **React Testing Library**, **MSW**
- 테스트 실행 명령어:
  ```bash
  cd frontend
  npm run test -- --coverage
  ```
- 최소 코드 커버리지: **70%**

### CI/CD 통합
테스트는 CI/CD 파이프라인에서 자동으로 실행되며, PR 병합 전 모든 테스트가 통과해야 합니다.
