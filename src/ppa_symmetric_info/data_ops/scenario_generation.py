from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

import logging

log = logging.getLogger(__name__)


def _yearly_index(start, periods):
    return pd.date_range(start=pd.Timestamp(start), periods=periods, freq="YS")


def _monthly_index(start, periods):
    return pd.date_range(start=pd.Timestamp(start), periods=periods, freq="MS")


def _save_matrix(folder: Path, kind: str, mat: np.ndarray, start, resample: bool, monte_price: bool = False):
    """Save a (timesteps x sims) matrix as a CSV with the standard naming convention."""
    n_months = 12
    years, sims = mat.shape

    if resample:
        df = pd.DataFrame(mat, index=_monthly_index(start, years), columns=pd.RangeIndex(sims, name="sim"))
        df = df.resample("YE").mean() if kind == "price" else df.resample("YE").sum()
        y = years // n_months
        suffix = "monte" if monte_price else None
        fname = f"{kind}_scenarios_{suffix}_{y}y_{sims}s.csv" if suffix else f"{kind}_scenarios_{y}y_{sims}s.csv"
    else:
        df = pd.DataFrame(mat, index=_yearly_index(start, years), columns=pd.RangeIndex(sims, name="sim"))
        df = df.resample("YE").sum()
        suffix = "monte" if monte_price else None
        fname = f"{kind}_scenarios_{suffix}_{years}y_{sims}s.csv" if suffix else f"{kind}_scenarios_{years}y_{sims}s.csv"

    df.to_csv(folder / fname, index_label="year")


@dataclass
class PriceModel:
    rng: np.random.Generator
    s: Optional[float] = None
    loc: Optional[float] = None
    scale: Optional[float] = None
    start_value: Optional[float] = None
    kappa: Optional[float] = None
    theta: Optional[float] = None
    theta_1: Optional[float] = None
    sigma: Optional[float] = None
    df: Optional[pd.DataFrame] = None

    @classmethod
    def from_csv(cls, sampling_type: str, csv_path: str, seed: Optional[int] = None) -> "PriceModel":
        df = pd.read_csv(csv_path, sep=";", decimal=",")
        df.index = pd.to_datetime(df["HourUTC"])
        mean_price = df["DK2_EUR/MWh"].mean()
        std_price = df["DK2_EUR/MWh"].std()
        df_clean = df[(df["DK2_EUR/MWh"] > mean_price - 3 * std_price) & (df["DK2_EUR/MWh"] < mean_price + 3 * std_price)]

        if sampling_type == "OU_Process":
            monthly = df_clean["DK2_EUR/MWh"].resample("ME").mean().to_numpy(float) * 1e-3
            start_value = monthly[-1]
            X = monthly
            X_t, X_tp1 = X[:-1], X[1:]
            t_normalized = np.arange(len(X_t)) / len(X_t)
            dt = 1 / 12
            dX_dt = (X_tp1 - X_t) / dt
            regression_matrix = np.column_stack([np.ones(len(X_t)), t_normalized, X_t])
            results = sm.OLS(dX_dt, regression_matrix).fit()
            a, b, c = results.params
            kappa = -c
            theta_0 = a / kappa if kappa != 0 else X.mean()
            theta_1_annual = (b / kappa if kappa != 0 else 0) / len(X_t) * 12
            sigma = results.resid.std() * np.sqrt(dt)
            log.info("OU params: kappa=%.4f, theta_0=%.4f, theta_1=%.6f, sigma=%.4f", kappa, theta_0, theta_1_annual, sigma)
            return cls(
                rng=np.random.default_rng(seed),
                start_value=start_value, kappa=kappa, theta=theta_0, theta_1=theta_1_annual, sigma=sigma,
                df=df_clean["DK2_EUR/MWh"].resample("ME").mean() * 1e-3,
            )
        else:
            monthly = df_clean["DK2_EUR/MWh"][1:].resample("ME").mean().to_numpy(float) * 1e-3
            s, loc, scale = stats.lognorm.fit(monthly)
            return cls(rng=np.random.default_rng(seed), s=s, loc=loc, scale=scale, df=monthly)

    def simulate(self, sampling_type: str, years: int, sims: int) -> np.ndarray:
        if sampling_type == "OU_Process":
            n_steps = years * 12
            dt = 1 / 12
            all_simulations = []
            for _ in range(sims):
                path = [self.start_value]
                for j in range(n_steps):
                    theta_t = self.theta + self.theta_1 * (j * dt)
                    drift = self.kappa * (theta_t - path[-1]) * dt
                    diffusion = self.sigma * np.sqrt(dt) * self.rng.normal(0, 1)
                    path.append(max(path[-1] + drift + diffusion, 0))
                all_simulations.append(path[1:])
            return np.array(all_simulations).T
        else:
            return stats.lognorm.rvs(s=self.s, loc=self.loc, scale=self.scale, size=(12 * years, sims), random_state=self.rng)


