# Nash Bargaining PPA — pipeline
# Usage:
#   make check        verify environment and input data
#   make scenarios    generate and reduce Monte Carlo scenarios
#   make negotiate    run the Nash bargaining optimisation
#   make figures      produce all plots
#   make all          run the full pipeline end-to-end
#   make clean        remove generated outputs (keeps raw data)

PYTHON = python

# ── Sentinel files ──────────────────────────────────────────────────────────
# Make tracks whether a step is done by checking whether its output file
# (the sentinel) exists. If it does, the step is skipped.
SCENARIOS_DONE  = simulations/.scenarios_done
NEGOTIATE_DONE  = results/.negotiate_done
FIGURES_DONE    = figures/.figures_done

# ── Top-level targets ────────────────────────────────────────────────────────
.PHONY: all check scenarios negotiate figures clean

all: figures

check:
	$(PYTHON) scripts/test_pipeline.py

scenarios: check $(SCENARIOS_DONE)

negotiate: $(SCENARIOS_DONE) $(NEGOTIATE_DONE)

figures: $(NEGOTIATE_DONE) $(FIGURES_DONE)

# ── Step definitions ─────────────────────────────────────────────────────────
$(SCENARIOS_DONE):
	$(PYTHON) ppa_symmetric_info/generate_scenarios.py
	$(PYTHON) ppa_symmetric_info/scenario_reduction.py
	mkdir -p simulations
	touch $(SCENARIOS_DONE)

$(NEGOTIATE_DONE): $(SCENARIOS_DONE)
	$(PYTHON) ppa_symmetric_info/main_forecast.py
	mkdir -p results
	touch $(NEGOTIATE_DONE)

$(FIGURES_DONE): $(NEGOTIATE_DONE)
	$(PYTHON) ppa_symmetric_info/Plot_visualizations.py
	mkdir -p figures
	touch $(FIGURES_DONE)

# ── Clean ────────────────────────────────────────────────────────────────────
clean:
	rm -f $(SCENARIOS_DONE) $(NEGOTIATE_DONE) $(FIGURES_DONE)
	@echo "Sentinel files removed. Run 'make all' to rerun the pipeline."
