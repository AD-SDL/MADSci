<template>
  <v-card class="pa-4">
    <v-card-title class="text-center">
      <h3>Location Transfer Graph</h3>
    </v-card-title>
    <v-card-text>
      <div class="graph-container">
        <svg
          ref="svgElement"
          :width="svgWidth"
          :height="svgHeight"
          class="transfer-graph"
        >
          <!-- Background -->
          <rect :width="svgWidth" :height="svgHeight" fill="#f5f5f5" stroke="#ddd" />

          <!-- Grid lines -->
          <defs>
            <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#e0e0e0" stroke-width="1"/>
            </pattern>
          </defs>
          <rect :width="svgWidth" :height="svgHeight" fill="url(#grid)" />

          <!-- Group bounding boxes -->
          <g class="group-backgrounds">
            <g v-for="group in groups" :key="group.id">
              <rect
                :x="group.bounds.x - 15"
                :y="group.bounds.y - 30"
                :width="group.bounds.width + 30"
                :height="group.bounds.height + 45"
                rx="8"
                :fill="group.isNodeManaged ? 'rgba(33, 150, 243, 0.06)' : 'rgba(76, 175, 80, 0.06)'"
                :stroke="group.isNodeManaged ? '#2196F3' : '#4CAF50'"
                stroke-width="1"
                stroke-dasharray="6 3"
                stroke-opacity="0.4"
              />
              <text
                :x="group.bounds.x - 10"
                :y="group.bounds.y - 15"
                font-size="11"
                font-weight="600"
                :fill="group.isNodeManaged ? '#1565C0' : '#2E7D32'"
                font-family="'Roboto', sans-serif"
              >
                {{ group.label }}
              </text>
            </g>
          </g>

          <!-- Transfer edges (location-to-location) -->
          <g class="edges">
            <g
              v-for="edge in renderedEdges"
              :key="`${edge.sourceId}-${edge.targetId}`"
              @mouseenter="hoveredEdge = edge"
              @mouseleave="hoveredEdge = null"
              style="cursor: pointer;"
            >
              <line
                :x1="edge.x1"
                :y1="edge.y1"
                :x2="edge.x2"
                :y2="edge.y2"
                stroke="#90A4AE"
                :stroke-width="hoveredEdge === edge ? 2.5 : 1"
                :stroke-opacity="hoveredEdge === edge ? 0.8 : 0.3"
              />
              <!-- Invisible wider line for easier hover targeting -->
              <line
                :x1="edge.x1"
                :y1="edge.y1"
                :x2="edge.x2"
                :y2="edge.y2"
                stroke="transparent"
                stroke-width="12"
              />
            </g>
          </g>

          <!-- Location nodes -->
          <g class="nodes">
            <g
              v-for="node in layoutNodes"
              :key="node.id"
              :transform="`translate(${node.x}, ${node.y})`"
              class="location-node"
              @click="handleNodeClick(node)"
              @mouseenter="hoveredNode = node.id"
              @mouseleave="hoveredNode = null"
            >
              <!-- Node circle: fill = resource quantity, stroke = management type -->
              <circle
                :r="20"
                :fill="getNodeFill(node)"
                :stroke="getNodeStroke(node)"
                stroke-width="3"
                class="node-circle"
              />
              <!-- Index label inside circle -->
              <text
                v-if="node.index !== null"
                text-anchor="middle"
                dominant-baseline="central"
                font-size="13"
                font-weight="bold"
                :fill="getIndexColor(node)"
                class="node-index"
              >
                {{ node.index }}
              </text>
            </g>
          </g>

          <!-- Hover tooltips for nodes (rendered last for top z-index) -->
          <g class="hover-tooltips" style="pointer-events: none;">
            <g
              v-for="node in layoutNodes"
              :key="`tooltip-${node.id}`"
              :transform="`translate(${node.x}, ${node.y})`"
            >
              <rect
                v-show="hoveredNode === node.id"
                :x="-Math.max(50, node.name.length * 4)"
                :y="-45"
                :width="Math.max(100, node.name.length * 8)"
                height="20"
                rx="4"
                fill="rgba(0, 0, 0, 0.9)"
                stroke="white"
                stroke-width="1"
              />
              <text
                v-show="hoveredNode === node.id"
                text-anchor="middle"
                y="-32"
                font-size="12"
                font-weight="bold"
                fill="white"
                class="node-label-hover"
              >
                {{ node.name }}
              </text>
            </g>
          </g>

          <!-- Hover tooltip for edges -->
          <g v-if="hoveredEdge" class="edge-tooltip" style="pointer-events: none;">
            <rect
              :x="(hoveredEdge.x1 + hoveredEdge.x2) / 2 - edgeTooltipWidth / 2"
              :y="(hoveredEdge.y1 + hoveredEdge.y2) / 2 - 30"
              :width="edgeTooltipWidth"
              height="22"
              rx="4"
              fill="rgba(0, 0, 0, 0.9)"
              stroke="white"
              stroke-width="1"
            />
            <text
              :x="(hoveredEdge.x1 + hoveredEdge.x2) / 2"
              :y="(hoveredEdge.y1 + hoveredEdge.y2) / 2 - 15"
              text-anchor="middle"
              font-size="11"
              fill="white"
              font-family="'Roboto', sans-serif"
            >
              via: {{ hoveredEdge.nodeNames.join(', ') }}
            </text>
          </g>
        </svg>
      </div>

      <!-- Legend -->
      <div class="mt-4">
        <v-row>
          <v-col cols="12" md="4">
            <div class="legend-item d-flex align-center mb-2">
              <svg width="24" height="24"><circle cx="12" cy="12" r="10" fill="#E0E0E0" stroke="#4CAF50" stroke-width="3" /></svg>
              <span class="ml-2">Lab-Managed</span>
            </div>
            <div class="legend-item d-flex align-center mb-2">
              <svg width="24" height="24"><circle cx="12" cy="12" r="10" fill="#E0E0E0" stroke="#2196F3" stroke-width="3" /></svg>
              <span class="ml-2">Node-Managed</span>
            </div>
          </v-col>
          <v-col cols="12" md="4">
            <div class="legend-item d-flex align-center mb-2">
              <svg width="24" height="24"><circle cx="12" cy="12" r="10" fill="#E0E0E0" stroke="#999" stroke-width="2" /></svg>
              <span class="ml-2">No Resource</span>
            </div>
            <div class="legend-item d-flex align-center mb-2">
              <svg width="80" height="24">
                <circle cx="12" cy="12" r="10" fill="#FFFFFF" stroke="#999" stroke-width="2" />
                <circle cx="36" cy="12" r="10" fill="#64B5F6" stroke="#999" stroke-width="2" />
                <circle cx="60" cy="12" r="10" fill="#1565C0" stroke="#999" stroke-width="2" />
              </svg>
              <span class="ml-2">Resource Fill (empty -> full)</span>
            </div>
          </v-col>
          <v-col cols="12" md="4">
            <div class="legend-item d-flex align-center mb-2">
              <svg width="30" height="24"><line x1="0" y1="12" x2="30" y2="12" stroke="#90A4AE" stroke-width="1" stroke-opacity="0.3" /></svg>
              <span class="ml-2">Transfer Connection</span>
            </div>
          </v-col>
        </v-row>
      </div>

      <!-- Info panel -->
      <div v-if="selectedNode" class="mt-4 pa-3" style="background-color: #f0f0f0; border-radius: 4px;">
        <h4>{{ selectedNode.name }}</h4>
        <p><strong>ID:</strong> {{ selectedNode.id }}</p>
        <p><strong>Managed By:</strong> {{ (selectedNode.managedBy || 'lab').toUpperCase() }}</p>
        <p><strong>Owner:</strong> {{ selectedNode.ownerNodeName || selectedNode.ownerNodeId || 'N/A' }}</p>
        <p><strong>Status:</strong> {{ selectedNode.occupied || 'Unknown' }}</p>
        <p><strong>Resource:</strong> {{ selectedNode.hasResource ? 'Present' : 'None' }}</p>
        <p v-if="selectedNode.quantity !== null"><strong>Quantity:</strong> {{ selectedNode.quantity }} / {{ selectedNode.capacity }}</p>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

