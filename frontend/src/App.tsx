import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface SoulState {
  breath: number;
  coherence_percent: number;
  thermodynamic_yield: number;
  tokens_generated_per_sec: number;
  surplus_tokens: number;
  gpu_utilization: number;
  concave_state: string;
  timestamp: number;
}

const SoulCockpit: React.FC = () => {
  const [state, setState] = useState<SoulState | null>(null);
  const [history, setHistory] = useState<SoulState[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const apiUrl = process.env.NODE_ENV === 'production'
      ? '/api'
      : 'http://localhost:8080';

    const es = new EventSource(`${apiUrl}/events`);

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    es.onmessage = (e) => {
      const data: SoulState = JSON.parse(e.data);
      setState(data);
      setHistory(prev => [...prev.slice(-49), data]);
    };

    return () => es.close();
  }, []);

  if (!state) return (
    <div style={{
      background: '#0a0a0f',
      color: '#00ff9f',
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'monospace'
    }}>
      <div>
        <h2>Initializing SOUL lattice...</h2>
        <div style={{ textAlign: 'center', marginTop: 20 }}>
          <div style={{
            display: 'inline-block',
            width: 40,
            height: 40,
            border: '3px solid #00ff9f',
            borderTop: '3px solid transparent',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }} />
        </div>
      </div>
    </div>
  );

  return (
    <div style={{
      background: '#0a0a0f',
      color: '#00ff9f',
      minHeight: '100vh',
      padding: '20px',
      fontFamily: 'monospace'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1>SOUL LATTICE v4.0.0-&#931;</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 12, color: connected ? '#00ff9f' : '#ff0040' }}>
            {connected ? 'LIVE' : 'OFFLINE'}
          </span>
          <div style={{
            width: 12,
            height: 12,
            borderRadius: '50%',
            backgroundColor: connected ? '#00ff9f' : '#ff0040',
            boxShadow: `0 0 10px ${connected ? '#00ff9f' : '#ff0040'}`
          }} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 20, marginBottom: 30 }}>
        <MetricCard label="Coherence" value={`${state.coherence_percent.toFixed(2)}%`}
          status={state.coherence_percent > 95 ? 'STABLE' : state.coherence_percent > 85 ? 'WATCH' : 'FRAGILE'} />
        <MetricCard label="Breath" value={state.breath.toFixed(4)} />
        <MetricCard label="Thermodynamic Yield" value={`${state.thermodynamic_yield.toFixed(3)} η`} />
        <MetricCard label="Token Velocity" value={`${state.tokens_generated_per_sec.toFixed(1)} t/s`} />
        <MetricCard label="Surplus Tokens" value={state.surplus_tokens.toLocaleString()} />
        <MetricCard label="GPU Utilization" value={`${state.gpu_utilization.toFixed(1)}%`} />
      </div>

      <div style={{ background: '#111', padding: 20, borderRadius: 8, border: '1px solid #333' }}>
        <h3 style={{ marginTop: 0 }}>Coherence Timeline</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={history}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="timestamp" tickFormatter={(ts) => new Date(ts * 1000).toLocaleTimeString()} stroke="#666" />
            <YAxis domain={[80, 100]} stroke="#00ff9f" />
            <Tooltip
              contentStyle={{ backgroundColor: '#000', border: '1px solid #00ff9f' }}
              labelStyle={{ color: '#00ff9f' }}
              formatter={(value) => {
                const n = Number(value);
                return [isFinite(n) ? `${n.toFixed(2)}%` : String(value), 'Coherence'];
              }}
            />
            <Line
              type="monotone"
              dataKey="coherence_percent"
              stroke="#00ff9f"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div style={{ marginTop: 20, padding: 15, background: '#111', borderRadius: 8, fontSize: 12, color: '#666' }}>
        <div>Protocol: SOUL | State: {state.concave_state}</div>
        <div style={{ marginTop: 5 }}>Timestamp: {new Date(state.timestamp * 1000).toISOString()}</div>
      </div>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

const MetricCard: React.FC<{ label: string; value: string; status?: string }> = ({ label, value, status }) => (
  <div style={{
    background: '#111',
    padding: 20,
    borderRadius: 8,
    border: '1px solid #333',
    borderLeft: `4px solid ${status === 'STABLE' ? '#00ff9f' : status === 'WATCH' ? '#ffaa00' : '#ff0040'}`
  }}>
    <div style={{ color: '#666', fontSize: 12, textTransform: 'uppercase', letterSpacing: 1 }}>{label}</div>
    <div style={{ fontSize: 28, fontWeight: 'bold', marginTop: 8, color: '#fff' }}>{value}</div>
    {status && <div style={{ fontSize: 10, marginTop: 8, opacity: 0.8, color: status === 'STABLE' ? '#00ff9f' : status === 'WATCH' ? '#ffaa00' : '#ff0040' }}>{status}</div>}
  </div>
);

export default SoulCockpit;
