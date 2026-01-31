import React from 'react';

interface ThinkingStatusProps {
    status: string | null;
}

export const ThinkingStatus: React.FC<ThinkingStatusProps> = ({ status }) => {
    if (!status) return null;

    return (
        <div className="thinking-status">
            <div className="thinking-spinner">
                <div className="bounce1"></div>
                <div className="bounce2"></div>
                <div className="bounce3"></div>
            </div>
            <span className="thinking-text">{status}</span>
            <style>{`
                .thinking-status {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 8px 12px;
                    color: var(--text-secondary);
                    font-size: 0.9em;
                    font-style: italic;
                    animation: fadeIn 0.3s ease;
                    margin-bottom: 8px;
                }
                
                .thinking-spinner > div {
                    width: 8px;
                    height: 8px;
                    background-color: var(--accent-color);
                    border-radius: 100%;
                    display: inline-block;
                    animation: sk-bouncedelay 1.4s infinite ease-in-out both;
                    margin-right: 3px;
                }
                
                .thinking-spinner .bounce1 { animation-delay: -0.32s; }
                .thinking-spinner .bounce2 { animation-delay: -0.16s; }
                
                @keyframes sk-bouncedelay {
                    0%, 80%, 100% { transform: scale(0); }
                    40% { transform: scale(1.0); }
                }

                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(5px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
};
