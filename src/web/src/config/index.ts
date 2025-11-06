/// <reference types="vite/client" />

export interface ApiConfig {
    baseUrl: string
}

export interface ObservabilityConfig {
    connectionString: string
}

export interface AppConfig {
    api: ApiConfig
    observability: ObservabilityConfig
}

// Async function to get configuration from Azure environment
const getConfigFromAzure = async (): Promise<{ apiBaseUrl: string }> => {
    try {
        // Try to fetch config from a config endpoint (if you create one)
        const response = await fetch('/api/config');
        if (response.ok) {
            return await response.json();
        }
    } catch (error) {
        console.warn('Could not fetch config from server:', error);
    }
    
    // Fallback logic
    if (typeof window !== 'undefined' && window.location.hostname.includes('azurewebsites.net')) {
        const hostname = window.location.hostname.replace('app-web-', 'app-api-');
        return { apiBaseUrl: `https://${hostname}` };
    }
    
    return { apiBaseUrl: 'http://localhost:3100' };
};

// Runtime function to get API base URL
const getApiBaseUrl = (): string => {
    // First try Vite environment variable (build-time)
    if (import.meta.env.VITE_API_BASE_URL) {
        return import.meta.env.VITE_API_BASE_URL;
    }
    
    // Smart detection for Azure deployments
    if (typeof window !== 'undefined' && window.location.hostname.includes('azurewebsites.net')) {
        const hostname = window.location.hostname.replace('app-web-', 'app-api-');
        return `https://${hostname}`;
    }
    
    // Fallback to localhost for development
    return 'http://localhost:3100';
};

const config: AppConfig = {
    api: {
        baseUrl: getApiBaseUrl()
    },
    observability: {
        connectionString: import.meta.env.VITE_APPLICATIONINSIGHTS_CONNECTION_STRING || ''
    }
}

// Export async function for dynamic config loading
export const getConfigAsync = async (): Promise<AppConfig> => {
    const azureConfig = await getConfigFromAzure();
    return {
        api: {
            baseUrl: azureConfig.apiBaseUrl
        },
        observability: {
            connectionString: import.meta.env.VITE_APPLICATIONINSIGHTS_CONNECTION_STRING || ''
        }
    };
};

export default config;