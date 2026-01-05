FROM node:20-alpine AS builder

WORKDIR /app

# Create a minimal demo UI
RUN cat > package.json << 'EOF'
{
  "name": "ai-platform-demo-ui",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.0.4",
    "react": "18.2.0",
    "react-dom": "18.2.0"
  }
}
EOF

RUN npm install

# Create pages
RUN mkdir -p pages && cat > pages/index.js << 'INDEXEOF'
import { useState, useRef, useEffect } from 'react';

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
  const AGENT_ID = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const createSession = async () => {
    const res = await fetch(`${API_URL}/api/v1/agents/${AGENT_ID}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: 'demo-user' }),
    });
    const data = await res.json();
    setSessionId(data.session_id);
    return data.session_id;
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      let sid = sessionId;
      if (!sid) {
        sid = await createSession();
      }

      const res = await fetch(`${API_URL}/api/v1/agents/${AGENT_ID}/invoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sid, input: userMessage }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: 'assistant', content: data.output }]);
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'error', content: 'Error: ' + error.message }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>Customer Support Agent</h1>
        <p style={styles.subtitle}>Enterprise AI Platform Demo</p>
      </header>

      <div style={styles.chatContainer}>
        <div style={styles.messages}>
          {messages.length === 0 && (
            <div style={styles.welcome}>
              <p>Welcome! I am your AI customer support assistant.</p>
              <p>Try asking about:</p>
              <ul>
                <li>Return policy</li>
                <li>Shipping information</li>
                <li>Account management</li>
              </ul>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} style={{
              ...styles.message,
              ...(msg.role === 'user' ? styles.userMessage : styles.assistantMessage),
            }}>
              <div style={styles.messageRole}>
                {msg.role === 'user' ? 'You' : 'Agent'}
              </div>
              <div style={styles.messageContent}>{msg.content}</div>
            </div>
          ))}
          {loading && (
            <div style={styles.loading}>Agent is thinking...</div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={sendMessage} style={styles.inputForm}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            style={styles.input}
            disabled={loading}
          />
          <button type="submit" style={styles.button} disabled={loading}>
            Send
          </button>
        </form>
      </div>

      <footer style={styles.footer}>
        <a href="http://localhost:3001" target="_blank">Grafana</a>
        {' | '}
        <a href="http://localhost:16686" target="_blank">Jaeger</a>
        {' | '}
        <a href="http://localhost:9090" target="_blank">Prometheus</a>
      </footer>
    </div>
  );
}

const styles = {
  container: {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '20px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    textAlign: 'center',
    marginBottom: '20px',
  },
  title: {
    margin: 0,
    fontSize: '24px',
    color: '#1a1a1a',
  },
  subtitle: {
    margin: '5px 0 0',
    color: '#666',
    fontSize: '14px',
  },
  chatContainer: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    border: '1px solid #ddd',
    borderRadius: '8px',
    overflow: 'hidden',
  },
  messages: {
    flex: 1,
    padding: '20px',
    overflowY: 'auto',
    backgroundColor: '#f9f9f9',
    minHeight: '400px',
  },
  welcome: {
    textAlign: 'center',
    color: '#666',
    padding: '40px',
  },
  message: {
    marginBottom: '15px',
    padding: '12px',
    borderRadius: '8px',
    maxWidth: '80%',
  },
  userMessage: {
    backgroundColor: '#007bff',
    color: 'white',
    marginLeft: 'auto',
  },
  assistantMessage: {
    backgroundColor: 'white',
    border: '1px solid #ddd',
  },
  messageRole: {
    fontSize: '12px',
    fontWeight: 'bold',
    marginBottom: '5px',
    opacity: 0.7,
  },
  messageContent: {
    whiteSpace: 'pre-wrap',
    lineHeight: 1.5,
  },
  loading: {
    textAlign: 'center',
    color: '#666',
    fontStyle: 'italic',
  },
  inputForm: {
    display: 'flex',
    padding: '15px',
    backgroundColor: 'white',
    borderTop: '1px solid #ddd',
  },
  input: {
    flex: 1,
    padding: '12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '16px',
    marginRight: '10px',
  },
  button: {
    padding: '12px 24px',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '16px',
    cursor: 'pointer',
  },
  footer: {
    textAlign: 'center',
    padding: '20px',
    color: '#666',
    fontSize: '14px',
  },
};
INDEXEOF

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV production

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/package*.json ./
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder --chown=nextjs:nodejs /app/node_modules ./node_modules

USER nextjs

EXPOSE 3000

CMD ["npm", "start"]
