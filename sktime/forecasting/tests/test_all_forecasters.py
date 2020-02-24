#!/usr/bin/env python3 -u
# coding: utf-8

__author__ = ["Markus Löning"]
__all__ = [
    "test_clone",
    "test_compute_pred_errors",
    "test_different_fh_in_fit_and_predict_req",
    "test_not_fitted_error",
    "test_fh_in_fit_opt",
    "test_fh_in_fit_req",
    "test_fh_in_predict_opt",
    "test_no_fh_in_fit_req",
    "test_no_fh_opt",
    "test_oh_setting",
    "test_predict_return_pred_interval_time_index",
    "test_return_self_for_fit_set_params_update",
    "test_same_fh_in_fit_and_predict_opt",
    "test_same_fh_in_fit_and_predict_req",
    "test_score",
    "test_not_fitted_error",
    "test_predict_time_index",
    "test_update_predict_predicted_indices",
]

import numpy as np
import pytest
from sklearn.base import clone
from sktime.forecasting.base import OptionalForecastingHorizonMixin, RequiredForecastingHorizonMixin
from sktime.forecasting.model_selection import SlidingWindowSplitter
from sktime.forecasting.tests import DEFAULT_FHS, DEFAULT_INSAMPLE_FHS, DEFAULT_STEP_LENGTHS, DEFAULT_WINDOW_LENGTHS
from sktime.performance_metrics.forecasting import smape_loss
from sktime.utils import all_estimators
from sktime.utils.exceptions import NotFittedError
from sktime.utils.testing.base import _construct_instance
from sktime.utils.testing.forecasting import compute_expected_index_from_update_predict
from sktime.utils.testing.forecasting import make_forecasting_problem
from sktime.utils.testing.forecasting import assert_correct_pred_time_index
from sktime.utils.validation.forecasting import check_fh

# get all forecasters
FORECASTERS = [e[1] for e in all_estimators(type_filter="forecaster")]
FH0 = DEFAULT_FHS[0]

# testing data
y_train, y_test = make_forecasting_problem()


########################################################################################################################
########################################################################################################################
# test API provided through BaseForecaster

########################################################################################################################
# test clone
@pytest.mark.parametrize("Forecaster", FORECASTERS)
def test_clone(Forecaster):
    f = _construct_instance(Forecaster)
    clone(f)

    # check cloning of fitted instance
    f = _construct_instance(Forecaster)
    f.fit(y_train, FH0)
    clone(f)


########################################################################################################################
# fit, set_params and update return self
@pytest.mark.parametrize("Forecaster", FORECASTERS)
def test_return_self_for_fit_set_params_update(Forecaster):
    f = _construct_instance(Forecaster)
    ret = f.fit(y_train, FH0)
    assert ret == f

    ret = f.update(y_test, update_params=False)
    assert ret == f

    ret = f.set_params()
    assert ret == f


########################################################################################################################
# test oh setting
@pytest.mark.parametrize("Forecaster", FORECASTERS)
def test_oh_setting(Forecaster):
    # check oh and cutoff is None after construction
    f = _construct_instance(Forecaster)
    assert f.oh is None
    assert f.cutoff is None

    # check that oh and cutoff is updated during fit
    f.fit(y_train, FH0)
    assert f.oh is not None
    assert f.cutoff == y_train.index[-1]

    # check data pointers
    # np.testing.assert_array_equal(f.oh.index, y_train.index)
    assert f.oh.index is y_train.index

    # check that oh and cutoff is updated during update
    f.update(y_test, update_params=False)
    np.testing.assert_array_equal(f.oh.index, np.append(y_train.index, y_test.index))
    assert f.cutoff == y_test.index[-1]


########################################################################################################################
# not fitted error
@pytest.mark.parametrize("Forecaster", FORECASTERS)
def test_not_fitted_error(Forecaster):
    f = _construct_instance(Forecaster)
    with pytest.raises(NotFittedError):
        f.predict(fh=1)

    with pytest.raises(NotFittedError):
        f.update(y_test, update_params=False)

    with pytest.raises(NotFittedError):
        cv = SlidingWindowSplitter(fh=1, window_length=1)
        f.update_predict(y_test, cv=cv)


########################################################################################################################
# predict
# predicted time index
@pytest.mark.parametrize("Forecaster", FORECASTERS)
@pytest.mark.parametrize("fh", DEFAULT_FHS)
def test_predict_time_index(Forecaster, fh):
    f = _construct_instance(Forecaster)
    f.fit(y_train, fh)
    y_pred = f.predict()
    assert_correct_pred_time_index(y_pred, y_train, fh)


########################################################################################################################
# test predicted pred int time index
@pytest.mark.parametrize("Forecaster", FORECASTERS)
@pytest.mark.parametrize("fh", DEFAULT_INSAMPLE_FHS)
def test_predict_insample(Forecaster, fh):
    f = _construct_instance(Forecaster)
    f.fit(y_train, fh=fh)

    try:
        y_pred = f.predict()
        assert_correct_pred_time_index(y_pred, y_train, fh)

    except NotImplementedError:
        print(f"{Forecaster}'s in-sample predictions are not implemented, test skipped.")
        pass


########################################################################################################################
# test predicted pred int time index
@pytest.mark.parametrize("Forecaster", FORECASTERS)
@pytest.mark.parametrize("fh", DEFAULT_FHS)
def test_predict_return_pred_interval_time_index(Forecaster, fh):
    f = _construct_instance(Forecaster)
    f.fit(y_train, fh=fh)
    try:
        _, pred_ints = f.predict(return_pred_int=True, alpha=0.05)
        assert_correct_pred_time_index(pred_ints, y_train, fh)

    except NotImplementedError:
        print(f"{Forecaster}'s `return_pred_int` option is not implemented, test skipped.")
        pass


