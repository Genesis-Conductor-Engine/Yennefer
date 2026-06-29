# Unified Inference Server - Architecture Diagrams (Mermaid)

## 1. System Architecture

```mermaid
graph TB
    subgraph Clients["Client Layer"]
        WS[WebSocket Clients]
        HTTP[HTTP/REST Clients]
        TRTC[TRTC Streaming]
    end

    subgraph Gateway["API Gateway (Node.js - Port 3000)"]
        Router[Request Router]
        Auth[Authentication]
        LB[Load Balancer]
        WS_Handler[WebSocket Handler]
    end

    subgraph Orchestrator["Orchestration Layer (Python FastAPI - Port 8001)"]
        VRAM[VRAM Orchestrator<br/>H = (VRAM/Total)*10 + 0.3*(T/89.6)]
        Monitor[Resource Monitor<br/>pynvml]
        Queue[Priority Queue<br/>P1: CUDA-Q<br/>P2: YOLO<br/>P3: LLM]
        Offload[Offload Client<br/>Diamond Gateway → Notion]
    end

    subgraph Services["Model Services"]
        CUDAQ[CUDA-Q Service<br/>124 MB, P1]
        YOLO[YOLO11s Service<br/>1200 MB, P2]
        LLM[Qwen 1.5 Service<br/>2800 MB, P3]
    end

    subgraph GPU["GTX 1650 (4 GB VRAM)"]
        Stream0[CUDA Stream 0<br/>CUDA-Q]
        Stream1[CUDA Stream 1<br/>YOLO11s]
        Stream2[CUDA Stream 2<br/>Qwen]
    end

    subgraph External["External Services"]
        DG[Diamond Gateway<br/>Port 8000]
        Notion[Notion Bridge<br/>Cloudflare Worker]
    end

    WS --> Router
    HTTP --> Router
    TRTC --> WS_Handler
    
    Router --> Auth
    Auth --> LB
    LB --> VRAM
    WS_Handler --> VRAM

    VRAM --> Monitor
    VRAM --> Queue
    VRAM --> Offload

    Queue --> CUDAQ
    Queue --> YOLO
    Queue --> LLM

    CUDAQ --> Stream0
    YOLO --> Stream1
    LLM --> Stream2

    Offload --> DG
    DG --> Notion

    Monitor -.->|Poll VRAM/Temp| GPU

    classDef clientStyle fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef gatewayStyle fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef orchStyle fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef serviceStyle fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef gpuStyle fill:#ffebee,stroke:#b71c1c,stroke-width:3px
    classDef externalStyle fill:#f1f8e9,stroke:#33691e,stroke-width:2px

    class WS,HTTP,TRTC clientStyle
    class Router,Auth,LB,WS_Handler gatewayStyle
    class VRAM,Monitor,Queue,Offload orchStyle
    class CUDAQ,YOLO,LLM serviceStyle
    class Stream0,Stream1,Stream2,GPU gpuStyle
    class DG,Notion externalStyle
```

---

## 2. VRAM State Machine

