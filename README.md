<div align="center">

# 🧠 MACO: A Multi-Agent LLM Framework for Automated CGRA Hardware/Software Co-Design

[![arXiv](https://img.shields.io/badge/arXiv-2509.13557-b31b1b.svg)](https://arxiv.org/abs/2509.13557)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-research-orange.svg)](#)

*An open-source multi-agent LLM framework that automates CGRA hardware/software co-design.*

</div>

---

## ✨ Overview

**MACO** is an LLM-based multi-agent framework for automated **CGRA** (Coarse-Grained Reconfigurable Array) architecture design and optimization. Four specialized agents collaboratively explore the joint HW/SW design space — generating, validating, judging, and refining designs — to balance **performance**, **power**, and **area** under a target objective.

```
   ┌──────────────┐    ┌────────────┐    ┌────────────────────┐    ┌──────────────────┐
   │ CGRA         │ →  │ CGRA       │ →  │ Coarse-grained     │ →  │ Fine-grained     │
   │ Co-designer  │    │ Fixer      │    │ Judge              │    │ Judge + EDA      │
   │ (Stage 1)    │    │ (Stage 2)  │    │ (Stage 3a)         │    │ (Stage 3b)       │
   └──────────────┘    └────────────┘    └────────────────────┘    └──────────────────┘
          ↑                                                                  │
          └────────────────── PPA feedback (Stage 4) ────────────────────────┘
```

---

## 🚀 Quick Start

```bash
# 1. Clone & install
git clone https://github.com/coredac/MACO.git
cd MACO
pip install -r requirements.txt

# 2. Set the LLM API key (DashScope-compatible endpoint)
export DASHSCOPE_API_KEY="sk-your-api-key-here"

# 3. Run the top-level pipeline
python3 run_maco.py
```

---

## 📁 Project Structure

```
MACO/
├── 🚀 run_maco.py                     # Top-level MACO entrypoint
├── 🚀 run_maco_experiment.py          # Per-kernel MACO experiment driver
├── 🚀 run_single_agent_baseline.py    # Single-agent LLM baseline
│
├── 🤖 agent/                          # The four MACO agents (paper Fig. 4)
│   ├── cgra_codesigner.py             #   Stage 1 — CGRA Co-designer
│   ├── cgra_fixer.py                  #   Stage 2 — CGRA Fixer
│   ├── coarse_grained_judge.py        #   Stage 3a — Coarse-grained Judge
│   └── fine_grained_judge.py          #   Stage 3b — Fine-grained Judge
│
├── ⚙️  algorithm/                      # MACO core mechanisms
│   ├── exploration_exploitation.py    #   ε-greedy ECE mechanism (Sec. III-B)
│   └── confidence_adaptive_selector.py #  Confidence-Adaptive Selection (Sec. III-D)
│
├── 📊 baseline/                       # Comparison baselines
│   ├── qwen_domain_agumented.py
│   └── qwen_few_shot_examples.py
│
├── 🔧 verilog_tool/                   # Hardware synthesis tools
│   ├── generate_verilog.py
│   ├── append_ppa.py
│   └── arch2dc.bash
│
├── 🛠️  eda_tool/                       # EDA tool integration
│   └── arch_sample_sv2v_run.tcl
│
├── 🧪 tool/                           # Evaluation utilities
│   └── test_process_candidates.py
│
└── 📂 results/                        # Output storage
    ├── cgra_best_design.json
    ├── cgra_candidates_raw.json
    ├── cgra_candidates_fixed.json
    ├── cgra_historical_design.json
    └── cgra_top_k.json
```

---

## 🔄 Workflow

The MACO four-stage iterative loop (paper Sec. III):

| Stage | Agent / Mechanism | Role |
|:-----:|-------------------|------|
| **1** | `CGRACoDesigner` + ε-greedy ECE | Proposes HW/SW candidates, scheduled between exploration and exploitation |
| **2** | `CGRAFixer` | Validates each candidate and applies rule-driven syntax / mapping repairs |
| **3a** | `CoarseGrainedJudge` | LLM-only top-K screen of the fixed pool |
| **3b** | `FineGrainedJudge` + `ConfidenceAdaptiveSelector` | Cooperates with EDA tools under an adaptive-confidence scheme and self-learns from tool feedback |
| **4** | PPA Evaluation | Synthesis reports are folded back into history for the next iteration |
| **+** | RTL / Synthesis | Best designs are emitted as synthesizable Verilog |

---

## 🧩 Components

### 🤖 Agent Modules

| Module | Class | Role |
|--------|-------|------|
| `cgra_codesigner.py`        | `CGRACoDesigner`     | Joint HW/SW candidate generator *(Stage 1)* |
| `cgra_fixer.py`             | `CGRAFixer`          | Rule-driven repair of syntax / mapping errors *(Stage 2)* |
| `coarse_grained_judge.py`   | `CoarseGrainedJudge` | LLM-only top-K shortlist *(Stage 3a)* |
| `fine_grained_judge.py`     | `FineGrainedJudge`   | Final single-best selection with self-learning *(Stage 3b)* |

### ⚙️ Mechanism Modules (`algorithm/`)

| Module | Mechanism |
|--------|-----------|
| `exploration_exploitation.py`     | Exponentially decaying ε-greedy ECE (Sec. III-B) — schedules the multi-iteration loop |
| `confidence_adaptive_selector.py` | Confidence-Adaptive Selection + self-learning between the Fine-grained Judge and the EDA tool (Sec. III-D) |

### 🚀 Entry Points (repo root)

| Script | Purpose |
|--------|---------|
| `run_maco.py`                  | Single-iteration top-level MACO entrypoint |
| `run_maco_experiment.py`       | Per-kernel MACO experiment driver |
| `run_single_agent_baseline.py` | Single-agent LLM baseline used for comparison |

### 🔧 Verilog Tools

| Tool | Purpose |
|------|---------|
| `generate_verilog.py` | Generates SystemVerilog / Verilog RTL from CGRA design specifications |
| `append_ppa.py`       | Estimates and appends Performance / Power / Area (PPA) metrics |
| `arch2dc.bash`        | Synthesis automation script |

---

## 🎯 Optimization Targets

| Goal | What MACO optimizes for |
|:----:|-------------------------|
| 🏎️ **Performance** | Maximize throughput and parallelism |
| 🔋 **Power**       | Minimize power consumption |
| 📐 **Area**        | Reduce hardware resource usage |
| ⚡ **Energy**      | Optimize overall energy efficiency |

---

## 🤖 Supported LLM Models

- **Qwen** models (e.g., `qwen-plus`)
- **OpenAI** models (GPT-4, GPT-4o)
- **DeepSeek** models
- Any **custom** OpenAI-compatible endpoint

---

## 📐 CGRA Design Format

Designs are represented as JSON specifications:

```json
{
  "tile_size": "4x4",
  "FUs": {
    "tile0": ["Ld", "Add"],
    "tile1": ["Mul", "Add"]
  },
  "config_mem": 128,
  "data_spm_kb": 64,
  "unroll_factor": 2,
  "vectorize": "interleaved",
  "kernel": "path/to/kernel.c"
}
```

---

## ⚙️ Detailed Setup

### Prerequisites

- 🐍 Python **3.8** or higher
- 🏭 **Synopsys Design Compiler** (for synthesis)
- 🔗 [**VectorCGRA**](https://github.com/tancheng/VectorCGRA) framework

### Environment Setup

**1.** Install Python dependencies:

```bash
pip install -r requirements.txt
```

**2.** Install the VectorCGRA framework following the instructions at <https://github.com/tancheng/VectorCGRA>.

**3.** Configure your API key:

The four agent modules read the LLM API key from the `DASHSCOPE_API_KEY` environment variable — never hardcode it in source. Export it in your shell:

```bash
export DASHSCOPE_API_KEY="sk-your-api-key-here"
```

…or load it from a local `.env` file (already git-ignored).

### Running the Pipeline

Configure the kernel type, optimization goal, and model selection in `run_maco.py`:

```python
kernel = "conv"                    # or "fir", "spmv", ...
optimization_goal = "performance"  # "performance" | "power" | "area" | "energy"
model = "qwen-plus"
```

Then run:

```bash
python3 run_maco.py
```

---

## 📂 Output Files

Results are stored in the `results/` directory:

| File | Contents |
|------|----------|
| `cgra_best_design.json`       | Optimal design(s) identified |
| `cgra_candidates_raw.json`    | Initial generated candidates |
| `cgra_candidates_fixed.json`  | Candidates after mapping fixes |
| `cgra_historical_design.json` | Historical designs for feedback loops |
| `cgra_top_k.json`             | Top-K candidate designs |

---

## ⚠️ Note

MACO uses **Synopsys Design Compiler** for synthesis — a valid license is required before running the synthesis-backed evaluation stages.

---

## 📖 Citation

If you use MACO in your research, please cite:

```bibtex
@article{jiang2025maco,
  title  = {MACO: A Multi-Agent LLM Framework for Automated CGRA Hardware/Software Co-Design},
  author = {Jiang, Zesong and Sun, Yuqi and Zhong, Qing and Krishna, Mahathi
            and Patil, Deepak and Tan, Cheng and Zhang, Jeff},
  journal = {arXiv preprint arXiv:2509.13557},
  year   = {2025}
}
```

---

## 📬 Contact

Questions? Open an issue or reach out: **zjian137@asu.edu** 🙂

## 🙏 Acknowledgments

This project integrates with the [VectorCGRA](https://github.com/tancheng/VectorCGRA) framework for hardware synthesis.
