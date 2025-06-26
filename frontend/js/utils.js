/**
 * Utility functions for County Health Explorer
 * Common helper functions used across the application
 */

const utils = {
    /**
     * Debounce function calls to improve performance
     */
    debounce(func, wait, immediate = false) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func(...args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func(...args);
        };
    },

    /**
     * Throttle function calls
     */
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * Format numbers for display
     */
    formatNumber(value, options = {}) {
        if (value === null || value === undefined || isNaN(value)) {
            return options.fallback || 'N/A';
        }

        const {
            decimals = 2,
            useCommas = true,
            prefix = '',
            suffix = '',
            fallback = 'N/A'
        } = options;

        try {
            let formatted = Number(value);
            
            if (decimals === 0) {
                formatted = Math.round(formatted);
            } else {
                formatted = formatted.toFixed(decimals);
            }

            if (useCommas) {
                formatted = Number(formatted).toLocaleString();
            }

            return `${prefix}${formatted}${suffix}`;
        } catch (error) {
            console.warn('Error formatting number:', value, error);
            return fallback;
        }
    },

    /**
     * Format percentages
     */
    formatPercentage(value, decimals = 1) {
        return this.formatNumber(value, {
            decimals,
            suffix: '%',
            fallback: 'N/A'
        });
    },

    /**
     * Format large numbers with K/M/B suffixes
     */
    formatLargeNumber(value) {
        if (value === null || value === undefined || isNaN(value)) {
            return 'N/A';
        }

        const absValue = Math.abs(value);
        
        if (absValue >= 1e9) {
            return this.formatNumber(value / 1e9, { decimals: 1, suffix: 'B' });
        } else if (absValue >= 1e6) {
            return this.formatNumber(value / 1e6, { decimals: 1, suffix: 'M' });
        } else if (absValue >= 1e3) {
            return this.formatNumber(value / 1e3, { decimals: 1, suffix: 'K' });
        } else {
            return this.formatNumber(value, { decimals: 0 });
        }
    },

    /**
     * Format variable names for display
     */
    formatVariableName(variableName) {
        if (!variableName || typeof variableName !== 'string') {
            return 'Unknown Variable';
        }

        return variableName
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    },

    /**
     * Parse and validate FIPS codes
     */
    validateFips(fips) {
        if (!fips) return false;
        
        const fipsStr = String(fips).padStart(5, '0');
        return /^\d{5}$/.test(fipsStr);
    },

    /**
     * Normalize FIPS code to 5-digit string
     */
    normalizeFips(fips) {
        if (!fips) return null;
        return String(fips).padStart(5, '0');
    },

    /**
     * Generate color palette for choropleth mapping
     */
    generateColorPalette(type = 'sequential', count = 8) {
        const palettes = {
            sequential: {
                blues: [
                    '#f7fbff', '#deebf7', '#c6dbef', '#9ecae1',
                    '#6baed6', '#4292c6', '#2171b5', '#084594'
                ],
                greens: [
                    '#f7fcf5', '#e5f5e0', '#c7e9c0', '#a1d99b',
                    '#74c476', '#41ab5d', '#238b45', '#005a32'
                ],
                oranges: [
                    '#fff5eb', '#fee6ce', '#fdd0a2', '#fdae6b',
                    '#fd8d3c', '#f16913', '#d94801', '#8c2d04'
                ]
            },
            diverging: {
                redblue: [
                    '#67001f', '#b2182b', '#d6604d', '#f4a582',
                    '#fddbc7', '#d1e5f0', '#92c5de', '#4393c3',
                    '#2166ac', '#053061'
                ]
            }
        };

        const paletteGroup = palettes[type] || palettes.sequential;
        const palette = paletteGroup.blues || Object.values(paletteGroup)[0];
        
        return palette.slice(0, count);
    },

    /**
     * Calculate quantile breaks for data classification
     */
    calculateQuantileBreaks(values, numBreaks = 5) {
        if (!Array.isArray(values) || values.length === 0) {
            return [];
        }

        const validValues = values
            .filter(v => v !== null && v !== undefined && !isNaN(v))
            .sort((a, b) => a - b);

        if (validValues.length === 0) return [];

        const breaks = [];
        for (let i = 0; i <= numBreaks; i++) {
            const quantile = i / numBreaks;
            const index = Math.floor(quantile * (validValues.length - 1));
            breaks.push(validValues[index]);
        }

        return [...new Set(breaks)]; // Remove duplicates
    },

    /**
     * Deep clone an object
     */
    deepClone(obj) {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }

        if (obj instanceof Date) {
            return new Date(obj.getTime());
        }

        if (obj instanceof Array) {
            return obj.map(item => this.deepClone(item));
        }

        if (typeof obj === 'object') {
            const cloned = {};
            Object.keys(obj).forEach(key => {
                cloned[key] = this.deepClone(obj[key]);
            });
            return cloned;
        }

        return obj;
    },

    /**
     * Check if value is empty (null, undefined, empty string, etc.)
     */
    isEmpty(value) {
        return value === null || 
               value === undefined || 
               value === '' || 
               (Array.isArray(value) && value.length === 0) ||
               (typeof value === 'object' && Object.keys(value).length === 0);
    },

    /**
     * Capitalize first letter of each word
     */
    titleCase(str) {
        if (!str || typeof str !== 'string') return '';
        
        return str.toLowerCase().replace(/\b\w/g, char => char.toUpperCase());
    },

    /**
     * Create a slug from a string (for URLs, IDs, etc.)
     */
    slugify(str) {
        if (!str || typeof str !== 'string') return '';
        
        return str
            .toLowerCase()
            .replace(/[^\w\s-]/g, '') // Remove special characters
            .replace(/[\s_-]+/g, '-') // Replace spaces and underscores with hyphens
            .replace(/^-+|-+$/g, ''); // Remove leading/trailing hyphens
    },

    /**
     * Get a contrasting text color (black or white) for a background color
     */
    getContrastColor(backgroundColor) {
        if (!backgroundColor) return '#000000';
        
        // Remove # if present
        const color = backgroundColor.replace('#', '');
        
        // Convert to RGB
        const r = parseInt(color.substr(0, 2), 16);
        const g = parseInt(color.substr(2, 2), 16);
        const b = parseInt(color.substr(4, 2), 16);
        
        // Calculate luminance
        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        
        return luminance > 0.5 ? '#000000' : '#ffffff';
    },

    /**
     * Download data as JSON file
     */
    downloadJSON(data, filename = 'data.json') {
        try {
            const jsonStr = JSON.stringify(data, null, 2);
            const blob = new Blob([jsonStr], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Error downloading JSON:', error);
        }
    },

    /**
     * Download data as CSV file
     */
    downloadCSV(data, filename = 'data.csv') {
        try {
            if (!Array.isArray(data) || data.length === 0) {
                throw new Error('Data must be a non-empty array');
            }

            // Get headers from first object
            const headers = Object.keys(data[0]);
            
            // Create CSV content
            const csvContent = [
                headers.join(','), // Header row
                ...data.map(row => 
                    headers.map(header => {
                        let value = row[header] || '';
                        // Escape commas and quotes
                        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                            value = `"${value.replace(/"/g, '""')}"`;
                        }
                        return value;
                    }).join(',')
                )
            ].join('\n');

            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Error downloading CSV:', error);
        }
    },

    /**
     * Simple logging utility with timestamps
     */
    log: {
        info: (message, ...args) => {
            console.log(`[${new Date().toISOString()}] ℹ️ ${message}`, ...args);
        },
        warn: (message, ...args) => {
            console.warn(`[${new Date().toISOString()}] ⚠️ ${message}`, ...args);
        },
        error: (message, ...args) => {
            console.error(`[${new Date().toISOString()}] ❌ ${message}`, ...args);
        },
        debug: (message, ...args) => {
            if (process.env.NODE_ENV === 'development') {
                console.debug(`[${new Date().toISOString()}] 🐛 ${message}`, ...args);
            }
        }
    },

    /**
     * Performance measurement utilities
     */
    perf: {
        start: (label) => {
            performance.mark(`${label}-start`);
        },
        end: (label) => {
            performance.mark(`${label}-end`);
            performance.measure(label, `${label}-start`, `${label}-end`);
            const measure = performance.getEntriesByName(label)[0];
            console.log(`⏱️ ${label}: ${measure.duration.toFixed(2)}ms`);
            return measure.duration;
        }
    },

    /**
     * URL parameter utilities
     */
    url: {
        getParams: () => {
            const params = new URLSearchParams(window.location.search);
            const result = {};
            for (const [key, value] of params) {
                result[key] = value;
            }
            return result;
        },
        
        setParam: (key, value) => {
            const url = new URL(window.location);
            url.searchParams.set(key, value);
            window.history.replaceState({}, '', url);
        },
        
        removeParam: (key) => {
            const url = new URL(window.location);
            url.searchParams.delete(key);
            window.history.replaceState({}, '', url);
        }
    }
};

export { utils }; 