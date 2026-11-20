import logging

import numpy as np
import pandas as pd

from sklearn.linear_model import Ridge, LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.impute import SimpleImputer

from ingestion.db import get_engine


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("train_backtest")


# ----- configurable parameters -----

MIN_TRAIN_MONTHS = 24

ALPHAS = np.logspace(-1, 3, 25)

CV_FOLDS = 5

TARGET_COL = "retail_sales_yoy_pct"

FEATURES = [

    # Previous month's retail sales
    "target_yoy_lag_1m",

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
]

# ------------------------------------


def create_ridge_search():

    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("ridge", Ridge())
    ])

    search = GridSearchCV(
        estimator=pipeline,
        param_grid={
            "ridge__alpha": ALPHAS
        },
        cv=TimeSeriesSplit(n_splits=CV_FOLDS),
        scoring="neg_mean_absolute_error",
        n_jobs=-1
    )

    return search


def run(min_train_months: int = MIN_TRAIN_MONTHS):

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

    prediction_rows = []
    coef_rows = []
    metric_rows = []

    for cat_code, group in df.groupby("category_code"):

        group = group.sort_values("month_date").copy()

        cat_name = group["category_name"].iloc[0]

        # Keep only rows with a known target and complete features
        hist = group.dropna(
            subset=[TARGET_COL] + FEATURES
        ).reset_index(drop=True)

        logger.info(
            f"{cat_code}: {len(hist)} usable historical observations"
        )

        if len(hist) <= min_train_months:

            logger.warning(
                f"Not enough history for {cat_code}. "
                f"Need more than {min_train_months}, "
                f"found {len(hist)}. Skipping."
            )

            continue

        # ------------------------------------
        # EXPANDING-WINDOW WALK-FORWARD TEST
        # ------------------------------------

        category_predictions = []

        for idx in range(min_train_months, len(hist)):

            train_df = hist.iloc[:idx]
            test_row = hist.iloc[[idx]]

            X_train = train_df[FEATURES]
            y_train = train_df[TARGET_COL]

            X_test = test_row[FEATURES]

            y_true = float(
                test_row[TARGET_COL].iloc[0]
            )

            prior_y = float(
                test_row["target_yoy_lag_1m"].iloc[0]
            )

            # Model 1: Ridge with alternative signals
            ridge_search = create_ridge_search()

            ridge_search.fit(X_train, y_train)

            y_pred_ridge = float(
                ridge_search.predict(X_test)[0]
            )

            best_alpha = float(
                ridge_search.best_params_["ridge__alpha"]
            )

            # Model 2: AR(1) baseline
            ar1 = LinearRegression()

            ar1.fit(
                train_df[["target_yoy_lag_1m"]],
                y_train
            )

            y_pred_ar1 = float(
                ar1.predict(
                    test_row[["target_yoy_lag_1m"]]
                )[0]
            )

            # Directional accuracy
            actual_dir = np.sign(y_true - prior_y)

            pred_dir = np.sign(
                y_pred_ridge - prior_y
            )

            result = {

                "month_date": test_row["month_date"].iloc[0],

                "category_code": cat_code,
                "category_name": cat_name,

                "actual_yoy_pct": round(y_true, 3),

                "predicted_yoy_pct": round(
                    y_pred_ridge, 3
                ),

                "baseline_ar1_pct": round(
                    y_pred_ar1, 3
                ),

                "abs_error_ridge": round(
                    abs(y_true - y_pred_ridge), 3
                ),

                "abs_error_ar1": round(
                    abs(y_true - y_pred_ar1), 3
                ),

                "direction_hit": int(
                    actual_dir == pred_dir
                ),

                "best_alpha": best_alpha,

                "is_live_forecast": False,
            }

            prediction_rows.append(result)
            category_predictions.append(result)

        # ------------------------------------
        # FULL-SAMPLE FEATURE COEFFICIENTS
        # ------------------------------------

        full_search = create_ridge_search()

        full_search.fit(
            hist[FEATURES],
            hist[TARGET_COL]
        )

        final_ridge = full_search.best_estimator_

        coefficients = (
            final_ridge.named_steps["ridge"].coef_
        )

        for feat_name, weight in zip(
            FEATURES, coefficients
        ):

            coef_rows.append({

                "category_code": cat_code,
                "category_name": cat_name,

                "feature_name": feat_name,

                "standardized_coef": round(
                    float(weight), 4
                ),
            })

        # ------------------------------------
        # BACKTEST SUMMARY METRICS
        # ------------------------------------

        cat_preds = pd.DataFrame(
            category_predictions
        )

        if cat_preds.empty:
            continue

        mae_ridge = mean_absolute_error(
            cat_preds["actual_yoy_pct"],
            cat_preds["predicted_yoy_pct"]
        )

        mae_ar1 = mean_absolute_error(
            cat_preds["actual_yoy_pct"],
            cat_preds["baseline_ar1_pct"]
        )

        rmse_ridge = np.sqrt(
            mean_squared_error(
                cat_preds["actual_yoy_pct"],
                cat_preds["predicted_yoy_pct"]
            )
        )

        dir_acc = (
            cat_preds["direction_hit"].mean() * 100
        )

        mae_improvement = (
            ((mae_ar1 - mae_ridge) / mae_ar1) * 100
            if mae_ar1 != 0 else 0.0
        )

        metric_rows.append({

            "category_code": cat_code,
            "category_name": cat_name,

            "backtest_months": len(cat_preds),

            "mae_ridge": round(
                float(mae_ridge), 3
            ),

            "mae_ar1": round(
                float(mae_ar1), 3
            ),

            "mae_improvement_pct": round(
                float(mae_improvement), 2
            ),

            "rmse_ridge": round(
                float(rmse_ridge), 3
            ),

            "directional_accuracy_pct": round(
                float(dir_acc), 2
            ),
        })

    # ------------------------------------
    # SAVE RESULTS TO POSTGRESQL
    # ------------------------------------

    if not prediction_rows:

        logger.warning(
            "No predictions generated. "
            "Check feature availability."
        )

        return

    predictions_df = pd.DataFrame(
        prediction_rows
    )

    coefficients_df = pd.DataFrame(
        coef_rows
    )

    summary_df = pd.DataFrame(
        metric_rows
    )

    predictions_df.to_sql(
        "fct_model_predictions",
        engine,
        schema="public_mart",
        if_exists="replace",
        index=False
    )

    coefficients_df.to_sql(
        "rpt_feature_coefficients",
        engine,
        schema="public_mart",
        if_exists="replace",
        index=False
    )

    summary_df.to_sql(
        "rpt_backtest_summary",
        engine,
        schema="public_mart",
        if_exists="replace",
        index=False
    )

    logger.info(
        "Backtest completed successfully."
    )

    logger.info(
        "\n" + summary_df.to_string(index=False)
    )

if __name__ == "__main__":
    run()