import React, { useState } from 'react';
import { CampusTopology, FinalDiagnosisReport } from '../types';
import { Server, Router, Network, Wifi, Shield } from 'lucide-react';

interface TopologyMapProps {
  topology: CampusTopology | null;
  report: FinalDiagnosisReport | null;
  hoveredDeviceId: string | null;
  onSelectDevice: (deviceId: string) => void;
}

export const TopologyMap: React.FC<TopologyMapProps> = ({
  topology,
  report,
  hoveredDeviceId,
  onSelectDevice,
}) => {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  if (!topology || !topology.nodes) {
    return (
      <div className="noc-card" style={{ padding: '24px', textAlign: 'center', height: '420px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: 'var(--text-muted)' }}>Loading campus topology graph...</span>
      </div>
    );
  }

  const affectedSet = new Set(report?.affected_devices || []);
  const rootCauseNode = (report?.status === 'diagnosed' && report?.affected_devices?.length) ? report.affected_devices[0] : null;

  const getNodeColor = (nodeId: string, status: string) => {
    if (rootCauseNode && nodeId === rootCauseNode && report?.status === 'diagnosed') {
      return 'var(--status-red)';
    }
    if (affectedSet.has(nodeId)) {
      return 'var(--status-amber)';
    }
    if (status === 'down') {
      return 'var(--status-red)';
    }
    if (status === 'degraded') {
      return 'var(--status-orange)';
    }
    return 'var(--accent-blue)';
  };

  const getNodeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'router':
        return <Router size={16} color="#fff" />;
      case 'firewall':
        return <Shield size={16} color="#fff" />;
      case 'access_point':
        return <Wifi size={16} color="#fff" />;
      case 'server':
        return <Server size={16} color="#fff" />;
      default:
        return <Network size={16} color="#fff" />;
    }
  };

  return (
    <div className="noc-card" style={{ padding: '16px', position: 'relative', overflow: 'hidden' }}>
      {/* Header Bar within Topology */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Network size={18} style={{ color: 'var(--accent-cyan)' }} />
          <span style={{ fontSize: '0.85rem', fontWeight: 600, letterSpacing: '0.04em' }}>
            CAMPUS NETWORK TOPOLOGY & BLAST RADIUS HEATMAP
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '0.725rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--status-red)' }} />
            <span style={{ color: 'var(--text-muted)' }}>Root Cause Node</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--status-amber)' }} />
            <span style={{ color: 'var(--text-muted)' }}>Impacted</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-blue)' }} />
            <span style={{ color: 'var(--text-muted)' }}>Nominal</span>
          </div>
        </div>
      </div>

      {/* SVG Canvas */}
      <svg
        viewBox="0 0 1000 520"
        style={{
          width: '100%',
          height: '420px',
          backgroundColor: '#05080f',
          borderRadius: '6px',
          border: '1px solid rgba(56, 189, 248, 0.08)',
        }}
      >
        <defs>
          <filter id="glow-root" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <filter id="glow-affected" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Links */}
        {topology.links.map((link) => {
          const srcNode = topology.nodes.find((n) => n.node_id === link.source_node);
          const tgtNode = topology.nodes.find((n) => n.node_id === link.target_node);
          if (!srcNode || !tgtNode) return null;

          const isFaultedLink = rootCauseNode
            ? (srcNode.node_id === rootCauseNode || tgtNode.node_id === rootCauseNode) && (report?.status === 'diagnosed')
            : false;
          const isHighlighted =
            hoveredDeviceId === srcNode.node_id ||
            hoveredDeviceId === tgtNode.node_id ||
            selectedNode === srcNode.node_id ||
            selectedNode === tgtNode.node_id;

          const strokeColor = isFaultedLink
            ? 'var(--status-red)'
            : isHighlighted
            ? 'var(--accent-cyan)'
            : 'rgba(56, 189, 248, 0.2)';

          const strokeWidth = isFaultedLink ? 3 : isHighlighted ? 2.5 : 1.5;

          return (
            <g key={link.link_id}>
              <line
                x1={srcNode.x || 500}
                y1={srcNode.y || 250}
                x2={tgtNode.x || 500}
                y2={tgtNode.y || 250}
                stroke={strokeColor}
                strokeWidth={strokeWidth}
                className={isFaultedLink ? 'link-congested' : ''}
              />
              {/* Optional Link Label on mid point */}
              {isFaultedLink && (
                <text
                  x={((srcNode.x || 0) + (tgtNode.x || 0)) / 2 + 10}
                  y={((srcNode.y || 0) + (tgtNode.y || 0)) / 2}
                  fill="var(--status-red)"
                  fontSize="9"
                  fontFamily="var(--font-mono)"
                  fontWeight="bold"
                >
                  FAULT PATH
                </text>
              )}
            </g>
          );
        })}

        {/* Nodes */}
        {topology.nodes.map((node) => {
          const isRoot = node.node_id === rootCauseNode && report?.status === 'diagnosed';
          const isAffected = affectedSet.has(node.node_id);
          const isHovered = hoveredDeviceId === node.node_id || selectedNode === node.node_id;
          const nx = node.x || 500;
          const ny = node.y || 250;
          const nodeColor = getNodeColor(node.node_id, node.status);

          return (
            <g
              key={node.node_id}
              transform={`translate(${nx}, ${ny})`}
              style={{ cursor: 'pointer' }}
              onClick={() => {
                setSelectedNode(node.node_id);
                onSelectDevice(node.node_id);
              }}
            >
              {/* Animated Blast Radius Ripple for Root Cause Node */}
              {isRoot && (
                <>
                  <circle cx="0" cy="0" r="18" fill="none" stroke="var(--status-red)" strokeWidth="2" className="blast-ripple" />
                  <circle cx="0" cy="0" r="30" fill="none" stroke="var(--status-red)" strokeWidth="1" strokeDasharray="4 2" className="blast-ripple" style={{ animationDelay: '0.6s' }} />
                </>
              )}

              {/* Node Outer Ring */}
              <circle
                cx="0"
                cy="0"
                r={isRoot ? 22 : isHovered ? 20 : 16}
                fill="#0a101d"
                stroke={nodeColor}
                strokeWidth={isRoot || isHovered ? 2.5 : 1.5}
                filter={isRoot ? 'url(#glow-root)' : isAffected ? 'url(#glow-affected)' : undefined}
                style={{ transition: 'all 0.2s ease' }}
              />

              {/* Node Inner Core */}
              <circle cx="0" cy="0" r={isRoot ? 15 : 11} fill={nodeColor} opacity={0.25} />

              {/* Node Label Text */}
              <text
                x="0"
                y={isRoot ? 34 : 28}
                textAnchor="middle"
                fill={isRoot ? 'var(--status-red)' : isHovered ? 'var(--accent-cyan)' : 'var(--text-secondary)'}
                fontSize={isRoot ? '11' : '9.5'}
                fontFamily="var(--font-mono)"
                fontWeight={isRoot || isHovered ? 'bold' : 'normal'}
              >
                {node.node_id}
              </text>

              <text
                x="0"
                y={isRoot ? 45 : 38}
                textAnchor="middle"
                fill="var(--text-muted)"
                fontSize="8"
                fontFamily="var(--font-ui)"
              >
                {node.segment}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
