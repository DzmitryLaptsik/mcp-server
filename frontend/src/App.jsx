import { useState, useRef, useEffect, useCallback } from 'react'
import Markdown from 'react-markdown'
import './App.css'

const SUGGESTIONS = [
  "What's the weather in London?",
  "What time is it in Tokyo?",
  "Save a note: project deadline is April 15",
  "Create a task: update the landing page, high priority",
  "Start tracking time on API integration",
  "Set a reminder in 30 minutes to take a break",
]

const MODELS = [
  { id: 'anthropic/claude-sonnet-4', name: 'Claude Sonnet 4', provider: 'Anthropic' },
  { id: 'anthropic/claude-haiku-4.5', name: 'Claude Haiku 4.5', provider: 'Anthropic' },
  { id: 'openai/gpt-4o', name: 'GPT-4o', provider: 'OpenAI' },
  { id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini', provider: 'OpenAI' },
  { id: 'google/gemini-2.5-flash', name: 'Gemini 2.5 Flash', provider: 'Google' },
  { id: 'google/gemini-2.5-pro', name: 'Gemini 2.5 Pro', provider: 'Google' },
  { id: 'meta-llama/llama-4-maverick', name: 'Llama 4 Maverick', provider: 'Meta' },
  { id: 'deepseek/deepseek-chat-v3', name: 'DeepSeek V3', provider: 'DeepSeek' },
]

// --- Auth helpers ---

function getAuth() {
  try {
    const stored = localStorage.getItem('mcp_auth')
    return stored ? JSON.parse(stored) : null
  } catch { return null }
}

function setAuth(data) {
  localStorage.setItem('mcp_auth', JSON.stringify(data))
}

function clearAuth() {
  localStorage.removeItem('mcp_auth')
}

function authHeaders(extra = {}) {
  const auth = getAuth()
  if (!auth?.api_key) return extra
  return { ...extra, 'Authorization': `Bearer ${auth.api_key}` }
}

// --- Clipboard helper ---

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).catch(() => {})
}

// --- Components ---

function ToolCall({ call }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className={`tool-call ${expanded ? 'expanded' : ''}`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="tool-call-header">
        <span className="tool-icon">fn</span>
        <span className="tool-name">{call.tool}</span>
        <span className="tool-arrow">&#9654;</span>
      </div>
      {expanded && (
        <div className="tool-call-detail">
          <div><strong>Input:</strong> {JSON.stringify(call.input, null, 2)}</div>
          {call.output && (
            <div><strong>Output:</strong> {JSON.stringify(call.output, null, 2)}</div>
          )}
        </div>
      )}
    </div>
  )
}

