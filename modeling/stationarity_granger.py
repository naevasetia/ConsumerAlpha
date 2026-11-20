import logging
import warnings

import pandas as pd
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

from ingestion.db import get_engine

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("stationarity_granger")

# ----- configurable parameters -----

TARGET_COL = "retail_sales_yoy_pct"

GRANGER_LAGS = 3
MIN_OBS = 24

ADF_P_THRESH = 0.05
GC_P_THRESH = 0.05

FEATURE_COLS = [
    # Google Trends
    "trend_electronics_yoy",
    "trend_furniture_yoy",
    "trend_home_improvement_yoy",
    "trend_deals_yoy",
    "trend_financial_pressure_yoy",

    # Reddit
    "reddit_sentiment_m",
    "reddit_neg_share_m",
    "reddit_posts_yoy",
    "reddit_budget_yoy",
    "reddit_deals_yoy",
    "reddit_shopping_yoy",

    # ETFs
    "xrt_yoy",
    "xrt_vol_m",
    "xly_yoy",

    # Macroeconomic indicators
    "job_openings_yoy",
    "lagged_umich_sentiment",
    "lagged_cc_delinquency",
]

# ------------------------------------


def check_adf(series: pd.Series) -> tuple[float, bool]:
    clean = series.dropna()

    if len(clean) < 15:
        return 1.0, False

    p_val = adfuller(clean, autolag="AIC")[1]

    return float(p_val), bool(p_val < ADF_P_THRESH)


def has_consecutive_months(dates: pd.Series) -> bool:
    dates = pd.to_datetime(dates).sort_values()

    expected = pd.date_range(
        start=dates.min(),
        end=dates.max(),
        freq="MS"
    )

    return dates.reset_index(drop=True).equals(
        pd.Series(expected)
    )


def run():

    engine = get_engine()

    logger.info("Loading monthly retail signals...")

    df = pd.read_sql(
        """
        SELECT *
        FROM public_mart.fct_retail_signals_monthly
        ORDER BY category_code, month_date
        """,
        engine
    )

    df["month_date"] = pd.to_datetime(df["month_date"])

    # Exclude months where official retail sales are unavailable
    df = df.dropna(subset=[TARGET_COL])

    results = []

    for cat_code, group in df.groupby("category_code"):

        group = group.sort_values("month_date")

        cat_name = group["category_name"].iloc[0]

        logger.info(
            f"Processing {cat_code}: {cat_name}"
        )

        for feat in FEATURE_COLS:

            sub = group[
                ["month_date", TARGET_COL, feat]
            ].dropna().sort_values("month_date")

            if len(sub) < MIN_OBS:
                logger.warning(
                    f"Skipping {feat} for {cat_code}: "
                    f"only {len(sub)} observations"
                )
                continue

            # Granger testing assumes equally spaced observations.
            # Skip a feature if its available observations have gaps.
            if not has_consecutive_months(sub["month_date"]):
                logger.warning(
                    f"Skipping {feat} for {cat_code}: "
                    "missing months in the series"
                )
                continue

            target_p, target_stat = check_adf(sub[TARGET_COL])
            feat_p, feat_stat = check_adf(sub[feat])

            # Difference both series once if either is non-stationary
            test_df = sub[[TARGET_COL, feat]].copy()

            if not target_stat or not feat_stat:
                test_df = test_df.diff().dropna()

            if len(test_df) < MIN_OBS:
                continue

            try:

                gc = grangercausalitytests(
                    test_df[[TARGET_COL, feat]],
                    maxlag=GRANGER_LAGS,
                    verbose=False
                )

                best_lag = min(
                    gc.keys(),
                    key=lambda k: gc[k][0]["ssr_ftest"][1]
                )

                best_f_stat = float(
                    gc[best_lag][0]["ssr_ftest"][0]
                )

                best_p_val = float(
                    gc[best_lag][0]["ssr_ftest"][1]
                )

            except Exception as e:

                logger.warning(
                    f"Granger test failed for "
                    f"{feat} / {cat_code}: {e}"
                )

                best_lag = 0
                best_f_stat = 0.0
                best_p_val = 1.0

            results.append({

                "category_code": cat_code,
                "category_name": cat_name,
                "signal_name": feat,

                "observations": len(test_df),

                "target_adf_p_value": round(target_p, 4),
                "target_is_stationary": target_stat,

                "adf_p_value": round(feat_p, 4),
                "is_stationary": feat_stat,

                "optimal_lag_months": int(best_lag),
                "granger_f_stat": round(best_f_stat, 4),
                "granger_p_value": round(best_p_val, 4),

                "is_significant_lead": bool(
                    best_p_val < GC_P_THRESH
                ),
            })

    out_df = pd.DataFrame(results)

    if out_df.empty:
        logger.warning(
            "No Granger results generated. "
            "Check data availability and missing values."
        )
        return

    # Save diagnostic results in the correct dbt schema
    out_df.to_sql(
        "rpt_granger_diagnostics",
        engine,
        schema="public_mart",
        if_exists="replace",
        index=False
    )

    sig_count = int(
        out_df["is_significant_lead"].sum()
    )

    logger.info(
        f"Saved {len(out_df)} Granger tests."
    )

    logger.info(
        f"{sig_count} signals were significant "
        f"at p < {GC_P_THRESH}."
    )


if __name__ == "__main__":
    run()