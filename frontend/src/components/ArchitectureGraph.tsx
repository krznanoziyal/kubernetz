import React, { useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  type Node,
  type Edge as RFEdge,
  Position,
  Handle,
  NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useArchitectureStore } from '../stores/architectureStore';
import type { Platform, Cluster, Namespace, Workload, Service, Ingress } from '../types/platform';

// ─── Node Data Types ───────────────────────────────────────────────────────────

interface ClusterNodeData {
  label: string;
  provider: string;
  version: string;
  [key: string]: unknown;
}

interface NamespaceNodeData {
  label: string;
  [key: string]: unknown;
}

interface WorkloadNodeData {
  label: string;
  kind: string;
  replicas: number;
  image: string;
  [key: string]: unknown;
}

interface ServiceNodeData {
  label: string;
  serviceType: string;
  [key: string]: unknown;
}

interface IngressNodeData {
  label: string;
  ingressClass: string;
  [key: string]: unknown;
}

// ─── Custom Node Components ───────────────────────────────────────────────────

const workloadColors: Record<string, string> = {
  Deployment: 'bg-blue-600 border-blue-400',
  StatefulSet: 'bg-orange-600 border-orange-400',
  DaemonSet: 'bg-purple-600 border-purple-400',
  Job: 'bg-gray-600 border-gray-400',
  CronJob: 'bg-amber-700 border-amber-500',
  default: 'bg-slate-600 border-slate-400',
};

const WorkloadNode: React.FC<NodeProps> = ({ data }) => {
  const d = data as WorkloadNodeData;
  const colorClass = workloadColors[d.kind] ?? workloadColors.default;

  return (
    <div
      className={`
        px-3 py-2 rounded-lg border-2 shadow-lg min-w-[120px]
        ${colorClass}
      `}
    >
      <Handle type="target" position={Position.Top} className="!bg-white/30 !border-white/50 !w-2 !h-2" />
      <div className="text-white font-semibold text-xs truncate max-w-[140px]">
        {d.label}
      </div>
      <div className="text-white/70 text-[10px] mt-0.5">
        {d.kind} · ×{d.replicas}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-white/30 !border-white/50 !w-2 !h-2" />
    </div>
  );
};

const ServiceNode: React.FC<NodeProps> = ({ data }) => {
  const d = data as ServiceNodeData;
  return (
    <div className="px-3 py-2 rounded-lg border-2 border-green-400 bg-green-700 shadow-lg min-w-[100px]">
      <Handle type="target" position={Position.Top} className="!bg-white/30 !border-white/50 !w-2 !h-2" />
      <div className="text-white font-semibold text-xs truncate max-w-[140px]">
        {d.label}
      </div>
      <div className="text-green-200 text-[10px] mt-0.5">
        {d.serviceType}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-white/30 !border-white/50 !w-2 !h-2" />
    </div>
  );
};

const IngressNode: React.FC<NodeProps> = ({ data }) => {
  const d = data as IngressNodeData;
  return (
    <div className="px-3 py-2 rounded-lg border-2 border-purple-400 bg-purple-700 shadow-lg min-w-[110px]">
      <Handle type="target" position={Position.Top} className="!bg-white/30 !border-white/50 !w-2 !h-2" />
      <div className="text-white font-semibold text-xs truncate max-w-[140px]">
        {d.label}
      </div>
      <div className="text-purple-200 text-[10px] mt-0.5">
        Ingress · {d.ingressClass || 'nginx'}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-white/30 !border-white/50 !w-2 !h-2" />
    </div>
  );
};

const NamespaceNode: React.FC<NodeProps> = ({ data }) => {
  const d = data as NamespaceNodeData;
  return (
    <div className="px-2 py-1 rounded border-2 border-dashed border-cyan-600/60 bg-cyan-900/10 min-w-[160px]">
      <div className="text-cyan-400 text-[10px] font-medium uppercase tracking-wide">
        ns: {d.label}
      </div>
    </div>
  );
};

