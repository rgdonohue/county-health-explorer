/**
 * Map Renderer using Observable Plot with Albers Equal Area Projection
 * Implements choropleth mapping for County Health Explorer
 */

class MapRenderer {
    constructor() {
        this.currentPlot = null;
        this.mapContainer = document.getElementById('map-plot');
        this.projection = d3.geoAlbersUsa(); // Albers Equal Area projection
        this.colorScale = null;
        this.hoveredCounty = null;
        this.onCountyClick = null;
        
        // Map configuration
        this.config = {
            width: 800,
            height: 500,
            margin: { top: 20, right: 20, bottom: 20, left: 20 },
            strokeWidth: 0.5,
            strokeColor: '#ffffff',
            hoveredStrokeWidth: 2,
            hoveredStrokeColor: '#2563eb'
        };
        
        this.updateDimensions();
    }

    /**
     * Update map dimensions based on container size
     */
    updateDimensions() {
        if (!this.mapContainer) return;
        
        const containerRect = this.mapContainer.getBoundingClientRect();
        this.config.width = Math.max(400, containerRect.width - 40);
        this.config.height = Math.max(300, Math.min(600, this.config.width * 0.625));
    }

    /**
     * Create color scale for choropleth mapping
     */
    createColorScale(data, statistics) {
        if (!data?.features?.length) {
            console.warn('⚠️ No data features for color scale');
            return null;
        }

        // Extract values and calculate quantiles for class breaks
        const values = data.features
            .map(f => f.properties?.value)
            .filter(v => v !== null && v !== undefined && !isNaN(v));

        if (values.length === 0) {
            console.warn('⚠️ No valid values for color scale');
            return null;
        }

        // Use quantile-based classification (as specified in PRD)
        const quantiles = [0, 0.2, 0.4, 0.6, 0.8, 1.0];
        const breaks = quantiles.map(q => d3.quantile(values.sort(d3.ascending), q));
        
        // Professional Blues sequential scheme (accessible and data-focused)
        const colors = [
            '#f0f9ff',  // Lightest
            '#e0f2fe',
            '#bae6fd',
            '#7dd3fc',
            '#38bdf8',
            '#0ea5e9',
            '#0284c7'   // Darkest
        ];

        // Create scale with quantile breaks
        this.colorScale = d3.scaleThreshold()
            .domain(breaks.slice(1, -1)) // Remove min/max for threshold scale
            .range(colors);

        return {
            scale: this.colorScale,
            breaks: breaks,
            colors: colors
        };
    }

    /**
     * Get color for a feature based on its value
     */
    getFeatureColor(feature) {
        if (!this.colorScale || !feature?.properties?.value) {
            return '#f8fafc'; // Default panel background
        }

        const value = feature.properties.value;
        return this.colorScale(value);
    }

    /**
     * Render choropleth map using Observable Plot
     */
    async renderChoropleth(geoJsonData, options = {}) {
        try {
            console.log('🎨 Rendering choropleth with Observable Plot...');
            
            if (!geoJsonData?.features?.length) {
                throw new Error('No GeoJSON features to render');
            }

            // Update configuration
            this.updateDimensions();
            this.onCountyClick = options.onCountyClick;
            
            // Create color scale
            const colorInfo = this.createColorScale(geoJsonData, options.statistics);
            
            // Clear existing plot
            if (this.currentPlot) {
                this.currentPlot.remove();
            }

            // Create Observable Plot
            this.currentPlot = Plot.plot({
                width: this.config.width,
                height: this.config.height,
                projection: this.projection,
                marks: [
                    // County fills (choropleth)
                    Plot.geo(geoJsonData.features, {
                        fill: (d) => this.getFeatureColor(d),
                        stroke: this.config.strokeColor,
                        strokeWidth: this.config.strokeWidth,
                        title: (d) => this.getTooltipText(d, options.variable),
                        cursor: 'pointer'
                    })
                ],
                style: {
                    background: 'transparent'
                }
            });

            // Add click and hover interactions
            this.addInteractions(geoJsonData.features, options);

            // Mount plot to container
            if (this.mapContainer) {
                this.mapContainer.innerHTML = '';
                this.mapContainer.appendChild(this.currentPlot);
            }

            console.log(`✅ Rendered ${geoJsonData.features.length} counties`);
            
            return colorInfo;

        } catch (error) {
            console.error('❌ Failed to render choropleth:', error);
            throw error;
        }
    }