const props = defineProps<{
  locations: Record<string, any>;
  resources: any[];
  transferEdges?: Array<{
    source_location_id: string;
    target_location_id: string;
    node_names: string[];
    min_cost: number;
  }>;
  locationIndices?: Record<string, number>;
}>();

const emit = defineEmits<{
  'node-click': [node: any];
}>();

const svgElement = ref<SVGElement>();
const svgWidth = ref(800);
const svgHeight = ref(600);
const selectedNode = ref<any>(null);
const hoveredNode = ref<string | null>(null);
const hoveredEdge = ref<any>(null);

interface GraphNode {
  id: string;
  name: string;
  index: number | null;
  x: number;
  y: number;
  vx: number;
  vy: number;
  managedBy: string;
  ownerNodeId: string | null;
  ownerNodeName: string | null;
  groupId: string;
  hasResource: boolean;
  occupied: string;
  quantity: number | null;
  capacity: number | null;
  fillRatio: number | null;
  originalLocation: any;
}

// Build graph nodes from locations
const layoutNodes = computed(() => {
  const locationArray = Object.entries(props.locations || {});
  if (locationArray.length === 0) return [];

  const nodes: GraphNode[] = [];
  const margin = 80;

  // Seeded random for consistent layout
  let seed = 12345;
  const seededRandom = () => {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };

  locationArray.forEach(([key, location]) => {
    // Resource info
    const resource = location.resource_id
      ? props.resources?.find((r: any) => r.resource_id === location.resource_id)
      : null;

    const hasResource = !!(resource && (resource.quantity || 0) > 0);
    const occupied = hasResource ? 'Occupied' : location.resource_id ? 'Empty' : 'Unknown';

    const quantity = resource?.quantity ?? null;
    const capacity = resource?.capacity ?? null;
    const fillRatio = (quantity !== null && capacity !== null && capacity > 0)
      ? Math.min(1, Math.max(0, quantity / capacity))
      : null;

    // Group by management type
    const managedBy = location.managed_by || 'lab';
    const ownerNodeId = location.owner?.node_id || null;
    // For node-managed locations, derive a human-readable name from the
    // first representation key (which is the node name), falling back to
    // a truncated owner ID.
    let ownerNodeName: string | null = null;
    if (managedBy === 'node') {
      const repKeys = Object.keys(location.representations || {});
      ownerNodeName = repKeys.length > 0 ? repKeys[0] : (ownerNodeId ? ownerNodeId.slice(0, 8) + '...' : null);
    }
    const groupId = managedBy === 'node' && ownerNodeName ? `node:${ownerNodeName}` : 'lab';

    nodes.push({
      id: location.location_id || key,
      name: location.name || location.location_name || key,
      index: props.locationIndices?.[location.location_id] ?? null,
      x: margin + seededRandom() * (svgWidth.value - 2 * margin),
      y: margin + seededRandom() * (svgHeight.value - 2 * margin),
      vx: 0,
      vy: 0,
      managedBy,
      ownerNodeId,
      ownerNodeName,
      groupId,
      hasResource,
      occupied,
      quantity,
      capacity,
      fillRatio,
      originalLocation: location,
    });
  });

  return applyForceDirectedLayout(nodes);
});

