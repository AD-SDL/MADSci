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

          <!-- Transfer connections (edges) -->
          <g class="connections">
            <line
              v-for="connection in connections"
              :key="`${connection.from}-${connection.to}`"
              :x1="connection.x1"
              :y1="connection.y1"
              :x2="connection.x2"
              :y2="connection.y2"
              stroke="#2196F3"
              :stroke-width="connection.weight || 2"
              stroke-opacity="0.6"
              marker-end="url(#arrowhead)"
            />
          </g>

          <!-- Location nodes -->
          <g class="nodes">
            <g
              v-for="node in nodes"
              :key="node.id"
              :transform="`translate(${node.x}, ${node.y})`"
              class="location-node"
              @click="handleNodeClick(node)"
              @mouseenter="hoveredNode = node.id"
              @mouseleave="hoveredNode = null"
            >
              <!-- Node circle -->
              <circle
                :r="node.radius || 25"
                :fill="getNodeColor(node)"
                stroke="#333"
                stroke-width="2"
                class="node-circle"
              />

              <!-- Resource indicator (only for location nodes) -->
              <circle
                v-if="node.type === 'location' && node.hasResource"
                :cx="15"
                :cy="-15"
                r="5"
                fill="#4CAF50"
                stroke="white"
                stroke-width="1"
                class="resource-indicator"
              />

              <!-- MADSci node indicator -->
              <circle
                v-if="node.type === 'madsci_node'"
                :cx="0"
                :cy="0"
                r="3"
                fill="white"
                class="node-type-indicator"
              />
            </g>
          </g>

          <!-- Hover tooltips (rendered last for top z-index) -->
          <g class="hover-tooltips">
            <g
              v-for="node in nodes"
              :key="`tooltip-${node.id}`"
              :transform="`translate(${node.x}, ${node.y})`"
              class="tooltip-group"
              style="pointer-events: none;"
            >
              <!-- Hover tooltip background -->
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
                class="hover-tooltip"
              />

              <!-- Full name on hover (no truncation) -->
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

          <!-- Arrow marker definition -->
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7"
                    refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#2196F3" />
            </marker>
          </defs>
        </svg>
      </div>

      <!-- Legend -->
      <div class="mt-4">
        <v-row>
          <v-col cols="12" md="6">
            <div class="legend-item d-flex align-center mb-2">
              <div class="legend-color occupied mr-2"></div>
              <span>Occupied Location</span>
            </div>
            <div class="legend-item d-flex align-center mb-2">
              <div class="legend-color empty mr-2"></div>
              <span>Empty Location</span>
            </div>
            <div class="legend-item d-flex align-center mb-2">
              <div class="legend-color unknown mr-2"></div>
              <span>Unknown Status</span>
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <div class="legend-item d-flex align-center mb-2">
              <div class="legend-color madsci-node mr-2"></div>
              <span>MADSci Node</span>
            </div>
            <div class="legend-item d-flex align-center mb-2">
              <div class="transfer-line mr-2"></div>
              <span>Location-Node Access</span>
            </div>
          </v-col>
        </v-row>
      </div>

      <!-- Info panel -->
      <div v-if="selectedNode" class="mt-4 pa-3" style="background-color: #f0f0f0; border-radius: 4px;">
        <h4>{{ selectedNode.name }}</h4>
        <p><strong>ID:</strong> {{ selectedNode.id }}</p>
        <p><strong>Type:</strong> {{ selectedNode.type === 'madsci_node' ? 'MADSci Node' : 'Location' }}</p>

        <!-- Location-specific information -->
        <div v-if="selectedNode.type === 'location'">
          <p><strong>Status:</strong> {{ selectedNode.occupied || 'Unknown' }}</p>
          <p><strong>Resource:</strong> {{ selectedNode.hasResource ? 'Present' : 'None' }}</p>
        </div>

        <!-- MADSci node-specific information -->
        <div v-if="selectedNode.type === 'madsci_node'">
          <p><strong>Connected Locations:</strong> {{ getConnectedLocations(selectedNode).length }}</p>
          <div v-if="getConnectedLocations(selectedNode).length > 0">
            <p><strong>Accessible Locations:</strong></p>
            <ul class="ml-4">
              <li v-for="location in getConnectedLocations(selectedNode)" :key="location.id">
                {{ location.name }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';

const props = defineProps<{
  locations: Record<string, any>;
  resources: any[];
  transfers?: any[]; // Future: transfer events/history
}>();

const emit = defineEmits<{
  'node-click': [node: any];
}>();

const svgElement = ref<SVGElement>();
const svgWidth = ref(800);
const svgHeight = ref(600);
const selectedNode = ref<any>(null);
const hoveredNode = ref<string | null>(null);

// Create nodes from locations data and MADSci nodes with force-directed layout
const nodes = computed(() => {
  const locationArray = Object.entries(props.locations || {});
  const allNodes: any[] = [];

  if (locationArray.length === 0) return [];

  // Get all unique MADSci nodes from location representations
  const madsciNodes = new Set<string>();
  locationArray.forEach(([_, location]) => {
    const representations = getNodeRepresentations(location);
    representations.forEach(nodeId => madsciNodes.add(nodeId));
  });

  const madsciNodeArray = Array.from(madsciNodes);

  // Initialize nodes with seeded random positions for consistency
  const centerX = svgWidth.value / 2;
  const centerY = svgHeight.value / 2;
  const margin = 80;

  // Simple seeded random generator for consistent layout
  let seed = 12345;
  const seededRandom = () => {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };

  // Add location nodes
  locationArray.forEach(([key, location]) => {
    // Determine if location has a resource
    const hasResource = location.resource_id &&
      props.resources?.some((resource: any) =>
        resource.resource_id === location.resource_id &&
        (resource.quantity || 0) > 0
      );

    // Determine occupation status
    const occupied = hasResource ? 'Occupied' :
                    location.resource_id ? 'Empty' : 'Unknown';

    allNodes.push({
      id: location.location_id || key,
      name: location.name || location.location_name || key,
      x: margin + seededRandom() * (svgWidth.value - 2 * margin),
      y: margin + seededRandom() * (svgHeight.value - 2 * margin),
      vx: 0,
      vy: 0,
      radius: 20,
      type: 'location',
      hasResource,
      occupied,
      originalLocation: location
    });
  });

  // Add MADSci node vertices
  madsciNodeArray.forEach((nodeId) => {
    allNodes.push({
      id: `node_${nodeId}`,
      name: nodeId,
      x: margin + seededRandom() * (svgWidth.value - 2 * margin),
      y: margin + seededRandom() * (svgHeight.value - 2 * margin),
      vx: 0,
      vy: 0,
      radius: 15,
      type: 'madsci_node',
      nodeId: nodeId
    });
  });

  // Apply force-directed layout
  return applyForceDirectedLayout(allNodes);
});

// Create connections between locations and MADSci nodes
const connections = computed(() => {
  const connections: any[] = [];

  const locationNodes = nodes.value.filter(n => n.type === 'location');
  const madsciNodes = nodes.value.filter(n => n.type === 'madsci_node');

  // Create edges between locations and MADSci nodes they can access
  locationNodes.forEach(locationNode => {
    const representations = getNodeRepresentations(locationNode.originalLocation);

    representations.forEach(nodeId => {
      const madsciNode = madsciNodes.find(n => n.nodeId === nodeId);
      if (madsciNode) {
        connections.push({
          from: locationNode.id,
          to: madsciNode.id,
          x1: locationNode.x,
          y1: locationNode.y,
          x2: madsciNode.x,
          y2: madsciNode.y,
          weight: 2,
          type: 'location_to_node'
        });
      }
    });
  });

  return connections;
});

function getNodeColor(node: any): string {
  if (node.type === 'madsci_node') {
    return '#2196F3'; // Blue for MADSci nodes
  }

  // Location nodes
  switch (node.occupied) {
    case 'Occupied':
      return '#4CAF50'; // Green
    case 'Empty':
      return '#FFC107'; // Amber
    default:
      return '#9E9E9E'; // Grey
  }
}


function getNodeRepresentations(location: any): string[] {
  const representations: string[] = [];

  if (location.representations && typeof location.representations === 'object') {
    representations.push(...Object.keys(location.representations));
  }

  // Remove duplicates and return
  return [...new Set(representations)];
}

function applyForceDirectedLayout(nodes: any[]): any[] {
  const iterations = 150;
  const margin = 80;
  const centerX = svgWidth.value / 2;
  const centerY = svgHeight.value / 2;

  // Create connections for force calculations
  const edges: any[] = [];
  const locationNodes = nodes.filter(n => n.type === 'location');
  const madsciNodes = nodes.filter(n => n.type === 'madsci_node');

  // Build edges based on representations
  locationNodes.forEach(locationNode => {
    const representations = getNodeRepresentations(locationNode.originalLocation);
    representations.forEach(nodeId => {
      const madsciNode = madsciNodes.find(n => n.nodeId === nodeId);
      if (madsciNode) {
        edges.push({ source: locationNode, target: madsciNode });
      }
    });
  });

  for (let iter = 0; iter < iterations; iter++) {
    const alpha = Math.max(0.01, 0.3 * (1 - iter / iterations)); // Cooling factor

    // Reset forces
    nodes.forEach(node => {
      node.fx = 0;
      node.fy = 0;
    });

    // 1. Repulsion forces (all nodes repel each other)
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const nodeA = nodes[i];
        const nodeB = nodes[j];

        const dx = nodeB.x - nodeA.x;
        const dy = nodeB.y - nodeA.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance > 0) {
          const repulsionStrength = nodeA.type === nodeB.type ? 2000 : 1000;
          const force = repulsionStrength / (distance * distance);
          const fx = (dx / distance) * force;
          const fy = (dy / distance) * force;

          nodeA.fx -= fx;
          nodeA.fy -= fy;
          nodeB.fx += fx;
          nodeB.fy += fy;
        }
      }
    }

    // 2. Attraction forces (connected nodes attract)
    edges.forEach(edge => {
      const dx = edge.target.x - edge.source.x;
      const dy = edge.target.y - edge.source.y;
      const distance = Math.sqrt(dx * dx + dy * dy);

      if (distance > 0) {
        const idealDistance = 120; // Desired edge length
        const attractionStrength = 0.1;
        const force = attractionStrength * (distance - idealDistance);
        const fx = (dx / distance) * force;
        const fy = (dy / distance) * force;

        edge.source.fx += fx;
        edge.source.fy += fy;
        edge.target.fx -= fx;
        edge.target.fy -= fy;
      }
    });

    // 3. Center gravity (weak pull toward center)
    nodes.forEach(node => {
      const dx = centerX - node.x;
      const dy = centerY - node.y;
      node.fx += dx * 0.01;
      node.fy += dy * 0.01;
    });

    // 4. Apply forces and update positions
    nodes.forEach(node => {
      node.vx = (node.vx + node.fx * alpha) * 0.8; // Damping
      node.vy = (node.vy + node.fy * alpha) * 0.8;

      node.x += node.vx;
      node.y += node.vy;

      // Keep nodes within bounds
      node.x = Math.max(margin, Math.min(svgWidth.value - margin, node.x));
      node.y = Math.max(margin, Math.min(svgHeight.value - margin, node.y));
    });
  }

  return nodes;
}