@dataclass
class ProductionModel:
    c: float
    loc: float
    scale: float
    cap_gwh: Optional[float]
    rng: np.random.Generator

    @classmethod
    def from_csv(cls, csv_path: str, capacity_mw: Optional[float] = None, seed: Optional[int] = None) -> "ProductionModel":
        df = pd.read_csv(csv_path)
        df["time"] = pd.to_datetime(df["time"])
        monthly = df.set_index("time")["electricity"].resample("ME").sum().to_numpy(float)
        c, loc, scale = stats.dweibull.fit(monthly)
        cap_gwh = capacity_mw * 8760 / 1000 if capacity_mw else None
        return cls(c, loc, scale, cap_gwh, np.random.default_rng(seed))

    def simulate(self, years: int, sims: int) -> np.ndarray:
        draws = stats.dweibull.rvs(c=self.c, loc=self.loc, scale=self.scale, size=(12 * years, sims), random_state=self.rng) / 1000
        if self.cap_gwh is not None:
            np.clip(draws, 0, self.cap_gwh, out=draws)
        return draws


@dataclass
class CaptureRateModel:
    price_mu: float
    price_std: float
    prod_mu: float
    prod_std: float
    corr_agg: float
    z_year_corr: np.ndarray
    mu_z_corr: float
    std_z_corr: float
    rng: np.random.Generator

    @classmethod
    def from_csv(cls, csv_path: str, seed: Optional[int] = None) -> "CaptureRateModel":
        df = pd.read_csv(csv_path, sep=";", decimal=",")
        df["HourUTC"] = pd.to_datetime(df["HourUTC"])
        df = df.set_index("HourUTC")
        price_mu, price_std = df["DK2_EUR/MWh"].mean(), df["DK2_EUR/MWh"].std()
        prod_mu, prod_std = df["OnshoreWindGe50kW_MWhDK2"].mean(), df["OnshoreWindGe50kW_MWhDK2"].std()
        df["year"] = df.index.year
        corr_by_year = (
            df.groupby("year")[["OnshoreWindGe50kW_MWhDK2", "DK2_EUR/MWh"]]
            .corr().iloc[0::2, 1].reset_index()
            .rename(columns={"DK2_EUR/MWh": "hourly_corr"}).drop("level_1", axis=1)
        )
        corr_by_year_arr = corr_by_year["hourly_corr"].to_numpy()[1:]
        corr_agg = df["DK2_EUR/MWh"].corr(df["OnshoreWindGe50kW_MWhDK2"])
        z_year_corr = np.arctanh(corr_by_year_arr)
        return cls(price_mu, price_std, prod_mu, prod_std, corr_agg, z_year_corr, z_year_corr.mean(), z_year_corr.std(ddof=1), np.random.default_rng(seed))

    def simulate(self, years: int, sims: int) -> np.ndarray:
        noise = self.rng.normal(0, self.std_z_corr, size=(years, sims))
        rho = np.tanh(self.mu_z_corr + noise)
        return 1 + rho * (self.price_std / self.price_mu) * (self.prod_std / self.prod_mu)


