/**
 * County Health Explorer - Main Application Module
 * Implements Observable Plot mapping with Albers Equal Area projection
 * and API integration for dynamic health data visualization
 */

// Import modules
import { ApiClient } from './api.js';
import { MapRenderer } from './map.js';
import { UIManager } from './ui.js';
import { utils } from './utils.js';

/**
 * Central Application State Management
 * As specified in PRD: AppState object for frontend state management
 */
const AppState = {
    currentVariable: 'premature_death', // Default variable
    selectedCounty: null,
    mapLoaded: false,
    projection: 'albers-usa', // Albers Equal Area projection
    data: {
        variables: [],
        choroplethData: null,
        statistics: null,
        categories: {}
    },
    ui: {
        loading: false,
        error: null
    }
};

/**
 * Main Application Class
 */
class CountyHealthExplorer {
    constructor() {
        this.api = new ApiClient();
        this.mapRenderer = new MapRenderer();
        this.ui = new UIManager();
        
        // Bind methods to preserve context
        this.handleVariableChange = this.handleVariableChange.bind(this);
        this.handleCountyClick = this.handleCountyClick.bind(this);
        this.handleError = this.handleError.bind(this);
        
        // Initialize application
        this.init();
    }

    /**
     * Initialize the application
     */
    async init() {
        try {
            console.log('🚀 Initializing County Health Explorer...');
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Load initial data
            await this.loadInitialData();
            
            // Initialize the map with default variable
            await this.initializeMap();
            
            console.log('✅ County Health Explorer initialized successfully');
            
        } catch (error) {
            console.error('❌ Failed to initialize application:', error);
            this.handleError('Failed to initialize application. Please refresh the page.');
        }
    }

    /**
     * Set up all event listeners
     */
    setupEventListeners() {
        // Variable selection change
        const variableSelect = document.getElementById('variable-select');
        if (variableSelect) {
            variableSelect.addEventListener('change', this.handleVariableChange);
        }

        // Analysis buttons
        document.getElementById('histogram-btn')?.addEventListener('click', () => {
            this.showAnalysis('histogram');
        });
        
        document.getElementById('correlation-btn')?.addEventListener('click', () => {
            this.showAnalysis('correlation');
        });
        
        document.getElementById('spatial-btn')?.addEventListener('click', () => {
            this.showAnalysis('spatial');
        });

        // County info panel close button
        document.getElementById('close-county-info')?.addEventListener('click', () => {
            this.ui.hideCountyInfo();
            AppState.selectedCounty = null;
        });

        // Error modal close button
        document.getElementById('close-error')?.addEventListener('click', () => {
            this.ui.hideError();
        });

        // Handle window resize for responsive map
        window.addEventListener('resize', utils.debounce(() => {
            if (AppState.mapLoaded) {
                this.mapRenderer.resize();
            }
        }, 250));
    }

    /**
     * Load initial application data
     */
    async loadInitialData() {
        this.ui.setLoading(true);
        
        try {
            // Load health variables
            console.log('📊 Loading health variables...');
            const variablesResponse = await this.api.getVariables();
            AppState.data.variables = variablesResponse.variables || [];
            
            // Load variable categories
            console.log('🏷️ Loading variable categories...');
            AppState.data.categories = await this.api.getVariableCategories();
            
            // Populate variable selector
            this.ui.populateVariableSelector(AppState.data.variables, AppState.data.categories);
            
            // Set default variable if available
            if (AppState.data.variables.length > 0) {
                // Try to find premature_death, otherwise use first variable
                const defaultVar = AppState.data.variables.find(v => v.name === 'premature_death') 
                                || AppState.data.variables[0];
                AppState.currentVariable = defaultVar.name;
                
                // Update UI to reflect current selection
                const variableSelect = document.getElementById('variable-select');
                if (variableSelect) {
                    variableSelect.value = AppState.currentVariable;
                }
            }
            
        } catch (error) {
            console.error('❌ Failed to load initial data:', error);
            this.handleError('Failed to load health variables. Please check your connection.');
            throw error;
        } finally {
            this.ui.setLoading(false);
        }
    }

    /**
     * Initialize the map with the default variable
     */
    async initializeMap() {
        if (!AppState.currentVariable) {
            console.warn('⚠️ No variable selected for map initialization');
            return;
        }

        try {
            console.log(`🗺️ Initializing map with variable: ${AppState.currentVariable}`);
            
            // Load choropleth data for current variable
            await this.loadChoroplethData(AppState.currentVariable);
            
            // Render the map
            await this.renderMap();
            
            // Load and display statistics
            await this.loadStatistics(AppState.currentVariable);
            
            // Enable analysis buttons
            this.ui.enableAnalysisButtons();
            
            AppState.mapLoaded = true;
            
        } catch (error) {
            console.error('❌ Failed to initialize map:', error);
            this.handleError('Failed to load map data. Please try again.');
        }
    }

