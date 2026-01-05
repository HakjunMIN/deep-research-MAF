targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment that can be used as part of naming resource convention')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@secure()
@description('Azure OpenAI API Key')
param azureOpenAiApiKey string = ''

@description('Azure OpenAI Endpoint')
param azureOpenAiEndpoint string = ''

@description('Azure OpenAI Deployment Name')
param azureOpenAiDeployment string = ''

@secure()
@description('Google API Key')
param googleApiKey string = ''

@description('Google Custom Search Engine ID')
param googleCseId string = ''

// Variables
var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

// Resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

// Container Apps Environment
module containerAppsEnvironment './core/host/container-apps-environment.bicep' = {
  name: 'container-apps-environment'
  scope: rg
  params: {
    name: '${abbrs.appManagedEnvironments}${resourceToken}'
    location: location
    tags: tags
    logAnalyticsWorkspaceName: monitoring.outputs.logAnalyticsWorkspaceName
  }
}

// Backend Container App (includes frontend static files)
module backend './core/host/container-app.bicep' = {
  name: 'backend'
  scope: rg
  params: {
    name: '${abbrs.appContainerApps}backend-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'backend' })
    containerAppsEnvironmentName: containerAppsEnvironment.outputs.name
    containerRegistryName: containerRegistry.outputs.name
    containerName: 'backend'
    targetPort: 8000
    env: [
      {
        name: 'CORS_ORIGINS'
        value: '*'
      }
      {
        name: 'AZURE_OPENAI_API_KEY'
        secretRef: 'azure-openai-api-key'
      }
      {
        name: 'AZURE_OPENAI_ENDPOINT'
        secretRef: 'azure-openai-endpoint'
      }
      {
        name: 'AZURE_OPENAI_DEPLOYMENT'
        secretRef: 'azure-openai-deployment'
      }
      {
        name: 'GOOGLE_API_KEY'
        secretRef: 'google-api-key'
      }
      {
        name: 'GOOGLE_CSE_ID'
        secretRef: 'google-cse-id'
      }
    ]
    secrets: !empty(azureOpenAiApiKey) ? [
      {
        name: 'azure-openai-api-key'
        value: azureOpenAiApiKey
      }
      {
        name: 'azure-openai-endpoint'
        value: azureOpenAiEndpoint
      }
      {
        name: 'azure-openai-deployment'
        value: azureOpenAiDeployment
      }
      {
        name: 'google-api-key'
        value: googleApiKey
      }
      {
        name: 'google-cse-id'
        value: googleCseId
      }
    ] : []
  }
}

// Container Registry
module containerRegistry './core/host/container-registry.bicep' = {
  name: 'container-registry'
  scope: rg
  params: {
    name: '${abbrs.containerRegistryRegistries}${resourceToken}'
    location: location
    tags: tags
  }
}

// Monitoring with Log Analytics
module monitoring './core/monitor/monitoring.bicep' = {
  name: 'monitoring'
  scope: rg
  params: {
    location: location
    tags: tags
    logAnalyticsName: '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    applicationInsightsName: '${abbrs.insightsComponents}${resourceToken}'
  }
}

// Output variables
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = rg.name

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerRegistry.outputs.name

output SERVICE_BACKEND_URI string = backend.outputs.uri
output SERVICE_BACKEND_IMAGE_NAME string = backend.outputs.imageName
