#!/usr/bin/env python3 -u
# coding: utf-8

__author__ = ["Markus Löning"]

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sktime.forecasting.base import BaseForecaster
from sktime.forecasting.compose import EnsembleForecaster
from sktime.forecasting.compose import TransformedTargetForecaster
from sktime.forecasting.compose import DirectRegressionForecaster
from sktime.forecasting.compose import DirectTimeSeriesRegressionForecaster
from sktime.forecasting.compose import RecursiveRegressionForecaster
from sktime.forecasting.compose import RecursiveTimeSeriesRegressionForecaster
from sktime.forecasting.naive import NaiveForecaster
from sktime.forecasting.theta import ThetaForecaster
from sktime.transformers.compose import Tabulariser
from sktime.transformers.detrend import Detrender

# look up table for estimators which require arguments during constructions,
# links base classes with the default constructor arguments
REGRESSOR = LinearRegression()

DEFAULT_INSTANTIATIONS = {
    DirectRegressionForecaster: {"regressor": REGRESSOR},
    RecursiveRegressionForecaster: {"regressor": REGRESSOR},
    DirectTimeSeriesRegressionForecaster: {"regressor": make_pipeline(Tabulariser(), REGRESSOR)},
    RecursiveTimeSeriesRegressionForecaster: {"regressor": make_pipeline(Tabulariser(), REGRESSOR)},
    TransformedTargetForecaster: {"forecaster": NaiveForecaster(), "transformer": Detrender(ThetaForecaster())},
    EnsembleForecaster: {"forecasters": [
        ("last", NaiveForecaster()),
        ("mean", NaiveForecaster(strategy="mean", window_length=3))
    ]}
}


def _construct_instance(Estimator):
    """Construct Estimator instance if possible"""
    required_parameters = getattr(Estimator, "_required_parameters", [])
    if len(required_parameters) > 0:
        # if estimator requires parameters for construction,
        # set default ones for testing
        if issubclass(Estimator, BaseForecaster):
            kwargs = {}
            if Estimator in DEFAULT_INSTANTIATIONS:
                kwargs = DEFAULT_INSTANTIATIONS[Estimator]
            if not kwargs:
                raise ValueError(f"No default instantiation has been found "
                                 f"for estimator: {Estimator}")
        else:
            raise NotImplementedError()

        estimator = Estimator(**kwargs)

    else:
        # construct without kwargs if no parameters are required
        estimator = Estimator()

    return estimator


def generate_df_from_array(array, n_rows=10, n_cols=1):
    return pd.DataFrame([[pd.Series(array) for _ in range(n_cols)] for _ in range(n_rows)],
                        columns=[f'col{c}' for c in range(n_cols)])