```mermaid
stateDiagram-v2
    [*] --> Idle
    
    Idle: STATE 1: IDLE (H = 0.2-2.0)
    Idle: CUDA-Q ✓ (124 MB)
    Idle: YOLO ✓ (1200 MB)
    Idle: Qwen ✗ (0 MB)
    Idle: Available: 2676 MB

    VisionActive: STATE 2: VISION ACTIVE (H = 3.3-4.5)
    VisionActive: CUDA-Q ✓ Idle (124 MB)
    VisionActive: YOLO ▶ Running (1200 MB)
    VisionActive: Qwen ✗ (0 MB)

    PrepLLM: STATE 3: PREP FOR LLM (H = 3.3)
    PrepLLM: Unload YOLO, Load Qwen
    PrepLLM: CUDA-Q ✓ (124 MB)
    PrepLLM: YOLO ✗ Unloading
    PrepLLM: Qwen ⏳ Loading

    LLMActive: STATE 4: LLM ACTIVE (H = 7.3-7.8)
    LLMActive: CUDA-Q ✓ Idle (124 MB)
    LLMActive: YOLO ✗ (0 MB)
    LLMActive: Qwen ▶ Running (2800 MB)

    Sequential: STATE 5: SEQUENTIAL (H = 7.3-8.2)
    Sequential: CUDA-Q queued (P1)
    Sequential: YOLO ✗ (0 MB)
    Sequential: Qwen ▶ Running (2800 MB)

    Offload: STATE 6: OFFLOAD (H > 8.5)
    Offload: Context → Notion
    Offload: Unload Qwen
    Offload: HTTP 503 Error

    Idle --> VisionActive: POST /vision/detect
    VisionActive --> Idle: Request complete
    
    Idle --> PrepLLM: POST /llm/chat
    VisionActive --> PrepLLM: POST /llm/chat
    PrepLLM --> LLMActive: Qwen loaded
    
    LLMActive --> Sequential: POST /cuda-q/qaoa
    Sequential --> LLMActive: CUDA-Q complete
    
    LLMActive --> Offload: H > 8.5 (temp spike)
    Sequential --> Offload: H > 8.5
    VisionActive --> Offload: H > 8.5 (rare)
    
    Offload --> Idle: Context saved, models unloaded
    
    LLMActive --> Idle: Idle timeout (60s)
```

---

## 3. Request Flow (Sequence Diagram)

```mermaid
sequenceDiagram
    participant C as Client
    participant G as Gateway<br/>(Node.js)
    participant O as Orchestrator<br/>(Python)
    participant M as Resource<br/>Monitor
    participant S as Model<br/>Service
    participant GPU as GTX 1650
    participant D as Diamond<br/>Gateway
    participant N as Notion

    C->>G: POST /cuda-q/qaoa
    G->>O: Forward request
    
    O->>M: Get GPU metrics
    M->>GPU: Query VRAM/Temp
    GPU-->>M: VRAM=1324MB, T=45°C
    M-->>O: Return metrics
    
    O->>O: Calculate H = 3.48
    
    alt H < 8.5 (SAFE)
        O->>O: Enqueue P1 request
        O->>S: Execute QAOA
        S->>GPU: Load onto Stream 0
        GPU-->>S: Result
        S-->>O: Result
        O-->>G: Response
        G-->>C: 200 OK + Result
    else H >= 8.5 (SATURATED)
        O->>D: POST /v1/orchestrate
        D-->>O: OFFLOAD action
        O->>N: Save context
        N-->>O: Context saved
        O->>S: Unload low-priority models
        O-->>G: 503 Error
        G-->>C: 503 "VRAM saturated, retry in 30s"
    end
```

---

## 4. VRAM Allocation Timeline

```mermaid
gantt
    title VRAM Allocation Over Time
    dateFormat X
    axisFormat %s

    section CUDA-Q (P1)
    Always Loaded: cudaq, 0, 60

    section YOLO11s (P2)
    Loaded: yolo1, 0, 30
    Unloaded: yolo_off, 30, 40
    Loaded Again: yolo2, 40, 60

    section Qwen 1.5 (P3)
    Unloaded: qwen_off1, 0, 30
    Loading: qwen_load, 30, 33
    Running: qwen_run, 33, 40
    Idle TTL: qwen_idle, 40, 42
    Unloaded: qwen_off2, 42, 60

    section Hamiltonian
    H=3.3 (Safe): h1, 0, 30
    H=7.8 (Orange): h2, 30, 40
    H=3.3 (Safe): h3, 40, 60
```

---

## 5. Priority Queue Flow

