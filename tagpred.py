import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import minimize

st.set_page_config(page_title="Predittore TAG", layout="wide")
st.title("Predittore TAG")

# ==============================================================================
# MOTORE MATEMATICO
# ==============================================================================
def build_pools(x, T, active_fas, coupled_map, frozen_fas):
    p2 = {fa: T[fa] for fa in frozen_fas}
    for fa, val in zip(active_fas, x):
        p2[fa] = val
    for child, parent in coupled_map.items():
        p2[child] = p2[parent] * (T[child] / T[parent])
    p13 = {fa: (3.0 * T[fa] - p2[fa]) / 2.0 for fa in T.keys()}
    return p2, p13

def predict_tag(tag, p2, p13):
    a, b, c = tag
    sym = 1.0 if a == c else 2.0
    return sym * p13[a] * p2[b] * p13[c] * 100.0

def solve_model(T, known_tags, active_fas, coupled_map, frozen_fas, loss_type="Chi2", n_starts=20):
    target_sum = 1.0 - sum(T[fa] for fa in frozen_fas)

    bounds = []
    for fa in active_fas:
        low = max(0.0, 3.0 * T[fa] - 2.0)
        high = min(1.0, 3.0 * T[fa])
        for child, parent in coupled_map.items():
            if parent == fa:
                low = max(low, (T[fa] / T[child]) * (3.0 * T[child] - 2.0))
                high = min(high, T[fa] / T[child])
        bounds.append((low, high))

    def sum_constraint(x):
        p2, _ = build_pools(x, T, active_fas, coupled_map, frozen_fas)
        non_frozen = active_fas + list(coupled_map.keys())
        return sum(p2[fa] for fa in non_frozen) - target_sum

    def loss_fn(x):
        p2, p13 = build_pools(x, T, active_fas, coupled_map, frozen_fas)
        if loss_type == "Chi2":
            return sum(((predict_tag(tag, p2, p13) - exp) ** 2) / max(exp, 1e-6)
                       for tag, exp in known_tags.items())
        return sum((predict_tag(tag, p2, p13) - exp) ** 2 for tag, exp in known_tags.items())

    rng = np.random.default_rng(42)
    starts = [np.array([T[fa] for fa in active_fas])]
    for _ in range(n_starts - 1):
        starts.append(np.array([rng.uniform(lo, hi) for lo, hi in bounds]))

    best_res = None
    converged = 0
    for x0 in starts:
        res = minimize(
            loss_fn, x0, method="SLSQP", bounds=bounds,
            constraints={"type": "eq", "fun": sum_constraint},
            options={"ftol": 1e-10, "maxiter": 500}
        )
        if res.success:
            converged += 1
            if best_res is None or res.fun < best_res.fun:
                best_res = res

    if best_res is None:
        return None, None, None, 0

    p2_opt, p13_opt = build_pools(best_res.x, T, active_fas, coupled_map, frozen_fas)
    return p2_opt, p13_opt, best_res, converged

def generate_all_tags(T, p2, p13):
    fas = list(T.keys())
    rows = []
    for b in fas:
        for i, a in enumerate(fas):
            for j in range(i, len(fas)):
                c = fas[j]
                rows.append({
                    "TAG": f"{a}-{b}-{c}",
                    "Predetto (%)": predict_tag((a, b, c), p2, p13)
                })
    return pd.DataFrame(rows).sort_values("Predetto (%)", ascending=False).reset_index(drop=True)

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    loss_type = st.selectbox("Loss", ["Chi2", "SSE"], index=0)
    n_starts = st.slider("Multi-start", 5, 50, 20, 5)
    min_display = st.number_input("Soglia output TAG (%)", 0.0, 5.0, 0.1, 0.1)

# ==============================================================================
# INPUT
# ==============================================================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("Acidi grassi")
    default_fa = pd.DataFrame({
        "Acido grasso": ["P", "O", "S", "L", "ALTRO"],
        "Valore": [6.5, 40.6, 43.8, 3.3, 1.4]
    })
    fa_df = st.data_editor(default_fa, num_rows="dynamic", use_container_width=True, key="fa_editor")

fa_df = fa_df.dropna(subset=["Acido grasso", "Valore"])
fa_df["Acido grasso"] = fa_df["Acido grasso"].astype(str).str.strip()
fa_df = fa_df[(fa_df["Acido grasso"] != "") & (fa_df["Valore"] > 0)]

if len(fa_df) < 2:
    st.stop()

fa_list = fa_df["Acido grasso"].tolist()
tot_fa = fa_df["Valore"].sum()
T = {row["Acido grasso"]: row["Valore"] / tot_fa for _, row in fa_df.iterrows()}

with col2:
    st.subheader("TAG noti")
    default_tags = pd.DataFrame({
        "sn-1/3": ["P", "S", "P"],
        "sn-2":   ["O", "O", "O"],
        "sn-3/1": ["P", "S", "S"],
        "%":      [2.4, 41.2, 10.5]
    })
    tag_df = st.data_editor(
        default_tags,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "sn-1/3": st.column_config.SelectboxColumn(options=fa_list, required=True),
            "sn-2":   st.column_config.SelectboxColumn(options=fa_list, required=True),
            "sn-3/1": st.column_config.SelectboxColumn(options=fa_list, required=True),
            "%":      st.column_config.NumberColumn(min_value=0.0, max_value=100.0, format="%.2f", required=True),
        },
        key="tag_editor"
    )