// Compute groups with bounding boxes
const groups = computed(() => {
  const groupMap: Record<string, { nodes: GraphNode[]; isNodeManaged: boolean; label: string }> = {};

  for (const node of layoutNodes.value) {
    if (!groupMap[node.groupId]) {
      const isNodeManaged = node.groupId !== 'lab';
      const label = isNodeManaged ? `Node: ${node.ownerNodeName || node.ownerNodeId}` : 'Lab-Managed';
      groupMap[node.groupId] = { nodes: [], isNodeManaged, label };
    }
    groupMap[node.groupId].nodes.push(node);
  }

  return Object.entries(groupMap).map(([id, group]) => {
    const xs = group.nodes.map(n => n.x);
    const ys = group.nodes.map(n => n.y);
    const pad = 25;
    return {
      id,
      label: group.label,
      isNodeManaged: group.isNodeManaged,
      bounds: {
        x: Math.min(...xs) - pad,
        y: Math.min(...ys) - pad,
        width: Math.max(...xs) - Math.min(...xs) + pad * 2,
        height: Math.max(...ys) - Math.min(...ys) + pad * 2,
      },
    };
  });
});

// Build edges from transferEdges prop
const renderedEdges = computed(() => {
  if (!props.transferEdges || layoutNodes.value.length === 0) return [];

  const nodeMap = new Map(layoutNodes.value.map(n => [n.id, n]));
  const edgeList: any[] = [];
  const seen = new Set<string>();

  for (const edge of props.transferEdges) {
    const source = nodeMap.get(edge.source_location_id);
    const target = nodeMap.get(edge.target_location_id);
    if (!source || !target) continue;

    // Deduplicate bidirectional edges (A->B and B->A become one line)
    const pairKey = [edge.source_location_id, edge.target_location_id].sort().join('|');
    if (seen.has(pairKey)) {
      // Merge node names into existing edge
      const existing = edgeList.find(e => {
        const ek = [e.sourceId, e.targetId].sort().join('|');
        return ek === pairKey;
      });
      if (existing) {
        for (const n of edge.node_names) {
          if (!existing.nodeNames.includes(n)) {
            existing.nodeNames.push(n);
          }
        }
      }
      continue;
    }
    seen.add(pairKey);

    edgeList.push({
      sourceId: edge.source_location_id,
      targetId: edge.target_location_id,
      x1: source.x,
      y1: source.y,
      x2: target.x,
      y2: target.y,
      nodeNames: [...edge.node_names],
    });
  }

  return edgeList;
});

