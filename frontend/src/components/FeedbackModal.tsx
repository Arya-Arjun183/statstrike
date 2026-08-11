import { useState } from 'react';
import { X, Send, Loader2 } from 'lucide-react';

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function FeedbackModal({ isOpen, onClose }: FeedbackModalProps) {
  const [type, setType] = useState('Feature Request');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    setIsSubmitting(true);
    setSubmitStatus('idle');

    try {
      const response = await fetch('http://localhost:8000/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ type, name, email, message }),
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      setSubmitStatus('success');
      setTimeout(() => {
        onClose();
        setSubmitStatus('idle');
        setMessage('');
        setType('Feature Request');
      }, 2000);
    } catch (error) {
      console.error(error);
      setSubmitStatus('error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div 
        className="modal-container glass-panel animate-scale-in"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '500px', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}
      >
        <div className="modal-header" style={{ padding: '0', borderBottom: 'none', marginBottom: '0' }}>
          <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: '600', color: 'var(--text-primary)' }}>
            Send Feedback
          </h3>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {submitStatus === 'success' ? (
          <div style={{ padding: '3rem 0', textAlign: 'center' }}>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1rem', color: 'var(--emerald-500)' }}>
              <Send size={48} />
            </div>
            <h4 style={{ fontSize: '1.1rem', fontWeight: '500', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
              Sent Successfully!
            </h4>
            <p style={{ color: 'var(--text-secondary)' }}>Thank you for your feedback.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label htmlFor="type" style={{ fontSize: '0.875rem', fontWeight: '500', color: 'var(--text-secondary)' }}>
                Type of Feedback
              </label>
              <select
                id="type"
                value={type}
                onChange={(e) => setType(e.target.value)}
                style={{ 
                  padding: '0.75rem', 
                  borderRadius: '0.5rem', 
                  backgroundColor: 'var(--bg-tertiary)', 
                  border: '1px solid var(--border-light)', 
                  color: 'var(--text-primary)' 
                }}
              >
                <option value="Feature Request">Feature Request</option>
                <option value="Bug Report">Bug Report</option>
                <option value="General Feedback">General Feedback</option>
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label htmlFor="name" style={{ fontSize: '0.875rem', fontWeight: '500', color: 'var(--text-secondary)' }}>
                  Name <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>(optional)</span>
                </label>
                <input
                  type="text"
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="John Doe"
                  style={{ 
                    padding: '0.75rem', 
                    borderRadius: '0.5rem', 
                    backgroundColor: 'var(--bg-tertiary)', 
                    border: '1px solid var(--border-light)', 
                    color: 'var(--text-primary)' 
                  }}
                />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label htmlFor="email" style={{ fontSize: '0.875rem', fontWeight: '500', color: 'var(--text-secondary)' }}>
                  Email <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>(optional)</span>
                </label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  style={{ 
                    padding: '0.75rem', 
                    borderRadius: '0.5rem', 
                    backgroundColor: 'var(--bg-tertiary)', 
                    border: '1px solid var(--border-light)', 
                    color: 'var(--text-primary)' 
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label htmlFor="message" style={{ fontSize: '0.875rem', fontWeight: '500', color: 'var(--text-secondary)' }}>
                Message <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <textarea
                id="message"
                required
                rows={4}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="What's on your mind?"
                style={{ 
                  padding: '0.75rem', 
                  borderRadius: '0.5rem', 
                  backgroundColor: 'var(--bg-tertiary)', 
                  border: '1px solid var(--border-light)', 
                  color: 'var(--text-primary)',
                  resize: 'none'
                }}
              />
            </div>

            {submitStatus === 'error' && (
              <p style={{ color: '#ef4444', fontSize: '0.875rem', margin: 0 }}>Failed to send feedback. Please try again later.</p>
            )}

            <button
              type="submit"
              disabled={isSubmitting || !message.trim()}
              className="btn-primary"
              style={{ width: '100%', justifyContent: 'center', marginTop: '0.5rem', padding: '0.75rem' }}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span>Sending...</span>
                </>
              ) : (
                <>
                  <Send size={18} />
                  <span>Submit Feedback</span>
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
