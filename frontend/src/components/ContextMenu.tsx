import React, { useEffect, useRef } from 'react';

export interface MenuItem {
    label: string;
    icon?: React.ReactNode;
    onClick: () => void;
    danger?: boolean;
    disabled?: boolean;
}

interface ContextMenuProps {
    x: number;
    y: number;
    items: MenuItem[];
    onClose: () => void;
}

export const ContextMenu: React.FC<ContextMenuProps> = ({ x, y, items, onClose }) => {
    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                onClose();
            }
        };

        const handleEscape = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                onClose();
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        document.addEventListener('keydown', handleEscape);

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('keydown', handleEscape);
        };
    }, [onClose]);

    const handleItemClick = (item: MenuItem) => {
        if (!item.disabled) {
            item.onClick();
            onClose();
        }
    };

    return (
        <div
            ref={menuRef}
            className="context-menu"
            style={{
                position: 'fixed',
                left: `${x}px`,
                top: `${y}px`,
                zIndex: 1000,
            }}
        >
            {items.map((item, index) => (
                <button
                    key={index}
                    className={`context-menu-item ${item.danger ? 'danger' : ''} ${item.disabled ? 'disabled' : ''}`}
                    onClick={() => handleItemClick(item)}
                    disabled={item.disabled}
                >
                    {item.icon && <span className="context-menu-icon">{item.icon}</span>}
                    <span className="context-menu-label">{item.label}</span>
                </button>
            ))}
        </div>
    );
};