    /**
     * Handle variable selection change
     */
    async handleVariableChange(event) {
        const newVariable = event.target.value;
        
        if (!newVariable || newVariable === AppState.currentVariable) {
            return;
        }

        console.log(`🔄 Changing variable from ${AppState.currentVariable} to ${newVariable}`);
        
        try {
            this.ui.setLoading(true);
            
            // Update app state
            AppState.currentVariable = newVariable;
            AppState.selectedCounty = null; // Clear selected county
            
            // Hide county info if visible
            this.ui.hideCountyInfo();
            
            // Load new data
            await this.loadChoroplethData(newVariable);
            await this.loadStatistics(newVariable);
            
            // Update the map
            await this.renderMap();
            
            // Update variable description
            this.ui.updateVariableDescription(newVariable, AppState.data.variables);
            
        } catch (error) {
            console.error('❌ Failed to change variable:', error);
            this.handleError(`Failed to load data for ${newVariable}. Please try again.`);
        } finally {
            this.ui.setLoading(false);
        }
    }

    /**
     * Load choropleth data for a variable
     */
    async loadChoroplethData(variable) {
        console.log(`📍 Loading choropleth data for ${variable}...`);
        
        try {
            const data = await this.api.getChoroplethData(variable);
            AppState.data.choroplethData = data;
            
            console.log(`✅ Loaded ${data.features?.length || 0} county features`);
            
        } catch (error) {
            console.error(`❌ Failed to load choropleth data for ${variable}:`, error);
            throw error;
        }
    }

    /**
     * Load statistics for a variable
     */
    async loadStatistics(variable) {
        console.log(`📈 Loading statistics for ${variable}...`);
        
        try {
            const stats = await this.api.getStatistics(variable);
            AppState.data.statistics = stats;
            
            // Update UI with statistics
            this.ui.updateStatistics(stats);
            
            console.log(`✅ Loaded statistics for ${variable}:`, stats);
            
        } catch (error) {
            console.error(`❌ Failed to load statistics for ${variable}:`, error);
            // Don't throw - statistics are non-critical for map display
        }
    }

    /**
     * Render the map with current data
     */
    async renderMap() {
        if (!AppState.data.choroplethData) {
            console.warn('⚠️ No choropleth data available for map rendering');
            return;
        }

        console.log('🎨 Rendering map with Observable Plot...');
        
        try {
            // Render the choropleth map
            await this.mapRenderer.renderChoropleth(
                AppState.data.choroplethData,
                {
                    variable: AppState.currentVariable,
                    projection: AppState.projection,
                    onCountyClick: this.handleCountyClick,
                    statistics: AppState.data.statistics
                }
            );
            
            // Update legend
            this.ui.updateLegend(AppState.data.choroplethData, AppState.data.statistics);
            
            console.log('✅ Map rendered successfully');
            
        } catch (error) {
            console.error('❌ Failed to render map:', error);
            throw error;
        }
    }

    /**
     * Handle county click/selection
     */
    async handleCountyClick(countyData) {
        console.log('🖱️ County clicked:', countyData);
        
        try {
            AppState.selectedCounty = countyData;
            
            // Show county information
            await this.ui.showCountyInfo(countyData, AppState.currentVariable);
            
            // Optionally load additional county details from API
            if (countyData.properties?.fips) {
                const details = await this.api.getCountyDetails(countyData.properties.fips);
                this.ui.updateCountyInfo(details);
            }
            
        } catch (error) {
            console.error('❌ Failed to handle county click:', error);
            // Don't show error to user for this non-critical operation
        }
    }

    /**
     * Show analysis charts
     */
    async showAnalysis(type) {
        console.log(`📊 Showing ${type} analysis...`);
        
        try {
            this.ui.setLoading(true);
            
            // Implementation will be expanded in future milestones
            switch (type) {
                case 'histogram':
                    await this.showHistogram();
                    break;
                case 'correlation':
                    await this.showCorrelation();
                    break;
                case 'spatial':
                    await this.showSpatialStats();
                    break;
            }
            
        } catch (error) {
            console.error(`❌ Failed to show ${type} analysis:`, error);
            this.handleError(`Failed to load ${type} analysis. Please try again.`);
        } finally {
            this.ui.setLoading(false);
        }
    }

    /**
     * Show histogram analysis (placeholder for future implementation)
     */
    async showHistogram() {
        console.log('📊 Histogram analysis - placeholder for Milestone 4');
        this.ui.showNotification('Histogram analysis coming in Milestone 4!');
    }

    /**
     * Show correlation analysis (placeholder for future implementation)
     */
    async showCorrelation() {
        console.log('📈 Correlation analysis - placeholder for Milestone 4');
        this.ui.showNotification('Correlation analysis coming in Milestone 4!');
    }

    /**
     * Show spatial statistics (placeholder for future implementation)
     */
    async showSpatialStats() {
        console.log('🌐 Spatial statistics - placeholder for Milestone 4');
        this.ui.showNotification('Spatial statistics coming in Milestone 4!');
    }

    /**
     * Handle application errors
     */
    handleError(message) {
        console.error('🚨 Application error:', message);
        AppState.ui.error = message;
        this.ui.showError(message);
    }

    /**
     * Get current application state (for debugging)
     */
    getState() {
        return { ...AppState };
    }
}

/**
 * Initialize application when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('🌍 County Health Explorer - Initializing...');
    
    // Create global app instance for debugging
    window.healthExplorer = new CountyHealthExplorer();
});

// Export for testing
export { CountyHealthExplorer, AppState }; 