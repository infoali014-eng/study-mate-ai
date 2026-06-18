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

      case 'Chat With Notes':
        return (
          <div>
            <div className="page-header">
              <div className="page-kicker">Discussion Lab</div>
              <h2 className="page-title">Chat With Notes</h2>
              <p className="page-subtitle">Retrieve context directly from your study documents using AI.</p>
            </div>

            <div className="chat-workspace">
              <div className="glass-card chat-sessions-pane">
                <div className="form-group">
                  <label className="form-label">Active Subject</label>
                  <select className="form-control" value={chatSubId} onChange={e => { setChatSubId(e.target.value); setActiveSessionId(null); }}>
                    {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
                
                <div className="section-title-bar" style={{ margin: '8px 0' }}>
                  <h5>Chat History</h5>
                  <button className="btn btn-primary" style={{ padding: '6px 10px', fontSize: '12px' }} onClick={handleCreateChatSession}>New Chat</button>
                </div>

                <div className="chat-sessions-list">
                  {chatSessions.map(session => (
                    <div key={session.id} className={`session-item ${activeSessionId === session.id ? 'active' : ''}`} onClick={() => setActiveSessionId(session.id)}>
                      <span>💬 {session.title || 'Untitled Chat'}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="glass-card chat-main-pane">
                <div style={{ display: 'flex', gap: '12px', marginBottom: '14px' }}>
                  <select className="form-control" style={{ width: '140px' }} value={chatMode} onChange={e => setChatMode(e.target.value)}>
                    <option value="General Chat">General Chat</option>
                    <option value="Chat with Subject">Subject Chat</option>
                    <option value="Teach Me Mode">Teach Me</option>
                  </select>
                  <select className="form-control" style={{ width: '140px' }} value={chatStyle} onChange={e => setChatStyle(e.target.value)}>
                    <option value="Simple English">Simple English</option>
                    <option value="Roman Urdu">Roman Urdu</option>
                    <option value="Exam Style">Exam Style</option>
                  </select>
                </div>

                <div className="chat-history">
                  {chatMessages.length === 0 && <div className="empty-state"><p>Ask a question or explain a math problem to begin.</p></div>}
                  {chatMessages.map((msg, i) => (
                    <div key={i} className={`chat-message ${msg.role}`}>
                      <div className="msg-meta">{msg.role === 'user' ? 'You' : 'StudyMate AI'}</div>
                      <div className="msg-content" dangerouslySetInnerHTML={{ __html: msg.content.replace(/\n/g, '<br/>') }} />
                      
                      {/* Render custom Plotly figure if generated */}
                      {msg.metadata && typeof msg.metadata === 'string' && JSON.parse(msg.metadata).math_visualizations?.map((vis, j) => (
                        vis.figure_json && <PlotlyChart key={j} jsonStr={vis.figure_json} />
                      ))}
                      {msg.metadata && typeof msg.metadata === 'object' && msg.metadata.math_visualizations?.map((vis, j) => (
                        vis.figure_json && <PlotlyChart key={j} jsonStr={vis.figure_json} />
                      ))}
                    </div>
                  ))}
                  {chatLoading && <div className="chat-message assistant"><div className="msg-meta">StudyMate AI</div><div>Thinking...</div></div>}
                  <div ref={messagesEndRef} />
                </div>

                <form onSubmit={handleSendChatMessage} className="chat-input-bar">
                  <input className="chat-input" placeholder="Type your query here..." value={chatInput} onChange={e => setChatInput(e.target.value)} required />
                  <button className="btn btn-primary" type="submit" disabled={chatLoading}>Send</button>
                </form>
              </div>
            </div>
          </div>
        );

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

      default:
        return <div>Not found</div>;
    }
  };

  return (
    <div className="app-shell">
      <div className="sidebar">
        <div className="brand-section">
          <div className="brand-logo">🎓</div>
          <div className="brand-name">StudyMate AI</div>
        </div>

        <div className="nav-links">
          {['Dashboard', 'Upload Notes', 'Chat With Notes', 'Quiz Mode', 'Flashcards', 'Revision Planner', 'Pomodoro Timer', 'AI Settings'].map(tab => (
            <div key={tab} className={`nav-item ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)}>
              <span>{tab === 'Dashboard' ? '🏠' : tab === 'Upload Notes' ? '☁️' : tab === 'Chat With Notes' ? '💬' : tab === 'Quiz Mode' ? '❓' : tab === 'Flashcards' ? '📘' : tab === 'Revision Planner' ? '📅' : tab === 'Pomodoro Timer' ? '⏱️' : '⚙️'}</span>
              <span>{tab}</span>
            </div>
          ))}
        </div>

        <button className="btn btn-secondary logout-btn" onClick={logout}>Sign Out</button>
      </div>

      <div className="main-content">
        {renderActiveView()}
      </div>
    </div>
  );
}

export default App;