// Tooltip width for edge hover
const edgeTooltipWidth = computed(() => {
  if (!hoveredEdge.value) return 100;
  const text = `via: ${hoveredEdge.value.nodeNames.join(', ')}`;
  return Math.max(80, text.length * 7);
});

function getNodeFill(node: GraphNode): string {
  if (!node.originalLocation.resource_id) {
    return '#E0E0E0'; // Gray: no resource attached
  }
  if (node.fillRatio === null) {
    return '#BBDEFB'; // Light blue: resource present but no quantity data
  }
  // Interpolate white (255,255,255) to deep blue (21,101,192)
  const r = Math.round(255 - node.fillRatio * (255 - 21));
  const g = Math.round(255 - node.fillRatio * (255 - 101));
  const b = Math.round(255 - node.fillRatio * (255 - 192));
  return `rgb(${r}, ${g}, ${b})`;
}

function getNodeStroke(node: GraphNode): string {
  return node.managedBy === 'node' ? '#2196F3' : '#4CAF50';
}

function getIndexColor(node: GraphNode): string {
  // Use white text on dark fills, dark text on light fills
  if (node.fillRatio !== null && node.fillRatio > 0.5) return '#FFFFFF';
  return '#333333';
}

function applyForceDirectedLayout(nodes: GraphNode[]): GraphNode[] {
  const iterations = 200;
  const margin = 80;
  const centerX = svgWidth.value / 2;
  const centerY = svgHeight.value / 2;

  // Build group membership map (stable across iterations)
  const groupMembers: Record<string, GraphNode[]> = {};
  for (const n of nodes) {
    if (!groupMembers[n.groupId]) groupMembers[n.groupId] = [];
    groupMembers[n.groupId].push(n);
  }
  const groupIds = Object.keys(groupMembers);

  // Build edges from transferEdges for attraction
  const transferEdgeSet: Array<{ source: GraphNode; target: GraphNode }> = [];
  if (props.transferEdges) {
    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    for (const edge of props.transferEdges) {
      const s = nodeMap.get(edge.source_location_id);
      const t = nodeMap.get(edge.target_location_id);
      if (s && t) transferEdgeSet.push({ source: s, target: t });
    }
  }

  for (let iter = 0; iter < iterations; iter++) {
    const alpha = Math.max(0.01, 0.3 * (1 - iter / iterations));

    // Reset forces
    for (const node of nodes) {
      (node as any).fx = 0;
      (node as any).fy = 0;
    }

    // 1. Node-level repulsion (same strength for all — group separation
    //    is handled by centroid repulsion below)
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = 1500 / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        (a as any).fx -= fx;
        (a as any).fy -= fy;
        (b as any).fx += fx;
        (b as any).fy += fy;
      }
    }

    // 2. Group centroid repulsion — push entire groups apart
    //    This is the key force that prevents group overlap.
    const centroids: Record<string, { cx: number; cy: number; count: number }> = {};
    for (const gid of groupIds) {
      let cx = 0, cy = 0;
      for (const m of groupMembers[gid]) { cx += m.x; cy += m.y; }
      const count = groupMembers[gid].length;
      centroids[gid] = { cx: cx / count, cy: cy / count, count };
    }
    for (let i = 0; i < groupIds.length; i++) {
      for (let j = i + 1; j < groupIds.length; j++) {
        const ga = centroids[groupIds[i]];
        const gb = centroids[groupIds[j]];
        const dx = gb.cx - ga.cx;
        const dy = gb.cy - ga.cy;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        // Scale force by combined group size so larger groups push harder
        const combinedSize = ga.count + gb.count;
        const minSeparation = 220 + combinedSize * 25;
        if (dist < minSeparation) {
          const strength = 8.0 * (minSeparation - dist) / minSeparation;
          const fx = (dx / dist) * strength;
          const fy = (dy / dist) * strength;
          // Apply to all members of each group
          for (const m of groupMembers[groupIds[i]]) {
            (m as any).fx -= fx;
            (m as any).fy -= fy;
          }
          for (const m of groupMembers[groupIds[j]]) {
            (m as any).fx += fx;
            (m as any).fy += fy;
          }
        }
      }
    }

    // 3. Intra-group attraction (pull group members toward their centroid)
    for (const gid of groupIds) {
      const members = groupMembers[gid];
      if (members.length < 2) continue;
      const c = centroids[gid];
      for (const m of members) {
        const dx = c.cx - m.x;
        const dy = c.cy - m.y;
        (m as any).fx += dx * 0.08;
        (m as any).fy += dy * 0.08;
      }
    }

    // 4. Transfer edge attraction (weaker — don't override group separation)
    for (const edge of transferEdgeSet) {
      const dx = edge.target.x - edge.source.x;
      const dy = edge.target.y - edge.source.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const idealDist = 120;
      const force = 0.04 * (dist - idealDist);
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      (edge.source as any).fx += fx;
      (edge.source as any).fy += fy;
      (edge.target as any).fx -= fx;
      (edge.target as any).fy -= fy;
    }

    // 5. Center gravity (stronger to fill available space)
    for (const node of nodes) {
      (node as any).fx += (centerX - node.x) * 0.02;
      (node as any).fy += (centerY - node.y) * 0.02;
    }

    // 6. Apply forces
    for (const node of nodes) {
      node.vx = (node.vx + (node as any).fx * alpha) * 0.8;
      node.vy = (node.vy + (node as any).fy * alpha) * 0.8;
      node.x = Math.max(margin, Math.min(svgWidth.value - margin, node.x + node.vx));
      node.y = Math.max(margin, Math.min(svgHeight.value - margin, node.y + node.vy));
    }
  }

  return nodes;
}

