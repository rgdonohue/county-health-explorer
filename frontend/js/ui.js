/**
 * UI Manager for County Health Explorer
 * Handles all user interface updates and interactions
 */

class UIManager {
    constructor() {
        this.elements = this.getUIElements();
        this.currentNotification = null;
    }

    /**
     * Get references to UI elements
     */
    getUIElements() {
        return {
            variableSelect: document.getElementById('variable-select'),
            variableDescription: document.getElementById('variable-description'),
            loadingIndicator: document.getElementById('loading-indicator'),
            mapPlot: document.getElementById('map-plot'),
            
            // Statistics elements
            statCount: document.getElementById('stat-count'),
            statMean: document.getElementById('stat-mean'),
            statStd: document.getElementById('stat-std'),
            statMin: document.getElementById('stat-min'),
            statMax: document.getElementById('stat-max'),
            
            // Legend elements
            legendContainer: document.getElementById('legend-container'),
            
            // County info elements
            countyInfo: document.getElementById('county-info'),
            countyName: document.getElementById('county-name'),
            countyState: document.getElementById('county-state'),
            countyStats: document.getElementById('county-stats'),
            closeCountyInfo: document.getElementById('close-county-info'),
            
            // Analysis buttons
            histogramBtn: document.getElementById('histogram-btn'),
            correlationBtn: document.getElementById('correlation-btn'),
            spatialBtn: document.getElementById('spatial-btn'),
            
            // Error modal
            errorModal: document.getElementById('error-modal'),
            errorMessage: document.getElementById('error-message'),
            closeError: document.getElementById('close-error'),
            
            // Charts section
            chartsSection: document.getElementById('charts-section')
        };
    }

    /**
     * Set loading state
     */
    setLoading(isLoading) {
        if (this.elements.loadingIndicator) {
            if (isLoading) {
                this.elements.loadingIndicator.classList.remove('hidden');
            } else {
                this.elements.loadingIndicator.classList.add('hidden');
            }
        }
    }

    /**
     * Populate variable selector with categorized options
     */
    populateVariableSelector(variables, categories) {
        if (!this.elements.variableSelect || !variables.length) {
            console.warn('⚠️ Cannot populate variable selector');
            return;
        }

        console.log('🎛️ Populating variable selector with', variables.length, 'variables');

        // Clear existing options
        this.elements.variableSelect.innerHTML = '';

        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Select a health variable...';
        defaultOption.disabled = true;
        this.elements.variableSelect.appendChild(defaultOption);

        // Group variables by category
        const categoryGroups = this.groupVariablesByCategory(variables, categories);
        
        // Add options by category
        Object.entries(categoryGroups).forEach(([categoryName, categoryVars]) => {
            if (categoryVars.length > 0) {
                // Add category optgroup
                const optgroup = document.createElement('optgroup');
                optgroup.label = this.formatCategoryName(categoryName);
                
                categoryVars.forEach(variable => {
                    const option = document.createElement('option');
                    option.value = variable.name;
                    option.textContent = variable.display_name || this.formatVariableName(variable.name);
                    optgroup.appendChild(option);
                });
                
                this.elements.variableSelect.appendChild(optgroup);
            }
        });

        // If no categories, add all variables to a general group
        if (Object.keys(categoryGroups).length === 0) {
            variables.forEach(variable => {
                const option = document.createElement('option');
                option.value = variable.name;
                option.textContent = variable.display_name || this.formatVariableName(variable.name);
                this.elements.variableSelect.appendChild(option);
            });
        }
    }

    /**
     * Group variables by category
     */
    groupVariablesByCategory(variables, categories) {
        const groups = {};
        
        // Initialize category groups
        Object.keys(categories || {}).forEach(categoryName => {
            groups[categoryName] = [];
        });

        // Add uncategorized group
        groups['other'] = [];

        // Categorize variables
        variables.forEach(variable => {
            let assigned = false;
            
            // Check each category for this variable
            Object.entries(categories || {}).forEach(([categoryName, categoryVars]) => {
                if (categoryVars.some(catVar => catVar.name === variable.name)) {
                    groups[categoryName].push(variable);
                    assigned = true;
                }
            });
            
            // If not categorized, add to 'other'
            if (!assigned) {
                groups['other'].push(variable);
            }
        });

        // Remove empty categories
        Object.keys(groups).forEach(key => {
            if (groups[key].length === 0) {
                delete groups[key];
            }
        });

        return groups;
    }