########################################################################################################################
# score
@pytest.mark.parametrize("Forecaster", FORECASTERS)
@pytest.mark.parametrize("fh", DEFAULT_FHS)
def test_score(Forecaster, fh):
    # compute expected score
    f = _construct_instance(Forecaster)
    f.fit(y_train, fh)
    y_pred = f.predict()

    fh_idx = check_fh(fh) - 1  # get zero based index
    expected = smape_loss(y_pred, y_test.iloc[fh_idx])

    # compare with actual score
    f = _construct_instance(Forecaster)
    f.fit(y_train, fh)
    actual = f.score(y_test.iloc[fh_idx], fh=fh)
    assert actual == expected


########################################################################################################################
# compute_pred_errors
@pytest.mark.parametrize("Forecaster", FORECASTERS)
def test_compute_pred_errors(Forecaster):
    f = _construct_instance(Forecaster)
    f.fit(y_train, fh=FH0)
    try:
        errs = f.compute_pred_errors(alpha=0.05)

        # Prediction errors should always increase with the horizon
        assert errs.is_monotonic_increasing

    except NotImplementedError:
        print(f"{Forecaster}'s `compute_pred_errors` method is not implemented, test skipped.")
        pass


########################################################################################################################
# update_predict
# check if predicted time index is correct
@pytest.mark.parametrize("Forecaster", FORECASTERS)
@pytest.mark.parametrize("fh", DEFAULT_FHS)
@pytest.mark.parametrize("window_length", DEFAULT_WINDOW_LENGTHS)
@pytest.mark.parametrize("step_length", DEFAULT_STEP_LENGTHS)
def test_update_predict_predicted_indices(Forecaster, fh, window_length, step_length):
    cv = SlidingWindowSplitter(fh, window_length=window_length, step_length=step_length)
    f = _construct_instance(Forecaster)
    f.fit(y_train, fh)
    y_pred = f.update_predict(y_test, cv=cv)

    pred_index = y_pred.index.values
    expected_index = compute_expected_index_from_update_predict(y_test, f.fh, step_length)
    np.testing.assert_array_equal(pred_index, expected_index)


########################################################################################################################
########################################################################################################################
# check setting/getting API for forecasting horizon

# divide Forecasters into groups
FORECASTERS_REQUIRED = [f for f in FORECASTERS if issubclass(f, RequiredForecastingHorizonMixin)]
FORECASTERS_OPTIONAL = [f for f in FORECASTERS if issubclass(f, OptionalForecastingHorizonMixin)]


########################################################################################################################
# testing Forecasters which require fh during fitting
@pytest.mark.parametrize("Forecaster", FORECASTERS_REQUIRED)
def test_no_fh_in_fit_req(Forecaster):
    f = _construct_instance(Forecaster)
    # fh required in fit, raises error if not passed
    with pytest.raises(ValueError):
        f.fit(y_train)


########################################################################################################################
@pytest.mark.parametrize("Forecaster", FORECASTERS_REQUIRED)
def test_fh_in_fit_req(Forecaster):
    f = _construct_instance(Forecaster)
    f.fit(y_train, FH0)
    np.testing.assert_array_equal(f.fh, FH0)
    f.predict()
    np.testing.assert_array_equal(f.fh, FH0)


########################################################################################################################
@pytest.mark.parametrize("Forecaster", FORECASTERS_REQUIRED)
def test_same_fh_in_fit_and_predict_req(Forecaster):
    f = _construct_instance(Forecaster)
    f.fit(y_train, FH0)
    np.testing.assert_array_equal(f.fh, FH0)
    f.predict(FH0)
    np.testing.assert_array_equal(f.fh, FH0)


########################################################################################################################
@pytest.mark.parametrize("Forecaster", FORECASTERS_REQUIRED)
def test_different_fh_in_fit_and_predict_req(Forecaster):
    f = _construct_instance(Forecaster)
    f.fit(y_train, FH0)
    np.testing.assert_array_equal(f.fh, FH0)
    # updating fh during predict raises error as fitted model depends on fh seen in fit
    with pytest.raises(ValueError):
        f.predict(fh=FH0 + 1)


########################################################################################################################
# testing Forecasters which take fh either during fitting or predicting
@pytest.mark.parametrize("Forecaster", FORECASTERS_OPTIONAL)
def test_no_fh_opt(Forecaster):
    f = _construct_instance(Forecaster)
    f.fit(y_train)
    # not passing fh to either fit or predict raises error
    with pytest.raises(ValueError):
        f.predict()


########################################################################################################################
@pytest.mark.parametrize("Forecaster", FORECASTERS_OPTIONAL)
def test_fh_in_fit_opt(Forecaster):
    f = _construct_instance(Forecaster)
    f.fit(y_train, FH0)
    np.testing.assert_array_equal(f.fh, FH0)
    f.predict()
    np.testing.assert_array_equal(f.fh, FH0)


########################################################################################################################
@pytest.mark.parametrize("Forecaster", FORECASTERS_OPTIONAL)
def test_fh_in_predict_opt(Forecaster):
    f = _construct_instance(Forecaster)
    f.fit(y_train)
    f.predict(FH0)
    np.testing.assert_array_equal(f.fh, FH0)


########################################################################################################################
@pytest.mark.parametrize("Forecaster", FORECASTERS_OPTIONAL)
def test_same_fh_in_fit_and_predict_opt(Forecaster):
    f = _construct_instance(Forecaster)
    # passing the same fh to both fit and predict works
    f.fit(y_train, FH0)
    f.predict(FH0)
    np.testing.assert_array_equal(f.fh, FH0)
