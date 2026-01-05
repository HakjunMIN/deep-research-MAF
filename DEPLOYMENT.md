# Azure Container App 배포 가이드

이 가이드는 Deep Research Agent 애플리케이션을 Azure Container Apps에 배포하는 방법을 설명합니다.

**중요**: 프론트엔드는 백엔드의 static 폴더에 포함되어 있어 하나의 Container App만 배포됩니다.

## 필수 사항

1. [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli) 설치
2. [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) 설치
3. Docker Desktop 실행 중
4. Azure OpenAI API 키 및 엔드포인트 (필수)
5. Google Search API 키 (선택사항)

## 배포 전 준비

### 1. 프론트엔드 빌드

먼저 프론트엔드를 빌드하여 백엔드 static 폴더에 복사합니다:

```bash
cd frontend
npm install
npm run build
cd ..
```

### 2. 환경 변수 파일 준비

`backend/.env` 파일을 생성하고 필수 값을 설정합니다:

```bash
cd backend
cp .env.template .env
```

`.env` 파일을 편집하여 다음 값을 설정:

```dotenv
# 필수: Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-actual-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4

# 선택사항: Google Custom Search API
GOOGLE_API_KEY=your-google-api-key
GOOGLE_CSE_ID=your-custom-search-engine-id
```

## 배포 단계

### 1. Azure 로그인

```bash
az login
azd auth login
```

### 2. 환경 초기화 (첫 배포시만)

```bash
azd init
```

프롬프트가 나오면:
- **Environment name**: 원하는 환경 이름 입력 (예: `dev`, `prod`)
- 이미 azure.yaml이 있으므로 자동으로 감지됩니다

### 3. Azure 구독 및 지역 선택

```bash
azd env set AZURE_LOCATION koreacentral  # 또는 원하는 지역
```

### 4. 환경 변수 설정

**중요**: 배포 전에 Container App의 secrets을 설정해야 합니다.

```bash
# Azure OpenAI 설정 (필수)
azd env set AZURE_OPENAI_API_KEY "your-actual-api-key"
azd env set AZURE_OPENAI_ENDPOINT "https://your-resource.openai.azure.com/"
azd env set AZURE_OPENAI_DEPLOYMENT "gpt-4"

# Google Search API 설정 (선택사항, 없으면 빈 문자열)
azd env set GOOGLE_API_KEY "your-google-api-key"
azd env set GOOGLE_CSE_ID "your-cse-id"
```

### 5. 인프라 프로비저닝 및 배포

```bash
azd up
```

이 명령은 자동으로:
- Azure 리소스 그룹 생성
- Container Registry 생성
- Container Apps Environment 생성
- Log Analytics Workspace 및 Application Insights 생성
- 백엔드 Docker 이미지 빌드 (프론트엔드 포함)
- Container Registry에 이미지 푸시
- Container App에 배포

## 유용한 명령어

### 배포된 앱 URL 확인

```bash
# 앱 URL 확인
azd env get-values | grep SERVICE_BACKEND_URI
```

또는:

```bash
# Container App URL 직접 확인
az containerapp show --name <app-name> --resource-group <resource-group> --query properties.configuration.ingress.fqdn -o tsv
```

### 로그 확인

```bash
azd monitor --logs
```

또는:

```bash
az containerapp logs show --name <app-name> --resource-group <resource-group> --follow
```

### 업데이트 배포

코드 변경 후:

```bash
# 프론트엔드 변경시 먼저 빌드
cd frontend
npm run build
cd ..

# 백엔드 배포 (프론트엔드 static 포함)
azd deploy backend
```

### 리소스 정리

모든 Azure 리소스 삭제:

```bash
azd down
```

## 생성된 리소스

이 배포는 다음 Azure 리소스를 생성합니다:

- **Resource Group**: 모든 리소스를 포함하는 컨테이너
- **Container Registry**: Docker 이미지 저장소
- **Container Apps Environment**: Container Apps를 실행하는 환경
- **Container App (Backend)**: FastAPI 백엔드 + React 프론트엔드 통합 (포트 8000)
- **Log Analytics Workspace**: 로그 및 메트릭 저장소
- **Application Insights**: 애플리케이션 모니터링

### 네트워크 구성

- 하나의 Container App으로 프론트엔드와 백엔드가 통합되어 배포됩니다
- 프론트엔드는 백엔드의 static 폴더에서 제공되므로 동일 origin입니다
- API 요청은 상대 경로(`/research/*`)를 사용합니다
- Container App은 HTTPS로 외부에 노출됩니다
- Health probes가 `/health` 엔드포인트를 모니터링합니다

## 트러블슈팅

### Docker 빌드 실패

static 폴더가 없는 경우 프론트엔드를 먼저 빌드:

```bash
cd frontend
npm install
npm run build
cd ..
```

백엔드 의존성 확인:

```bash
cd backend
uv sync
```

Docker 빌드 테스트:

```bash
cd backend
docker build -t deep-researcher-test .
```

### 배포 실패

리소스 할당량 확인:

```bash
az vm list-usage --location <region> -o table
```

### 앱이 시작되지 않음

Container App 로그 확인:

```bash
az containerapp logs show --name <app-name> --resource-group <resource-group> --tail 100 --follow
```

Health probe 상태 확인:

```bash
az containerapp revision list --name <app-name> --resource-group <resource-group> --output table
```

### 환경 변수 누락

앱이 시작되지 않으면 필수 환경 변수를 확인:

```bash
# 현재 설정된 환경 변수 확인
azd env get-values

# 필수 환경 변수 설정
azd env set AZURE_OPENAI_API_KEY "your-key"
azd env set AZURE_OPENAI_ENDPOINT "https://your-resource.openai.azure.com/"
azd env set AZURE_OPENAI_DEPLOYMENT "gpt-4"

# 재배포
azd deploy backend
```

**참고**: Container App의 secrets은 Bicep 템플릿에서 관리되므로, 환경 변수 변경 후에는 반드시 재배포가 필요합니다.

## CI/CD 설정 (선택사항)

GitHub Actions를 사용한 자동 배포:

```bash
azd pipeline config
```

이 명령은:
- GitHub 리포지토리와 연결
- 필요한 시크릿 설정
- GitHub Actions 워크플로우 생성

## 참고 문서

- [Azure Container Apps 문서](https://learn.microsoft.com/azure/container-apps/)
- [Azure Developer CLI 문서](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- [Bicep 문서](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
