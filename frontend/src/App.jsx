import React, { useState, useEffect, useRef } from 'react';

const API_BASE = window.location.origin.includes("5173") 
  ? "http://localhost:8000" 
  : window.location.origin;

function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [subjects, setSubjects] = useState([]);
  
  // Auth Form States
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'signup'
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authName, setAuthName] = useState('');
  const [authError, setAuthError] = useState('');
  
  // Dashboard & Subjects States
  const [newSubName, setNewSubName] = useState('');
  const [newSubDesc, setNewSubDesc] = useState('');
  const [subToDelete, setSubToDelete] = useState(null);
  const [dashStats, setDashStats] = useState({ subjects: 0, documents: 0 });

  // Upload States
  const [uploadSubId, setUploadSubId] = useState('');
  const [uploadDesc, setUploadDesc] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadWarning, setUploadWarning] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState('');

  // Chat States
  const [chatSessions, setChatSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatSubId, setChatSubId] = useState('');
  const [chatMode, setChatMode] = useState('General Chat');
  const [chatStyle, setChatStyle] = useState('Simple English');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatSearch, setChatSearch] = useState('');
  const [activeMenuSessionId, setActiveMenuSessionId] = useState(null);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const messagesEndRef = useRef(null);

  // Quiz States
  const [quizSubId, setQuizSubId] = useState('');
  const [quizTopic, setQuizTopic] = useState('');
  const [quizType, setQuizType] = useState('MCQ');
  const [quizDifficulty, setQuizDifficulty] = useState('Easy');
  const [quizCount, setQuizCount] = useState(5);
  const [quizQuestions, setQuizQuestions] = useState([]);
  const [quizAnswers, setQuizAnswers] = useState({});
  const [quizFeedback, setQuizFeedback] = useState(null);
  const [quizLoading, setQuizLoading] = useState(false);

  // Flashcard States
  const [cardSubId, setCardSubId] = useState('');
  const [cardTopic, setCardTopic] = useState('');
  const [cardCount, setCardCount] = useState(8);
  const [cards, setCards] = useState([]);
  const [cardIndex, setCardIndex] = useState(0);
  const [cardFlipped, setCardFlipped] = useState(false);
  const [cardsLoading, setCardsLoading] = useState(false);

  // Planner States
  const [planSubId, setPlanSubId] = useState('');
  const [planDate, setPlanDate] = useState('');
  const [planPrep, setPlanPrep] = useState(5);
  const [planConf, setPlanConf] = useState(5);
  const [planWeak, setPlanWeak] = useState([]);
  const [planText, setPlanText] = useState('');
  const [planLoading, setPlanLoading] = useState(false);

  // Pomodoro States
  const [pomoMode, setPomoMode] = useState('Focus'); // 'Focus', 'Short Break', 'Long Break'
  const [pomoRemaining, setPomoRemaining] = useState(25 * 60);
  const [pomoRunning, setPomoRunning] = useState(false);
  const [pomoSubId, setPomoSubId] = useState('');
  const [pomoNote, setPomoNote] = useState('');
  const [pomoSessions, setPomoSessions] = useState([]);
  const pomoTimerRef = useRef(null);

  // AI Settings States
  const [aiProvider, setAIProvider] = useState('Gemini');
  const [geminiKey, setGeminiKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [settingsStatus, setSettingsStatus] = useState(null);
  const [ocrStatus, setOcrStatus] = useState('Checking...');

  // Fetch current user and initialize app if authenticated
  useEffect(() => {
    if (token) {
      localStorage.setItem('token', token);
      fetchUser();
    } else {
      localStorage.removeItem('token');
      setUser(null);
    }
  }, [token]);

  useEffect(() => {
    if (user) {
      fetchSubjects();
      if (activeTab === 'Upload Notes') {
        fetchOcrStatus();
      }
      if (activeTab === 'Pomodoro Timer') {
        fetchPomodoroSessions();
      }
      if (activeTab === 'AI Settings') {
        fetchAISettings();
      }
    }
  }, [user, activeTab]);

  const fetchUser = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data.user);
      } else {
        logout();
      }
    } catch (e) {
      logout();
    }
  };

  const fetchOcrStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/settings/ocr`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setOcrStatus(data.status);
      }
    } catch (e) {
      setOcrStatus('Unavailable');
    }
  };

  const logout = () => {
    setToken('');
    setUser(null);
  };

  const fetchSubjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/subjects`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSubjects(data);
        setDashStats(prev => ({ ...prev, subjects: data.length }));
        if (data.length > 0) {
          if (!uploadSubId) setUploadSubId(data[0].id);
          if (!chatSubId) setChatSubId(data[0].id);
          if (!quizSubId) setQuizSubId(data[0].id);
          if (!cardSubId) setCardSubId(data[0].id);
          if (!planSubId) setPlanSubId(data[0].id);
          if (!pomoSubId) setPomoSubId(data[0].id);
        }
      }
    } catch (e) {}
  };

  // --- Auth Handlers ---
  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthError('');
    const endpoint = authMode === 'login' ? 'login' : 'signup';
    const body = authMode === 'login' 
      ? { email: authEmail, password: authPassword }
      : { name: authName, email: authEmail, password: authPassword };

    try {
      const res = await fetch(`${API_BASE}/api/auth/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (res.ok) {
        setToken(data.token);
      } else {
        setAuthError(data.detail || 'Authentication failed');
      }
    } catch (err) {
      setAuthError('Server connection error');
    }
  };

  // --- Subjects Handlers ---
  const handleAddSubject = async (e) => {
    e.preventDefault();
    if (!newSubName.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/api/subjects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name: newSubName, description: newSubDesc })
      });
      if (res.ok) {
        setNewSubName('');
        setNewSubDesc('');
        fetchSubjects();
      } else {
        const err = await res.json();
        alert(err.detail || 'Could not create subject');
      }
    } catch (err) {}
  };

  const handleDeleteSubject = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/subjects/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        setSubToDelete(null);
        fetchSubjects();
      }
    } catch (e) {}
  };

  // --- File Upload ---
  const handleUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile || !uploadSubId) return;
    setUploading(true);
    setUploadWarning('');
    setUploadSuccess('');
    
    const formData = new FormData();
    formData.append('subject_id', uploadSubId);
    formData.append('description', uploadDesc);
    formData.append('file', uploadFile);

    try {
      const res = await fetch(`${API_BASE}/api/documents/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setUploadSuccess(`Successfully processed document! Indexed ${data.saved_chunks} searchable chunks.`);
        setUploadFile(null);
        setUploadDesc('');
        if (data.warning) setUploadWarning(data.warning);
      } else {
        setUploadWarning(data.detail || 'Processing failed');
      }
    } catch (err) {
      setUploadWarning('Server connection failed during upload');
    } finally {
      setUploading(false);
    }
  };

  // --- Chat Handlers ---
  useEffect(() => {
    if (activeTab === 'Chat With Notes') {
      fetchChatSessions();
    }
  }, [activeTab, chatSubId]);

  useEffect(() => {
    if (activeSessionId) {
      fetchChatMessages(activeSessionId);
    } else {
      setChatMessages([]);
    }
  }, [activeSessionId]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages]);

  const fetchChatSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/chat/sessions?subject_id=${chatSubId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setChatSessions(data);
        if (data.length > 0 && !activeSessionId) {
          setActiveSessionId(data[0].id);
        }
      }
    } catch (e) {}
  };

  const fetchChatMessages = async (sid) => {
    try {
      const res = await fetch(`${API_BASE}/api/chat/messages/${sid}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setChatMessages(data);
      }
    } catch (e) {}
  };

  const handleCreateChatSession = async () => {
    if (!chatSubId) return;
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          question: "Hello! Set up my study workspace.",
          chat_mode: chatMode,
          subject_id: parseInt(chatSubId),
          answer_style: chatStyle
        })
      });
      if (res.ok) {
        const data = await res.json();
        fetchChatSessions();
        setActiveSessionId(data.session_id);
      }
    } catch (e) {}
  };

  const handleSendChatMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;
    const userMsg = chatInput;
    setChatInput('');
    setChatLoading(true);

    // Append user message locally for instant display
    setChatMessages(prev => [...prev, { role: 'user', content: userMsg }]);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          question: userMsg,
          chat_mode: chatMode,
          subject_id: chatSubId ? parseInt(chatSubId) : null,
          answer_style: chatStyle,
          session_id: activeSessionId
        })
      });
      if (res.ok) {
        const data = await res.json();
        if (!activeSessionId) {
          setActiveSessionId(data.session_id);
          fetchChatSessions();
        } else {
          fetchChatMessages(activeSessionId);
        }
      }
    } catch (err) {
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'Connection to server lost. Please retry.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  // --- Quiz Handlers ---
  const handleGenerateQuiz = async (e) => {
    e.preventDefault();
    if (!quizSubId) return;
    setQuizLoading(true);
    setQuizQuestions([]);
    setQuizAnswers({});
    setQuizFeedback(null);

    try {
      const res = await fetch(`${API_BASE}/api/quiz/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          subject_id: parseInt(quizSubId),
          topic: quizTopic,
          question_type: quizType,
          difficulty: quizDifficulty,
          question_count: parseInt(quizCount)
        })
      });
      const data = await res.json();
      if (res.ok) {
        setQuizQuestions(data.questions);
      } else {
        alert(data.detail || 'Could not generate quiz');
      }
    } catch (err) {
      alert('Network failure');
    } finally {
      setQuizLoading(false);
    }
  };

  const handleCheckQuiz = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/api/quiz/check`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          questions: quizQuestions,
          user_answers: quizAnswers
        })
      });
      const data = await res.json();
      if (res.ok) {
        setQuizFeedback(data.results);
      }
    } catch (e) {}
  };

  // --- Flashcard Handlers ---
  const handleGenerateCards = async (e) => {
    e.preventDefault();
    if (!cardSubId) return;
    setCardsLoading(true);
    setCards([]);
    setCardIndex(0);
    setCardFlipped(false);

    try {
      const res = await fetch(`${API_BASE}/api/flashcards/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          subject_id: parseInt(cardSubId),
          topic: cardTopic,
          card_count: parseInt(cardCount)
        })
      });
      const data = await res.json();
      if (res.ok) {
        setCards(data.flashcards);
      } else {
        alert(data.detail || 'Could not generate cards');
      }
    } catch (err) {} finally {
      setCardsLoading(false);
    }
  };

  // --- Revision Planner ---
  const handleGeneratePlan = async (e) => {
    e.preventDefault();
    if (!planSubId || !planDate) return;
    setPlanLoading(true);
    setPlanText('');

    const sub = subjects.find(s => s.id === parseInt(planSubId));

    try {
      const res = await fetch(`${API_BASE}/api/planner/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          subject_name: sub ? sub.name : 'Subject',
          subject_id: parseInt(planSubId),
          exam_date: planDate,
          preparation_level: planPrep,
          confidence_level: planConf,
          weak_topics: planWeak
        })
      });
      const data = await res.json();
      if (res.ok) {
        setPlanText(data.plan_text);
      } else {
        alert(data.detail || 'Could not create plan');
      }
    } catch (e) {} finally {
      setPlanLoading(false);
    }
  };

  // --- Pomodoro Timers ---
  useEffect(() => {
    if (pomoRunning) {
      pomoTimerRef.current = setInterval(() => {
        setPomoRemaining(prev => {
          if (prev <= 1) {
            setPomoRunning(false);
            clearInterval(pomoTimerRef.current);
            alert("Timer session completed! Save your minutes.");
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      clearInterval(pomoTimerRef.current);
    }
    return () => clearInterval(pomoTimerRef.current);
  }, [pomoRunning]);

  const handlePomoModeChange = (mode) => {
    setPomoMode(mode);
    setPomoRunning(false);
    if (mode === 'Focus') setPomoRemaining(25 * 60);
    if (mode === 'Short Break') setPomoRemaining(5 * 60);
    if (mode === 'Long Break') setPomoRemaining(15 * 60);
  };

  const handleSavePomoSession = async () => {
    const defaultMinutes = pomoMode === 'Focus' ? 25 : pomoMode === 'Short Break' ? 5 : 15;
    const duration = pomoRemaining === 0 
      ? defaultMinutes 
      : Math.max(1, Math.floor((defaultMinutes * 60 - pomoRemaining) / 60));
      
    try {
      const res = await fetch(`${API_BASE}/api/pomodoro/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          subject_id: pomoSubId ? parseInt(pomoSubId) : null,
          duration_minutes: duration,
          session_type: pomoMode,
          notes: pomoNote
        })
      });
      if (res.ok) {
        setPomoNote('');
        setPomoRemaining(defaultMinutes * 60);
        fetchPomodoroSessions();
        alert("Pomodoro study session saved!");
      }
    } catch (e) {}
  };

  const fetchPomodoroSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/pomodoro/sessions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setPomoSessions(data);
      }
    } catch (e) {}
  };

  // --- AI Settings Handlers ---
  const fetchAISettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/settings/ai`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAIProvider(data.provider);
        setSettingsStatus(data);
      }
    } catch (e) {}
  };

  const handleSaveAISettings = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/api/settings/ai`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          provider: aiProvider,
          gemini_api_key: geminiKey,
          openai_api_key: openaiKey
        })
      });
      if (res.ok) {
        setGeminiKey('');
        setOpenaiKey('');
        fetchAISettings();
        alert("AI Configuration saved securely!");
      }
    } catch (e) {}
  };

  // Custom hook/renderer for Plotly components
  const PlotlyChart = ({ jsonStr }) => {
    const elRef = useRef(null);
    useEffect(() => {
      if (elRef.current && jsonStr && window.Plotly) {
        try {
          const figure = JSON.parse(jsonStr);
          window.Plotly.newPlot(elRef.current, figure.data, figure.layout, { responsive: true });
        } catch (e) {
          console.error("Plotly rendering failed", e);
        }
      }
    }, [jsonStr]);
    return <div ref={elRef} className="plotly-plot-container" style={{ width: '100%', height: '400px' }} />;
  };

  // If not authenticated, render Auth Layout
  if (!user) {
    return (
      <div className="auth-container">
        <div className="auth-shell glass-card">
          <div className="auth-header">
            <div className="auth-kicker">Secure Study Workspace</div>
            <h1 className="auth-title">StudyMate AI</h1>
            <p className="auth-subtitle">Learn smarter. Revise faster. Prepare better.</p>
          </div>
          <div className="auth-tabs">
            <div className={`auth-tab ${authMode === 'login' ? 'active' : ''}`} onClick={() => setAuthMode('login')}>Log In</div>
            <div className={`auth-tab ${authMode === 'signup' ? 'active' : ''}`} onClick={() => setAuthMode('signup')}>Sign Up</div>
          </div>
          <form onSubmit={handleAuth}>
            {authMode === 'signup' && (
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input className="form-control" type="text" placeholder="Your name" value={authName} onChange={e => setAuthName(e.target.value)} required />
              </div>
            )}
            <div className="form-group">
              <label className="form-label">Email</label>
              <input className="form-control" type="email" placeholder="you@example.com" value={authEmail} onChange={e => setAuthEmail(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input className="form-control" type="password" placeholder="••••••••" value={authPassword} onChange={e => setAuthPassword(e.target.value)} required />
            </div>
            {authError && <div style={{ color: 'var(--color-secondary)', fontSize: '13px', marginBottom: '14px' }}>{authError}</div>}
            <button className="btn btn-primary" style={{ width: '100%' }} type="submit">
              {authMode === 'login' ? 'Log In' : 'Create Account'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Helper render for Active Views
  const renderActiveView = () => {
    switch (activeTab) {
      case 'Dashboard':
        return (
          <div>
            <div className="page-header">
              <div className="page-kicker">Tutor Lounge</div>
              <h2 className="page-title">Welcome back, {user.name}</h2>
              <p className="page-subtitle">Organize your study files, chat with notes, and test recall.</p>
            </div>
            
            <div className="dashboard-grid">
              <div className="glass-card metric-card">
                <div className="metric-icon" style={{ background: '#d8fff6', color: '#14b8b4' }}>📚</div>
                <div className="metric-details">
                  <h3>{dashStats.subjects}</h3>
                  <p>Study Subjects</p>
                </div>
              </div>
              <div className="glass-card metric-card">
                <div className="metric-icon" style={{ background: '#e3efff', color: '#2f7df6' }}>💬</div>
                <div className="metric-details">
                  <h3>{chatSessions.length}</h3>
                  <p>Study Chats</p>
                </div>
              </div>
            </div>

            <div className="section-title-bar">
              <h3>My Study Subjects</h3>
            </div>

            <div className="subjects-list">
              {subjects.map(sub => (
                <div key={sub.id} className="glass-card subject-card" onClick={() => { setChatSubId(sub.id); setActiveTab('Chat With Notes'); }}>
                  <div className="subject-header">
                    <h4 className="subject-title">{sub.name}</h4>
                    <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '12px' }} onClick={(e) => { e.stopPropagation(); setSubToDelete(sub.id); }}>Delete</button>
                  </div>
                  <p className="subject-desc">{sub.description || 'No description provided.'}</p>
                </div>
              ))}
              
              <form onSubmit={handleAddSubject} className="glass-card flex-center" style={{ borderStyle: 'dashed', flexDirection: 'column', gap: '12px' }}>
                <input className="form-control" type="text" placeholder="Subject Name (e.g. Physics)" value={newSubName} onChange={e => setNewSubName(e.target.value)} required />
                <input className="form-control" type="text" placeholder="Short description" value={newSubDesc} onChange={e => setNewSubDesc(e.target.value)} />
                <button className="btn btn-primary" type="submit" style={{ width: '100%' }}>Add Subject</button>
              </form>
            </div>

            {subToDelete && (
              <div className="glass-card" style={{ maxWidth: '400px', margin: '20px auto', border: '1px solid var(--color-secondary)' }}>
                <h4 style={{ marginBottom: '8px' }}>Are you sure?</h4>
                <p style={{ fontSize: '13px', color: 'var(--color-muted)', marginBottom: '16px' }}>Deleting this subject will permanently clear its documents, flashcards, and vector indexes.</p>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <button className="btn btn-danger" onClick={() => handleDeleteSubject(subToDelete)}>Yes, delete</button>
                  <button className="btn btn-secondary" onClick={() => setSubToDelete(null)}>Cancel</button>
                </div>
              </div>
            )}
          </div>
        );

      case 'Upload Notes':
        return (
          <div>
            <div className="page-header">
              <div className="page-kicker">Knowledge Builder</div>
              <h2 className="page-title">Upload Notes</h2>
              <p className="page-subtitle">Extract selectable text and save vectors subject-wise for AI search.</p>
            </div>

            <div className="glass-card" style={{ maxWidth: '600px', margin: '0 auto' }}>
              <div style={{
                background: 'rgba(47, 125, 246, 0.06)',
                border: '1px solid rgba(47, 125, 246, 0.15)',
                borderRadius: 'var(--radius-md)',
                padding: '12px 16px',
                marginBottom: '20px',
                fontSize: '13.5px',
                color: 'var(--color-charcoal)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span style={{ fontSize: '16px' }}>ℹ️</span>
                <span><strong>OCR Status:</strong> {ocrStatus}. Image/scanned notes may be limited if OCR is unavailable.</span>
              </div>

              <form onSubmit={handleUpload}>
                <div className="form-group">
                  <label className="form-label">Select Subject</label>
                  <select className="form-control" value={uploadSubId} onChange={e => setUploadSubId(e.target.value)}>
                    {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Document Description</label>
                  <textarea className="form-control" placeholder="Optional: chapter info, lecture note name..." value={uploadDesc} onChange={e => setUploadDesc(e.target.value)} rows="3" />
                </div>
                <div className="form-group">
                  <label className="form-label">Upload File (PDF, Images, DOCX, PPTX, TXT)</label>
                  <input className="form-control" type="file" onChange={e => setUploadFile(e.target.files[0])} required />
                </div>
                {uploadWarning && <div style={{ color: 'var(--color-secondary)', fontSize: '13px', marginBottom: '12px' }}>{uploadWarning}</div>}
                {uploadSuccess && <div style={{ color: 'var(--color-teal)', fontSize: '13px', marginBottom: '12px' }}>{uploadSuccess}</div>}
                <button className="btn btn-primary" type="submit" style={{ width: '100%' }} disabled={uploading}>
                  {uploading ? 'Processing Notes...' : 'Upload & Process Document'}
                </button>
              </form>
            </div>
          </div>
        );

      case 'Chat With Notes': {
        const groupSessions = (sessionsList) => {
          const today = [];
          const yesterday = [];
          const previous7 = [];
          const older = [];
          
          const now = new Date();
          const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
          const startOfYesterday = new Date(startOfToday.getTime() - 24 * 60 * 60 * 1000);
          const startOf7DaysAgo = new Date(startOfToday.getTime() - 7 * 24 * 60 * 60 * 1000);

          sessionsList.forEach(session => {
            let date;
            try {
              date = new Date(session.created_at || session.updated_at);
              if (isNaN(date.getTime())) {
                date = new Date();
              }
            } catch (e) {
              date = new Date();
            }

            if (date >= startOfToday) {
              today.push(session);
            } else if (date >= startOfYesterday) {
              yesterday.push(session);
            } else if (date >= startOf7DaysAgo) {
              previous7.push(session);
            } else {
              older.push(session);
            }
          });

          return { today, yesterday, previous7, older };
        };

        const getSubjectBadgeStyle = (subName) => {
          const name = (subName || '').toLowerCase();
          if (name.includes('math') || name.includes('calculus') || name.includes('integral')) {
            return { bg: '#e0f2fe', color: '#0369a1', label: 'Math' };
          }
          if (name.includes('physics') || name.includes('motion')) {
            return { bg: '#f3e8ff', color: '#6b21a8', label: 'Physics' };
          }
          if (name.includes('chemistry') || name.includes('organic')) {
            return { bg: '#d1fae5', color: '#065f46', label: 'Chemistry' };
          }
          if (name.includes('db') || name.includes('sql') || name.includes('database')) {
            return { bg: '#ecfdf5', color: '#047857', label: 'Database' };
          }
          if (name.includes('stat') || name.includes('normal')) {
            return { bg: '#fef3c7', color: '#92400e', label: 'Statistics' };
          }
          return { bg: '#f1f5f9', color: '#475569', label: subName ? subName.slice(0, 10) : 'Study' };
        };

        const renderAIResponseContent = (msg) => {
          let content = msg.content || '';
          
          let explanation = "";
          let examTip = "";
          let commonMistake = "";
          let mainBody = content;

          // Check for sections
          const explanationRegex = /(?:\n|^)(?:###\s+Explanation|\*\*Explanation:\*\*|Explanation:)\s*([\s\S]*?)(?=\n(?:###|\*\*|\n|$))/i;
          const examTipRegex = /(?:\n|^)(?:###\s+Exam\s+Tip|\*\*Exam\s+Tip:\*\*|Exam\s+Tip:)\s*([\s\S]*?)(?=\n(?:###|\*\*|\n|$))/i;
          const commonMistakeRegex = /(?:\n|^)(?:###\s+Common\s+Mistake|\*\*Common\s+Mistake:\*\*|Common\s+Mistake:)\s*([\s\S]*?)(?=\n(?:###|\*\*|\n|$))/i;

          const expMatch = content.match(explanationRegex);
          if (expMatch) {
            explanation = expMatch[1].trim();
            mainBody = mainBody.replace(explanationRegex, "");
          }

          const tipMatch = content.match(examTipRegex);
          if (tipMatch) {
            examTip = tipMatch[1].trim();
            mainBody = mainBody.replace(examTipRegex, "");
          }

          const mistakeMatch = content.match(commonMistakeRegex);
          if (mistakeMatch) {
            commonMistake = mistakeMatch[1].trim();
            mainBody = mainBody.replace(commonMistakeRegex, "");
          }

          mainBody = mainBody.trim();

          const parseMarkdownToHtml = (text) => {
            if (!text) return '';
            return text
              .replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
              .replace(/\*([^*]+)\*/g, '<em>$1</em>')
              .replace(/`([^`]+)`/g, '<code>$1</code>')
              .replace(/\n/g, '<br/>');
          };

          // Find math visualizations
          let hasGraph = false;
          let graphElement = null;
          
          let visList = [];
          if (msg.metadata) {
            try {
              const parsedMeta = typeof msg.metadata === 'string' ? JSON.parse(msg.metadata) : msg.metadata;
              if (parsedMeta.math_visualizations) {
                visList = parsedMeta.math_visualizations;
              }
            } catch(e) {}
          }

          visList.forEach((vis, idx) => {
            if (vis.figure_json) {
              hasGraph = true;
              graphElement = <PlotlyChart key={idx} jsonStr={vis.figure_json} />;
            }
          });

          // Check if code block generated
          const codeRegex = /```(\w*)\n([\s\S]*?)```/g;
          const codeMatches = [...mainBody.matchAll(codeRegex)];
          if (codeMatches.length > 0) {
            mainBody = mainBody.replace(codeRegex, (match, lang, code) => {
              return `<pre className="syntax-code-block"><code className="language-${lang}">${code.trim()}</code></pre>`;
            });
          }

          const parsedHtml = parseMarkdownToHtml(mainBody);

          return (
            <div className="structured-ai-response">
              {hasGraph ? (
                <div className="math-split-card">
                  <div className="math-split-left">
                    {graphElement}
                  </div>
                  <div className="math-split-right">
                    <h5>Step-by-Step Solution</h5>
                    <div dangerouslySetInnerHTML={{ __html: parsedHtml }} />
                  </div>
                </div>
              ) : (
                <div dangerouslySetInnerHTML={{ __html: parsedHtml }} />
              )}
              
              {explanation && (
                <div className="response-explanation-block">
                  <h6>Explanation</h6>
                  <p dangerouslySetInnerHTML={{ __html: parseMarkdownToHtml(explanation) }} />
                </div>
              )}

              {(examTip || commonMistake) && (
                <div className="side-cards-container">
                  {examTip && (
                    <div className="tip-card">
                      <h6>💡 Exam Tip</h6>
                      <p dangerouslySetInnerHTML={{ __html: parseMarkdownToHtml(examTip) }} />
                    </div>
                  )}
                  {commonMistake && (
                    <div className="mistake-card">
                      <h6>⚠️ Common Mistake</h6>
                      <p dangerouslySetInnerHTML={{ __html: parseMarkdownToHtml(commonMistake) }} />
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        };

        const handleKeyDownInput = (e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendChatMessage(e);
          }
        };

        const activeSub = subjects.find(s => s.id === parseInt(chatSubId));
        const filteredSessions = chatSessions.filter(s => 
          s.title && s.title.toLowerCase().includes(chatSearch.toLowerCase())
        );
        const grouped = groupSessions(filteredSessions);

        return (
          <div className="chat-workspace-redesign">
            {/* LEFT PANEL: Chat History Sidebar */}
            <div className="chat-history-sidebar">
              <div className="chat-history-sidebar-header">
                <span>💬</span>
                <span>Chat History</span>
              </div>
              
              <button className="new-chat-btn" onClick={handleCreateChatSession}>
                <span>+</span> New Chat
              </button>
              
              <div className="chat-search-container">
                <span className="chat-search-icon">🔍</span>
                <input 
                  className="chat-search-input" 
                  placeholder="Search chats..." 
                  value={chatSearch}
                  onChange={e => setChatSearch(e.target.value)}
                />
              </div>
              
              <div className="chat-sessions-scroll">
                {['today', 'yesterday', 'previous7', 'older'].map(category => {
                  const sessions = grouped[category];
                  if (!sessions || sessions.length === 0) return null;
                  
                  const label = category === 'today' ? 'Today' : 
                                category === 'yesterday' ? 'Yesterday' : 
                                category === 'previous7' ? 'Previous 7 Days' : 'Older';
                                
                  return (
                    <div key={category}>
                      <div className="history-category-label">{label}</div>
                      {sessions.map(session => {
                        const sub = subjects.find(s => s.id === session.subject_id);
                        const badge = getSubjectBadgeStyle(sub?.name);
                        
                        return (
                          <div 
                            key={session.id} 
                            className={`history-session-card ${activeSessionId === session.id ? 'active' : ''}`}
                            onClick={() => setActiveSessionId(session.id)}
                          >
                            <div className="history-card-title">{session.title || 'Untitled Chat'}</div>
                            <div className="history-card-footer">
                              <span className="subject-tag-pill" style={{ background: badge.bg, color: badge.color }}>
                                {badge.label}
                              </span>
                              <span className="history-card-time">
                                {new Date(session.created_at || session.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                            
                            {/* Three-dots actions menu */}
                            <div className="session-actions-menu">
                              <button className="three-dots-btn" onClick={(e) => {
                                e.stopPropagation();
                                setActiveMenuSessionId(activeMenuSessionId === session.id ? null : session.id);
                              }}>⋮</button>
                              
                              {activeMenuSessionId === session.id && (
                                <div className="session-card-popover">
                                  <div onClick={(e) => { e.stopPropagation(); handleRenameChatSession(session.id, session.title); setActiveMenuSessionId(null); }}>
                                    ✏️ Rename
                                  </div>
                                  <div style={{ color: 'red' }} onClick={(e) => { e.stopPropagation(); handleDeleteChatSession(session.id); setActiveMenuSessionId(null); }}>
                                    🗑️ Delete
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  );
                })}
                {chatSessions.length === 0 && (
                  <p style={{ textAlign: 'center', fontSize: '12px', color: 'var(--color-muted)', marginTop: '20px' }}>No saved chats yet.</p>
                )}
              </div>
              
              <button className="view-all-chats-btn" onClick={() => setChatSearch('')}>View All Chats</button>
            </div>
            
            {/* CENTER PANEL: Main Chat Workspace */}
            <div className="chat-center-panel">
              <div className="chat-workspace-header">
                <div>
                  <h2 className="chat-header-title">Chat With Notes</h2>
                  <p className="chat-header-subtitle">Ask from notes, documents, voice, images, or general AI knowledge.</p>
                </div>
                <div className="chat-header-actions">
                  <button className="header-action-btn" onClick={() => alert("Guide: Ask study queries, upload math problems to plot integrations or shade graphs.")}>
                    <span>📖</span> Guide
                  </button>
                  <button className="header-action-btn" onClick={() => setShowRightPanel(!showRightPanel)}>
                    <span>ℹ️</span> Details
                  </button>
                </div>
              </div>
              
              {/* Controls card */}
              <div className="chat-controls-card">
                <div className="chat-control-select-group">
                  <span className="chat-control-label">Chat Mode</span>
                  <select className="chat-control-select" value={chatMode} onChange={e => setChatMode(e.target.value)}>
                    <option value="General Chat">General Chat</option>
                    <option value="Chat with Subject">Chat with Subject</option>
                    <option value="Teach Me Mode">Teach Me Mode</option>
                  </select>
                </div>
                
                <div className="chat-control-select-group">
                  <span className="chat-control-label">Answer Style</span>
                  <select className="chat-control-select" value={chatStyle} onChange={e => setChatStyle(e.target.value)}>
                    <option value="Simple English">Simple English</option>
                    <option value="Roman Urdu">Roman Urdu</option>
                    <option value="Exam Style">Exam Style</option>
                  </select>
                </div>
                
                <div className="chat-control-select-group">
                  <span className="chat-control-label">Context</span>
                  <select className="chat-control-select" value={chatSubId} onChange={e => { setChatSubId(e.target.value); setActiveSessionId(null); }}>
                    {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
                
                <div className="provider-info-box">
                  <span style={{ fontSize: '14px' }}>✨</span>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontSize: '10px', color: '#94a3b8', fontWeight: '700' }}>AI PROVIDER</span>
                    <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-charcoal)' }}>
                      {aiProvider} 1.5 Pro <span className="status-dot-green"></span>
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Conversation stream */}
              <div className="conversation-scroll-panel">
                {chatMessages.length === 0 ? (
                  <div className="chat-welcome-container">
                    <div className="welcome-sparkle-logo">✨</div>
                    <h3 style={{ fontSize: '18px', fontWeight: '800' }}>StudyMate AI Tutor Workspace</h3>
                    <p style={{ color: 'var(--color-muted)', fontSize: '13.5px', marginTop: '6px', maxWidth: '460px' }}>
                      Choose a subject, load study notes, and ask me to explain topics, solve math, or write practice sheets.
                    </p>
                    
                    <div className="suggested-prompts-grid">
                      <div className="suggested-prompt-card" onClick={() => setChatInput("Plot the graph of y = sin(x) from -pi to pi step by step.")}>
                        <h6>📈 Plot y = sin(x)</h6>
                        <p>Analyze and plot standard trigonometric graphs step by step.</p>
                      </div>
                      <div className="suggested-prompt-card" onClick={() => setChatInput("Plot the area of y = x^2 and shade region from x=0 to x=2.")}>
                        <h6>📐 Double Integral Shading</h6>
                        <p>Calculate double integral regions and display shaded boundary areas.</p>
                      </div>
                      <div className="suggested-prompt-card" onClick={() => setChatInput("Explain Normal Distribution with real world examples.")}>
                        <h6>📊 Normal Distribution</h6>
                        <p>Break down statistics concepts with examples and exam tips.</p>
                      </div>
                      <div className="suggested-prompt-card" onClick={() => setChatInput("Write an overview of SQL Join types.")}>
                        <h6>🗄️ SQL Join Types</h6>
                        <p>Understand relational database join concepts and common mistakes.</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  chatMessages.map((msg, i) => (
                    <div key={i} className={`msg-bubble-wrapper ${msg.role}`}>
                      {msg.role === 'assistant' && (
                        <div className="assistant-avatar-circle">✨</div>
                      )}
                      <div className={`msg-bubble ${msg.role}`}>
                        {msg.role === 'user' ? (
                          <div>
                            <div style={{ wordBreak: 'break-word' }}>{msg.content}</div>
                            <div className="msg-time-ticks">
                              <span>10:24 AM</span>
                              <span style={{ color: '#6366f1' }}>✓✓</span>
                            </div>
                          </div>
                        ) : (
                          <div>
                            {renderAIResponseContent(msg)}
                            
                            {/* AI Response actions footer */}
                            <div className="ai-response-actions-row">
                              <button className="action-row-btn" onClick={() => {
                                navigator.clipboard.writeText(msg.content);
                                alert("Response copied to clipboard!");
                              }}>
                                📋 Copy
                              </button>
                              <button className="action-row-btn" onClick={() => alert("Graph download started...")}>
                                💾 Download Graph
                              </button>
                              <button className="action-row-btn" onClick={() => alert("Saved to study notes successfully!")}>
                                ⭐️ Save as Note
                              </button>
                              <button className="action-row-btn" style={{ marginLeft: 'auto' }}>👍</button>
                              <button className="action-row-btn">👎</button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
                
                {chatLoading && (
                  <div className="msg-bubble-wrapper assistant">
                    <div className="assistant-avatar-circle">✨</div>
                    <div className="msg-bubble assistant" style={{ background: '#f8fafc' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#6366f1', fontWeight: '600' }}>
                        <div className="status-dot-green" style={{ animation: 'pulse 1s infinite' }}></div>
                        AI is thinking...
                      </div>
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>
              
              {/* Sticky bottom input */}
              <div className="sticky-input-container">
                <textarea 
                  className="chat-input-textarea" 
                  placeholder="Ask anything about your notes..." 
                  value={chatInput} 
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={handleKeyDownInput}
                  rows={2}
                />
                <div className="chat-input-toolbar">
                  <div className="toolbar-left-btns">
                    <button className="toolbar-btn" onClick={() => alert("File attachment explorer opened...")}>
                      ➕ Attach
                    </button>
                    <button className="toolbar-btn" onClick={() => alert("Voice transcription active... speak now.")}>
                      🎤 Voice
                    </button>
                  </div>
                  <button 
                    className="send-circle-btn" 
                    onClick={handleSendChatMessage}
                    disabled={!chatInput.trim() || chatLoading}
                  >
                    ✈️
                  </button>
                </div>
              </div>
            </div>
            
            {/* RIGHT PANEL: Collapsible Details Panel */}
            {showRightPanel && (
              <div className="chat-right-panel">
                <h5>Context Details</h5>
                
                <div className="context-detail-card">
                  <h6>Selected Subject</h6>
                  <p>{activeSub?.name || 'No subject active'}</p>
                </div>
                
                <div className="context-detail-card">
                  <h6>Description</h6>
                  <p style={{ fontSize: '11px', color: '#64748b' }}>
                    {activeSub?.description || 'No subject description configured.'}
                  </p>
                </div>

                <div className="context-detail-card">
                  <h6>OCR Subsystem Status</h6>
                  <p style={{ fontSize: '11px', color: '#10b981', fontWeight: '700' }}>
                    🟢 {ocrStatus}
                  </p>
                </div>

                <div className="context-detail-card">
                  <h6>Memory Profile</h6>
                  <p style={{ fontSize: '11.5px', color: '#64748b' }}>
                    Active and ready to load preferences.
                  </p>
                </div>

                <div className="context-detail-card" style={{ marginTop: 'auto' }}>
                  <h6>Quick Actions</h6>
                  <button className="btn btn-primary" style={{ width: '100%', padding: '8px', fontSize: '11.5px', marginBottom: '8px' }} onClick={() => setActiveTab('Quiz Mode')}>
                    ✏️ Generate Subject Quiz
                  </button>
                  <button className="btn btn-secondary" style={{ width: '100%', padding: '8px', fontSize: '11.5px' }} onClick={() => setActiveTab('Flashcards')}>
                    ⚡ Study Flashcards
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      }

      case 'Quiz Mode':
        return (
          <div>
            <div className="page-header">
              <div className="page-kicker">Self Evaluation</div>
              <h2 className="page-title">Quiz Mode</h2>
              <p className="page-subtitle">Test active recall and identify topics that need revision.</p>
            </div>

            <div className="grid-cols-2">
              <div className="glass-card">
                <form onSubmit={handleGenerateQuiz}>
                  <div className="form-group">
                    <label className="form-label">Subject</label>
                    <select className="form-control" value={quizSubId} onChange={e => setQuizSubId(e.target.value)}>
                      {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Quiz Topic</label>
                    <input className="form-control" type="text" placeholder="e.g. thermodynamics" value={quizTopic} onChange={e => setQuizTopic(e.target.value)} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Question Type</label>
                    <select className="form-control" value={quizType} onChange={e => setQuizType(e.target.value)}>
                      <option value="MCQ">Multiple Choice (MCQ)</option>
                      <option value="Short">Short Answer</option>
                      <option value="Long">Long Explanation</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Difficulty</label>
                    <select className="form-control" value={quizDifficulty} onChange={e => setQuizDifficulty(e.target.value)}>
                      <option value="Easy">Easy</option>
                      <option value="Medium">Medium</option>
                      <option value="Hard">Hard</option>
                    </select>
                  </div>
                  <button className="btn btn-primary" type="submit" style={{ width: '100%' }} disabled={quizLoading}>
                    {quizLoading ? 'Generating Quiz...' : 'Generate Quiz'}
                  </button>
                </form>
              </div>

              <div className="glass-card">
                {quizQuestions.length === 0 && <div className="empty-state"><p>Configure settings and generate a quiz to start testing.</p></div>}
                
                {quizQuestions.length > 0 && (
                  <form onSubmit={handleCheckQuiz}>
                    {quizQuestions.map((q, i) => (
                      <div key={i} style={{ marginBottom: '20px' }}>
                        <p style={{ fontWeight: '700' }}>{i + 1}. {q.question}</p>
                        {q.options && q.options.length > 0 ? (
                          <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {q.options.map((opt, oIdx) => (
                              <label key={oIdx} style={{ fontSize: '14px', cursor: 'pointer', display: 'flex', gap: '8px' }}>
                                <input type="radio" name={`q_${i}`} value={opt} checked={quizAnswers[i] === opt} onChange={e => setQuizAnswers({ ...quizAnswers, [i]: e.target.value })} />
                                {opt}
                              </label>
                            ))}
                          </div>
                        ) : (
                          <textarea className="form-control" style={{ marginTop: '8px' }} placeholder="Type your answer..." value={quizAnswers[i] || ''} onChange={e => setQuizAnswers({ ...quizAnswers, [i]: e.target.value })} />
                        )}

                        {quizFeedback && quizFeedback[i] && (
                          <div style={{ marginTop: '8px', padding: '10px', borderRadius: '8px', background: quizFeedback[i].marks === 1 ? '#d8fff6' : '#ffe3e9', fontSize: '13px' }}>
                            <strong>Marks: {quizFeedback[i].marks} / 1</strong><br/>
                            {quizFeedback[i].feedback}<br/>
                            {quizFeedback[i].correct_answer && <span>Correct Answer: {quizFeedback[i].correct_answer}</span>}
                          </div>
                        )}
                      </div>
                    ))}
                    {!quizFeedback && <button className="btn btn-primary" type="submit" style={{ width: '100%' }}>Submit Answers</button>}
                  </form>
                )}
              </div>
            </div>
          </div>
        );

      case 'Flashcards':
        return (
          <div>
            <div className="page-header">
              <div className="page-kicker">Active Recall</div>
              <h2 className="page-title">Flashcards</h2>
              <p className="page-subtitle">Review question and answer cards generated from your notes.</p>
            </div>

            <div className="grid-cols-2">
              <div className="glass-card">
                <form onSubmit={handleGenerateCards}>
                  <div className="form-group">
                    <label className="form-label">Subject</label>
                    <select className="form-control" value={cardSubId} onChange={e => setCardSubId(e.target.value)}>
                      {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Topic</label>
                    <input className="form-control" type="text" placeholder="e.g. mitosis" value={cardTopic} onChange={e => setCardTopic(e.target.value)} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Card Count</label>
                    <input className="form-control" type="number" value={cardCount} onChange={e => setCardCount(e.target.value)} />
                  </div>
                  <button className="btn btn-primary" type="submit" style={{ width: '100%' }} disabled={cardsLoading}>
                    {cardsLoading ? 'Generating Cards...' : 'Generate & Save Flashcards'}
                  </button>
                </form>
              </div>

              <div className="glass-card flex-center" style={{ flexDirection: 'column' }}>
                {cards.length === 0 && <div className="empty-state"><p>No flashcards generated for this topic yet.</p></div>}
                
                {cards.length > 0 && (
                  <div style={{ width: '100%' }}>
                    <div className={`flashcard-wrapper ${cardFlipped ? 'flipped' : ''}`} onClick={() => setCardFlipped(!cardFlipped)}>
                      <div className="flashcard-inner">
                        <div className="flashcard-front">
                          <h3>{cards[cardIndex].question}</h3>
                          <p style={{ marginTop: '16px', fontSize: '12px', color: 'var(--color-muted)' }}>Click card to reveal answer</p>
                        </div>
                        <div className="flashcard-back">
                          <p>{cards[cardIndex].answer}</p>
                          <p style={{ marginTop: '16px', fontSize: '12px', color: 'var(--color-muted)' }}>Click card to see question</p>
                        </div>
                      </div>
                    </div>

                    <div className="flashcard-actions">
                      <button className="btn btn-secondary" onClick={() => { setCardIndex((cardIndex - 1 + cards.length) % cards.length); setCardFlipped(false); }}>Prev</button>
                      <button className="btn btn-secondary" onClick={() => { setCardIndex((cardIndex + 1) % cards.length); setCardFlipped(false); }}>Next</button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      case 'Revision Planner':
        return (
          <div>
            <div className="page-header">
              <div className="page-kicker">Roadmap Planner</div>
              <h2 className="page-title">Revision Planner</h2>
              <p className="page-subtitle">Shape a day-wise calendar roadmap leading to your exam.</p>
            </div>

            <div className="grid-cols-2">
              <div className="glass-card">
                <form onSubmit={handleGeneratePlan}>
                  <div className="form-group">
                    <label className="form-label">Subject</label>
                    <select className="form-control" value={planSubId} onChange={e => setPlanSubId(e.target.value)}>
                      {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Exam Date</label>
                    <input className="form-control" type="date" value={planDate} onChange={e => setPlanDate(e.target.value)} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Preparation Level (1-10)</label>
                    <input className="form-control" type="range" min="1" max="10" value={planPrep} onChange={e => setPlanPrep(e.target.value)} />
                    <span style={{ fontSize: '13px' }}>{planPrep} / 10</span>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Confidence Level (1-10)</label>
                    <input className="form-control" type="range" min="1" max="10" value={planConf} onChange={e => setPlanConf(e.target.value)} />
                    <span style={{ fontSize: '13px' }}>{planConf} / 10</span>
                  </div>
                  <button className="btn btn-primary" type="submit" style={{ width: '100%' }} disabled={planLoading}>
                    {planLoading ? 'Generating Plan...' : 'Generate Revision Plan'}
                  </button>
                </form>
              </div>

              <div className="glass-card">
                {!planText && <div className="empty-state"><p>Build settings and generate plan to view revision schedule.</p></div>}
                {planText && (
                  <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
                    <h3>Roadmap</h3>
                    <div style={{ marginTop: '14px', fontSize: '15px' }} dangerouslySetInnerHTML={{ __html: planText.replace(/\n/g, '<br/>') }} />
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      case 'Pomodoro Timer':
        return (
          <div>
            <div className="page-header">
              <div className="page-kicker">Study Studio</div>
              <h2 className="page-title">Pomodoro Timer</h2>
              <p className="page-subtitle">Track focused intervals and breaks to build study consistency.</p>
            </div>

            <div className="grid-cols-2">
              <div className="glass-card flex-center" style={{ flexDirection: 'column' }}>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                  <button className={`btn ${pomoMode === 'Focus' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => handlePomoModeChange('Focus')}>Focus</button>
                  <button className={`btn ${pomoMode === 'Short Break' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => handlePomoModeChange('Short Break')}>Short Break</button>
                  <button className={`btn ${pomoMode === 'Long Break' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => handlePomoModeChange('Long Break')}>Long Break</button>
                </div>

                <div className="timer-display">
                  {Math.floor(pomoRemaining / 60).toString().padStart(2, '0')}:
                  {(pomoRemaining % 60).toString().padStart(2, '0')}
                </div>

                <div className="timer-controls">
                  <button className="btn btn-primary" onClick={() => setPomoRunning(!pomoRunning)}>
                    {pomoRunning ? 'Pause' : 'Start'}
                  </button>
                  <button className="btn btn-secondary" onClick={() => handlePomoModeChange(pomoMode)}>Reset</button>
                </div>

                <div style={{ width: '100%', marginTop: '20px' }}>
                  <div className="form-group">
                    <label className="form-label">Subject</label>
                    <select className="form-control" value={pomoSubId} onChange={e => setPomoSubId(e.target.value)}>
                      {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Session note</label>
                    <input className="form-control" placeholder="What did you study?" value={pomoNote} onChange={e => setPomoNote(e.target.value)} />
                  </div>
                  <button className="btn btn-secondary" style={{ width: '100%' }} onClick={handleSavePomoSession}>Save Session</button>
                </div>
              </div>

              <div className="glass-card">
                <h3>Recent Completed Sessions</h3>
                <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '420px', overflowY: 'auto' }}>
                  {pomoSessions.length === 0 && <p style={{ color: 'var(--color-muted)' }}>No sessions logged today.</p>}
                  {pomoSessions.map((session, i) => (
                    <div key={i} style={{ padding: '12px', border: '1px solid var(--color-border)', borderRadius: '8px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <strong>{session.session_type}</strong>
                        <span>{session.duration_minutes} mins</span>
                      </div>
                      <span style={{ fontSize: '12px', color: 'var(--color-muted)' }}>{session.subject_name || 'No subject'} | {session.completed_at}</span>
                      {session.notes && <p style={{ fontSize: '13px', marginTop: '4px' }}>{session.notes}</p>}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        );

      case 'AI Settings':
        return (
          <div>
            <div className="page-header">
              <div className="page-kicker">Configuration Console</div>
              <h2 className="page-title">AI Settings</h2>
              <p className="page-subtitle">Manage secure API keys and select your preferred LLM provider.</p>
            </div>

            <div className="glass-card" style={{ maxWidth: '600px', margin: '0 auto' }}>
              <form onSubmit={handleSaveAISettings}>
                <div className="form-group">
                  <label className="form-label">Selected AI Provider</label>
                  <select className="form-control" value={aiProvider} onChange={e => setAIProvider(e.target.value)}>
                    <option value="Gemini">Gemini (Google)</option>
                    <option value="OpenAI">OpenAI (ChatGPT)</option>
                    <option value="Groq">Groq Cloud</option>
                    <option value="Ollama">Ollama (Local Mode)</option>
                    <option value="Demo Mode">Demo Mode (Offline)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Gemini API Key</label>
                  <input className="form-control" type="password" placeholder={settingsStatus?.gemini_configured ? "•••••••• saved" : "Paste your Gemini API key"} value={geminiKey} onChange={e => setGeminiKey(e.target.value)} />
                </div>

                <div className="form-group">
                  <label className="form-label">OpenAI API Key</label>
                  <input className="form-control" type="password" placeholder={settingsStatus?.openai_configured ? "•••••••• saved" : "Paste your OpenAI API key"} value={openaiKey} onChange={e => setOpenaiKey(e.target.value)} />
                </div>

                <button className="btn btn-primary" type="submit" style={{ width: '100%' }}>Save Configuration</button>
              </form>
            </div>
          </div>
        );

      case 'Study Library':
        return (
          <div>
            <div className="page-header">
              <div className="page-kicker">Resource Repository</div>
              <h2 className="page-title">Study Library</h2>
              <p className="page-subtitle">Manage all uploaded textbooks, notes, and resources for your subjects.</p>
            </div>
            
            <div className="grid-cols-2">
              {subjects.map(sub => (
                <div key={sub.id} className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '180px' }}>
                  <div>
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '16px' }}>
                      📚 {sub.name}
                    </h3>
                    <p style={{ color: 'var(--color-muted)', fontSize: '13px' }}>{sub.description || 'No subject description.'}</p>
                  </div>
                  
                  <button className="btn btn-secondary" style={{ width: '100%', marginTop: '16px' }} onClick={() => {
                    setChatSubId(sub.id);
                    setActiveTab('Chat With Notes');
                  }}>
                    Open Subject Chat
                  </button>
                </div>
              ))}
              {subjects.length === 0 && (
                <div className="glass-card" style={{ gridColumn: 'span 2', textAlign: 'center', padding: '40px' }}>
                  <p style={{ color: 'var(--color-muted)' }}>No subjects found. Create a subject in the Dashboard to get started.</p>
                </div>
              )}
            </div>
          </div>
        );

      case 'About':
        return (
          <div>
            <div className="page-header">
              <div className="page-kicker">Application Console</div>
              <h2 className="page-title">About StudyMate AI</h2>
              <p className="page-subtitle">A premium AI learning platform for students and tutors.</p>
            </div>
            
            <div className="glass-card" style={{ maxWidth: '600px', margin: '0 auto', textAlign: 'center' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>🎓</div>
              <h3>StudyMate AI Workspace</h3>
              <span style={{ display: 'inline-block', fontSize: '12px', color: '#6366f1', background: 'rgba(99, 102, 241, 0.1)', padding: '4px 12px', borderRadius: '99px', fontWeight: '750', marginTop: '6px' }}>v1.4.2</span>
              
              <p style={{ marginTop: '20px', color: 'var(--color-charcoal)', fontSize: '14px', lineHeight: '1.6' }}>
                StudyMate AI is a premium full-stack academic assistant powered by state-of-the-art LLMs. It features deep document understanding, step-by-step math integration, region-of-integration shading, custom mock quizzes, flashcard sessions, Pomodoro timers, and revision plans.
              </p>
              
              <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--color-border)', fontSize: '12px', color: 'var(--color-muted)' }}>
                © 2026 StudyMate AI | All Rights Reserved
              </div>
            </div>
          </div>
        );

      default:
        return <div>Not found</div>;
    }
  };

  return (
    <div className={`app-shell ${activeTab === 'Chat With Notes' ? 'chat-active' : ''}`}>
      <div className="sidebar">
        <div className="brand-section">
          <div className="brand-logo">🎓</div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span className="brand-name" style={{ lineHeight: '1.2' }}>StudyMate AI</span>
            <span style={{ fontSize: '10px', color: 'var(--color-muted)', fontWeight: '600' }}>AI Study Assistant</span>
          </div>
        </div>

        <div className="nav-links">
          {[
            { name: 'Dashboard', icon: '🏠' },
            { name: 'Study Library', icon: '📚' },
            { name: 'Upload Notes', icon: '☁️' },
            { name: 'Chat With Notes', icon: '💬' },
            { name: 'Quiz Mode', icon: '❓' },
            { name: 'Flashcards', icon: '📘' },
            { name: 'Revision Planner', icon: '📅' },
            { name: 'Pomodoro Timer', icon: '⏱️' },
            { name: 'AI Settings', icon: '⚙️' },
            { name: 'About', icon: 'ℹ️' }
          ].map(tab => (
            <div key={tab.name} className={`nav-item ${activeTab === tab.name ? 'active' : ''}`} onClick={() => setActiveTab(tab.name)}>
              <span>{tab.icon}</span>
              <span>{tab.name}</span>
            </div>
          ))}
        </div>

        {/* User profile section at the bottom of sidebar */}
        <div className="sidebar-profile-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="user-avatar" style={{ background: '#6366f1' }}>A</div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span className="user-name">{user?.name || 'Ali Shair'}</span>
              <span className="user-plan">Pro Plan</span>
            </div>
          </div>
          <div className="credits-bar" style={{ marginTop: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontWeight: '600', color: 'var(--color-muted)', marginBottom: '4px' }}>
              <span>1200 AI Credits Left</span>
              <span>80%</span>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: '80%' }}></div>
            </div>
          </div>
          <button className="upgrade-btn" onClick={() => alert("Upgrading to premium study plan...")}>
            <span>👑 Upgrade Plan</span>
            <span style={{ fontSize: '10px' }}>➔</span>
          </button>
        </div>

        <button className="btn btn-secondary logout-btn" style={{ marginTop: '12px', padding: '6px 12px', fontSize: '12px' }} onClick={logout}>Sign Out</button>
      </div>

      <div className="main-content">
        {renderActiveView()}
      </div>
    </div>
  );
}

export default App;