```mermaid
flowchart TD
    Start[New Request] --> Auth{Authenticated?}
    Auth -->|No| Reject[401 Unauthorized]
    Auth -->|Yes| Validate{Valid Input?}
    Validate -->|No| BadReq[400 Bad Request]
    Validate -->|Yes| CheckVRAM[Check Current VRAM]
    
    CheckVRAM --> CalcH[Calculate H = VRAM*10 + 0.3*T/89.6]
    CalcH --> CheckThreshold{H > 8.5?}
    
    CheckThreshold -->|Yes| TriggerOffload[Trigger OFFLOAD]
    TriggerOffload --> SaveContext[Save Context to Notion]
    SaveContext --> UnloadModels[Unload P3, then P2 if needed]
    UnloadModels --> Return503[503 Service Unavailable]
    
    CheckThreshold -->|No| DeterminePriority{Which Service?}
    
    DeterminePriority -->|CUDA-Q| P1[Priority 1 Queue]
    DeterminePriority -->|YOLO| P2[Priority 2 Queue]
    DeterminePriority -->|LLM| P3[Priority 3 Queue]
    
    P1 --> CheckLoaded1{Model Loaded?}
    CheckLoaded1 -->|Yes| Execute1[Execute CUDA-Q]
    CheckLoaded1 -->|No| Load1[Load CUDA-Q]
    Load1 --> Execute1
    
    P2 --> CheckLoaded2{Model Loaded?}
    CheckLoaded2 -->|Yes| Execute2[Execute YOLO]
    CheckLoaded2 -->|No| CheckSpace2{VRAM Available?}
    CheckSpace2 -->|Yes| Load2[Load YOLO]
    CheckSpace2 -->|No| UnloadP3_2[Unload P3]
    UnloadP3_2 --> Load2
    Load2 --> Execute2
    
    P3 --> CheckLoaded3{Model Loaded?}
    CheckLoaded3 -->|Yes| Execute3[Execute Qwen]
    CheckLoaded3 -->|No| CheckSpace3{VRAM Available?}
    CheckSpace3 -->|Yes| Load3[Load Qwen]
    CheckSpace3 -->|No| UnloadP2_3[Unload P2]
    UnloadP2_3 --> Load3
    Load3 --> Execute3
    
    Execute1 --> Success[Return 200 + Results]
    Execute2 --> Success
    Execute3 --> Success
    
    Success --> UpdateMetrics[Update Last Used Timestamp]
    UpdateMetrics --> End[Complete]
    
    Return503 --> End
    Reject --> End
    BadReq --> End

    style Start fill:#e1f5ff
    style Success fill:#c8e6c9
    style Return503 fill:#ffcdd2
    style Reject fill:#ffcdd2
    style BadReq fill:#ffcdd2
    style TriggerOffload fill:#fff9c4
    style P1 fill:#e8f5e9
    style P2 fill:#fff3e0
    style P3 fill:#f3e5f5
```

---

## 6. Model Loading Decision Tree

