import React, { useState, type KeyboardEvent } from 'react';

interface InputAreaProps {
    onSendMessage: (message: string) => void;
    isLoading: boolean;
}

export const InputArea: React.FC<InputAreaProps> = ({ onSendMessage, isLoading }) => {
    const [input, setInput] = useState('');

    const handleSend = () => {
        if (input.trim() && !isLoading) {
            onSendMessage(input);
            setInput('');
        }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="input-area">
            <textarea
                className="chat-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your message..."
                disabled={isLoading}
                rows={1}
            />
            <button
                className={`send-button ${isLoading ? 'loading' : ''}`}
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                title="Send message"
            >
                {isLoading ? (
                    <svg viewBox="0 0 16 16" fill="currentColor">
                        <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="2" fill="none" opacity="0.3" />
                        <path d="M8 1a7 7 0 0 1 7 7" stroke="currentColor" strokeWidth="2" fill="none" />
                    </svg>
                ) : (
                    <svg viewBox="0 0 16 16" fill="currentColor">
                        <path d="M15.854.146a.5.5 0 0 1 .11.54l-5.819 14.547a.75.75 0 0 1-1.329.124l-3.178-4.995L.643 7.184a.75.75 0 0 1 .124-1.33L15.314.037a.5.5 0 0 1 .54.11ZM6.636 10.07l2.761 4.338L14.13 2.576 6.636 10.07Zm6.787-8.201L1.591 6.602l4.339 2.76 7.494-7.493Z" />
                    </svg>
                )}
            </button>
        </div>
    );
};
