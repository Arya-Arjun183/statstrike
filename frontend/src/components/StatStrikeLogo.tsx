import React from 'react';

interface StatStrikeLogoProps {
  size?: number;
  className?: string;
  withGlow?: boolean;
}

export const StatStrikeLogo: React.FC<StatStrikeLogoProps> = ({
  size = 36,
  className = '',
  withGlow = true,
}) => {
  return (
    <div
      className={`statstrike-logo-wrapper ${className}`}
      style={{
        width: size,
        height: size,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        flexShrink: 0,
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{
          filter: withGlow
            ? 'drop-shadow(0 0 10px rgba(0, 242, 254, 0.6)) drop-shadow(0 0 18px rgba(168, 85, 247, 0.45))'
            : 'none',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >
        <defs>
          <linearGradient id="ss-bar-1" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#00F2FE" />
            <stop offset="100%" stopColor="#0284C7" />
          </linearGradient>
          <linearGradient id="ss-bar-2" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#38BDF8" />
            <stop offset="100%" stopColor="#6366F1" />
          </linearGradient>
          <linearGradient id="ss-bar-3" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#818CF8" />
            <stop offset="100%" stopColor="#8B5CF6" />
          </linearGradient>
          <linearGradient id="ss-bar-4" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#A855F7" />
            <stop offset="100%" stopColor="#D946EF" />
          </linearGradient>
          <linearGradient id="ss-bar-5" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#E879F9" />
            <stop offset="100%" stopColor="#F43F5E" />
          </linearGradient>
          <linearGradient id="ss-bolt" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="25%" stopColor="#00F2FE" />
            <stop offset="70%" stopColor="#A855F7" />
            <stop offset="100%" stopColor="#FF007A" />
          </linearGradient>
        </defs>

        {/* 5 Ascending Data Telemetry Bars */}
        <rect x="12" y="60" width="10" height="26" rx="3" fill="url(#ss-bar-1)" />
        <rect x="28" y="46" width="10" height="40" rx="3" fill="url(#ss-bar-2)" />
        <rect x="44" y="32" width="10" height="54" rx="3" fill="url(#ss-bar-3)" />
        <rect x="60" y="20" width="10" height="66" rx="3" fill="url(#ss-bar-4)" />
        <rect x="76" y="10" width="10" height="76" rx="3" fill="url(#ss-bar-5)" />

        {/* Diagonal Lightning Bolt Slicing Across All Bars */}
        <polygon
          points="74,6 36,46 54,48 16,94 46,54 30,52"
          fill="url(#ss-bolt)"
          stroke="#FFFFFF"
          strokeWidth="2"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
};
