import React from 'react';

const COLORS = [
    '#7c3aed', // Purple (default)
    '#3b82f6', // Blue
    '#10b981', // Green
    '#f59e0b', // Amber
    '#ef4444', // Red
    '#ec4899', // Pink
    '#8b5cf6', // Violet
    '#06b6d4', // Cyan
    '#84cc16', // Lime
    '#f97316', // Orange
    '#6366f1', // Indigo
    '#14b8a6', // Teal
];

interface ColorPickerProps {
    value: string;
    onChange: (color: string) => void;
    onClose: () => void;
}

export const ColorPicker: React.FC<ColorPickerProps> = ({ value, onChange, onClose }) => {
    return (
        <div className="color-picker-dialog">
            <div className="color-picker-backdrop" onClick={onClose} />
            <div className="color-picker-content">
                <h3>Choose Project Color</h3>
                <div className="color-grid">
                    {COLORS.map(color => (
                        <button
                            key={color}
                            className={`color-option ${color === value ? 'selected' : ''}`}
                            style={{ backgroundColor: color }}
                            onClick={() => {
                                onChange(color);
                                onClose();
                            }}
                            title={color}
                        >
                            {color === value && (
                                <svg viewBox="0 0 24 24" fill="white" width="16" height="16">
                                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                                </svg>
                            )}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
};