```mermaid
flowchart TD
    Start[Request Received] --> CheckService{Which<br/>Service?}
    
    CheckService -->|CUDA-Q| CheckCUDAQ{CUDA-Q<br/>Loaded?}
    CheckCUDAQ -->|Yes| ExecCUDAQ[Execute]
    CheckCUDAQ -->|No| LoadCUDAQ[Load CUDA-Q<br/>124 MB]
    LoadCUDAQ --> ExecCUDAQ
    
    CheckService -->|YOLO| CheckYOLO{YOLO<br/>Loaded?}
    CheckYOLO -->|Yes| ExecYOLO[Execute]
    CheckYOLO -->|No| CheckVRAMYOLO{VRAM Available<br/>> 1200 MB?}
    CheckVRAMYOLO -->|Yes| LoadYOLO[Load YOLO]
    CheckVRAMYOLO -->|No| CheckQwen{Qwen<br/>Loaded?}
    CheckQwen -->|Yes| UnloadQwen[Unload Qwen<br/>Free 2800 MB]
    UnloadQwen --> LoadYOLO
    CheckQwen -->|No| Error503YOLO[503 Error]
    LoadYOLO --> ExecYOLO
    
    CheckService -->|LLM| CheckLLM{Qwen<br/>Loaded?}
    CheckLLM -->|Yes| ExecLLM[Execute]
    CheckLLM -->|No| CheckVRAMLLM{VRAM Available<br/>> 2800 MB?}
    CheckVRAMLLM -->|Yes| LoadLLM[Load Qwen]
    CheckVRAMLLM -->|No| CheckBoth{YOLO +<br/>CUDA-Q<br/>Loaded?}
    CheckBoth -->|YOLO Only| UnloadYOLO[Unload YOLO<br/>Free 1200 MB]
    CheckBoth -->|Both| UnloadBoth[Unload YOLO<br/>Free 1200 MB]
    CheckBoth -->|Neither| Error503LLM[503 Error]
    UnloadYOLO --> LoadLLM
    UnloadBoth --> LoadLLM
    LoadLLM --> ExecLLM
    
    ExecCUDAQ --> Success[Return Results]
    ExecYOLO --> Success
    ExecLLM --> Success
    Error503YOLO --> End[503 Response]
    Error503LLM --> End
    Success --> End

    style Start fill:#e1f5ff
    style Success fill:#c8e6c9
    style Error503YOLO fill:#ffcdd2
    style Error503LLM fill:#ffcdd2
    style LoadCUDAQ fill:#e8f5e9
    style LoadYOLO fill:#fff3e0
    style LoadLLM fill:#f3e5f5
```

---

## 7. OFFLOAD Flow

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant M as Monitor
    participant G as GPU
    participant D as Diamond<br/>Gateway
    participant N as Notion<br/>Bridge
    participant S as Model<br/>Services

    loop Every 2 seconds
        M->>G: Query VRAM + Temp
        G-->>M: Metrics
    end

    Note over O: New request arrives
    O->>M: Get current metrics
    M-->>O: VRAM=3800MB, T=82°C
    
    O->>O: Calculate H = 9.2
    
    alt H > 8.5 (OFFLOAD TRIGGER)
        O->>O: Generate session context
        
        O->>D: POST /v1/orchestrate<br/>{session_id, context, vram, H}
        
        D->>D: Validate H > 8.5
        D-->>O: {action: "OFFLOAD", ...}
        
        O->>N: POST /<br/>{action: "OFFLOAD", context_buffer, ...}
        
        N->>N: Create Notion page
        N->>N: Write to soul-capsule DB
        N-->>O: {status: "saved", page_id}
        
        O->>S: Unload P3 (Qwen)
        S->>G: Free 2800 MB
        G-->>S: Released
        
        alt Still H > 8.5
            O->>S: Unload P2 (YOLO)
            S->>G: Free 1200 MB
            G-->>S: Released
        end
        
        O->>M: Verify VRAM reduced
        M-->>O: VRAM=124MB, T=75°C
        
        O->>O: Calculate new H = 1.2
        
        Note over O: System stabilized
        O-->>Client: 503 Service Unavailable<br/>"Context saved, retry in 60s"
    end