@dataclass
class LoadRateModel:
    price_mu: float
    price_std: float
    consump_mu: float
    consump_std: float
    corr_agg: float
    z_year_corr: np.ndarray
    mu_z_corr: float
    std_z_corr: float
    rng: np.random.Generator

    @classmethod
    def from_csv(cls, csv_path_price: str, csv_path_consumption: str, seed: Optional[int] = None) -> "LoadRateModel":
        df_price = pd.read_csv(csv_path_price, sep=";", decimal=",")
        df_price["HourUTC"] = pd.to_datetime(df_price["HourUTC"])
        df_price = df_price.set_index("HourUTC")
        df_cons = pd.read_csv(csv_path_consumption, sep=";", decimal=",")
        df_cons["HourUTC"] = pd.to_datetime(df_cons["HourUTC"])
        df_cons = df_cons.set_index("HourUTC").drop(columns=["HourDK", "MunicipalityNo"])
        df_cons = df_cons[df_cons["Branche"] == "Erhverv"]
        df_cons["ConsumptionMWh"] = df_cons["ConsumptionkWh"] / 1000
        df = pd.concat([df_price, df_cons], axis=1).dropna()
        price_mu, price_std = df["DK2_EUR/MWh"].mean(), df["DK2_EUR/MWh"].std()
        consump_mu, consump_std = df["ConsumptionMWh"].mean(), df["ConsumptionMWh"].std()
        df["year"] = df.index.year
        corr_by_year = (
            df.groupby("year")[["ConsumptionMWh", "DK2_EUR/MWh"]]
            .corr().iloc[0::2, 1].reset_index()
            .rename(columns={"DK2_EUR/MWh": "hourly_corr"}).drop("level_1", axis=1)
        )
        corr_by_year_arr = corr_by_year["hourly_corr"].to_numpy()[1:]
        corr_agg = df["DK2_EUR/MWh"].corr(df["ConsumptionMWh"])
        z_year_corr = np.arctanh(corr_by_year_arr)
        return cls(price_mu, price_std, consump_mu, consump_std, corr_agg, z_year_corr, z_year_corr.mean(), z_year_corr.std(ddof=1), np.random.default_rng(seed))

    def simulate(self, years: int, sims: int) -> np.ndarray:
        noise = self.rng.normal(0, self.std_z_corr, size=(years, sims))
        rho = np.tanh(self.mu_z_corr + noise)
        return 1 + rho * (self.price_std / self.price_mu) * (self.consump_std / self.consump_mu)


@dataclass
class LoadModel:
    a: float
    b: float
    loc: float
    scale: float
    rng: np.random.Generator

    @classmethod
    def from_csv(cls, csv_path_consumption: str, seed: Optional[int] = None) -> "LoadModel":
        df = pd.read_csv(csv_path_consumption, sep=";", decimal=",")
        df["HourUTC"] = pd.to_datetime(df["HourUTC"])
        df = df.set_index("HourUTC").drop(columns=["HourDK", "MunicipalityNo"])
        df = df[df["Branche"] == "Erhverv"]
        df["ConsumptionGWh"] = df["ConsumptionkWh"] * 1e-6
        monthly = df["ConsumptionGWh"][1:].resample("ME").sum().to_numpy(float)
        a, b, loc, scale = stats.beta.fit(monthly)
        return cls(a, b, loc, scale, np.random.default_rng(seed))

    def simulate(self, years: int, sims: int) -> np.ndarray:
        return stats.beta.rvs(a=self.a, b=self.b, loc=self.loc, scale=self.scale, size=(12 * years, sims), random_state=self.rng)


def generate_scenarios(
    *,
    years: int,
    num_scenarios: int,
    start_time,
    price_csv_path: str,
    prod_csv_path: str,
    consumption_csv_path: str,
    capacity_mw: Optional[float],
    output_dir: str = "outputs",
    seed: int = 42,
    monte_price: bool = False,
):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    sampling_type = "normal" if monte_price else "OU_Process"

    price_mdl = PriceModel.from_csv(sampling_type, price_csv_path, seed)
    _save_matrix(out, "price", price_mdl.simulate(sampling_type, years, num_scenarios), start_time, resample=True, monte_price=monte_price)

    prod_mdl = ProductionModel.from_csv(prod_csv_path, capacity_mw, seed)
    _save_matrix(out, "production", prod_mdl.simulate(years, num_scenarios), start_time, resample=True, monte_price=monte_price)

    cr_mdl = CaptureRateModel.from_csv(price_csv_path, seed)
    _save_matrix(out, "capture_rate", cr_mdl.simulate(years, num_scenarios), start_time, resample=False, monte_price=monte_price)

    load_mdl = LoadModel.from_csv(consumption_csv_path, seed)
    _save_matrix(out, "load", load_mdl.simulate(years, num_scenarios), start_time, resample=True, monte_price=monte_price)

    lr_mdl = LoadRateModel.from_csv(price_csv_path, consumption_csv_path, seed)
    _save_matrix(out, "load_capture_rate", lr_mdl.simulate(years, num_scenarios), start_time, resample=False, monte_price=monte_price)

    log.info("Wrote scenarios to %s", out.resolve())