function handleNodeClick(node: GraphNode) {
  selectedNode.value = node;
  emit('node-click', node);
}

// Handle window resize
onMounted(() => {
  const container = svgElement.value?.parentElement;
  if (container) {
    const resizeObserver = new ResizeObserver(() => {
      const newWidth = Math.max(400, container.clientWidth - 32);
      const newHeight = Math.max(300, newWidth * 0.6);
      if (Math.abs(newWidth - svgWidth.value) > 50 || Math.abs(newHeight - svgHeight.value) > 30) {
        svgWidth.value = newWidth;
        svgHeight.value = newHeight;
      }
    });
    resizeObserver.observe(container);
  }
});
</script>

<style scoped>
.graph-container {
  width: 100%;
  overflow: auto;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.transfer-graph {
  display: block;
  margin: 0 auto;
}

.location-node {
  cursor: pointer;
  transition: all 0.2s ease;
}

.location-node:hover .node-circle {
  stroke-width: 4;
  filter: brightness(1.1);
}

.node-index {
  pointer-events: none;
  user-select: none;
  font-family: 'Roboto', sans-serif;
}

.node-label-hover {
  pointer-events: none;
  user-select: none;
  font-family: 'Roboto', sans-serif;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8);
}

.legend-item {
  font-size: 14px;
}
</style>