function getConnectedLocations(madsciNode: any) {
  if (madsciNode.type !== 'madsci_node') return [];

  const locationNodes = nodes.value.filter(n => n.type === 'location');
  const connectedLocations: any[] = [];

  locationNodes.forEach(locationNode => {
    const representations = getNodeRepresentations(locationNode.originalLocation);
    if (representations.includes(madsciNode.nodeId)) {
      connectedLocations.push(locationNode);
    }
  });

  return connectedLocations;
}

function handleNodeClick(node: any) {
  selectedNode.value = node;

  // Only emit node-click for location nodes, not MADSci nodes
  if (node.type === 'location') {
    emit('node-click', node);
  }
  // For MADSci nodes, we just update the selection for the info panel
}

// Handle window resize and layout recalculation
onMounted(() => {
  const container = svgElement.value?.parentElement;
  if (container) {
    const resizeObserver = new ResizeObserver(() => {
      const newWidth = Math.max(600, container.clientWidth - 32);
      const newHeight = Math.max(400, newWidth * 0.6);

      // Only trigger layout recalculation if size changed significantly
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
  stroke-width: 3;
  filter: brightness(1.1);
}

.node-label-hover {
  pointer-events: none;
  user-select: none;
  font-family: 'Roboto', sans-serif;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8);
}

.hover-tooltip {
  transition: opacity 0.2s ease-in-out;
  filter: drop-shadow(2px 2px 4px rgba(0, 0, 0, 0.3));
}

.resource-indicator {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
  100% {
    opacity: 1;
  }
}

.legend-color {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid #333;
}

.legend-color.occupied {
  background-color: #4CAF50;
}

.legend-color.empty {
  background-color: #FFC107;
}

.legend-color.unknown {
  background-color: #9E9E9E;
}

.legend-color.madsci-node {
  background-color: #2196F3;
}

.transfer-line {
  width: 30px;
  height: 3px;
  background-color: #2196F3;
  opacity: 0.6;
}

.legend-item {
  font-size: 14px;
}
</style>
