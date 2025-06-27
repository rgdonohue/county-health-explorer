import { getVariableMetadata, transformValue, formatValue } from './metadata.js';

/**
 * UI Manager for County Health Explorer
 * Handles all user interface updates and interactions
 */

export class UIManager {
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
     * Format units for display
     */
    formatUnitsForDisplay(units) {
        if (!units) return '';
        
        // Clean up common unit formats
        const unitMap = {
            'percentage': '%',
            'per 100,000 population': 'per 100,000',
            'per 1,000 population': 'per 1,000',
            'per 10,000 population': 'per 10,000',
            'years': 'years',
            'days': 'days',
            'ratio': 'ratio',
            'index': 'index',
            'count': 'count',
            'rate': 'rate',
            'numeric': ''
        };
        
        return unitMap[units] || units;
    }

    /**
     * Format value for legend display
     */
    formatValueForLegend(value, dataType, units) {
        if (value === null || value === undefined || isNaN(value)) {
            return '-';
        }

        // Format based on data type and value range
        if (dataType === 'percentage' || units === 'percentage') {
            // If values are 0-1, convert to percentage
            if (value <= 1) {
                return `${(value * 100).toFixed(1)}%`;
            } else {
                return `${value.toFixed(1)}%`;
            }
        } else if (dataType === 'rate' && (units.includes('per 100,000') || units.includes('per 1,000'))) {
            // Rates should be whole numbers typically
            return value.toFixed(0);
        } else if (dataType === 'currency') {
            return `$${value.toLocaleString()}`;
        } else if (dataType === 'mortality' || units.includes('per 100,000')) {
            return value.toFixed(0);
        } else if (dataType === 'rate' || units.includes('per 1,000')) {
            return value.toFixed(0);
        } else if (units === 'years') {
            return `${value.toFixed(1)} yrs`;
        } else if (units === 'days') {
            return `${value.toFixed(1)} days`;
        } else if (value < 1) {
            return value.toFixed(3);
        } else if (value < 10) {
            return value.toFixed(2);
        } else {
            return value.toFixed(1);
        }
    }

    /**
     * Update variable description with proper context and units
     */
    updateVariableDescription(variableName, variables, stats = null) {
        if (!this.elements.variableDescription) return;

        // Get systematic metadata
        const metadata = getVariableMetadata(variableName);
        
        let description = `<strong>${metadata.displayName}</strong>`;
        
        if (metadata.units) {
            description += ` <span class="text-blue-600">(${metadata.units})</span>`;
        }
        
        if (metadata.description) {
            description += `<br><span class="text-gray-600 text-sm">${metadata.description}</span>`;
        }

        if (metadata.interpretation) {
            description += `<br><span class="text-green-600 text-xs">💡 ${metadata.interpretation}</span>`;
        }

        // Add transformation note for percentage variables
        if (metadata.transform === 'decimalToPercentage') {
            description += `<br><span class="text-purple-600 text-xs">📊 Values converted from decimals to percentages</span>`;
        }

        this.elements.variableDescription.innerHTML = description;
    }

    /**
     * Update statistics display with proper metadata context
     */
    updateStatistics(stats, currentVariable, variables) {
        if (!stats) {
            console.warn('⚠️ No statistics to display');
            return;
        }

        console.log('📊 Updating statistics display:', stats);

        // Get metadata for systematic formatting
        const metadata = getVariableMetadata(currentVariable);

        // Update individual statistics with proper formatting using metadata
        if (this.elements.statCount) {
            this.elements.statCount.textContent = stats.count?.toLocaleString() || 'N/A';
        }

        if (this.elements.statMean) {
            this.elements.statMean.textContent = formatValue(stats.mean, currentVariable);
        }

        if (this.elements.statStd) {
            this.elements.statStd.textContent = formatValue(stats.std, currentVariable);
        }

        if (this.elements.statMin) {
            this.elements.statMin.textContent = formatValue(stats.min, currentVariable);
        }

        if (this.elements.statMax) {
            this.elements.statMax.textContent = formatValue(stats.max, currentVariable);
        }

        console.log('✅ Statistics updated with metadata formatting');
    }

    /**
     * Update legend with proper metadata and context
     */
    updateLegend(choroplethData, statistics, currentVariable, variables) {
        if (!this.elements.legendContainer || !choroplethData) return;

        console.log('🏷️ Updating legend with metadata...');

        // Clear existing legend
        this.elements.legendContainer.innerHTML = '';

        // Get systematic metadata
        const metadata = getVariableMetadata(currentVariable);

        // Create legend title with variable name and units (NO "LEGEND" text)
        const legendTitle = document.createElement('h3');
        legendTitle.className = 'text-lg font-semibold mb-4 text-gray-800';
        
        // Format the title with units
        if (metadata.units) {
            legendTitle.innerHTML = `${metadata.displayName}<br><span class="text-sm font-normal text-blue-600">(${metadata.units})</span>`;
        } else {
            legendTitle.textContent = metadata.displayName;
        }
        this.elements.legendContainer.appendChild(legendTitle);

        // Get class breaks from choropleth data
        const classBreaks = choroplethData.metadata?.class_breaks || [];
        
        if (classBreaks.length < 2) {
            console.warn('⚠️ No valid class breaks for legend');
            return;
        }

        // Create color scale (using a simple blue gradient)
        const colors = [
            '#f0f9ff', // lightest blue
            '#bae6fd', // light blue  
            '#7dd3fc', // medium light blue
            '#38bdf8', // medium blue
            '#0ea5e9', // darker blue
        ];

        // Create legend items using metadata for formatting
        for (let i = 0; i < classBreaks.length - 1; i++) {
            const legendItem = document.createElement('div');
            legendItem.className = 'flex items-center mb-2';

            // Color box
            const colorBox = document.createElement('div');
            colorBox.className = 'w-4 h-4 mr-3 border border-gray-300';
            colorBox.style.backgroundColor = colors[i] || colors[colors.length - 1];
            
            // Value range using metadata formatting
            const valueRange = document.createElement('span');
            valueRange.className = 'text-sm text-gray-700';
            
            // Use metadata system for consistent formatting
            const minVal = formatValue(classBreaks[i], currentVariable);
            const maxVal = formatValue(classBreaks[i + 1], currentVariable);
            
            valueRange.textContent = `${minVal} - ${maxVal}`;

            legendItem.appendChild(colorBox);
            legendItem.appendChild(valueRange);
            this.elements.legendContainer.appendChild(legendItem);
        }

        // Add "No data" category if needed
        const noDataItem = document.createElement('div');
        noDataItem.className = 'flex items-center mb-2 mt-3';
        
        const noDataBox = document.createElement('div');
        noDataBox.className = 'w-4 h-4 mr-3 border border-gray-300';
        noDataBox.style.backgroundColor = '#f3f4f6'; // gray for no data
        
        const noDataLabel = document.createElement('span');
        noDataLabel.className = 'text-sm text-gray-500';
        noDataLabel.textContent = 'No data';
        
        noDataItem.appendChild(noDataBox);
        noDataItem.appendChild(noDataLabel);
        this.elements.legendContainer.appendChild(noDataItem);

        console.log('✅ Legend updated successfully with metadata formatting');
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