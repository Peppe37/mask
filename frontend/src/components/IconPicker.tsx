import React from 'react';

const ICONS = ['📁', '⭐', '💼', '🎯', '🚀', '💡', '🔧', '📊', '🎨', '📝', '🔥', '⚡', '🌟', '📦', '🎮', '🏆'];

interface IconPickerProps {
    value: string;
    onChange: (icon: string) => void;
    onClose: () => void;
}

export const IconPicker: React.FC<IconPickerProps> = ({ value, onChange, onClose }) => {
    return (
        <div className="icon-picker-dialog">
            <div className="icon-picker-backdrop" onClick={onClose} />
            <div className="icon-picker-content">
                <h3>Choose Project Icon</h3>
                <div className="icon-grid">
                    {ICONS.map(icon => (
                        <button
                            key={icon}
                            className={`icon-option ${icon === value ? 'selected' : ''}`}
                            onClick={() => {
                                onChange(icon);
                                onClose();
                            }}
                        >
                            <span className="icon-emoji">{icon}</span>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
};