    /**
     * Add interactive behavior to the map
     */
    addInteractions(features, options) {
        if (!this.currentPlot) return;

        // Find all county paths in the SVG
        const countyCells = this.currentPlot.querySelectorAll('path');
        
        countyCells.forEach((path, index) => {
            const feature = features[index];
            if (!feature) return;

            // Add click handler
            path.addEventListener('click', (event) => {
                event.preventDefault();
                this.handleCountyClick(feature, path);
            });

            // Add hover handlers
            path.addEventListener('mouseenter', (event) => {
                this.handleCountyHover(feature, path, true);
            });

            path.addEventListener('mouseleave', (event) => {
                this.handleCountyHover(feature, path, false);
            });

            // Store feature data on element for reference
            path._featureData = feature;
        });
    }

    /**
     * Handle county click events
     */
    handleCountyClick(feature, element) {
        console.log('🖱️ County clicked:', feature.properties);
        
        // Highlight selected county
        this.highlightCounty(element, true);
        
        // Clear previous selection highlighting
        if (this.selectedElement && this.selectedElement !== element) {
            this.highlightCounty(this.selectedElement, false);
        }
        
        this.selectedElement = element;
        
        // Call external click handler
        if (this.onCountyClick) {
            this.onCountyClick(feature);
        }
    }

    /**
     * Handle county hover events
     */
    handleCountyHover(feature, element, isEntering) {
        if (isEntering) {
            this.hoveredCounty = feature;
            element.style.stroke = this.config.hoveredStrokeColor;
            element.style.strokeWidth = this.config.hoveredStrokeWidth;
            element.style.filter = 'brightness(1.1)';
        } else {
            this.hoveredCounty = null;
            // Don't override selection highlighting
            if (element !== this.selectedElement) {
                element.style.stroke = this.config.strokeColor;
                element.style.strokeWidth = this.config.strokeWidth;
                element.style.filter = 'none';
            }
        }
    }

    /**
     * Highlight a county (for selection)
     */
    highlightCounty(element, isSelected) {
        if (isSelected) {
            element.style.stroke = '#059669'; // Green accent highlight for selection
            element.style.strokeWidth = '3';
            element.style.filter = 'brightness(1.2)';
        } else {
            element.style.stroke = this.config.strokeColor;
            element.style.strokeWidth = this.config.strokeWidth;
            element.style.filter = 'none';
        }
    }

    /**
     * Generate tooltip text for a county
     */
    getTooltipText(feature, variable) {
        const props = feature.properties;
        if (!props) return 'County data unavailable';

        const countyName = props.county_name || 'Unknown County';
        const stateName = props.state_name || props.state || 'Unknown State';
        const value = props.value;
        const fips = props.fips;

        let text = `${countyName}, ${stateName}`;
        
        if (fips) {
            text += `\nFIPS: ${fips}`;
        }
        
        if (value !== null && value !== undefined) {
            const formattedValue = this.formatValue(value, variable);
            text += `\n${this.formatVariableName(variable)}: ${formattedValue}`;
        } else {
            text += `\n${this.formatVariableName(variable)}: No data`;
        }

        return text;
    }

    /**
     * Format variable name for display
     */
    formatVariableName(variable) {
        if (!variable) return 'Health Indicator';
        
        return variable
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    /**
     * Format value for display based on variable type
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
     * Resize map (for responsive behavior)
     */
    resize() {
        if (!this.currentPlot) return;
        
        console.log('📏 Resizing map...');
        this.updateDimensions();
        
        // Re-render with new dimensions
        // Note: This is a simple approach; more sophisticated resize handling
        // could preserve current state and just update dimensions
        const currentData = this.currentPlot._data;
        if (currentData) {
            this.renderChoropleth(currentData.geoJson, currentData.options);
        }
    }

    /**
     * Clear the map
     */
    clear() {
        if (this.currentPlot) {
            this.currentPlot.remove();
            this.currentPlot = null;
        }
        
        if (this.mapContainer) {
            this.mapContainer.innerHTML = '';
        }
        
        this.colorScale = null;
        this.hoveredCounty = null;
        this.selectedElement = null;
    }

    /**
     * Get current color scale information
     */
    getColorScale() {
        return this.colorScale;
    }

    /**
     * Get currently hovered county
     */
    getHoveredCounty() {
        return this.hoveredCounty;
    }

    /**
     * Set projection (for future customization)
     */
    setProjection(projectionName) {
        switch (projectionName) {
            case 'albers-usa':
                this.projection = d3.geoAlbersUsa();
                break;
            case 'mercator':
                this.projection = d3.geoMercator();
                break;
            case 'natural-earth':
                this.projection = d3.geoNaturalEarth1();
                break;
            default:
                console.warn(`Unknown projection: ${projectionName}`);
                return;
        }
        
        console.log(`🗺️ Projection changed to: ${projectionName}`);
    }
}

export { MapRenderer }; 