```

---

## 8. Deployment Architecture

```mermaid
C4Context
    title Unified Inference Server - Deployment Architecture

    Person(client, "Client", "WebSocket/HTTP client")
    
    System_Boundary(server, "Diamond Node Server") {
        Container(gateway, "API Gateway", "Node.js, TRTC SDK", "Port 3000<br/>WebSocket + HTTP routing")
        Container(orch, "Orchestrator", "Python FastAPI", "Port 8001<br/>VRAM management")
        
        ContainerDb(cudaq_svc, "CUDA-Q Service", "Python, CUDA-Q", "Port 8002<br/>124 MB VRAM")
        ContainerDb(yolo_svc, "YOLO Service", "Python, YOLOv11s", "Port 8003<br/>1200 MB VRAM")
        ContainerDb(llm_svc, "LLM Service", "Python, Xinference", "Port 8004<br/>2800 MB VRAM")
        
        ContainerDb(gpu, "GTX 1650", "NVIDIA GPU", "4 GB VRAM<br/>CUDA 12.x")
    }
    
    System_Ext(dg, "Diamond Gateway", "FastAPI on 8000<br/>Metrics + Orchestrate")
    System_Ext(notion, "Notion Bridge", "Cloudflare Worker<br/>Context Storage")
    
    Rel(client, gateway, "Uses", "WS/HTTPS")
    Rel(gateway, orch, "Routes to", "HTTP")
    Rel(orch, cudaq_svc, "Manages", "HTTP")
    Rel(orch, yolo_svc, "Manages", "HTTP")
    Rel(orch, llm_svc, "Manages", "HTTP")
    Rel(cudaq_svc, gpu, "Uses", "CUDA")
    Rel(yolo_svc, gpu, "Uses", "CUDA")
    Rel(llm_svc, gpu, "Uses", "CUDA")
    Rel(orch, dg, "Queries", "HTTP")
    Rel(orch, notion, "Offloads to", "HTTPS")
    
    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

---

## 9. Monitoring Dashboard Components

```mermaid
flowchart LR
    subgraph Metrics["Metrics Collection"]
        VRAM[VRAM Usage<br/>pynvml]
        Temp[GPU Temp<br/>pynvml]
        Ham[Hamiltonian<br/>Calculated]
        Queue[Queue Depth<br/>Internal]
        Latency[Request Latency<br/>Timing]
    end
    
    subgraph Aggregation["Aggregation Layer"]
        Prometheus[Prometheus<br/>Time Series DB]
        Logs[Logs<br/>Structured JSON]
    end
    
    subgraph Visualization["Visualization"]
        Grafana[Grafana Dashboard]
        Alerts[Alert Manager]
    end
    
    subgraph Alerts_Rules["Alert Rules"]
        Crit[CRITICAL<br/>H > 8.5 for 30s<br/>Temp > 85°C]
        Warn[WARNING<br/>H > 7.5 for 2min<br/>Temp > 75°C]
        Info[INFO<br/>Model loaded/unloaded<br/>OFFLOAD triggered]
    end
    
    VRAM --> Prometheus
    Temp --> Prometheus
    Ham --> Prometheus
    Queue --> Prometheus
    Latency --> Prometheus
    
    VRAM --> Logs
    Queue --> Logs
    
    Prometheus --> Grafana
    Logs --> Grafana
    Prometheus --> Alerts
    
    Alerts --> Crit
    Alerts --> Warn
    Alerts --> Info
    
    Grafana --> Dashboards[Web UI<br/>Real-time Graphs]
    Alerts --> Notifications[Email/Slack<br/>PagerDuty]

    style VRAM fill:#e8f5e9
    style Temp fill:#fff3e0
    style Ham fill:#f3e5f5
    style Crit fill:#ffcdd2
    style Warn fill:#fff9c4
    style Info fill:#e1f5ff
```

---

## How to Use These Diagrams

### Viewing Online
1. Copy any diagram block (between \`\`\`mermaid and \`\`\`)
2. Paste into [Mermaid Live Editor](https://mermaid.live/)
3. View rendered diagram

### Embedding in Documentation
- GitHub Markdown: Renders automatically
- Notion: Use Mermaid block
- Confluence: Install Mermaid plugin

### Exporting
```bash
# Install mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# Export as PNG
mmdc -i diagram.mmd -o diagram.png

# Export as SVG
mmdc -i diagram.mmd -o diagram.svg
```

---

**File:** `UNIFIED_INFERENCE_DIAGRAMS.md`  
**Version:** 1.0  
**Last Updated:** 2025-05-12  
**Format:** Mermaid.js
