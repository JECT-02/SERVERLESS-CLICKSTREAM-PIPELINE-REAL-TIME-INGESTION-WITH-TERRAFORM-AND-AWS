import numpy as np
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score,
    confusion_matrix, classification_report,
)


def evaluate_model(model, X_test, y_test, X_train=None, y_train=None):
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        'precision': float(precision_score(y_test, y_pred, zero_division=0)),
        'recall': float(recall_score(y_test, y_pred, zero_division=0)),
        'f1_score': float(f1_score(y_test, y_pred, zero_division=0)),
        'auc_roc': float(roc_auc_score(y_test, y_proba)),
        'auc_pr': float(average_precision_score(y_test, y_proba)),
    }

    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    metrics['true_negatives'] = int(tn)
    metrics['false_positives'] = int(fp)
    metrics['false_negatives'] = int(fn)
    metrics['true_positives'] = int(tp)

    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    metrics['specificity'] = float(specificity)

    if X_train is not None and y_train is not None:
        train_proba = model.predict_proba(X_train)[:, 1]
        metrics['train_auc_roc'] = float(roc_auc_score(y_train, train_proba))
        metrics['train_auc_pr'] = float(average_precision_score(y_train, train_proba))

    return metrics
