interface Theme {
    name: string;
    primary: string;
    primaryHover: string;
    background: string;
    surface: string;
    surfaceHover: string;
    border: string;
    text: string;
    textSecondary: string;
    success: string;
    warning: string;
    error: string;
}

interface BrandingConfig {
    branding: {
        appName: string;
        logo: string;
        logoSvg: string;
        favicon: string;
    };
    themes: {
        [key: string]: Theme;
    };
    defaultTheme: string;
}

let brandingConfig: BrandingConfig | null = null;

export const loadBranding = async (): Promise<BrandingConfig> => {
    if (brandingConfig) return brandingConfig;

    const response = await fetch('/branding.json');
    brandingConfig = await response.json();
    return brandingConfig!;
};

export const applyTheme = (themeName: string, config: BrandingConfig) => {
    const theme = config.themes[themeName];
    if (!theme) {
        console.warn(`Theme "${themeName}" not found, using default`);
        return;
    }

    const root = document.documentElement;

    // Map theme properties to CSS variables
    const colorMapping: { [key: string]: string } = {
        'primary': theme.primary,
        'primary-hover': theme.primaryHover,
        'bg-primary': theme.background,
        'bg-secondary': theme.surface,
        'bg-tertiary': theme.surfaceHover,
        'bg-hover': theme.surfaceHover,
        'bg-active': theme.primary + '20',
        'text-primary': theme.text,
        'text-secondary': theme.textSecondary,
        'border-primary': theme.border,
        'accent-primary': theme.primary,
        'accent-hover': theme.primaryHover,
        'success': theme.success,
        'warning': theme.warning,
        'error': theme.error,
        'input-bg': theme.surface,
        'input-border': theme.border,
        'input-focus-border': theme.primary,
        'sidebar-bg': theme.background,
        'sidebar-border': theme.border,
        'message-user-bg': theme.primary,
        'message-user-text': '#ffffff',
        'message-assistant-bg': theme.surface,
        'message-assistant-text': theme.text,
        'message-assistant-border': theme.border,
    };

    Object.entries(colorMapping).forEach(([key, value]) => {
        root.style.setProperty(`--${key}`, value);
    });

    // Hard-coded spacing and radius
    root.style.setProperty('--spacing-xs', '4px');
    root.style.setProperty('--spacing-sm', '8px');
    root.style.setProperty('--spacing-md', '16px');
    root.style.setProperty('--spacing-lg', '24px');
    root.style.setProperty('--spacing-xl', '32px');

    root.style.setProperty('--radius-sm', '6px');
    root.style.setProperty('--radius-md', '8px');
    root.style.setProperty('--radius-lg', '12px');
    root.style.setProperty('--radius-xl', '16px');
    root.style.setProperty('--radius-full', '9999px');

    // Store current theme
    localStorage.setItem('theme', themeName);
};

export const getCurrentTheme = (): string => {
    return localStorage.getItem('theme') || 'dark';
};

export const initializeTheme = async () => {
    const config = await loadBranding();
    const currentTheme = getCurrentTheme();
    applyTheme(currentTheme, config);
    return { config, currentTheme };
};
