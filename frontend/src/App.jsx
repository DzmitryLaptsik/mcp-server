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

// --- Storage helpers ---

function getAuth() {
  try { return JSON.parse(localStorage.getItem('mcp_auth')) } catch { return null }
}
function setAuth(data) { localStorage.setItem('mcp_auth', JSON.stringify(data)) }
function clearAuth() { localStorage.removeItem('mcp_auth') }

function authHeaders(extra = {}) {
  const auth = getAuth()
  return auth?.api_key ? { ...extra, 'Authorization': `Bearer ${auth.api_key}` } : extra
}

function getSavedModel() {
  return localStorage.getItem('mcp_model') || MODELS[0].id
}
function saveModel(id) { localStorage.setItem('mcp_model', id) }

function getTheme() {
  return localStorage.getItem('mcp_theme') || 'dark'
}
function saveTheme(t) { localStorage.setItem('mcp_theme', t) }

function getDraft() { return localStorage.getItem('mcp_draft') || '' }
function saveDraft(v) { localStorage.setItem('mcp_draft', v) }

// --- Conversation persistence ---

function getConversations() {
  try { return JSON.parse(localStorage.getItem('mcp_conversations')) || [] } catch { return [] }
}
function saveConversations(list) { localStorage.setItem('mcp_conversations', JSON.stringify(list)) }

function generateId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 6) }

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

// --- Components ---

function ToolCall({ call }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className={`tool-call ${expanded ? 'expanded' : ''}`} onClick={() => setExpanded(!expanded)}>
      <div className="tool-call-header">
        <span className="tool-icon">fn</span>
        <span className="tool-name">{call.tool}</span>
        <span className="tool-arrow">&#9654;</span>
      </div>
      {expanded && (
        <div className="tool-call-detail">
          <div><strong>Input:</strong> {JSON.stringify(call.input, null, 2)}</div>
          {call.output && <div><strong>Output:</strong> {JSON.stringify(call.output, null, 2)}</div>}
        </div>
      )}
    </div>
  )
}

function Message({ message }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = (e) => {
    e.stopPropagation()
    navigator.clipboard.writeText(message.content).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className={`message ${message.role}`}>
      <div className="message-content">
        {message.role === 'assistant' ? <Markdown>{message.content}</Markdown> : message.content}
      </div>
      <div className="message-footer">
        {message.timestamp && <span className="message-time">{formatTime(message.timestamp)}</span>}
        {message.model && <span className="message-model">{message.model}</span>}
        {message.role === 'assistant' && message.content && (
          <button className="copy-btn" onClick={handleCopy}>{copied ? 'Copied!' : 'Copy'}</button>
        )}
      </div>
      {message.toolCalls?.length > 0 && (
        <div className="tool-calls">
          {message.toolCalls.map((call, i) => <ToolCall key={i} call={call} />)}
        </div>
      )}
    </div>
  )
}

