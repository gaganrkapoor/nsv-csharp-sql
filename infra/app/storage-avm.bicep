@description('Storage account name')
param name string

@description('Location for the storage account')
param location string = resourceGroup().location

@description('Tags to apply to the storage account')
param tags object = {}

@description('Storage account SKU')
param skuName string = 'Standard_LRS'

@description('Storage account kind')
param kind string = 'StorageV2'

@description('Storage account access tier')
param accessTier string = 'Hot'

@description('Blob containers to create')
param containerNames array = []

@description('Enable public access to the storage account')
param allowBlobPublicAccess bool = false

@description('Minimum TLS version')
param minimumTlsVersion string = 'TLS1_2'

// Deploy the storage account
module storageAccount 'br/public:avm/res/storage/storage-account:0.15.0' = {
  name: 'storage-account'
  params: {
    name: name
    location: location
    tags: tags
    skuName: skuName
    kind: kind
    accessTier: accessTier
    allowBlobPublicAccess: allowBlobPublicAccess
    minimumTlsVersion: minimumTlsVersion
    blobServices: {
      containers: [for containerName in containerNames: {
        name: containerName
        publicAccess: 'None'
      }]
    }
  }
}

// Outputs
output storageAccountName string = storageAccount.outputs.name
output storageAccountId string = storageAccount.outputs.resourceId
output storageEndpoints object = storageAccount.outputs.serviceEndpoints