const ClusterNode: React.FC<NodeProps> = ({ data }) => {
  const d = data as ClusterNodeData;
  return (
    <div className="px-3 py-2 rounded-xl border-2 border-dashed border-gray-500/50 bg-gray-800/40 min-w-[200px]">
      <div className="text-gray-300 text-xs font-semibold">{d.label}</div>
      <div className="text-gray-500 text-[10px] mt-0.5">
        {d.provider} · k8s {d.version}
      </div>
    </div>
  );
};

const ExternalNode: React.FC<NodeProps> = ({ data }) => {
  const d = data as { label: string; depType: string };
  return (
    <div className="px-3 py-2 rounded-lg border-2 border-amber-600/60 bg-amber-900/20 min-w-[100px]">
      <Handle type="target" position={Position.Top} className="!bg-white/30 !border-white/50 !w-2 !h-2" />
      <div className="text-amber-300 text-xs font-semibold truncate max-w-[140px]">
        {d.label}
      </div>
      <div className="text-amber-500 text-[10px] mt-0.5">{d.depType}</div>
      <Handle type="source" position={Position.Bottom} className="!bg-white/30 !border-white/50 !w-2 !h-2" />
    </div>
  );
};

const nodeTypes = {
  workload: WorkloadNode,
  service: ServiceNode,
  ingress: IngressNode,
  namespace: NamespaceNode,
  cluster: ClusterNode,
  external: ExternalNode,
};

// ─── Layout Helper ─────────────────────────────────────────────────────────────

function buildGraphFromPlatform(platform: Platform): {
  nodes: Node[];
  edges: RFEdge[];
} {
  const nodes: Node[] = [];
  const edges: RFEdge[] = [];
  const edgeSet = new Set<string>();

  const addEdge = (source: string, target: string, label?: string) => {
    const key = `${source}→${target}`;
    if (edgeSet.has(key)) return;
    edgeSet.add(key);
    edges.push({
      id: key,
      source,
      target,
      label,
      animated: false,
      style: { stroke: '#4b5563', strokeWidth: 1.5 },
      labelStyle: { fill: '#9ca3af', fontSize: 10 },
      labelBgStyle: { fill: '#1f2937' },
    });
  };

  let clusterX = 40;

  platform.clusters.forEach((cluster: Cluster, ci: number) => {
    const clusterId = cluster.id || `cluster-${ci}`;
    const clusterY = 40;

    nodes.push({
      id: clusterId,
      type: 'cluster',
      position: { x: clusterX, y: clusterY },
      data: {
        label: cluster.name,
        provider: cluster.provider,
        version: cluster.kubernetes_version,
      } as ClusterNodeData,
      style: { width: 700, height: 500 },
    });

    let nsY = 80;

    cluster.namespaces.forEach((ns: Namespace, ni: number) => {
      const nsId = ns.id || `ns-${ci}-${ni}`;
      const nsX = clusterX + 20;

      nodes.push({
        id: nsId,
        type: 'namespace',
        position: { x: nsX, y: clusterY + nsY },
        data: { label: ns.name } as NamespaceNodeData,
        parentId: clusterId,
        extent: 'parent' as const,
        style: { width: 640, height: 200 },
      });

      let wX = 20;
      let svcX = 20;
      let ingX = 20;

      // Ingresses at top
      ns.ingresses.forEach((ing: Ingress, ii: number) => {
        const ingId = ing.id || `ing-${ci}-${ni}-${ii}`;
        nodes.push({
          id: ingId,
          type: 'ingress',
          position: { x: nsX + ingX, y: clusterY + nsY + 30 },
          data: {
            label: ing.name,
            ingressClass: ing.ingress_class ?? 'nginx',
          } as IngressNodeData,
          parentId: clusterId,
          extent: 'parent' as const,
        });
        ingX += 160;
      });

      // Workloads
      ns.workloads.forEach((w: Workload, wi: number) => {
        const wId = w.id || `wl-${ci}-${ni}-${wi}`;
        nodes.push({
          id: wId,
          type: 'workload',
          position: { x: nsX + wX, y: clusterY + nsY + 80 },
          data: {
            label: w.name,
            kind: w.kind,
            replicas: w.replicas,
            image: w.image,
          } as WorkloadNodeData,
          parentId: clusterId,
          extent: 'parent' as const,
        });
        wX += 160;
      });

      // Services
      ns.services.forEach((svc: Service, si: number) => {
        const svcId = svc.id || `svc-${ci}-${ni}-${si}`;
        nodes.push({
          id: svcId,
          type: 'service',
          position: { x: nsX + svcX, y: clusterY + nsY + 148 },
          data: {
            label: svc.name,
            serviceType: svc.service_type,
          } as ServiceNodeData,
          parentId: clusterId,
          extent: 'parent' as const,
        });
        svcX += 160;

        // Link services to workloads with matching selector
        ns.workloads.forEach((w: Workload) => {
          const wId = w.id || `wl-${ci}-${ni}-${ns.workloads.indexOf(w)}`;
          addEdge(svcId, wId);
        });
      });

      // Link ingresses to services
      ns.ingresses.forEach((ing: Ingress, ii: number) => {
        const ingId = ing.id || `ing-${ci}-${ni}-${ii}`;
        ns.services.forEach((svc: Service, si: number) => {
          const svcId = svc.id || `svc-${ci}-${ni}-${si}`;
          addEdge(ingId, svcId);
        });
      });

      nsY += 260;
    });

    clusterX += 780;
  });

  // External dependencies
  let extX = 40;
  platform.external_dependencies.forEach((dep, di) => {
    const depId = dep.id || `ext-${di}`;
    nodes.push({
      id: depId,
      type: 'external',
      position: { x: extX, y: 600 },
      data: { label: dep.name, depType: dep.dependency_type },
    });
    extX += 180;
  });

  // Backend-provided edges
  platform.edges.forEach((edge) => {
    addEdge(edge.source_id, edge.target_id, edge.label);
  });

  return { nodes, edges };
}

