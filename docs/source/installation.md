# Installation

## Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended) or conda
- Gurobi optimizer with a valid license

!!! note "Gurobi license"
    Academic licenses are free at [gurobi.com/academia](https://www.gurobi.com/academia/academic-program-and-licenses/).

## With uv (recommended)

```bash
git clone https://github.com/<your-username>/Nash-Bargaining-ADH-Paper.git
cd Nash-Bargaining-ADH-Paper
uv sync
```

## With conda

```bash
conda env create -f envs/environment.yaml
conda activate nash-bargaining
pip install -e .
```
