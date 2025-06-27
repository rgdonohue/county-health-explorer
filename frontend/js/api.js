/**
 * API Client for County Health Explorer
 * Handles all communication with the FastAPI backend
 */

class ApiClient {
    constructor(baseUrl = '/api') {
        // Use direct backend URL if we're on Live Server (port 5500)
        if (window.location.port === '5500') {
            this.baseUrl = 'http://localhost:8000/api';
        } else {
            this.baseUrl = baseUrl;
        }
        this.timeout = 10000; // 10 second timeout
    }

    /**
     * Make an HTTP request with proper error handling
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const config = {
            timeout: this.timeout,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            console.log(`🌐 API Request: ${config.method || 'GET'} ${url}`);
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);
            
            const response = await fetch(url, {
                ...config,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new ApiError(
                    errorData.error || `HTTP ${response.status}`,
                    response.status,
                    errorData.details || response.statusText
                );
            }
            
            const data = await response.json();
            console.log(`✅ API Response: ${url}`, data);
            
            return data;
            
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new ApiError('Request timeout', 408, 'The request took too long to complete');
            }
            
            if (error instanceof ApiError) {
                throw error;
            }
            
            console.error(`❌ API Error: ${url}`, error);
            throw new ApiError(
                'Network error',
                0,
                error.message || 'Failed to connect to the server'
            );
        }
    }

    /**
     * Get list of available health variables
     */
    async getVariables() {
        return await this.request('/vars');
    }

    /**
     * Get health variables grouped by categories
     */
    async getVariableCategories() {
        return await this.request('/variables/categories');
    }

    /**
     * Get variable statistics with metadata and transformations
     */
    async getVariableStats(variable) {
        try {
            console.log(`📊 Fetching transformed statistics for variable: ${variable}`);
            
            const response = await fetch(`${this.baseUrl}/stats/transformed?var=${encodeURIComponent(variable)}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            console.log(`✅ Received transformed statistics for ${variable}:`, data);
            
            return data;
            
        } catch (error) {
            console.error(`❌ Failed to fetch statistics for ${variable}:`, error);
            throw error;
        }
    }

    /**
     * Get choropleth data with metadata
     */
    async getChoropleth(variable) {
        try {
            console.log(`🗺️ Fetching choropleth data for variable: ${variable}`);
            
            const response = await fetch(`${this.baseUrl}/choropleth?var=${encodeURIComponent(variable)}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            console.log(`✅ Received choropleth data for ${variable}:`, {
                type: data.type,
                features: data.features?.length || 0,
                metadata: data.metadata
            });
            
            return data;

        } catch (error) {
            console.error(`❌ Failed to fetch choropleth data for ${variable}:`, error);
            throw error;
        }
    }

    /**
     * Get correlation between two variables
     */
    async getCorrelation(var1, var2) {
        if (!var1 || !var2) {
            throw new Error('Both variable parameters are required');
        }
        
        const vars = `${encodeURIComponent(var1)},${encodeURIComponent(var2)}`;
        return await this.request(`/corr?vars=${vars}`);
    }

    /**
     * Get details for a specific county
     */
    async getCountyDetails(fips) {
        if (!fips) {
            throw new Error('FIPS code parameter is required');
        }
        
        return await this.request(`/counties/${encodeURIComponent(fips)}`);
    }

    /**
     * Get spatial neighbors for a county
     */
    async getCountyNeighbors(fips) {
        if (!fips) {
            throw new Error('FIPS code parameter is required');
        }
        
        return await this.request(`/neighbors/${encodeURIComponent(fips)}`);
    }

    /**
     * Get Moran's I spatial autocorrelation statistic for a variable
     */
    async getMoranI(variable) {
        if (!variable) {
            throw new Error('Variable parameter is required');
        }
        
        return await this.request(`/moran?var=${encodeURIComponent(variable)}`);
    }

    /**
     * Test API connectivity
     */
    async testConnection() {
        try {
            // Use the health endpoint if available, otherwise try variables
            const response = await fetch('/health');
            if (response.ok) {
                return await response.json();
            }
            
            // Fallback to variables endpoint
            return await this.getVariables();
            
        } catch (error) {
            console.error('❌ API connection test failed:', error);
            throw new ApiError(
                'API connection failed',
                0,
                'Unable to connect to the County Health Explorer API'
            );
        }
    }

    /**
     * Get API status and health information
     */
    async getApiStatus() {
        try {
            const response = await fetch('/health');
            return await response.json();
        } catch (error) {
            console.error('❌ Failed to get API status:', error);
            throw error;
        }
    }
}

/**
 * Custom API Error class
 */
class ApiError extends Error {
    constructor(message, status = 0, details = '') {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.details = details;
    }

    /**
     * Get user-friendly error message
     */
    getUserMessage() {
        switch (this.status) {
            case 400:
                return 'Invalid request. Please check your selection and try again.';
            case 404:
                return 'The requested data was not found.';
            case 408:
                return 'Request timeout. Please check your connection and try again.';
            case 500:
                return 'Server error. Please try again later.';
            case 503:
                return 'Service temporarily unavailable. Please try again later.';
            default:
                return this.message || 'An unexpected error occurred.';
        }
    }

    /**
     * Get detailed error information for logging
     */
    getDetails() {
        return {
            message: this.message,
            status: this.status,
            details: this.details,
            name: this.name
        };
    }
}

/**
 * Utility functions for API responses
 */
const ApiUtils = {
    /**
     * Validate variable name format
     */
    isValidVariable(variable) {
        return typeof variable === 'string' && 
               variable.length > 0 && 
               /^[a-z_][a-z0-9_]*$/.test(variable);
    },

    /**
     * Validate FIPS code format
     */
    isValidFips(fips) {
        return typeof fips === 'string' && 
               /^\d{5}$/.test(fips);
    },

    /**
     * Format variable name for display
     */
    formatVariableName(variable) {
        return variable
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    },

    /**
     * Parse and validate statistics response
     */
    validateStatistics(stats) {
        const required = ['variable', 'count', 'mean', 'std', 'min', 'max'];
        const missing = required.filter(field => !(field in stats));
        
        if (missing.length > 0) {
            throw new Error(`Missing required statistics fields: ${missing.join(', ')}`);
        }
        
        return true;
    },

    /**
     * Parse and validate GeoJSON response
     */
    validateGeoJSON(geojson) {
        if (geojson.type !== 'FeatureCollection') {
            throw new Error('Invalid GeoJSON: missing FeatureCollection type');
        }
        
        if (!Array.isArray(geojson.features)) {
            throw new Error('Invalid GeoJSON: features must be an array');
        }
        
        // Validate first feature structure
        if (geojson.features.length > 0) {
            const feature = geojson.features[0];
            if (feature.type !== 'Feature') {
                throw new Error('Invalid GeoJSON: feature missing type');
            }
            
            if (!feature.properties || !feature.geometry) {
                throw new Error('Invalid GeoJSON: feature missing properties or geometry');
            }
        }
        
        return true;
    }
};

export { ApiClient, ApiError, ApiUtils }; 