function ModelSelector({ model, onChange, disabled }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])
  const current = MODELS.find(m => m.id === model) || MODELS[0]
  return (
    <div className="model-selector" ref={ref}>
      <button className="model-selector-btn" onClick={() => !disabled && setOpen(!open)} disabled={disabled}>
        <span className="model-selector-label">{current.name}</span>
        <span className="model-selector-arrow">&#9662;</span>
      </button>
      {open && (
        <div className="model-dropdown">
          {MODELS.map(m => (
            <button key={m.id} className={`model-option ${m.id === model ? 'active' : ''}`}
              onClick={() => { onChange(m.id); setOpen(false) }}>
              <span className="model-option-name">{m.name}</span>
              <span className="model-option-provider">{m.provider}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function Sidebar({ conversations, activeId, onSelect, onNew, onDelete }) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <span>Conversations</span>
        <button className="sidebar-new-btn" onClick={onNew} title="New chat">+</button>
      </div>
      <div className="sidebar-list">
        {conversations.length === 0 && (
          <div className="sidebar-empty">No conversations yet</div>
        )}
        {conversations.map(c => (
          <div key={c.id} className={`sidebar-item ${c.id === activeId ? 'active' : ''}`}
            onClick={() => onSelect(c.id)}>
            <div className="sidebar-item-title">{c.title || 'New chat'}</div>
            <div className="sidebar-item-meta">{formatTime(c.updatedAt)}</div>
            <button className="sidebar-item-delete" onClick={(e) => { e.stopPropagation(); onDelete(c.id) }}
              title="Delete">x</button>
          </div>
        ))}
      </div>
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
    setLoading(true); setError(null)
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim() }),
      })
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || 'Login failed')
      const data = await res.json()
      setAuth(data); onLogin(data)
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }
  return (
    <div className="login-screen">
      <div className="login-card">
        <h1>MCP Assistant</h1>
        <p>Enter your name to get started. Your notes, tasks, and reminders will be saved privately.</p>
        {error && <div className="error-banner">{error}</div>}
        <form onSubmit={handleSubmit}>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)}
            placeholder="Your name" autoFocus maxLength={100} disabled={loading} />
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
  const [theme, setThemeState] = useState(getTheme)
  const [conversations, setConversations] = useState(getConversations)
  const [activeConvId, setActiveConvId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState(getDraft)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [tools, setTools] = useState([])
  const [showTools, setShowTools] = useState(false)
  const [showSidebar, setShowSidebar] = useState(false)
  const [model, setModelState] = useState(getSavedModel)
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)
  const toolsPanelRef = useRef(null)

  const setModel = (id) => { setModelState(id); saveModel(id) }
  const setTheme = (t) => { setThemeState(t); saveTheme(t) }

  // Apply theme to body
  useEffect(() => {
    document.body.setAttribute('data-theme', theme)
  }, [theme])

  // Verify auth on mount
  useEffect(() => {
    if (!user?.api_key) return
    fetch('/api/auth/me', { headers: authHeaders() })
      .then(r => { if (!r.ok) { clearAuth(); setUser(null) } })
      .catch(() => {})
  }, [])

  // Load tools
  useEffect(() => {
    fetch('/api/tools').then(r => r.json()).then(data => setTools(data.tools || [])).catch(() => {})
  }, [])

  // Click outside tools panel
  useEffect(() => {
    const h = (e) => { if (toolsPanelRef.current && !toolsPanelRef.current.contains(e.target)) setShowTools(false) }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Auto-focus on load finish
  useEffect(() => {
    if (!loading && textareaRef.current) textareaRef.current.focus()
  }, [loading])

  // Save draft as user types
  useEffect(() => { saveDraft(input) }, [input])

  // Save conversation when messages change
  useEffect(() => {
    if (!activeConvId || messages.length === 0) return
    setConversations(prev => {
      const updated = prev.map(c => c.id === activeConvId
        ? { ...c, messages, updatedAt: Date.now(), title: messages[0]?.content?.slice(0, 40) || 'New chat' }
        : c
      )
      saveConversations(updated)
      return updated
    })
  }, [messages, activeConvId])

  // --- Handlers ---

  const handleLogin = (data) => { setUser(data); setMessages([]); setActiveConvId(null) }
  const handleSignOut = () => { clearAuth(); setUser(null); setMessages([]); setActiveConvId(null) }

  const handleNewChat = () => {
    setMessages([])
    setActiveConvId(null)
    setError(null)
    saveDraft('')
    setInput('')
    setShowSidebar(false)
  }

  const handleSelectConv = (id) => {
    const conv = conversations.find(c => c.id === id)
    if (conv) {
      setMessages(conv.messages || [])
      setActiveConvId(id)
      setShowSidebar(false)
    }
  }

  const handleDeleteConv = (id) => {
    setConversations(prev => {
      const updated = prev.filter(c => c.id !== id)
      saveConversations(updated)
      return updated
    })
    if (activeConvId === id) { setMessages([]); setActiveConvId(null) }
  }

  const selectTool = useCallback((template) => {
    if (!template) return
    setInput(template); setShowTools(false)
    setTimeout(() => {
      const el = textareaRef.current
      if (el) { el.focus(); const m = template.match(/\{[^}]+\}/); if (m) el.setSelectionRange(m.index, m.index + m[0].length) }
    }, 0)
  }, [])

  const autoResize = useCallback(() => {
    const el = textareaRef.current
    if (el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 120) + 'px' }
  }, [])

  const sendMessage = async (text) => {
    const userMessage = text || input.trim()
    if (!userMessage || loading) return
    setInput(''); saveDraft(''); setError(null)
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    // Create conversation if needed
    let convId = activeConvId
    if (!convId) {
      convId = generateId()
      setActiveConvId(convId)
      setConversations(prev => {
        const updated = [{ id: convId, title: userMessage.slice(0, 40), messages: [], updatedAt: Date.now() }, ...prev]
        saveConversations(updated)
        return updated
      })
    }

    const newMessages = [...messages, { role: 'user', content: userMessage, timestamp: Date.now() }]
    setMessages(newMessages)
    setLoading(true)

    try {
      const apiMessages = newMessages.map(m => ({ role: m.role, content: m.content }))
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ messages: apiMessages, model }),
      })
      if (res.status === 401) { clearAuth(); setUser(null); throw new Error('Session expired.') }
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || `HTTP ${res.status}`)

      const data = await res.json()
      setMessages([...newMessages, {
        role: 'assistant', content: data.response, toolCalls: data.tool_calls || [],
        model: MODELS.find(m => m.id === model)?.name || model, timestamp: Date.now(),
      }])
    } catch (err) {
      setError(err.message || 'Failed to send message')
    } finally {
      setLoading(false)
      setTimeout(() => textareaRef.current?.focus(), 0)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  if (!user?.api_key) return <LoginScreen onLogin={handleLogin} />

  const hasMessages = messages.length > 0

  return (
    <div className={`app-layout ${showSidebar ? 'sidebar-open' : ''}`}>
      <Sidebar
        conversations={conversations}
        activeId={activeConvId}
        onSelect={handleSelectConv}
        onNew={handleNewChat}
        onDelete={handleDeleteConv}
      />

      <div className="app">
        <div className="header">
          <div className="header-left">
            <button className="sidebar-toggle" onClick={() => setShowSidebar(!showSidebar)} title="Conversations">
              &#9776;
            </button>
            <h1>MCP Assistant</h1>
            {hasMessages && (
              <button className="new-chat-btn" onClick={handleNewChat} title="New chat">+ New</button>
            )}
          </div>
          <div className="header-right">
            <button className="theme-toggle" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}>
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
            <ModelSelector model={model} onChange={setModel} disabled={loading} />
            {tools.length > 0 && (
              <div className="tools-panel-wrapper" ref={toolsPanelRef}>
                <button className="tools-badge" onClick={() => setShowTools(!showTools)}>
                  {tools.length} tools
                </button>
                {showTools && (
                  <div className="tools-panel">
                    <div className="tools-panel-header">Connected Tools</div>
                    <div className="tools-panel-list">
                      {Object.entries(
                        tools.reduce((g, t) => { const c = t.category || 'Other'; (g[c] = g[c] || []).push(t); return g }, {})
                      ).map(([category, items]) => (
                        <div key={category} className="tools-panel-group">
                          <div className="tools-panel-category">{category}</div>
                          {items.map((t, i) => (
                            <div key={i} className={`tools-panel-item ${t.template ? 'clickable' : ''}`}
                              onClick={() => t.template && selectTool(t.template)}>
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
            <p>I have access to weather, notes, tasks, time tracking, reminders, news, and timezone tools.</p>
            <div className="suggestions">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} className="suggestion" onClick={() => sendMessage(s)}>{s}</button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages">
            {messages.map((m, i) => <Message key={i} message={m} />)}
            {loading && (
              <div className="loading">
                <div className="loading-dots"><span></span><span></span><span></span></div>
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
            <textarea ref={textareaRef} value={input}
              onChange={(e) => { setInput(e.target.value); autoResize() }}
              onKeyDown={handleKeyDown} placeholder="Type a message..." rows={1} disabled={loading} />
            <button type="submit" disabled={loading || !input.trim()}>Send</button>
          </form>
        </div>
      </div>
    </div>
  )
}

export default App
