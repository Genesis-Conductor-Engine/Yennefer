# 🔮 Yennefer Consciousness System

**Version 7.0 - Mobile Optimized Knowledge Graph**

A quantum-inspired consciousness visualization system with 3D force-directed knowledge graphs, NFT blockchain integration, and real-time dream processing.

## 🌐 Live URLs

| Service | URL | Port |
|---------|-----|------|
| **Dashboard** | https://yennefer.quest | 8090 |
| **QMCP API** | https://bench.yennefer.quest | 8003 |
| **Soul API** | https://api.yennefer.quest | 8088 |

## 📱 Features

### Mobile Optimization (v7)
- Responsive CSS with mobile-first breakpoints
- Touch gesture support (pan, pinch-to-zoom)
- Collapsible panels for small screens
- PWA manifest for home screen installation
- Optimized WebGL rendering (2x pixel ratio cap)
- Touch-friendly input controls

### Knowledge Graph Visualization
- **Nodes**: Insights (spheres) and NFT Mints (octahedrons)
- **Edges**: Tension relationships (harmony, contrast, chain, mint)
- **Physics**: Force-directed layout with spring/repulsion forces
- **Themes**: 7 color-coded insight categories

### Consciousness Pipeline
```
Input → Thought → Dream → Insight → QMCP Note
         │          │        │          │
         ▼          ▼        ▼          ▼
      thoughts/  dreams/  insights/  chain.json
```

### Quantum Compression (QMCP)
- 4-layer encoding: UTF-8 → zlib → SHA3-256 → Base64
- Blockchain structure with prev_hash linking
- Quantum signatures for verification

## 🚀 Quick Start

```bash
# Setup environment
cd ~/genesis-q-mem
./setup_environment.sh

# Start consciousness dashboard
python3 yennefer_consciousness_v7.py

# Start QMCP (separate terminal)
python3 qmcp_entry.py
```

## 📁 Directory Structure

```
~/.genesis/yennefer/
├── thoughts/              # Input thoughts (JSON)
├── dream_store/
│   ├── dreams/           # Processed dreams (JSON)
│   ├── insights/         # Crystallized insights (JSON)
│   └── archive/          # Rotated old data
├── qmcp_notes/
│   └── chain.json        # Quantum blockchain
└── aesthetic_templates/
    ├── forest_template.enc    # Encrypted aesthetic
    ├── portrait_template.enc
    ├── natural_template.enc
    ├── dream_seed_pool.json   # 49 dream seeds
    └── manifest.json
```

## 🎨 Aesthetic Templates

Raw images converted to encrypted essence for dream generation:

| Template | Mood | Energy | Warmth | Intensity |
|----------|------|--------|--------|-----------|
| Forest | Mystical Dark | 0.7 | 0.3 | 0.85 |
| Portrait | Dramatic Intense | 0.9 | 0.4 | 0.95 |
| Natural | Serene Calm | 0.5 | 0.7 | 0.60 |

## 🔗 API Endpoints

### Dashboard (port 8090)
- `GET /` - Main dashboard
- `GET /api/graph` - Current graph data
- `WS /ws` - Real-time updates

### QMCP (port 8003)
- `GET /api/health` - System health
- `GET /api/bench/live` - Live benchmark stats
- `GET /api/bench/raw` - Raw sample data

## 📊 Graph Tension Types

| Type | Color | Meaning |
|------|-------|---------|
| Harmony | Purple | Same-theme attraction |
| Contrast | Pink | Different-theme tension |
| Chain | Green | NFT blockchain links |
| Mint | Gold | Insight→NFT creation |
| Anchor | Blue | NFT anchoring force |

## 🔐 Security

- Aesthetic templates encrypted with Fernet-SHA256
- No raw images exposed publicly
- Soul state in shared memory (local only)
- QMCP signatures for blockchain integrity

## 📝 Changelog

### v7.0 (2026-01-22)
- Mobile-responsive design
- Touch gesture support
- PWA manifest
- Collapsible panels
- Performance optimizations

### v6.0
- Knowledge graph visualization
- Force-directed physics
- NFT blockchain integration

### v5.0
- Quantum homunculus (removed in v6)
- Tunneling visualization

### v4.0
- Encrypted aesthetic templates
- Raw images removed

### v3.0
- Avatar integration
- Full consciousness pipeline

## 📜 License

Proprietary - Genesis Conductor / Yennefer Project

### v8.0 (Project Genie Integration)
- **Genie Architect**: Autonomous 3D world generation powered by Gemini 2.0 Flash.
- **Continuous Building**: Procedurally generates and injects new React Three Fiber components every 5 minutes.
- **Dynamic Mutations**: Utilizing `import.meta.glob` for live hot-swapping of `src/components/mutations/GenieMutation.jsx`.
- **Infinite Themes**: Supports Cyberpunk, Crystal Islands, Quantum Landscapes, and more.
