import ReactMarkdown from 'react-markdown';

interface MessageBubbleProps {
    role: 'user' | 'assistant';
    content: string;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ role, content }) => {
    const isUser = role === 'user';
    return (
        <div className={`message-container ${isUser ? 'user-container' : 'assistant-container'}`}>
            <div className={`message-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
                {isUser ? (
                    <p className="message-text">{content}</p>
                ) : (
                    <div className="markdown-content">
                        <ReactMarkdown>{content}</ReactMarkdown>
                    </div>
                )}
            </div>
        </div>
    );
};
