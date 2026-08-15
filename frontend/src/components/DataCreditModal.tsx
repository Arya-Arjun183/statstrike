
import { X, Database } from 'lucide-react';

interface DataCreditModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function DataCreditModal({ isOpen, onClose }: DataCreditModalProps) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div 
        className="modal-container glass-panel animate-scale-in"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '500px', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}
      >
        <div className="modal-header" style={{ padding: '0', borderBottom: 'none', marginBottom: '0' }}>
          <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: '600', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Database size={20} />
            Data Sources & Credits
          </h3>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.5' }}>
          <p>
            StatStrike is powered by a variety of world-class football data providers. We would like to thank the following platforms for making this project possible:
          </p>
          
          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-tertiary)', borderRadius: '0.5rem', border: '1px solid var(--border-light)' }}>
            <h4 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-primary)', fontSize: '1rem' }}>API-Football</h4>
            <p style={{ margin: 0 }}>Provides comprehensive match fixtures, historical results, team forms, and basic statistics.</p>
          </div>

          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-tertiary)', borderRadius: '0.5rem', border: '1px solid var(--border-light)' }}>
            <h4 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-primary)', fontSize: '1rem' }}>Understat</h4>
            <p style={{ margin: 0 }}>Supplies advanced Expected Goals (xG) models and detailed shot creation data used in our Poisson distributions.</p>
          </div>

          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-tertiary)', borderRadius: '0.5rem', border: '1px solid var(--border-light)' }}>
            <h4 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-primary)', fontSize: '1rem' }}>The Odds API</h4>
            <p style={{ margin: 0 }}>Delivers live, up-to-date moneyline betting odds from major bookmakers to calculate Expected Value (+EV).</p>
          </div>
        </div>

      </div>
    </div>
  );
}
