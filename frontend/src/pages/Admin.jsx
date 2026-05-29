import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Settings, Shield, Zap, ChevronDown, ChevronUp, Save, RefreshCw, CheckCircle, Users, Database, AlertTriangle, TrendingUp } from 'lucide-react';
import { API_BASE } from '../App';

// Tiny inline sparkline (no external lib) — accepts array of numbers 0..1
function Sparkline({ data, color = 'var(--ink)', threshold = 0.10, width = 140, height = 32 }) {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data, threshold * 1.2);
  const min = 0;
  const range = max - min || 1;
  const stepX = width / (data.length - 1 || 1);
  const points = data.map((v, i) => `${i * stepX},${height - ((v - min) / range) * height}`).join(' ');
  const thresholdY = height - ((threshold - min) / range) * height;
  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      {/* threshold line */}
      <line x1={0} x2={width} y1={thresholdY} y2={thresholdY} stroke="var(--risk-high)" strokeWidth="1" strokeDasharray="2,3" opacity="0.4" />
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      {data.map((v, i) => (
        <circle key={i} cx={i * stepX} cy={height - ((v - min) / range) * height} r={i === data.length - 1 ? 3 : 1.5} fill={color} />
      ))}
    </svg>
  );
}

function ConfigSection({ title, icon: Icon, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card" style={{ marginBottom: '1rem' }}>
      <div onClick={() => setOpen(o => !o)} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}>
        <div className="card-title" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Icon size={14} /> {title}
        </div>
        {open ? <ChevronUp size={16} color="var(--text-secondary)" /> : <ChevronDown size={16} color="var(--text-secondary)" />}
      </div>
      {open && <div style={{ marginTop: '1rem' }}>{children}</div>}
    </div>
  );
}