tag_df = tag_df.dropna(subset=["sn-1/3", "sn-2", "sn-3/1", "%"])
known_tags = {}
for _, row in tag_df.iterrows():
    a, b, c = row["sn-1/3"], row["sn-2"], row["sn-3/1"]
    if a in T and b in T and c in T:
        a_c, c_c = sorted([a, c])
        known_tags[(a_c, b, c_c)] = float(row["%"])

if not known_tags:
    st.stop()

# ==============================================================================
# ACIDI GRASSI SENZA TAG NOTI
# ==============================================================================
fa_osservati = set(fa for tag in known_tags.keys() for fa in tag)
active_fas = [fa for fa in fa_list if fa in fa_osservati]
unobserved_fas = [fa for fa in fa_list if fa not in fa_osservati]

coupled_map = {}
frozen_fas = []

if unobserved_fas:
    st.subheader("Acidi grassi senza TAG noti")
    cols_unobs = st.columns(min(len(unobserved_fas), 4))
    opt_map = {"Fisso (distribuzione casuale)": None, **{f"Stessa probabilità di {fa}": fa for fa in active_fas}}
    opt_labels = list(opt_map.keys())

    for idx, fa in enumerate(unobserved_fas):
        with cols_unobs[idx % 4]:
            choice = st.selectbox(f"{fa} ({T[fa]*100:.1f}%)", opt_labels, key=f"rule_{fa}")
            parent = opt_map[choice]
            if parent is not None:
                coupled_map[fa] = parent
            else:
                frozen_fas.append(fa)

# ==============================================================================
# CALCOLO E OUTPUT
# ==============================================================================
st.divider()
if st.button("Calcola", type="primary"):
    if len(active_fas) < 2:
        st.error("Servono almeno 2 acidi grassi distinti nei TAG noti.")
        st.stop()

    p2_opt, p13_opt, res, conv = solve_model(
        T, known_tags, active_fas, coupled_map, frozen_fas,
        loss_type=loss_type, n_starts=n_starts
    )

    if res is None:
        st.error("Nessuna convergenza.")
        st.stop()

    fit_rows = []
    for tag, exp in known_tags.items():
        pred = predict_tag(tag, p2_opt, p13_opt)
        fit_rows.append({
            "TAG": "-".join(tag),
            "Reale (%)": round(exp, 2),
            "Predetto (%)": round(pred, 2),
            "Δ (%)": round(pred - exp, 2)
        })
    max_abs_err = max(abs(r["Δ (%)"]) for r in fit_rows)

    p_pop = known_tags.get(("P", "O", "P"))
    p_sos = known_tags.get(("S", "O", "S"))
    p_pos = known_tags.get(("P", "O", "S"))
    R_index = (p_pos / (2.0 * np.sqrt(p_pop * p_sos))) if (p_pop and p_sos and p_pos) else None

    cols_m = st.columns(4 if R_index is not None else 3)
    cols_m[0].metric(f"Loss ({loss_type})", f"{res.fun:.4f}")
    cols_m[1].metric("Scarto max fit", f"{max_abs_err:.2f}%")
    cols_m[2].metric("Convergenze", f"{conv}/{n_starts}")
    if R_index is not None:
        cols_m[3].metric("R (POS / 2√POP·SOS)", f"{R_index:.2f}")

    # Warning solo se lo scarto sul fit esplode o se R è basso con entrambi i picchi >= 5%
    is_blend_R = (R_index is not None) and (R_index < 0.65) and (min(p_pop, p_sos) >= 5.0)
    if max_abs_err > 5.0 or is_blend_R:
        st.warning(f"Scarto elevato sul fit (max {max_abs_err:.2f}%): possibile blend fisico o deviazione dal modello 1,3-random-2-random.")

    st.subheader("Profilo posizionale")
    prof_rows = []
    for fa in fa_list:
        alpha = (p2_opt[fa] / (3.0 * T[fa])) * 100.0
        stato = "Ottimizzato" if fa in active_fas else (f"Come {coupled_map[fa]}" if fa in coupled_map else "Fisso")
        prof_rows.append({
            "Acido grasso": fa,
            "Totale (%)": round(T[fa] * 100, 2),
            "p2 (%)": round(p2_opt[fa] * 100, 2),
            "p13 (%)": round(p13_opt[fa] * 100, 2),
            "In sn-2 (%)": round(alpha, 1),
            "In sn-1,3 (%)": round(100.0 - alpha, 1),
            "Stato": stato
        })
    st.dataframe(pd.DataFrame(prof_rows), use_container_width=True, hide_index=True)

    c_fit, c_pred = st.columns([1, 1.2])

    with c_fit:
        st.subheader("Fit sui TAG noti")
        st.dataframe(pd.DataFrame(fit_rows), use_container_width=True, hide_index=True)

    with c_pred:
        st.subheader(f"TAG predetti (≥ {min_display}%)")
        df_all = generate_all_tags(T, p2_opt, p13_opt)
        df_show = df_all[df_all["Predetto (%)"] >= min_display].copy()
        df_show["Predetto (%)"] = df_show["Predetto (%)"].round(2)
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.download_button("Scarica CSV", df_all.to_csv(index=False).encode("utf-8"), "tag_predetti.csv", "text/csv")