    /**
     * Format category name for display
     */
    formatCategoryName(categoryName) {
        const categoryDisplayNames = {
            'mortality': '💀 Mortality',
            'behavioral': '🚬 Behavioral Factors',
            'clinical': '🏥 Clinical Care',
            'social': '🏘️ Social & Economic',
            'physical_environment': '🌍 Environment',
            'demographics': '👥 Demographics',
            'other': '📊 Other Indicators'
        };
        
        return categoryDisplayNames[categoryName] || 
               categoryName.charAt(0).toUpperCase() + categoryName.slice(1).replace(/_/g, ' ');
    }

    /**
     * Format variable name for display
     */
    formatVariableName(variableName) {
        return variableName
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    /**
     * Update variable description
     */
    updateVariableDescription(variableName, variables) {
        if (!this.elements.variableDescription) return;

        const variable = variables.find(v => v.name === variableName);
        
        if (variable && variable.description) {
            this.elements.variableDescription.textContent = variable.description;
            this.elements.variableDescription.style.display = 'block';
        } else {
            // Provide default description based on variable name
            const description = this.getDefaultDescription(variableName);
            this.elements.variableDescription.textContent = description;
            this.elements.variableDescription.style.display = description ? 'block' : 'none';
        }
    }

    /**
     * Get default description for a variable
     */
    getDefaultDescription(variableName) {
        const descriptions = {
            'premature_death': 'Years of potential life lost before age 75 per 100,000 population',
            'adult_obesity': 'Percentage of adults with a BMI >= 30',
            'adult_smoking': 'Percentage of adults who are current smokers',
            'physical_inactivity': 'Percentage of adults aged 20 and over reporting no leisure-time physical activity',
            'excessive_drinking': 'Percentage of adults reporting binge or heavy drinking'
        };
        
        return descriptions[variableName] || '';
    }

    /**
     * Update statistics display
     */
    updateStatistics(stats) {
        if (!stats) return;

        console.log('📊 Updating statistics display:', stats);

        // Update count
        if (this.elements.statCount) {
            this.elements.statCount.textContent = stats.count?.toLocaleString() || '-';
        }

        // Update mean
        if (this.elements.statMean) {
            this.elements.statMean.textContent = stats.mean ? 
                Number(stats.mean).toFixed(2) : '-';
        }

        // Update standard deviation
        if (this.elements.statStd) {
            this.elements.statStd.textContent = stats.std ? 
                Number(stats.std).toFixed(2) : '-';
        }

        // Update minimum
        if (this.elements.statMin) {
            this.elements.statMin.textContent = stats.min ? 
                Number(stats.min).toFixed(2) : '-';
        }

        // Update maximum
        if (this.elements.statMax) {
            this.elements.statMax.textContent = stats.max ? 
                Number(stats.max).toFixed(2) : '-';
        }
    }

    /**
     * Update legend based on choropleth data
     */
    updateLegend(choroplethData, statistics) {
        if (!this.elements.legendContainer || !choroplethData) return;

        console.log('🏷️ Updating legend...');

        // Clear existing legend
        this.elements.legendContainer.innerHTML = '';

        // Get data values for legend
        const values = choroplethData.features
            .map(f => f.properties?.value)
            .filter(v => v !== null && v !== undefined && !isNaN(v));

        if (values.length === 0) {
            this.elements.legendContainer.innerHTML = '<p class="text-gray-500">No data available</p>';
            return;
        }

        // Calculate quantile breaks
        const sortedValues = values.sort(d3.ascending);
        const quantiles = [0, 0.2, 0.4, 0.6, 0.8, 1.0];
        const breaks = quantiles.map(q => d3.quantile(sortedValues, q));

        // Colors (matching map renderer)
        const colors = [
            '#f0f9ff', '#e0f2fe', '#bae6fd', '#7dd3fc',
            '#38bdf8', '#0ea5e9', '#0284c7'
        ];

        // Create legend items
        for (let i = 0; i < breaks.length - 1; i++) {
            const legendItem = document.createElement('div');
            legendItem.className = 'legend-item';

            const colorBox = document.createElement('div');
            colorBox.className = 'legend-color';
            colorBox.style.backgroundColor = colors[i];

            const label = document.createElement('span');
            label.className = 'legend-label';
            
            const minVal = breaks[i];
            const maxVal = breaks[i + 1];
            label.textContent = `${minVal?.toFixed(1)} - ${maxVal?.toFixed(1)}`;

            legendItem.appendChild(colorBox);
            legendItem.appendChild(label);
            this.elements.legendContainer.appendChild(legendItem);
        }

        // Add no data legend item
        const noDataItem = document.createElement('div');
        noDataItem.className = 'legend-item';

        const noDataColor = document.createElement('div');
        noDataColor.className = 'legend-color';
                    noDataColor.style.backgroundColor = '#f8fafc';

        const noDataLabel = document.createElement('span');
        noDataLabel.className = 'legend-label';
        noDataLabel.textContent = 'No data';

        noDataItem.appendChild(noDataColor);
        noDataItem.appendChild(noDataLabel);
        this.elements.legendContainer.appendChild(noDataItem);
    }

    /**
     * Show county information panel
     */
    async showCountyInfo(countyData, currentVariable) {
        if (!this.elements.countyInfo || !countyData?.properties) return;

        console.log('ℹ️ Showing county info:', countyData.properties);

        const props = countyData.properties;

        // Update county name and state
        if (this.elements.countyName) {
            this.elements.countyName.textContent = props.county_name || 'Unknown County';
        }

        if (this.elements.countyState) {
            this.elements.countyState.textContent = props.state_name || props.state || 'Unknown State';
        }

        // Update county statistics
        if (this.elements.countyStats) {
            this.elements.countyStats.innerHTML = '';

            // Show current variable value
            if (props.value !== null && props.value !== undefined) {
                const statDiv = document.createElement('div');
                statDiv.className = 'county-stat-item';
                statDiv.innerHTML = `
                    <strong>${this.formatVariableName(currentVariable)}:</strong>
                    <span>${this.formatValue(props.value, currentVariable)}</span>
                `;
                this.elements.countyStats.appendChild(statDiv);
            }

            // Show FIPS code if available
            if (props.fips) {
                const fipsDiv = document.createElement('div');
                fipsDiv.className = 'county-stat-item text-sm text-gray-600';
                fipsDiv.innerHTML = `<strong>FIPS:</strong> ${props.fips}`;
                this.elements.countyStats.appendChild(fipsDiv);
            }
        }

        // Show the panel
        this.elements.countyInfo.classList.remove('hidden');
    }

    /**
     * Update county info with additional details
     */
    updateCountyInfo(countyDetails) {
        if (!this.elements.countyStats || !countyDetails) return;

        // Add any additional county details from API
        console.log('🔄 Updating county info with details:', countyDetails);
        
        // Implementation can be expanded based on API response structure
    }

    /**
     * Hide county information panel
     */
    hideCountyInfo() {
        if (this.elements.countyInfo) {
            this.elements.countyInfo.classList.add('hidden');
        }
    }

    /**
     * Format value for display
     */
    formatValue(value, variable) {
        if (value === null || value === undefined) return 'N/A';
        
        // Format based on variable type
        if (variable && (variable.includes('rate') || variable.includes('percent') || variable.includes('obesity'))) {
            return `${Number(value).toFixed(1)}%`;
        }
        
        if (variable && variable.includes('death')) {
            return Number(value).toLocaleString();
        }
        
        // Default formatting
        if (Number.isInteger(value)) {
            return value.toLocaleString();
        }
        
        return Number(value).toFixed(2);
    }

    /**
     * Enable analysis buttons
     */
    enableAnalysisButtons() {
        [this.elements.histogramBtn, this.elements.correlationBtn, this.elements.spatialBtn]
            .forEach(btn => {
                if (btn) {
                    btn.disabled = false;
                }
            });
    }

    /**
     * Show error modal
     */
    showError(message) {
        if (this.elements.errorModal && this.elements.errorMessage) {
            this.elements.errorMessage.textContent = message;
            this.elements.errorModal.classList.remove('hidden');
        }
    }

    /**
     * Hide error modal
     */
    hideError() {
        if (this.elements.errorModal) {
            this.elements.errorModal.classList.add('hidden');
        }
    }

    /**
     * Show notification (temporary message)
     */
    showNotification(message, duration = 3000) {
        // Remove existing notification
        if (this.currentNotification) {
            this.currentNotification.remove();
        }

        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--primary-color);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: var(--shadow-lg);
            z-index: 1000;
            transition: all 0.3s ease;
            max-width: 300px;
        `;
        notification.textContent = message;

        document.body.appendChild(notification);
        this.currentNotification = notification;

        // Auto-hide after duration
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.opacity = '0';
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => notification.remove(), 300);
            }
            if (this.currentNotification === notification) {
                this.currentNotification = null;
            }
        }, duration);
    }

    /**
     * Show charts section
     */
    showCharts() {
        if (this.elements.chartsSection) {
            this.elements.chartsSection.classList.remove('hidden');
        }
    }

    /**
     * Hide charts section
     */
    hideCharts() {
        if (this.elements.chartsSection) {
            this.elements.chartsSection.classList.add('hidden');
        }
    }
}

export { UIManager }; 