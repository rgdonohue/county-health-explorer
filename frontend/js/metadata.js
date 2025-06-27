/**
 * Health Variable Metadata Configuration
 * 
 * This master configuration defines how each health variable should be interpreted,
 * displayed, and formatted. It provides systematic handling instead of hard-coding
 * individual variables throughout the codebase.
 */

export const HEALTH_VARIABLE_METADATA = {
    // Mortality Variables
    premature_death: {
        displayName: "Premature Death",
        units: "years lost per 100,000",
        dataType: "rate",
        description: "Years of potential life lost before age 75 per 100,000 population (age-adjusted)",
        interpretation: "Higher values indicate more years of life lost to premature death",
        category: "mortality",
        isAlreadyStandardized: true
    },
    
    firearm_fatalities: {
        displayName: "Firearm Fatalities", 
        units: "per 100,000 population",
        dataType: "rate",
        description: "Number of deaths due to firearms per 100,000 population",
        interpretation: "Population-standardized rates for fair comparison",
        category: "mortality",
        isAlreadyStandardized: true
    },
    
    drug_overdose_deaths: {
        displayName: "Drug Overdose Deaths",
        units: "per 100,000 population", 
        dataType: "rate",
        description: "Number of deaths due to drug overdose per 100,000 population",
        interpretation: "Population-standardized mortality rates",
        category: "mortality",
        isAlreadyStandardized: true
    },

    // Health Behaviors (stored as decimals, displayed as percentages)
    adult_obesity: {
        displayName: "Adult Obesity",
        units: "percentage",
        dataType: "percentage",
        description: "Percentage of adults aged 20 and older with obesity (BMI ≥ 30)",
        interpretation: "Higher percentages indicate higher obesity prevalence",
        category: "behavioral",
        isAlreadyStandardized: false,
        transform: "decimalToPercentage"
    },
    
    adult_smoking: {
        displayName: "Adult Smoking",
        units: "percentage", 
        dataType: "percentage",
        description: "Percentage of adults who are current smokers",
        interpretation: "Higher percentages indicate higher smoking prevalence",
        category: "behavioral",
        isAlreadyStandardized: false,
        transform: "decimalToPercentage"
    },
    
    physical_inactivity: {
        displayName: "Physical Inactivity",
        units: "percentage",
        dataType: "percentage", 
        description: "Percentage of adults aged 20 and older reporting no leisure-time physical activity",
        interpretation: "Higher percentages indicate more sedentary populations",
        category: "behavioral",
        isAlreadyStandardized: false,
        transform: "decimalToPercentage"
    },

    // Social & Economic Variables (stored as decimals, displayed as percentages)
    unemployment: {
        displayName: "Unemployment",
        units: "percentage",
        dataType: "percentage",
        description: "Percentage of population ages 16 and older unemployed but seeking work",
        interpretation: "Higher percentages indicate higher unemployment rates",
        category: "social",
        isAlreadyStandardized: false,
        transform: "decimalToPercentage"
    },
    
    children_in_poverty: {
        displayName: "Children in Poverty",
        units: "percentage",
        dataType: "percentage", 
        description: "Percentage of people under age 18 in poverty",
        interpretation: "Higher percentages indicate higher child poverty rates",
        category: "social",
        isAlreadyStandardized: false,
        transform: "decimalToPercentage"
    },

    // Clinical Care (stored as decimals, displayed as percentages)
    mammography_screening: {
        displayName: "Mammography Screening",
        units: "percentage",
        dataType: "percentage",
        description: "Percentage of female Medicare enrollees ages 65-74 who received an annual mammography screening",
        interpretation: "Higher percentages indicate better preventive care access",
        category: "clinical",
        isAlreadyStandardized: false,
        transform: "decimalToPercentage"
    },
    
    flu_vaccinations: {
        displayName: "Flu Vaccinations", 
        units: "percentage",
        dataType: "percentage",
        description: "Percentage of adults aged 65 and older who received an annual flu vaccination",
        interpretation: "Higher percentages indicate better preventive care uptake",
        category: "clinical",
        isAlreadyStandardized: false,
        transform: "decimalToPercentage"
    },

    // Health Outcomes (days - no transformation needed)
    poor_physical_health_days: {
        displayName: "Poor Physical Health Days",
        units: "days per month",
        dataType: "days",
        description: "Average number of physically unhealthy days reported in past 30 days (age-adjusted)",
        interpretation: "Higher values indicate more poor physical health days",
        category: "clinical",
        isAlreadyStandardized: true
    },
    
    poor_mental_health_days: {
        displayName: "Poor Mental Health Days",
        units: "days per month", 
        dataType: "days",
        description: "Average number of mentally unhealthy days reported in past 30 days (age-adjusted)",
        interpretation: "Higher values indicate more poor mental health days",
        category: "clinical",
        isAlreadyStandardized: true
    },

    // Disease Prevalence (per 100K rates)
    hiv_prevalence: {
        displayName: "HIV Prevalence",
        units: "per 100,000 population",
        dataType: "rate", 
        description: "Number of people aged 13 years and older living with a diagnosis of HIV per 100,000 population",
        interpretation: "Population-standardized prevalence rates",
        category: "clinical",
        isAlreadyStandardized: true
    },

    // Environmental Variables
    adverse_climate_events: {
        displayName: "Adverse Climate Events",
        units: "0-3 categories",
        dataType: "index",
        description: "Indicator of climate thresholds met (heat, drought, disasters)",
        interpretation: "Scale: 0-3 threshold categories met",
        category: "environmental",
        isAlreadyStandardized: true
    },
    
    traffic_volume: {
        displayName: "Traffic Volume",
        units: "vehicles per meter per day",
        dataType: "rate",
        description: "Average daily traffic volume per meter of road length",
        interpretation: "Higher values indicate more traffic density",
        category: "environmental", 
        isAlreadyStandardized: true
    }
};

/**
 * Data transformation functions
 */
export const DATA_TRANSFORMS = {
    decimalToPercentage: (value) => {
        if (value === null || value === undefined || isNaN(value)) return null;
        return Number(value) * 100;
    },
    
    identity: (value) => value
};

/**
 * Get metadata for a variable
 */
export function getVariableMetadata(variableName) {
    return HEALTH_VARIABLE_METADATA[variableName] || {
        displayName: variableName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        units: "",
        dataType: "numeric", 
        description: "",
        interpretation: "",
        category: "other",
        isAlreadyStandardized: true
    };
}

/**
 * Transform a value based on variable metadata
 */
export function transformValue(value, variableName) {
    const metadata = getVariableMetadata(variableName);
    const transform = metadata.transform || 'identity';
    const transformFn = DATA_TRANSFORMS[transform] || DATA_TRANSFORMS.identity;
    return transformFn(value);
}

/**
 * Format a value for display based on variable metadata
 */
export function formatValue(value, variableName, precision = 1) {
    const transformedValue = transformValue(value, variableName);
    const metadata = getVariableMetadata(variableName);
    
    if (transformedValue === null || transformedValue === undefined || isNaN(transformedValue)) {
        return 'N/A';
    }
    
    const numValue = Number(transformedValue);
    
    switch (metadata.dataType) {
        case 'percentage':
            return `${numValue.toFixed(precision)}%`;
        case 'rate':
            if (metadata.units.includes('100,000') || metadata.units.includes('100K')) {
                return `${numValue.toFixed(precision)} per 100K`;
            }
            return numValue.toFixed(precision);
        case 'days':
            return `${numValue.toFixed(precision)} days`;
        case 'index':
            return numValue.toFixed(2);
        default:
            return numValue.toFixed(precision);
    }
} 