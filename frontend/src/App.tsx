import { useEffect } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { initializeTheme } from './utils/theme';
import './index.css';

function App() {
  useEffect(() => {
    initializeTheme();
  }, []);

  return (
    <div className="app-container">
      <ChatInterface />
    </div>
  );
}

export default App;
