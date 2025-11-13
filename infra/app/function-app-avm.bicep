@description('Function app name')
param name string

@description('Location for the function app')
param location string = resourceGroup().location

@description('Tags to apply to the function app')
param tags object = {}

@description('App Service Plan resource ID')
param appServicePlanId string

@description('Storage connection string')
param storageConnectionString string

@description('Application Insights resource ID')
param appInsightResourceId string = ''

@description('Key Vault endpoint')
param keyVaultEndpoint string = ''

@description('Function app settings')
param functionAppSettings object = {}

// Deploy the function app
module functionApp 'br/public:avm/res/web/site:0.10.0' = {
  name: 'function-app'
  params: {
    name: name
    location: location
    tags: tags
    kind: 'functionapp,linux'
    serverFarmResourceId: appServicePlanId
    managedIdentities: {
      systemAssigned: true
    }
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      functionAppScaleLimit: 200
      minimumElasticInstanceCount: 0
    }
    appSettingsKeyValuePairs: union(functionAppSettings, {
      AzureWebJobsStorage: storageConnectionString
      FUNCTIONS_EXTENSION_VERSION: '~4'
      FUNCTIONS_WORKER_RUNTIME: 'python'
      APPINSIGHTS_INSTRUMENTATIONKEY: !empty(appInsightResourceId) ? reference(appInsightResourceId, '2020-02-02').InstrumentationKey : ''
      APPLICATIONINSIGHTS_CONNECTION_STRING: !empty(appInsightResourceId) ? reference(appInsightResourceId, '2020-02-02').ConnectionString : ''
      AZURE_KEY_VAULT_ENDPOINT: keyVaultEndpoint
      SCM_DO_BUILD_DURING_DEPLOYMENT: 'true'
    })
  }
}

// Outputs
output functionAppName string = functionApp.outputs.name
output functionAppId string = functionApp.outputs.resourceId
output functionAppIdentityPrincipalId string = functionApp.outputs.systemAssignedMIPrincipalId
output functionAppUrl string = 'https://${functionApp.outputs.defaultHostname}'