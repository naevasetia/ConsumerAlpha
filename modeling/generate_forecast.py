import logging

import pandas as pd
from sqlalchemy import text

from ingestion.db import get_engine
from modeling.train_backtest import (
    FEATURES,
    TARGET_COL,
    create_ridge_search,
)

logger = logging.getLogger("generate_forecast")

MIN_TRAIN_FOR_LIVE = 24


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

    live_rows = []

    for cat_code, group in df.groupby("category_code"):

        group = group.sort_values("month_date").copy()

        cat_name = group["category_name"].iloc[0]

        # Historical observations with known retail sales
        train_df = group.dropna(
            subset=[TARGET_COL] + FEATURES
        ).copy()

        # Months where Census sales have not yet been released
        unreleased = group[
            group[TARGET_COL].isna()
        ].copy()

        logger.info(
            f"{cat_code}: {len(train_df)} training rows, "
            f"{len(unreleased)} unreleased months"
        )

        if unreleased.empty:
            continue

        if len(train_df) < MIN_TRAIN_FOR_LIVE:
            logger.warning(
                f"Not enough training data for {cat_code}. Skipping."
            )
            continue

        # Train using all available historical observations
        X_train = train_df[FEATURES]
        y_train = train_df[TARGET_COL]

        # Same time-series CV pipeline used in backtesting
        model = create_ridge_search()

        model.fit(X_train, y_train)

        predictions = model.predict(
            unreleased[FEATURES]
        )

        best_alpha = float(
            model.best_params_["ridge__alpha"]
        )

        for (_, row), pred_val in zip(
            unreleased.iterrows(),
            predictions
        ):

            prior_y = row["target_yoy_lag_1m"]

            live_rows.append({

                "month_date": row["month_date"],

                "category_code": cat_code,
                "category_name": cat_name,

                "actual_yoy_pct": None,

                "predicted_yoy_pct": round(
                    float(pred_val), 3
                ),

                "baseline_ar1_pct": (
                    round(float(prior_y), 3)
                    if pd.notna(prior_y) else None
                ),

                "abs_error_ridge": None,
                "abs_error_ar1": None,
                "direction_hit": None,

                "best_alpha": best_alpha,

                "is_live_forecast": True,
            })

    if not live_rows:

        logger.info(
            "No unreleased months available for forecasting."
        )

        return

    forecast_df = pd.DataFrame(live_rows)

    # Remove previous live forecasts before inserting updated ones
    with engine.begin() as conn:

        conn.execute(
            text("""
                DELETE FROM public_mart.fct_model_predictions
                WHERE is_live_forecast = TRUE
            """)
        )

    forecast_df.to_sql(
        "fct_model_predictions",
        engine,
        schema="public_mart",
        if_exists="append",
        index=False
    )

    logger.info(
        f"Wrote {len(live_rows)} live forecast predictions."
    )

    logger.info(
        "\n" + forecast_df[
            [
                "month_date",
                "category_code",
                "predicted_yoy_pct",
                "baseline_ar1_pct",
            ]
        ].to_string(index=False)
    )

if __name__ == "__main__":
    run()