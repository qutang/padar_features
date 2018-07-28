from functools import partial
from padar_features.features.accelerometer import stats, spectrum, orientation
import importlib
from numpy.linalg import norm
from padar_features.features.formatter import as_float64, vec2colarr
import pandas as pd


class FeatureSet:
    def __init__(self):
        self._feature_funcs = []
        self._ori = None
        self._freq = None

    def add_feature(self, feature_func, **kwargs):
        func = partial(feature_func, **kwargs)
        self._feature_funcs.append(func)
        return self

    def add_orientation_feature(self, feature_name, subwins=4, unit='deg'):
        def get_orientation_feature_func(X):
            if self._ori is None:
                self._ori = orientation.OrientationFeature(X, subwins=subwins)
                self._ori.estimate_orientation(unit=unit)
            result = getattr(self._ori, feature_name)()
            return result
        self._feature_funcs.append(get_orientation_feature_func)
        return self

    def add_freq_feature(self, feature_name, *, sr, **kwargs):
        def get_freq_feature_func(X):
            if self._freq is None:
                self._freq = spectrum.FrequencyFeature(X, sr=sr)
                self._freq.fft().peaks()
            result = getattr(self._freq, feature_name)(**kwargs)
            return result
        self._feature_funcs.append(get_freq_feature_func)
        return self

    def compute(self, X):
        result = [func(X) for func in self._feature_funcs]
        return pd.concat(result, axis=1)

    @staticmethod
    def compute_all(X, *, sr, ori_subwins, ori_unit, **kwargs):
        feature_set = FeatureSet() \
            .add_feature(stats.mean) \
            .add_feature(stats.std) \
            .add_feature(stats.positive_amplitude) \
            .add_feature(stats.negative_amplitude) \
            .add_freq_feature('dominant_frequency', sr=sr, n=1) \
            .add_freq_feature('highend_power', sr=sr) \
            .add_freq_feature('dominant_frequency_power_ratio', sr=sr, n=1) \
            .add_freq_feature('total_power', sr=sr) \
            .add_orientation_feature('median_angles', subwins=ori_subwins, unit=ori_unit) \
            .add_orientation_feature('range_angles', subwins=ori_subwins, unit=ori_unit) \
            .add_orientation_feature('std_angles', subwins=ori_subwins, unit=ori_unit)
        return feature_set.compute(X)

    @staticmethod
    def compute_posture_and_activity(X, sr, ori_subwins=4, ori_unit='deg', **kwargs):
        X = as_float64(X)
        vm_feature_set = FeatureSet() \
            .add_feature(stats.mean) \
            .add_feature(stats.std) \
            .add_feature(stats.positive_amplitude) \
            .add_feature(stats.negative_amplitude) \
            .add_freq_feature('dominant_frequency', sr=sr, n=1) \
            .add_freq_feature('highend_power', sr=sr) \
            .add_freq_feature('dominant_frequency_power_ratio', sr=sr, n=1) \
            .add_freq_feature('total_power', sr=sr)

        axis_feature_set = FeatureSet() \
            .add_orientation_feature('median_angles', subwins=ori_subwins, unit=ori_unit) \
            .add_orientation_feature('range_angles', subwins=ori_subwins, unit=ori_unit)

        X_vm = vec2colarr(norm(X, ord=2, axis=1))
        result = pd.concat([vm_feature_set.compute(X_vm),
                            axis_feature_set.compute(X)], axis=1)
        return result