// ─── Empty State ───────────────────────────────────────────────────────────────

const EmptyGraph: React.FC = () => (
  <div className="flex flex-col items-center justify-center h-full text-center">
    <div className="p-6 bg-gray-800/50 rounded-2xl border border-dashed border-gray-700 max-w-xs">
      <div className="text-4xl mb-3">📊</div>
      <h3 className="text-gray-300 font-semibold mb-1">No Architecture Yet</h3>
      <p className="text-gray-500 text-sm">
        Upload a diagram or paste Mermaid text to visualize your Kubernetes
        architecture.
      </p>
    </div>
  </div>
);

// ─── Main Component ────────────────────────────────────────────────────────────

export const ArchitectureGraph: React.FC = () => {
  const { platform, hasParsed } = useArchitectureStore();

  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (!hasParsed || !platform.clusters.length) {
      return { nodes: [], edges: [] };
    }
    return buildGraphFromPlatform(platform);
  }, [platform, hasParsed]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  if (!hasParsed || !platform.clusters.length) {
    return <EmptyGraph />;
  }

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        attributionPosition="bottom-right"
        colorMode="dark"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#374151"
        />
        <Controls
          className="!bg-gray-800 !border-gray-700"
          showFitView
          showZoom
          showInteractive={false}
        />
        <MiniMap
          nodeColor={(n) => {
            const type = n.type;
            if (type === 'workload') return '#2563eb';
            if (type === 'service') return '#16a34a';
            if (type === 'ingress') return '#7c3aed';
            if (type === 'external') return '#b45309';
            return '#4b5563';
          }}
          maskColor="rgba(0,0,0,0.4)"
          className="!bg-gray-800/80 !border-gray-700"
        />
      </ReactFlow>
    </div>
  );
};

export default ArchitectureGraph;
