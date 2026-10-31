import React, { useState, useEffect } from 'react';
import { Play, Pause, ChevronRight, ChevronLeft, X, Sparkles, CheckCircle2 } from 'lucide-react';

interface PresentationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PresentationModal: React.FC<PresentationModalProps> = ({ isOpen, onClose }) => {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);

  const slides = [
    {
      title: '1. Incident Ingestion & High-Dimensional Telemetry',
      subtitle: 'NOC telemetry ingestion across core, aggregation, and access points',
      narrative:
        'The system continuously ingests telemetry across campus segments (Hostels, Academic, Library, Labs, Data Center). In our flagship scenario, 12 access switches and APs report elevated latency and packet drops simultaneously.',
      highlight: '96% Link Saturation | 14,230 Egress Queue Drops | 145 ms Latency',
      proof: 'Deterministic validation ensures no malformed or out-of-range metrics enter the pipeline.',
    },
    {
      title: '2. Domain-Specific Parallel Agent Analysis',
      subtitle: 'Specialized agents with decoupled analytical lenses',
      narrative:
        'Instead of a generic chatbot, three specialized domain agents analyze telemetry in parallel: Performance Agent analyzes throughput & loss; Infrastructure Agent checks buffer drops & CRC hardware; Connectivity Agent traverses the graph topology.',
      highlight: 'Performance Agent: Severe Congestion | Infrastructure Agent: Queue Exhaustion',
      proof: 'Agents operate asynchronously with timeout protection and structured Pydantic v2 protocol envelopes.',
    },
    {
      title: '3. Interactive Multi-Agent Cross-Query Dialogue',
      subtitle: 'True agent-to-agent collaboration over standardized protocol',
      narrative:
        'When the Correlation Agent notices that 12 devices are degraded, it does not guess. It sends a dynamic clarification_request to the Connectivity Agent: "Do the 12 affected devices share a single upstream link?". The Connectivity Agent replies affirmatively with 100% path confirmation.',
      highlight: 'Correlation Agent ↔ Connectivity Agent (Live Clarification Exchange)',
      proof: 'This cross-query step directly updates the evidence matrix before picking a root cause.',
    },
    {
      title: '4. The Hypothesis Race: Evidence Convergence',
      subtitle: 'Transparent weighted scoring with uncertainty awareness',
      narrative:
        'All competing hypotheses race side-by-side (Bandwidth Congestion, Buffer Exhaustion, CPU Overload, Cable Degradation). Confidence is mathematically computed from corroborating signals and penalized if runner-up hypotheses are close.',
      highlight: 'Bandwidth Congestion Leads at 88% Confidence | Margin: +34%',
      proof: 'The system explicitly flags ambiguity when competing hypotheses are within 8% of each other.',
    },
    {
      title: '5. The "What If An Agent Were Missing?" Proof',
      subtitle: 'Empirical verification of genuine multi-agent interdependence',
      narrative:
        'Turn off the Infrastructure Agent with one click, and watch what happens: the confidence immediately drops from 88% to 58%, and the system flags missing hardware telemetry in the limitations section.',
      highlight: 'Remove One Agent → Diagnosis Visibly Changes',
      proof: 'This directly answers the hackathon judge question: "Where is the multi-agent collaboration?".',
    },
    {
      title: '6. Section 6 Strict Compliance & Simulated Remediation',
      subtitle: 'Standardized incident reporting for enterprise NOC teams',
      narrative:
        'The final output conforms strictly to the Section 6 JSON Schema. Every recommendation enforces the mandatory human review wording: "Recommended action — human review required." Simulated remediation models traffic shaping impact without ever touching live equipment.',
      highlight: '100% Section 6 JSON Compliant | Human-in-the-Loop Safeguards',
      proof: 'Includes both executive Markdown for management and raw JSON for automated ticketing integration.',
    },
  ];

  useEffect(() => {
    let timer: any;
    if (isOpen && isPlaying) {
      timer = setInterval(() => {
        setCurrentSlide((prev) => (prev + 1) % slides.length);
      }, 7000);
    }
    return () => clearInterval(timer);
  }, [isOpen, isPlaying, slides.length]);

  if (!isOpen) return null;

  const slide = slides[currentSlide];

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        backgroundColor: 'rgba(3, 7, 18, 0.92)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 200,
        padding: '24px',
        backdropFilter: 'blur(8px)',
      }}
    >
      <div
        className="noc-card"
        style={{
          width: '840px',
          maxWidth: '95vw',
          backgroundColor: '#0a101d',
          border: '1px solid var(--accent-cyan)',
          padding: '28px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
          position: 'relative',
          boxShadow: '0 0 50px rgba(0, 240, 255, 0.2)',
        }}
      >
        {/* Top Controls */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={20} style={{ color: 'var(--accent-cyan)' }} />
            <span style={{ fontSize: '0.95rem', fontWeight: 700, letterSpacing: '0.04em' }}>
              PRESENTER MODE: HACKATHON JUDGE WALKTHROUGH
            </span>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              fontSize: '1.2rem',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Progress Dots */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {slides.map((_, idx) => (
            <div
              key={idx}
              onClick={() => setCurrentSlide(idx)}
              style={{
                height: '4px',
                flex: 1,
                backgroundColor: idx === currentSlide ? 'var(--accent-cyan)' : 'rgba(56, 189, 248, 0.2)',
                borderRadius: '2px',
                cursor: 'pointer',
                transition: 'background-color 0.3s ease',
              }}
            />
          ))}
        </div>

        {/* Slide Body */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>
            {slide.title}
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--accent-blue)', fontWeight: 500 }}>
            {slide.subtitle}
          </div>

          <div
            style={{
              fontSize: '0.925rem',
              color: 'var(--text-primary)',
              lineHeight: 1.6,
              backgroundColor: '#05080f',
              padding: '16px',
              borderRadius: '6px',
              border: '1px solid var(--border-subtle)',
            }}
          >
            {slide.narrative}
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: 'rgba(0, 240, 255, 0.08)',
              border: '1px solid rgba(0, 240, 255, 0.3)',
              borderRadius: '6px',
              padding: '12px 16px',
            }}
          >
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>KEY HIGHLIGHT</div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                {slide.highlight}
              </div>
            </div>

            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>ARCHITECTURAL GUARANTEE</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                {slide.proof}
              </div>
            </div>
          </div>
        </div>

        {/* Footer Navigation */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '10px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }} className="font-mono">
            Slide {currentSlide + 1} of {slides.length}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={() => setCurrentSlide((prev) => (prev > 0 ? prev - 1 : slides.length - 1))}
              style={{
                backgroundColor: '#111827',
                border: '1px solid var(--border-subtle)',
                color: '#fff',
                borderRadius: '6px',
                padding: '6px 12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <ChevronLeft size={16} /> Previous
            </button>

            <button
              onClick={() => setIsPlaying(!isPlaying)}
              style={{
                backgroundColor: '#111827',
                border: '1px solid var(--border-subtle)',
                color: isPlaying ? 'var(--status-amber)' : 'var(--status-green)',
                borderRadius: '6px',
                padding: '6px 12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              {isPlaying ? <Pause size={16} /> : <Play size={16} />}
              {isPlaying ? 'Pause' : 'Auto-Play'}
            </button>

            <button
              onClick={() => setCurrentSlide((prev) => (prev + 1) % slides.length)}
              style={{
                backgroundColor: 'rgba(56, 189, 248, 0.2)',
                border: '1px solid var(--border-active)',
                color: 'var(--accent-cyan)',
                borderRadius: '6px',
                padding: '6px 16px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontWeight: 600,
              }}
            >
              Next <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