function Message({ message }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = (e) => {
    e.stopPropagation()
    copyToClipboard(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className={`message ${message.role}`}>
      <div className="message-content">
        {message.role === 'assistant' ? (
          <Markdown>{message.content}</Markdown>
        ) : (
          message.content
        )}
      </div>
      <div className="message-footer">
        {message.model && (
          <span className="message-model">{message.model}</span>
        )}
        {message.role === 'assistant' && message.content && (
          <button className="copy-btn" onClick={handleCopy} title="Copy to clipboard">
            {copied ? 'Copied!' : 'Copy'}
          </button>
        )}
      </div>
      {message.toolCalls && message.toolCalls.length > 0 && (
        <div className="tool-calls">
          {message.toolCalls.map((call, i) => (
            <ToolCall key={i} call={call} />
          ))}
        </div>
      )}
    </div>
  )
}

function ModelSelector({ model, onChange, disabled }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const current = MODELS.find(m => m.id === model) || MODELS[0]

  return (
    <div className="model-selector" ref={ref}>
      <button
        className="model-selector-btn"
        onClick={() => !disabled && setOpen(!open)}
        disabled={disabled}
      >
        <span className="model-selector-label">{current.name}</span>
        <span className="model-selector-arrow">&#9662;</span>
      </button>
      {open && (
        <div className="model-dropdown">
          {MODELS.map(m => (
            <button
              key={m.id}
              className={`model-option ${m.id === model ? 'active' : ''}`}
              onClick={() => { onChange(m.id); setOpen(false) }}
            >
              <span className="model-option-name">{m.name}</span>
              <span className="model-option-provider">{m.provider}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function LoginScreen({ onLogin }) {
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name.trim() || loading) return

    setLoading(true)
    setError(null)

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim() }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.error || 'Login failed')
      }

      const data = await res.json()
      setAuth(data)
      onLogin(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <h1>MCP Assistant</h1>
        <p>Enter your name to get started. Your notes, tasks, and reminders will be saved privately.</p>
        {error && <div className="error-banner">{error}</div>}
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            autoFocus
            maxLength={100}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !name.trim()}>
            {loading ? 'Signing in...' : 'Continue'}
          </button>
        </form>
      </div>
    </div>
  )
}

// --- Main App ---

function App() {
  const [user, setUser] = useState(getAuth)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [tools, setTools] = useState([])
  const [showTools, setShowTools] = useState(false)
  const [model, setModel] = useState(MODELS[0].id)
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)
  const toolsPanelRef = useRef(null)

  useEffect(() => {
    if (!user?.api_key) return
    fetch('/api/auth/me', { headers: authHeaders() })
      .then(r => {
        if (!r.ok) { clearAuth(); setUser(null) }
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetch('/api/tools')
      .then(r => r.json())
      .then(data => setTools(data.tools || []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    const handleClick = (e) => {
      if (toolsPanelRef.current && !toolsPanelRef.current.contains(e.target)) {
        setShowTools(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Auto-focus textarea when loading finishes
  useEffect(() => {
    if (!loading && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [loading])

  const handleLogin = (data) => {
    setUser(data)
    setMessages([])
  }

  const handleSignOut = () => {
    clearAuth()
    setUser(null)
    setMessages([])
  }

  const handleNewChat = () => {
    setMessages([])
    setError(null)
  }

  const selectTool = useCallback((template) => {
    if (template) {
      setInput(template)
      setShowTools(false)
      setTimeout(() => {
        const el = textareaRef.current
        if (el) {
          el.focus()
          const match = template.match(/\{[^}]+\}/)
          if (match) {
            el.setSelectionRange(match.index, match.index + match[0].length)
          }
        }
      }, 0)
    }
  }, [])

  const autoResize = useCallback(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 120) + 'px'
    }
  }, [])

  const sendMessage = async (text) => {
    const userMessage = text || input.trim()
    if (!userMessage || loading) return

    setInput('')
    setError(null)
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    const newMessages = [...messages, { role: 'user', content: userMessage }]
    setMessages(newMessages)
    setLoading(true)

    try {
      const apiMessages = newMessages.map(m => ({
        role: m.role,
        content: m.content,
      }))

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ messages: apiMessages, model }),
      })

      if (res.status === 401) {
        clearAuth()
        setUser(null)
        throw new Error('Session expired. Please sign in again.')
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.error || `HTTP ${res.status}`)
      }

      const data = await res.json()
      const modelName = MODELS.find(m => m.id === model)?.name || model
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          content: data.response,
          toolCalls: data.tool_calls || [],
          model: modelName,
        },
      ])
    } catch (err) {
      setError(err.message || 'Failed to send message')
    } finally {
      setLoading(false)
      setTimeout(() => textareaRef.current?.focus(), 0)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  if (!user?.api_key) {
    return <LoginScreen onLogin={handleLogin} />
  }

  const hasMessages = messages.length > 0

  return (
    <div className="app">
      <div className="header">
        <div className="header-left">
          <h1>MCP Assistant</h1>
          {hasMessages && (
            <button className="new-chat-btn" onClick={handleNewChat} title="New chat">
              + New
            </button>
          )}
        </div>
        <div className="header-right">
          <ModelSelector model={model} onChange={setModel} disabled={loading} />
          {tools.length > 0 && (
            <div className="tools-panel-wrapper" ref={toolsPanelRef}>
              <button
                className="tools-badge"
                onClick={() => setShowTools(!showTools)}
              >
                {tools.length} tools
              </button>
              {showTools && (
                <div className="tools-panel">
                  <div className="tools-panel-header">Connected Tools</div>
                  <div className="tools-panel-list">
                    {Object.entries(
                      tools.reduce((groups, t) => {
                        const cat = t.category || 'Other'
                        if (!groups[cat]) groups[cat] = []
                        groups[cat].push(t)
                        return groups
                      }, {})
                    ).map(([category, items]) => (
                      <div key={category} className="tools-panel-group">
                        <div className="tools-panel-category">{category}</div>
                        {items.map((t, i) => (
                          <div
                            key={i}
                            className={`tools-panel-item ${t.template ? 'clickable' : ''}`}
                            onClick={() => t.template && selectTool(t.template)}
                          >
                            <span className="tools-panel-emoji">{t.icon}</span>
                            <div>
                              <div className="tools-panel-name">{t.label}</div>
                              <div className="tools-panel-desc">{t.description}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          <div className="user-badge" onClick={handleSignOut} title="Sign out">
            {user.name.charAt(0).toUpperCase()}
          </div>
        </div>
      </div>

      {!hasMessages ? (
        <div className="welcome">
          <h2>Hi {user.name}! What can I help you with?</h2>
          <p>
            I have access to weather, notes, tasks, time tracking, reminders,
            news, and timezone tools. Try asking me something:
          </p>
          <div className="suggestions">
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                className="suggestion"
                onClick={() => sendMessage(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="messages">
          {messages.map((m, i) => (
            <Message key={i} message={m} />
          ))}
          {loading && (
            <div className="loading">
              <div className="loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
              Thinking...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button className="error-dismiss" onClick={() => setError(null)}>x</button>
        </div>
      )}

      <div className="input-area">
        <form className="input-form" onSubmit={(e) => { e.preventDefault(); sendMessage() }}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => { setInput(e.target.value); autoResize() }}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            rows={1}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  )
}

export default App
