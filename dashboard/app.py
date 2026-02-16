import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import shap
import joblib
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config import MODELS_DIR
from src.utils import generate_fraud_explanation

# ---------- Page configuration ----------
st.set_page_config(
    page_title="✨ FraudGuard Pro – AI Fraud Detection  #BY TEAM SGI",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- INJECT CUSTOM CSS + ANIMATIONS ----------
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    /* Global styles */
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }
    
    /* Animated gradient background for the whole app */
    .stApp {
        background: linear-gradient(-45deg, #0f0c29, #302b63, #24243e, #1a1a2e);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
    }
    
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255,255,255,0.2);
    }
    
    /* Sidebar text color */
    section[data-testid="stSidebar"] .css-1d391kg, 
    section[data-testid="stSidebar"] .css-1v3fvcr,
    section[data-testid="stSidebar"] .stRadio label {
        color: white !important;
    }
    
    /* Main title */
    h1 {
        background: linear-gradient(90deg, #ff6b6b, #feca57, #48dbfb, #ff9ff3);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3.5rem;
        animation: shine 3s infinite;
    }
    
    @keyframes shine {
        0% { filter: brightness(1); }
        50% { filter: brightness(1.3); }
        100% { filter: brightness(1); }
    }
    
    /* Card styling with glass morphism */
    .metric-card, .stDataFrame, .stAlert, .explanation {
        background: rgba(255, 255, 255, 0.15) !important;
        backdrop-filter: blur(10px) !important;
        border-radius: 20px !important;
        padding: 20px !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37) !important;
        color: white !important;
        transition: all 0.3s ease !important;
    }
    
    .metric-card:hover, .stDataFrame:hover {
        transform: translateY(-5px) scale(1.02);
        box-shadow: 0 15px 45px rgba(0,0,0,0.3) !important;
        border-color: #ff6b6b !important;
    }
    
    /* Fraud alert with pulse animation */
    .fraud-alert {
        background: linear-gradient(135deg, #ff0844, #ffb199) !important;
        border-left: none !important;
        border-radius: 15px !important;
        padding: 20px !important;
        animation: pulse 2s infinite !important;
        color: white !important;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 8, 68, 0.7); }
        70% { box-shadow: 0 0 0 20px rgba(255, 8, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 8, 68, 0); }
    }
    
    .authentic-alert {
        background: linear-gradient(135deg, #11998e, #38ef7d) !important;
        border-left: none !important;
        border-radius: 15px !important;
        padding: 20px !important;
        color: white !important;
    }
    
    /* Buttons */
    .stButton button {
        background: linear-gradient(90deg, #6a11cb, #2575fc) !important;
        color: white !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 10px 30px !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
    }
    
    .stButton button:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 8px 25px rgba(106, 17, 203, 0.5) !important;
    }
    
    /* Sliders */
    .stSlider label, .stNumberInput label {
        color: white !important;
    }
    
    /* Dataframe text color */
    .stDataFrame td, .stDataFrame th {
        color: white !important;
    }
    
    /* Headers in cards */
    h2, h3 {
        color: white !important;
        font-weight: 600 !important;
    }
    
    /* Explanation box with glow */
    .explanation {
        background: rgba(255,255,255,0.2) !important;
        border-left: 5px solid #ff6b6b !important;
    }
    
    /* Loading spinner animation */
    .stSpinner > div {
        border-top-color: #ff6b6b !important;
    }
    
    /* Hide default streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("💎 **FraudGuard Pro** – AI‑Powered Fraud Detection")
st.markdown("### *Real‑time credit card transaction analysis with stunning visuals*")

# ---------- Load artifacts ----------
@st.cache_resource
def load_artifacts():
    with st.spinner("✨ Loading AI models... Please wait..."):
        time.sleep(1)  # Simulate loading for effect
        models = {}
        for name in ['xgboost', 'lightgbm', 'randomforest', 'naivebayes']:
            models[name] = joblib.load(MODELS_DIR / f'{name}.pkl')
        X_train, X_val, X_test, y_train, y_val, y_test = joblib.load(MODELS_DIR / 'split_data.pkl')
        X_full, y_full = joblib.load(MODELS_DIR / 'full_data.pkl')
        explainer = joblib.load(MODELS_DIR / 'shap_explainer.pkl')
        return models, X_train, X_val, X_test, y_train, y_val, y_test, X_full, y_full, explainer

models, X_train, X_val, X_test, y_train, y_val, y_test, X_full, y_full, explainer = load_artifacts()

# ---------- Feature importance (for top features) ----------
feature_names = X_full.columns.tolist()
# Get global SHAP importance from XGBoost
xgb_model = models['xgboost']
explainer_global = shap.TreeExplainer(xgb_model, X_train.sample(100))
shap_values_global = explainer_global.shap_values(X_train.sample(100))
shap_importance = np.abs(shap_values_global).mean(axis=0)
top_features_idx = np.argsort(shap_importance)[-10:][::-1]
top_features = [feature_names[i] for i in top_features_idx]

# Pre‑computed feature descriptions for human‑readable reasons
feature_descriptions = {
    'V1':  '🔄 Transaction pattern anomaly',
    'V2':  '🌍 Geographical risk indicator',
    'V3':  '⚡ Transaction speed deviation',
    'V4':  '📊 Card usage frequency',
    'V5':  '💰 Purchase amount anomaly',
    'V6':  '🏪 Merchant category risk',
    'V7':  '⏱️ Time since last transaction',
    'V8':  '📱 Device fingerprint mismatch',
    'V9':  '🌐 IP address risk',
    'V10': '📍 Transaction location mismatch',
    'V11': '📈 Unusual spending pattern',
    'V12': '💳 Card entry method risk',
    'V13': '🔒 Authentication attempt failures',
    'V14': '⚠️ High‑risk transaction amount',
    'V15': '🌎 Cross‑border transaction flag',
    'V16': '🔗 Previous fraud关联',
    'V17': '🚀 Transaction velocity',
    'V18': '⭐ Merchant reputation score',
    'V19': '🛒 Card‑not‑present indicator',
    'V20': '💱 Currency conversion risk',
    'V21': '🕒 Transaction time anomaly',
    'V22': '💳 Card present/not present',
    'V23': '🏠 Distance from home',
    'V24': '🛍️ Unusual purchase category',
    'V25': '📡 Transaction channel risk',
    'V26': '📉 Previous chargebacks',
    'V27': '📅 Card expiry proximity',
    'V28': '📊 Risk score from external system',
    'Amount': '💵 Transaction amount',
    'Time':   '⏰ Transaction time'
}

def human_readable_explanation(shap_values, instance, feature_names):
    """Generate natural language explanation from SHAP values."""
    values = shap_values[0]
    base = shap_values.base_values[0] if hasattr(shap_values, 'base_values') else 0
    # Get top 3 positive contributors (fraud indicators)
    pos_contrib = []
    for i, feat in enumerate(feature_names):
        if values[i] > 0:
            pos_contrib.append((feat, values[i], instance.iloc[0][feat]))
    pos_contrib.sort(key=lambda x: x[1], reverse=True)
    
    reasons = []
    for feat, contrib, val in pos_contrib[:3]:
        desc = feature_descriptions.get(feat, f"Feature {feat}")
        # Determine if value is high/low relative to median
        median_val = X_full[feat].median()
        if val > median_val * 1.5:
            direction = "🚨 unusually high"
        elif val < median_val * 0.5:
            direction = "⚠️ unusually low"
        else:
            direction = "above normal" if val > median_val else "below normal"
        reasons.append(f"• **{desc}** is {direction} (value: {val:.3f}), contributing **+{contrib:.1%}** to fraud probability.")
    
    if not reasons:
        reasons = ["• No strong fraud indicators – transaction appears normal."]
    
    explanation = f"**Base fraud risk:** {base:.1%}\n\n"
    explanation += "**Why this transaction was flagged:**\n" + "\n".join(reasons)
    return explanation

# ---------- Sidebar navigation with icons ----------
st.sidebar.markdown("<h2 style='color:white;'>✨ Navigation</h2>", unsafe_allow_html=True)
page = st.sidebar.radio("", [
    "📊 Model Performance",
    "🔍 Fraud Explorer",
    "🎮 Live Simulator"
], format_func=lambda x: x)  # Keep icons

# ---------- PAGE 1: Model Performance ----------
if page == "📊 Model Performance":
    st.header("📊 Model Performance Comparison")
    
    from src.utils import evaluate_model
    metrics_list = []
    for name, model in models.items():
        metrics = evaluate_model(model, X_val, y_val)
        metrics['Model'] = name.upper()
        metrics_list.append(metrics)
    
    df_metrics = pd.DataFrame(metrics_list)
    df_metrics = df_metrics[['Model', 'accuracy', 'precision', 'recall', 'f1', 'roc_auc']]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🏆 Best F1 Score", f"{df_metrics['f1'].max():.3f}", 
                  delta=f"{(df_metrics['f1'].max() - df_metrics['f1'].mean()):.3f} vs avg")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🥇 Best Model", df_metrics.loc[df_metrics['f1'].idxmax(), 'Model'])
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("📈 ROC AUC (Avg)", f"{df_metrics['roc_auc'].mean():.3f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.subheader("📋 Detailed Metrics")
    st.dataframe(df_metrics.set_index('Model'), use_container_width=True)
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("📊 F1 Score by Model")
        fig, ax = plt.subplots()
        colors = sns.color_palette("viridis", len(df_metrics))
        sns.barplot(data=df_metrics, x='Model', y='f1', palette=colors, ax=ax)
        ax.set_ylim(0, 1)
        ax.set_ylabel('F1 Score')
        # Set white text for labels
        ax.tick_params(colors='white')
        ax.title.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.xaxis.label.set_color('white')
        for spine in ax.spines.values():
            spine.set_color('white')
        st.pyplot(fig)
    
    with col_right:
        st.subheader("🧩 Confusion Matrix – XGBoost")
        from sklearn.metrics import confusion_matrix
        y_pred_xgb = models['xgboost'].predict(X_val)
        cm = confusion_matrix(y_val, y_pred_xgb)
        fig, ax = plt.subplots()
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
                    xticklabels=['Authentic','Fraud'],
                    yticklabels=['Authentic','Fraud'])
        ax.set_xlabel('Predicted', color='white')
        ax.set_ylabel('Actual', color='white')
        ax.tick_params(colors='white')
        ax.title.set_color('white')
        st.pyplot(fig)

# ---------- PAGE 2: Fraud Explorer ----------
elif page == "🔍 Fraud Explorer":
    st.header("🔍 Fraudulent Transactions – Detailed Analysis")
    
    # Build full dataframe with predictions
    df_full = X_full.copy()
    df_full['Class'] = y_full.values
    df_full['Fraud_Probability'] = models['xgboost'].predict_proba(X_full)[:, 1]
    fraud_df = df_full[df_full['Class'] == 1].copy()
    
    # Advanced filters in sidebar
    st.sidebar.markdown("<h3 style='color:white;'>🔎 Filter Fraud Transactions</h3>", unsafe_allow_html=True)
    min_amount = st.sidebar.slider("Min Amount (scaled)", float(fraud_df['Amount'].min()),
                                    float(fraud_df['Amount'].max()), float(fraud_df['Amount'].min()))
    max_amount = st.sidebar.slider("Max Amount (scaled)", float(fraud_df['Amount'].min()),
                                    float(fraud_df['Amount'].max()), float(fraud_df['Amount'].max()))
    min_prob = st.sidebar.slider("Min Fraud Probability", 0.0, 1.0, 0.0)
    max_prob = st.sidebar.slider("Max Fraud Probability", 0.0, 1.0, 1.0)
    
    filtered = fraud_df[
        (fraud_df['Amount'] >= min_amount) &
        (fraud_df['Amount'] <= max_amount) &
        (fraud_df['Fraud_Probability'] >= min_prob) &
        (fraud_df['Fraud_Probability'] <= max_prob)
    ]
    
    st.subheader(f"📋 Showing {len(filtered)} fraudulent transactions")
    # Display a clean table with key columns
    display_cols = ['Time', 'Amount', 'V1', 'V2', 'V3', 'V4', 'V5', 'V10', 'V14', 'Fraud_Probability']
    st.dataframe(filtered[display_cols].head(20), use_container_width=True)
    
    # Explanation for a selected transaction
    st.subheader("🔎 Explain a Specific Fraud Case")
    if len(filtered) > 0:
        selected_idx = st.selectbox("Select transaction index", filtered.index)
        instance = X_full.loc[[selected_idx]]
        true_label = y_full.loc[selected_idx]
        prob = models['xgboost'].predict_proba(instance)[0, 1]
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**True label:** {'🚨 Fraud' if true_label==1 else '✅ Authentic'}")
            st.markdown(f"**Prediction:** {'🚨 FRAUD' if prob>0.5 else '✅ AUTHENTIC'}")
        with col_b:
            st.metric("Fraud Probability", f"{prob:.2%}")
        
        # SHAP explanation
        shap_values = explainer.shap_values(instance)
        explanation = human_readable_explanation(shap_values, instance, X_full.columns)
        st.markdown(f'<div class="explanation">{explanation}</div>', unsafe_allow_html=True)
        
        with st.expander("📊 View technical SHAP waterfall plot"):
            shap_exp = shap.Explanation(values=shap_values[0],
                                         base_values=explainer.expected_value,
                                         data=instance.iloc[0].values,
                                         feature_names=X_full.columns)
            fig = plt.figure()
            shap.plots.waterfall(shap_exp, max_display=10, show=False)
            # Adjust figure colors for dark background
            plt.gcf().set_facecolor('none')
            plt.gca().tick_params(colors='white')
            plt.gca().title.set_color('white')
            st.pyplot(fig)
    else:
        st.warning("No fraud transactions match the filters.")

# ---------- PAGE 3: Live Simulator ----------
elif page == "🎮 Live Simulator":
    st.header("🎮 Real‑Time Fraud Detection Simulator")
    st.markdown("Adjust the **most influential features** to test a transaction. The rest are set to typical values.")
    
    model = models['xgboost']
    
    # Use top 10 features for user input, others set to median
    default_vals = X_full.median().to_dict()
    st.subheader("⚙️ Adjust Key Transaction Attributes")
    
    cols = st.columns(3)
    user_input = {}
    for i, feat in enumerate(top_features):
        with cols[i % 3]:
            min_val = float(X_full[feat].quantile(0.01))
            max_val = float(X_full[feat].quantile(0.99))
            # Use a slider for continuous features, number for discrete-like
            if feat in ['Amount', 'Time']:
                user_input[feat] = st.slider(f"{feature_descriptions.get(feat, feat)}", 
                                              min_val, max_val, default_vals[feat], step=0.1)
            else:
                user_input[feat] = st.number_input(f"{feature_descriptions.get(feat, feat)}",
                                                    value=default_vals[feat], step=0.1)
    
    # Build full input vector with all features
    input_dict = {}
    for feat in feature_names:
        if feat in user_input:
            input_dict[feat] = user_input[feat]
        else:
            input_dict[feat] = default_vals[feat]
    
    input_df = pd.DataFrame([input_dict])
    
    # Prediction with loading effect
    if st.button("🔮 Analyze Transaction"):
        with st.spinner("✨ Analyzing with AI..."):
            time.sleep(1)  # Simulate thinking
            prob = model.predict_proba(input_df)[0, 1]
            pred = model.predict(input_df)[0]
        
        # Display result in a nice card
        st.markdown("---")
        if pred == 1:
            st.markdown(f'<div class="fraud-alert"><h2>🚨 FRAUD DETECTED</h2><p style="font-size:1.5rem;">Fraud probability: {prob:.2%}</p></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="authentic-alert"><h2>✅ AUTHENTIC</h2><p style="font-size:1.5rem;">Fraud probability: {prob:.2%}</p></div>', unsafe_allow_html=True)
        
        # Explanation
        if pred == 1:
            st.subheader("🔍 Why was this flagged?")
            shap_values = explainer.shap_values(input_df)
            explanation = human_readable_explanation(shap_values, input_df, X_full.columns)
            st.markdown(f'<div class="explanation">{explanation}</div>', unsafe_allow_html=True)
            
            with st.expander("📊 View SHAP waterfall plot"):
                shap_exp = shap.Explanation(values=shap_values[0],
                                             base_values=explainer.expected_value,
                                             data=input_df.iloc[0].values,
                                             feature_names=X_full.columns)
                fig = plt.figure()
                shap.plots.waterfall(shap_exp, max_display=10, show=False)
                plt.gcf().set_facecolor('none')
                plt.gca().tick_params(colors='white')
                plt.gca().title.set_color('white')
                st.pyplot(fig)
        else:
            st.info("✅ No strong fraud indicators – transaction appears normal.")