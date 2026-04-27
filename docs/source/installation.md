# Installation

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Gurobi optimizer with a valid license

!!! note "Gurobi license"
    Academic licenses are free at [gurobi.com/academia](https://www.gurobi.com/academia/academic-program-and-licenses/).

## Steps

```bash
git clone https://github.com/<your-username>/Nash-Bargaining-ADH-Paper.git
cd Nash-Bargaining-ADH-Paper
uv sync
```

Or with pip:

```bash
pip install -e .
```

## Environment file

Copy the example and fill in your local path for Overleaf/Dropbox figure export:

```bash
cp ppa_symmetric_info/.env.example ppa_symmetric_info/.env
```

Set `DROPBOX_FIGURES_DIR` inside `.env`. This is optional; if unset, figures are only saved to `outputs/`.