import lightgbm as lgb
import pandas as pd

from ml import config as cfg


def train_classifier(X_train: pd.DataFrame, y_train: pd.Series) -> lgb.LGBMClassifier:
    model = lgb.LGBMClassifier(**cfg.LGBM_CLASSIFIER_PARAMS)
    model.fit(X_train, y_train)
    return model


def train_regressor(X_train: pd.DataFrame, y_train: pd.Series) -> lgb.LGBMRegressor:
    model = lgb.LGBMRegressor(**cfg.LGBM_REGRESSOR_PARAMS)
    model.fit(X_train, y_train)
    return model
