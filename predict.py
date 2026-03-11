"""
Prediction and SHAP explanation module.
Loads the best saved model and provides fraud predictions with explanations.
"""

import os
import json
import joblib
import numpy as np
import shap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64


class FraudPredictor:
    """Loads the trained model and scaler, provides predictions and SHAP explanations."""

    def __init__(self, model_dir):
        self.model_dir = model_dir
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.explainer = None
        self.metrics = None
        self._load()

    def _load(self):
        """Load model, scaler, and metadata."""
        model_path = os.path.join(self.model_dir, 'best_model.pkl')
        scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
        metrics_path = os.path.join(self.model_dir, 'metrics.json')

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at {model_path}. Run ml/train.py first."
            )

        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)

        with open(metrics_path, 'r') as f:
            meta = json.load(f)
        self.feature_names = meta['feature_names']
        self.metrics = meta

        # Create SHAP explainer
        try:
            self.explainer = shap.TreeExplainer(self.model)
        except Exception:
            self.explainer = shap.KernelExplainer(
                self.model.predict_proba,
                np.zeros((1, len(self.feature_names)))
            )

    def predict(self, features_dict):
        """
        Predict fraud probability and risk level.

        Args:
            features_dict: dict with feature name -> value

        Returns:
            dict with probability, risk_level, prediction
        """
        feature_array = np.array([[features_dict.get(f, 0) for f in self.feature_names]])
        scaled = self.scaler.transform(feature_array)

        probability = float(self.model.predict_proba(scaled)[0][1]) * 100
        prediction = 1 if probability >= 50 else 0

        if probability <= 30:
            risk_level = 'Low'
        elif probability <= 70:
            risk_level = 'Medium'
        else:
            risk_level = 'High'

        return {
            'probability': round(probability, 2),
            'risk_level': risk_level,
            'prediction': prediction
        }

    def explain(self, features_dict):
        """
        Generate SHAP explanations for a single transaction.

        Returns:
            dict with shap_values, feature_importance, force_plot_html, summary_text
        """
        feature_array = np.array([[features_dict.get(f, 0) for f in self.feature_names]])
        scaled = self.scaler.transform(feature_array)

        shap_values = self.explainer.shap_values(scaled)

        # Handle different SHAP output formats
        if isinstance(shap_values, list):
            sv = shap_values[1][0]  # Class 1 (fraud)
        else:
            sv = shap_values[0]

        # Feature importance for this prediction
        importance = {}
        for fname, sval in zip(self.feature_names, sv):
            importance[fname] = round(float(sval), 4)

        # Sort by absolute importance
        sorted_importance = dict(sorted(
            importance.items(), key=lambda x: abs(x[1]), reverse=True
        ))

        # Generate force plot as base64 image
        force_plot_html = self._generate_force_plot(scaled, shap_values)

        # Generate summary text
        summary_lines = []
        for fname, sval in list(sorted_importance.items())[:5]:
            direction = "increases" if sval > 0 else "decreases"
            summary_lines.append(
                f"• {fname}: {direction} fraud risk (SHAP: {sval:+.4f})"
            )
        summary_text = "\n".join(summary_lines)

        return {
            'feature_importance': sorted_importance,
            'force_plot_html': force_plot_html,
            'summary_text': summary_text
        }

    def _generate_force_plot(self, scaled_data, shap_values):
        """Generate SHAP force plot as base64 HTML image."""
        try:
            if isinstance(shap_values, list):
                sv = shap_values[1]
            else:
                sv = shap_values

            # Create a bar chart of SHAP values as a more reliable visualization
            fig, ax = plt.subplots(figsize=(10, 4))
            sv_flat = sv[0] if len(sv.shape) > 1 else sv
            colors = ['#ff4444' if v > 0 else '#4488ff' for v in sv_flat]
            bars = ax.barh(self.feature_names, sv_flat, color=colors)
            ax.set_xlabel('SHAP Value (impact on fraud prediction)')
            ax.set_title('Feature Impact on Prediction')
            ax.axvline(x=0, color='gray', linewidth=0.5)
            plt.tight_layout()

            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return f'<img src="data:image/png;base64,{img_base64}" class="img-fluid" alt="SHAP Force Plot">'
        except Exception as e:
            return f'<p class="text-muted">SHAP plot unavailable: {str(e)}</p>'

    def get_feature_importance_chart(self):
        """Generate global feature importance bar chart as base64."""
        try:
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
            else:
                return None

            fig, ax = plt.subplots(figsize=(8, 5))
            sorted_idx = np.argsort(importances)
            ax.barh(
                [self.feature_names[i] for i in sorted_idx],
                importances[sorted_idx],
                color='#1a73e8'
            )
            ax.set_xlabel('Feature Importance')
            ax.set_title('Global Feature Importance')
            plt.tight_layout()

            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return f'data:image/png;base64,{img_base64}'
        except Exception:
            return None

    def get_model_comparison(self):
        """Return model comparison metrics."""
        if self.metrics and 'results' in self.metrics:
            return self.metrics['results']
        return {}

    def get_best_model_name(self):
        """Return name of the best model."""
        if self.metrics and 'best_model_name' in self.metrics:
            return self.metrics['best_model_name']
        return 'Unknown'