function SliderField({ label, value, min, max, step = 0.01, onChange, suffix = '' }) {
  return (
    <div style={{ marginBottom: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
        <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--accent-primary)', fontFamily: 'monospace' }}>
          {value}{suffix}
        </span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
      />
    </div>
  );
}

function Admin() {
  const [config, setConfig] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [ccData, setCcData] = useState(null);
  const [fairness, setFairness] = useState(null);
  const [provenance, setProvenance] = useState(null);

  useEffect(() => {
    axios.get(`${API_BASE}/api/v1/admin/config`).then(r => setConfig(r.data)).catch(() => {});
    axios.get(`${API_BASE}/api/v1/model/champion-challenger`).then(r => setCcData(r.data)).catch(() => {});
    axios.get(`${API_BASE}/api/v1/model/fairness/v2`)
      .then(r => setFairness(r.data))
      .catch(() => axios.get(`${API_BASE}/api/v1/model/fairness`).then(r => setFairness(r.data)).catch(() => {}));
    axios.get(`${API_BASE}/api/v1/model/data-provenance`).then(r => setProvenance(r.data)).catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      await axios.put(`${API_BASE}/api/v1/admin/config`, config);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch {}
    setSaving(false);
  };

  const updateNested = (section, key, val) => {
    setConfig(c => ({ ...c, [section]: { ...c[section], [key]: val } }));
  };

  if (!config) return (
    <div style={{ padding: '3rem', color: 'var(--text-secondary)' }}>
      <RefreshCw size={16} style={{ animation: 'spin 1s linear infinite', marginRight: '0.5rem' }} />
      Loading admin config...
    </div>
  );

  return (
    <div className="animate-fade-up">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1>Admin Configuration Panel (F-12)</h1>
          <p>Manage risk thresholds, model config, NBA costs, and tenant settings. Requires Admin role with MFA.</p>
        </div>
        <button className="btn btn-primary" onClick={save} disabled={saving}>
          {saved ? <CheckCircle size={14} /> : saving ? <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Save size={14} />}
          {saved ? 'Saved!' : saving ? 'Saving...' : 'Save Config'}
        </button>
      </div>

      {/* Tenant info */}
      <div className="card" style={{ marginBottom: '1rem', borderTop: '2px solid var(--accent-primary)' }}>
        <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
          {[
            { label: 'Lender', val: config.tenant?.lender_name },
            { label: 'Lender ID', val: config.tenant?.lender_id },
            { label: 'Max Students', val: config.tenant?.max_students?.toLocaleString() },
            { label: 'MFA Required', val: config.tenant?.mfa_required ? '✅ Yes' : '❌ No' },
            { label: 'Last Modified', val: config.last_modified?.slice(0, 10) },
            { label: 'Modified By', val: config.modified_by },
          ].map(({ label, val }) => (
            <div key={label}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.15rem' }}>{label}</div>
              <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>{val}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Risk Thresholds */}
      <ConfigSection title="Risk Band Thresholds" icon={Shield} defaultOpen>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
          Adjust the 6-month placement probability cutoffs that determine HIGH / MEDIUM / LOW risk classification.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          <div>
            <SliderField
              label="HIGH Risk — max probability"
              value={config.risk_thresholds?.high_max}
              min={0.20} max={0.60} step={0.01}
              suffix=" (≤ this = HIGH)"
              onChange={v => updateNested('risk_thresholds', 'high_max', v)}
            />
            <div style={{ padding: '0.5rem 0.75rem', background: 'rgba(239,68,68,0.08)', borderRadius: '6px', fontSize: '0.8rem', color: 'var(--risk-high)' }}>
              🔴 P(6m) ≤ {config.risk_thresholds?.high_max} → HIGH Risk
            </div>
          </div>
          <div>
            <SliderField
              label="MEDIUM Risk — max probability"
              value={config.risk_thresholds?.medium_max}
              min={0.50} max={0.90} step={0.01}
              suffix=" (≤ this = MEDIUM)"
              onChange={v => updateNested('risk_thresholds', 'medium_max', v)}
            />
            <div style={{ padding: '0.5rem 0.75rem', background: 'rgba(245,158,11,0.08)', borderRadius: '6px', fontSize: '0.8rem', color: 'var(--risk-medium)' }}>
              🟡 {config.risk_thresholds?.high_max} &lt; P(6m) ≤ {config.risk_thresholds?.medium_max} → MEDIUM
            </div>
          </div>
        </div>
      </ConfigSection>

      {/* EMI Comfort Tiers */}
      <ConfigSection title="EMI Comfort Tier Thresholds" icon={Zap}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
          {Object.entries(config.emi_comfort_tiers || {}).map(([tier, val]) => (
            <div key={tier}>
              <SliderField
                label={tier.charAt(0).toUpperCase() + tier.slice(1)}
                value={val} min={0.5} max={5} step={0.1}
                suffix="x EMI ratio"
                onChange={v => updateNested('emi_comfort_tiers', tier, v)}
              />
            </div>
          ))}
        </div>
      </ConfigSection>

      {/* Alert Engine */}
      <ConfigSection title="Early Alert Engine Thresholds" icon={Settings}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          <SliderField
            label="Critical CGPA threshold"
            value={config.alert_engine?.critical_cgpa_threshold}
            min={4.0} max={8.0} step={0.1}
            onChange={v => updateNested('alert_engine', 'critical_cgpa_threshold', v)}
          />
          <SliderField
            label="Medium CGPA threshold"
            value={config.alert_engine?.medium_cgpa_threshold}
            min={5.0} max={9.0} step={0.1}
            onChange={v => updateNested('alert_engine', 'medium_cgpa_threshold', v)}
          />
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Max alerts per run:</span>
          <input
            type="number" min={10} max={1000} value={config.alert_engine?.max_alerts_per_run}
            onChange={e => updateNested('alert_engine', 'max_alerts_per_run', parseInt(e.target.value))}
            className="select-input" style={{ width: '100px' }}
          />
        </div>
      </ConfigSection>

      {/* Intervention Costs */}
      <ConfigSection title="NBA Intervention Cost Table" icon={Users}>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>Costs (₹ INR) used by the Intervention Simulator ROI calculator.</p>
        <table className="data-table">
          <thead><tr><th>Intervention</th><th>Cost (₹)</th></tr></thead>
          <tbody>
            {Object.entries(config.intervention_costs || {}).map(([action, cost]) => (
              <tr key={action}>
                <td>{action}</td>
                <td>
                  <input
                    type="number" min={0} value={cost}
                    onChange={e => setConfig(c => ({ ...c, intervention_costs: { ...c.intervention_costs, [action]: parseInt(e.target.value) || 0 } }))}
                    className="select-input" style={{ width: '100px' }}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ConfigSection>

      {/* Data Provenance — what the active model was trained from */}
      {provenance?.active && (() => {
        const a = provenance.active;
        const KIND_META = {
          combined:  { label: 'AMCAT + SYNTHETIC · combined',  badge: 'badge-low'    },
          amcat:     { label: 'AMCAT · real outcomes',         badge: 'badge-low'    },
          synthetic: { label: 'SYNTHETIC · generated',         badge: 'badge-medium' },
        };
        const meta = KIND_META[a._kind] || KIND_META.synthetic;
        const mix = a.origin_mix || null;
        return (
          <div className="card" style={{ marginBottom: '1rem', borderLeft: '3px solid var(--signal)' }}>
            <div className="card-title"><Database size={14} /> Training Data Provenance</div>
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap', marginTop: '0.5rem' }}>
              <span className={`badge ${meta.badge}`} style={{ fontFamily: 'var(--font-mono)', letterSpacing: '0.10em' }}>
                {meta.label}
              </span>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                <strong>{(a.row_count || 0).toLocaleString('en-IN')}</strong> records
                {mix && (
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: '0.4em', fontFamily: 'var(--font-mono)' }}>
                    ({Object.entries(mix).map(([k, v]) => `${k.slice(0,3)} ${v.toLocaleString('en-IN')}`).join(' + ')})
                  </span>
                )}
              </span>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                F1 (6m): <strong className="mono">{(a.classifier_f1_6m ?? 0).toFixed(3)}</strong>
              </span>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                MAPE: <strong className="mono">{a.salary_mape != null ? `${(a.salary_mape * 100).toFixed(1)}%` : '—'}</strong>
              </span>
              {a.median_salary_inr ? (
                <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                  Median CTC: <strong className="mono">₹{a.median_salary_inr.toLocaleString('en-IN')}</strong>
                </span>
              ) : null}
              {a.trained_at_utc && (
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  trained {a.trained_at_utc.slice(0, 10)}
                </span>
              )}
            </div>
            {provenance.variants?.length > 1 && (
              <div style={{ marginTop: '0.75rem', fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                {provenance.variants.length} variants on disk · A/B-switchable via <span className="mono">backend/scoring_engine.py</span>. Active preference: combined &gt; amcat &gt; synthetic.
              </div>
            )}
            {a.note && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.74rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                {a.note}
              </div>
            )}
          </div>
        );
      })()}

      {/* Model Config */}
      <ConfigSection title="Model Configuration & Champion/Challenger" icon={Zap}>
        {ccData && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div style={{ padding: '1rem', background: 'rgba(16,185,129,0.06)', borderRadius: '8px', border: '1px solid rgba(16,185,129,0.2)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--risk-low)', fontWeight: 700, marginBottom: '0.5rem' }}>👑 CHAMPION MODEL</div>
              {Object.entries(ccData.champion).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.2rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{String(v)}</span>
                </div>
              ))}
            </div>
            <div style={{ padding: '1rem', background: 'rgba(100,116,139,0.05)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '0.5rem' }}>🥊 CHALLENGER MODEL</div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{ccData.challenger?.status}</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>{ccData.challenger?.note}</div>
            </div>
          </div>
        )}
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Auto-retrain PSI threshold:</span>
          <SliderField
            label="" value={config.model_config?.retrain_psi_threshold}
            min={0.05} max={0.50} step={0.01}
            onChange={v => updateNested('model_config', 'retrain_psi_threshold', v)}
          />
        </div>
      </ConfigSection>

      {/* Fairness Report — v2 with dimension cards + sparkline trends */}
      {fairness && (
        <div className="card">
          <div className="card-title"><Shield size={14} /> Model Fairness Audit · v2</div>
          <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <span className={`badge ${fairness.overall_status === 'PASS' ? 'badge-low' : 'badge-high'}`}>
              {fairness.overall_status === 'PASS' ? '✓ Overall PASS' : '⚠ Overall FAIL'}
            </span>
            <span style={{ fontSize: '0.78rem', color: 'var(--ink-muted)' }}>Audit date: {fairness.audit_date} · Next: {fairness.next_audit}</span>
            {fairness.thresholds && (
              <span style={{ fontSize: '0.74rem', color: 'var(--ink-faint)', fontStyle: 'italic', marginLeft: 'auto' }}>
                Thresholds: warn {fairness.thresholds.warning_pp}pp · act {fairness.thresholds.action_pp}pp · {fairness.thresholds.framework}
              </span>
            )}
          </div>

          {/* RBI threshold annotation banner */}
          {fairness.overall_status === 'FAIL' && (
            <div className="alert-banner" style={{
              background: 'rgba(168, 40, 40, 0.05)',
              border: '1px solid rgba(168, 40, 40, 0.2)',
              borderLeftColor: 'var(--risk-high)',
              marginBottom: '1rem',
            }}>
              <AlertTriangle size={16} color="var(--risk-high)" />
              <div>
                <strong style={{ color: 'var(--risk-high)', fontSize: '0.86rem' }}>
                  One or more dimensions exceed the 10pp action threshold
                </strong>
                <p style={{ fontSize: '0.78rem', color: 'var(--ink-soft)', marginTop: '0.2rem', lineHeight: 1.5 }}>
                  Remediation SLA: 30 days. Escalate to Model Risk Committee before next model promotion.
                </p>
              </div>
            </div>
          )}

          {/* Per-dimension cards (grid, responsive) */}
          <div className="fairness-grid">
            {Object.entries(fairness.dimensions || {}).map(([dim, info]) => {
              const disparityPct = info.max_disparity_pct ?? (info.max_disparity * 100).toFixed(1);
              const band = info.band || (info.max_disparity >= 0.10 ? 'HIGH' : info.max_disparity >= 0.05 ? 'MEDIUM' : 'LOW');
              const color = band === 'HIGH' ? 'var(--risk-high)' : band === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)';
              return (
                <div key={dim} className="fairness-dim-card" style={{ borderTop: `3px solid ${color}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.55rem' }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--ink)' }}>{dim}</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--ink-faint)', marginTop: '2px' }}>
                        {Object.keys(info.groups || {}).length} groups · {Object.values(info.groups || {}).reduce((a, b) => a + (b?.n || 0), 0).toLocaleString()} students
                      </div>
                    </div>
                    <span className={`badge badge-${band.toLowerCase()}`} style={{ fontSize: '0.7rem' }}>{band}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '0.65rem' }}>
                    <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.7rem', color, lineHeight: 1, fontWeight: 400, fontFeatureSettings: '"tnum"' }}>
                      {disparityPct}%
                    </span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--ink-faint)' }}>max disparity</span>
                  </div>
                  {info.trend_7_periods && (
                    <div style={{ marginBottom: '0.5rem' }}>
                      <Sparkline data={info.trend_7_periods} color={color} threshold={0.10} width={180} height={28} />
                      <div style={{ fontSize: '0.66rem', color: 'var(--ink-faint)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                        7-period trend · red line = 10pp action threshold
                      </div>
                    </div>
                  )}
                  {info.remediation_sla_days && (
                    <div style={{ fontSize: '0.72rem', color: 'var(--risk-high)', marginTop: '0.45rem', fontStyle: 'italic' }}>
                      ⚠ Remediation SLA: {info.remediation_sla_days} days
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div style={{ marginTop: '0.85rem', fontSize: '0.74rem', color: 'var(--ink-faint)', fontStyle: 'italic' }}>
            Protected attributes excluded from features: {(fairness.protected_attributes_excluded_from_features || fairness.protected_attributes_excluded || []).join(', ')}
          </div>
          {fairness.data_note && (
            <div style={{ marginTop: '0.45rem', fontSize: '0.72rem', color: 'var(--ink-faint)', fontStyle: 'italic' }}>
              <TrendingUp size={10} style={{ verticalAlign: '-1px', marginRight: '5px' }} />
              {fairness.data_note}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Admin;
