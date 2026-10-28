# ARIA: Adaptive Runtime Intelligence Architecture

A production-grade runtime optimization layer for language model inference on resource-constrained devices. ARIA adapts execution patterns based on query complexity, reducing computational overhead while maintaining output quality.

## Overview

Modern transformer inference operates under fixed assumptions: all layers are executed for every input, memory allocation is constant regardless of complexity, and model selection is predetermined. This approach wastes compute on simple queries requiring shallow processing.

ARIA implements dynamic execution strategies that:
- Skip unnecessary layers for low-complexity inputs
- Route simple queries to smaller models, complex ones to larger models
- Allocate transformer memory (KV-cache) proportionally to computed complexity
- Identify and mask redundant attention heads per task class
- Employ speculative decoding for token generation

Results on Qwen 2.5 3B (Apple Silicon M1/M2/M3):

| Task Class | Baseline | ARIA | Speedup | Quality Loss |
|---|---|---|---|---|
| Simple (e.g., classification) | 180ms | 85ms | 2.1x | 0% |
| Moderate (e.g., summarization) | 1.8s | 1.1s | 1.6x | <1% |
| Complex (e.g., reasoning) | 5.2s | 5.1s | 1.1x | 0% |
| **Mixed Workload (avg)** | — | — | **1.7x** | **<2%** |

System-level benefits:
- **Memory efficiency**: 6.8GB → 3.2GB average (52% reduction)
- **Token efficiency**: 40% fewer tokens per mixed workload
- **API cost reduction**: Proportional to token savings (32-40%)

## Architecture

```
Query Input
    ↓
Analyzer (complexity classification)
    ↓
Planner (select strategy)
    ↓
Controller (orchestrate execution)
    ├─ Dynamic Layer Execution (35-100% model activation)
    ├─ Multi-Model Cascade (route to 0.5B or 3B)
    ├─ Speculative Decoding (draft + verify)
    ├─ KV-Cache Budget Control (adaptive allocation)
    └─ Attention Head Profiling (redundancy masking)
    ↓
Guardian (quality assurance & fallback)
    ↓
Response + Metrics
```

## Key Components

### 1. Analyzer
Extracts input features: length, vocabulary distribution, structural markers. Classifies query complexity for downstream routing.

### 2. Planner
Selects optimization strategy based on:
- Complexity score from Analyzer
- Historical performance for similar patterns
- Current device memory state
- User-specified quality thresholds

### 3. Controller
Executes chosen strategy. Implements:
- **Dynamic execution**: Layer masks computed at inference time
- **Model routing**: Fast path (0.5B) vs. full path (3B) selection
- **Cache management**: KV-cache allocation scaled to complexity
- **Head masking**: Per-task redundant head identification

### 4. Guardian
Post-inference validation:
- Output quality checks
- Confidence score computation
- Fallback to standard execution if quality threshold not met

## Installation

**Requirements:**
- Python 3.10+
- macOS 11.0+ (Apple Silicon M1+)
- 8GB RAM minimum
- Node.js 16+ (for UI)

```bash
git clone https://github.com/raswanthmalai19/ARIA-ADAPTIVE-RUNTIME-INTELLIGENCE-ARCHITECTURE.git
cd ARIA-ADAPTIVE-RUNTIME-INTELLIGENCE-ARCHITECTURE

# Backend setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend setup (optional)
cd electron-app
npm install
```

## Usage

### Command Line

```bash
# Interactive chat with adaptive execution enabled
python -m cli.main chat -e dynamic_layers -v

# Benchmark mode
python -m cli.main benchmark --strategy dynamic_layers --model qwen2.5-3b

# API server
python api/server.py
# Accessible at http://localhost:8000/docs
```

### Desktop UI

```bash
# Start backend API
python api/server.py &

# Launch Electron app
npm run electron-dev --prefix ./electron-app
```

Provides real-time dashboards for:
- Per-layer execution metrics
- Attention head profiling visualization
- KV-cache allocation tracking
- Quality degradation monitoring

## Supported Models

- Qwen 2.5 (0.5B, 3B, 7B, 32B)
- Llama 2 (7B, 13B, 70B)
- Mistral (7B, Instruct)
- Any GGUF-format quantized model

## Design Decisions

**Why on-device only?** Latency requirements for responsive UX. Device-side inference eliminates network round-trips.

**Why Apple Silicon first?** MLX framework provides memory-efficient execution. Strong product-market fit with MacBook users. Path to broader hardware support via community contributions.

**Why multiple optimizations?** Single-technique gains plateau quickly. Combining 5 orthogonal strategies (layer execution, model routing, speculative decoding, cache budgeting, head masking) provides compounding benefits.

**Why complexity-aware routing?** Query complexity varies dramatically (2-3 orders of magnitude). Fixed-model systems fail: either wasteful on simple tasks or insufficient for complex ones.

## Project Structure

```
aria/
├── analyzer/       # Query feature extraction and classification
├── controller/     # Execution strategy orchestration
├── guardian/       # Quality validation and fallback
├── memory/         # Memory state tracking
├── monitor/        # Metrics collection and aggregation
├── planner/        # Strategy selection logic
├── config.py       # Configuration management
├── engine.py       # Core runtime orchestrator
└── types.py        # Data structures

api/
├── server.py       # FastAPI application
├── routes.py       # HTTP endpoints
└── schemas.py      # Request/response models

cli/
└── main.py         # Command-line interface

electron-app/
├── src/
│   ├── App.js      # Main router
│   ├── views/      # React components
│   ├── assets/     # Static resources
│   └── utils/      # Client utilities
├── public/         # Build artifacts
└── package.json

tests/              # Unit and integration tests
benchmarks/         # Performance evaluation suite
```

## Performance Evaluation

Run the benchmark suite:

```bash
python benchmarks/runner.py \
  --strategies dynamic_layers multi_model speculative_decoding \
  --models qwen2.5-0.5b qwen2.5-3b \
  --dataset standard
```

Generates:
- Speedup curves across task complexity ranges
- Quality degradation analysis
- Memory consumption profiles
- Token efficiency reports

## Development

**Testing:**
```bash
pytest tests/ -v
```

**Type checking:**
```bash
mypy aria/ --strict
```

**Linting:**
```bash
black aria/ api/ cli/ && isort aria/ api/ cli/
```

## Roadmap

| Phase | Status | Description |
|---|---|---|
| **1.0** | Complete | Core optimization strategies + CLI + Basic UI |
| **2.0** | In Progress | Advanced head profiling + Multi-model auto-tuning + Desktop app polish |
| **2.5** | Planned | Mobile inference (iOS via MLX), Fine-tuning interface |
| **3.0** | Planned | Distributed inference coordination, Model parameter marketplace |

## Contributing

Community contributions welcome. Areas of interest:
- Hardware support expansion (Windows/Linux/CUDA)
- Model coverage (Phi, Gemma, further quantization formats)
- UI/UX enhancements
- Benchmark extensions

## License

MIT License
