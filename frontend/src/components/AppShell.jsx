import React from 'react';
import { NavLink, useNavigate, Outlet } from 'react-router-dom';
import {
  LayoutDashboard, Users, BarChart3, BookOpen, LogOut,
  Building2, Settings, Brain, Sun, Moon, Zap,
  FileText, User as UserIcon, ShieldCheck, Sparkles, Archive, Plug, CheckCheck,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import Background3D from './Background3D';

// ─── Brand mark — Poonawalla "P" lettermark ─────────────────────────
export function BrandMark({ size = 42, withWordmark = true, compact = false }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
      <div style={{
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: '2px',
        background: 'var(--navy)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        boxShadow: 'inset 0 -2px 0 rgba(0,0,0,0.20), 0 1px 0 rgba(255,255,255,0.4)',
      }}>
        <svg width={size * 0.55} height={size * 0.6} viewBox="0 0 24 26" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="2" y="2" width="4.5" height="22" rx="1.5" fill="white"/>
          <path d="M6.5 2.5 H15.5 Q22 2.5 22 9.5 Q22 16.5 15.5 16.5 H6.5 Z" fill="white"/>
          <path d="M6.5 6 H14 Q18 6 18 9.5 Q18 13 14 13 H6.5 Z" fill="#1B2C5E"/>
        </svg>
      </div>
      {withWordmark && (
        <div style={{ minWidth: 0 }}>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontSize: compact ? '1.05rem' : '1.18rem',
            fontWeight: 400,
            letterSpacing: '-0.02em',
            fontVariationSettings: '"opsz" 36, "SOFT" 50',
            color: 'var(--ink)',
            lineHeight: 1.1,
          }}>
            PlacementIQ
          </div>
          <div style={{
            fontSize: '0.6rem',
            color: 'var(--ink-faint)',
            fontWeight: 700,
            letterSpacing: '0.18em',
            display: 'block',
            marginTop: '3px',
            textTransform: 'uppercase',
          }}>
            by Poonawalla Fincorp
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Admin (lender) sidebar nav items ───────────────────────────────
const ADMIN_NAV = [
  { path: '/dashboard',   icon: LayoutDashboard, label: 'Dashboard',         iconColor: '#1B2C5E' },
  { path: '/students',    icon: Users,            label: 'Portfolio',         iconColor: '#1E56C7' },
  { path: '/heatmap',     icon: BarChart3,        label: 'Heatmap',           iconColor: '#2F6E45' },
  { path: '/reports',     icon: BookOpen,         label: 'Reports & Drift',   iconColor: '#A5751F' },
  { path: '/institutes',  icon: Building2,        label: 'Institutes',        iconColor: '#1B2C5E' },
  { path: '/agentic',     icon: Brain,            label: 'AI Agents',         iconColor: '#C2410C' },
  { path: '/admin/audit', icon: Archive,          label: 'Audit Log',         iconColor: '#5E564B' },
  { path: '/admin',       icon: Settings,         label: 'Admin Panel',       iconColor: '#5E564B' },
];

const STUDENT_NAV = [
  { path: '/me/dashboard', icon: LayoutDashboard, label: 'My Dashboard',     iconColor: '#1B2C5E' },
  { path: '/me/apply',     icon: FileText,         label: 'My Application',  iconColor: '#C2410C' },
  { path: '/me/profile',   icon: Plug,             label: 'Linked Profiles', iconColor: '#1E56C7' },
  { path: '/me/decision',  icon: CheckCheck,       label: 'Loan Decision',   iconColor: '#2F6E45' },
];

function Sidebar({ navItems, variant }) {
  const { theme, toggleTheme } = useTheme();
  const { user, signout } = useAuth();
  const navigate = useNavigate();

  const handleSignout = () => {
    signout();
    navigate('/');
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <BrandMark size={40} />
      </div>

      <button onClick={toggleTheme} className="theme-toggle">
        {theme === 'dark'
          ? <Sun size={15} color="#C2410C" />
          : <Moon size={15} color="#1B2C5E" />}
        <span>{theme === 'dark' ? 'Switch to Light' : 'Switch to Dark'}</span>
      </button>

      <span className="sidebar-section-label">
        {variant === 'student' ? 'Borrower' : 'Navigation'}
      </span>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        {navItems.map(({ path, icon: Icon, label, iconColor }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/dashboard' || path === '/me/dashboard' || path === '/admin'}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            {({ isActive }) => (
              <>
                <div className="nav-icon-wrap" style={isActive ? { background: iconColor, borderColor: iconColor, color: 'var(--card-raised)' } : {}}>
                  <Icon size={16} />
                </div>
                <span style={{ fontSize: '0.875rem' }}>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {variant === 'student' && (
        <div className="borrower-mini-quote">
          Every loan is a bet on a career.
          <div style={{
            marginTop: '0.4rem',
            fontFamily: 'var(--font-sans)',
            fontStyle: 'normal',
            fontSize: '0.62rem',
            fontWeight: 700,
            letterSpacing: '0.16em',
            textTransform: 'uppercase',
            color: 'var(--ink-faint)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
          }}>
            <Sparkles size={10} color="var(--signal)" /> PlacementIQ
          </div>
        </div>
      )}

      <div className="sidebar-footer">
        {user && (
          <div style={{
            padding: '0.6rem 0.75rem',
            border: '1px solid var(--card-edge)',
            borderLeft: '3px solid var(--signal)',
            marginBottom: '0.75rem',
            display: 'flex', alignItems: 'center', gap: '10px',
          }}>
            <div style={{
              width: '30px', height: '30px',
              background: 'var(--paper-deep)',
              borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <UserIcon size={14} color="var(--ink-muted)" />
            </div>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{
                fontSize: '0.78rem', fontWeight: 700,
                color: 'var(--ink)', lineHeight: 1.2,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>{user.name}</div>
              <div style={{
                fontSize: '0.62rem', letterSpacing: '0.14em',
                color: 'var(--ink-faint)', textTransform: 'uppercase',
                marginTop: '1px', fontWeight: 700,
              }}>
                {user.role === 'student' ? 'Borrower' : 'Lender'}
              </div>
            </div>
          </div>
        )}

        {variant === 'admin' && (
          <div className="api-status-pill">
            <span className="pulse-dot" style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'var(--risk-low)', display: 'inline-block', flexShrink: 0 }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--ink)', lineHeight: 1.2 }}>API Live</div>
              <div style={{ fontSize: '0.66rem', color: 'var(--ink-faint)', marginTop: '1px', fontFamily: 'var(--font-mono)' }}>v2.0 · 8001 · 10K records</div>
            </div>
            <div style={{
              display: 'flex', alignItems: 'center', gap: '4px',
              background: 'var(--risk-low-bg)',
              padding: '2px 8px',
              border: '1px solid var(--risk-low-edge)',
              borderRadius: '2px',
            }}>
              <Zap size={10} color="var(--risk-low)" />
              <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--risk-low)', letterSpacing: '0.08em' }}>5 agents</span>
            </div>
          </div>
        )}

        {variant === 'student' && user && (
          <BorrowerStatusPill user={user} />
        )}

        <button className="nav-item" onClick={handleSignout} style={{ color: 'var(--ink-muted)', fontSize: '0.82rem' }}>
          <div className="nav-icon-wrap">
            <LogOut size={15} />
          </div>
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
}

// ─── Borrower-side status pill (fills the empty space the admin side has) ──
function BorrowerStatusPill({ user }) {
  const hasApp = Boolean(user?.lastPrescreen);
  const pred = user?.lastPrescreen?.prediction || {};
  const prob6m = Math.round(((pred.placement_probability || {})['6m'] || 0) * 100);
  const riskBand = pred.risk_band || (hasApp ? 'MEDIUM' : '—');
  const offerStatus = user?.lastPrescreen?.indicative_offer?.status || (hasApp ? 'PROCESSING' : 'NO APPLICATION');

  const bandColor = riskBand === 'LOW' ? 'var(--risk-low)'
                  : riskBand === 'HIGH' ? 'var(--risk-high)'
                  : 'var(--risk-medium)';

  return (
    <div className="borrower-status-pill" style={{ borderLeftColor: hasApp ? bandColor : 'var(--ink-faint)' }}>
      <ShieldCheck size={14} color={hasApp ? bandColor : 'var(--ink-faint)'} style={{ flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="label">
          {hasApp ? `${prob6m}% · ${riskBand}` : 'No application yet'}
        </div>
        <div className="sub">{offerStatus}</div>
      </div>
    </div>
  );
}

export default function AppShell({ variant = 'admin' }) {
  const navItems = variant === 'student' ? STUDENT_NAV : ADMIN_NAV;
  return (
    <div className="app-container">
      <Background3D />
      <Sidebar navItems={navItems} variant={variant} />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
