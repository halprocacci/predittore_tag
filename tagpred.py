import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import minimize

st.set_page_config(page_title="TAG Reverse Engineering (1,3-random-2-random)", layout="wide")
st.title("Reverse Engineering Posizionale TAG (sn-2 vs sn-1,3)")

# ==============================================================================
# FUNZIONI DEL MOTORE MATEMATICO
# ==============================================================================
def build_pools(x, T, active_fas, coupled_map, frozen_fas):
    p2 = {fa: T[fa] for fa in frozen_fas}
    for fa, val in zip(active_fas, x):
        p2[fa] = val
    # Accoppiamento: alpha_child = alpha_parent  =>  p2_child = p2_parent * (T_child / T_parent)
    for child, parent in coupled_map.items():
        p2[child] = p2[parent] * (T[child] / T[parent])
    # Bilancio di massa esatto per sn-1,3
    p13 = {fa: (3.0 * T[fa] - p2[fa]) / 2.0 for fa in T.keys()}
    return p2, p13

def predict_tag(tag, p2, p13):
    a, b, c = tag
    sym = 1.0 if a == c else 2.0
    return sym * p13[a] * p2[b] * p13[c] * 100.0

def solve_positional_model(T, known_tags, active_fas, coupled_map, frozen_fas, loss_type="Chi-quadro", n_starts=20):
    target_sum = 1.0 - sum(T[fa] for fa in frozen_fas)

    # Bounds fisici su ogni acido attivo, includendo i vincoli dei suoi "figli" accoppiati
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
        if loss_type == "Chi-quadro":
            return sum(((predict_tag(tag, p2, p13) - exp) ** 2) / max(exp, 1e-6)
                       for tag, exp in known_tags.items())
        else:
            return sum((predict_tag(tag, p2, p13) - exp) ** 2
                       for tag, exp in known_tags.items())

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
    for b in fas:  # sn-2
        for i, a in enumerate(fas):  # sn-1/3
            for j in range(i, len(fas)):  # sn-3/1 (evita duplicati speculari A-B-C / C-B-A)
                c = fas[j]
                pred = predict_tag((a, b, c), p2, p13)
                rows.append({
                    "TAG (sn-1/3 - sn-2 - sn-1/3)": f"{a}-{b}-{c}",
                    "Simmetrico": "Sì" if a == c else "No (×2)",
                    "Predetto (%)": pred
                })
    df_all = pd.DataFrame(rows).sort_values("Predetto (%)", ascending=False).reset_index(drop=True)
    return df_all

# ==============================================================================
# SIDEBAR: IMPOSTAZIONI SOLVER
# ==============================================================================
with st.sidebar:
    st.header("Impostazioni Ottimizzatore")
    loss_type = st.selectbox("Loss Function", ["Chi-quadro", "SSE"], index=0)
    n_starts = st.slider("Tentativi Multi-start", min_value=5, max_value=50, value=20, step=5)
    min_display = st.number_input("Soglia minima visualizzazione TAG (%)", min_value=0.0, max_value=5.0, value=0.1, step=0.1)

# ==============================================================================
# SEZIONE 1: INPUT ACIDI GRASSI E TAG NOTI
# ==============================================================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Composizione Acidi Grassi (FA)")
    st.caption("Inserisci i g/100g o % (vengono normalizzati automaticamente al 100% degli FA, escludendo il glicerolo).")
    default_fa = pd.DataFrame({
        "FA": ["P", "O", "S", "L", "ALTRO"],
        "Quantità": [6.5, 40.6, 43.8, 3.3, 1.4]
    })
    fa_df = st.data_editor(default_fa, num_rows="dynamic", use_container_width=True, key="fa_editor")

# Pulizia FA
fa_df = fa_df.dropna(subset=["FA", "Quantità"])
fa_df["FA"] = fa_df["FA"].astype(str).str.strip()
fa_df = fa_df[(fa_df["FA"] != "") & (fa_df["Quantità"] > 0)]

if len(fa_df) < 2:
    st.warning("Inserisci almeno 2 acidi grassi con quantità > 0.")
    st.stop()

fa_list = fa_df["FA"].tolist()
tot_fa = fa_df["Quantità"].sum()
T = {row["FA"]: row["Quantità"] / tot_fa for _, row in fa_df.iterrows()}

with col2:
    st.subheader("2. TAG Sperimentali Noti (Isomeri Posizionali)")
    st.caption("Inserisci i TAG misurati (es. POP, SOS, POS). A-B-C e C-B-A sono trattati come equivalenti.")
    default_tags = pd.DataFrame({
        "sn-1/3 (A)": ["P", "S", "P"],
        "sn-2 (B)":   ["O", "O", "O"],
        "sn-1/3 (C)": ["P", "S", "S"],
        "Reale (%)":  [2.4, 41.2, 10.5]
    })
    tag_df = st.data_editor(
        default_tags,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "sn-1/3 (A)": st.column_config.SelectboxColumn(options=fa_list, required=True),
            "sn-2 (B)":   st.column_config.SelectboxColumn(options=fa_list, required=True),
            "sn-1/3 (C)": st.column_config.SelectboxColumn(options=fa_list, required=True),
            "Reale (%)":  st.column_config.NumberColumn(min_value=0.0, max_value=100.0, format="%.2f", required=True),
        },
        key="tag_editor"
    )

# Pulizia TAG noti
tag_df = tag_df.dropna(subset=["sn-1/3 (A)", "sn-2 (B)", "sn-1/3 (C)", "Reale (%)"])
known_tags = {}
for _, row in tag_df.iterrows():
    a, b, c = row["sn-1/3 (A)"], row["sn-2 (B)"], row["sn-1/3 (C)"]
    if a in T and b in T and c in T:
        # Ordine canonico sui lati per evitare duplicati tipo P-O-S e S-O-P
        a_c, c_c = sorted([a, c])
        known_tags[(a_c, b, c_c)] = float(row["Reale (%)"])

if len(known_tags) == 0:
    st.warning("Inserisci almeno un TAG noto valido.")
    st.stop()

# ==============================================================================
# SEZIONE 2: GESTIONE DINAMICA DEGLI ACIDI GRASSI NON OSSERVATI
# ==============================================================================
fa_osservati = set(fa for tag in known_tags.keys() for fa in tag)
active_fas = [fa for fa in fa_list if fa in fa_osservati]
unobserved_fas = [fa for fa in fa_list if fa not in fa_osservati]

coupled_map = {}
frozen_fas = []

if unobserved_fas:
    st.subheader("3. Acidi Grassi non presenti nei TAG noti")
    st.caption("Scegli se tenerli fissi alla distribuzione casuale (uguale dentro e fuori) oppure accoppiarli alla selettività di un acido attivo.")
    cols_unobs = st.columns(min(len(unobserved_fas), 4))
    options = ["Fisso / Casuale (p2 = p13 = T)"] + [f"Accoppia selettività a {fa}" for fa in active_fas]

    for idx, fa in enumerate(unobserved_fas):
        with cols_unobs[idx % 4]:
            choice = st.selectbox(f"Regola per **{fa}** ({T[fa]*100:.1f}%)", options, key=f"rule_{fa}")
            if choice.startswith("Accoppia"):
                parent = choice.replace("Accoppia selettività a ", "")
                coupled_map[fa] = parent
            else:
                frozen_fas.append(fa)

# ==============================================================================
# SEZIONE 3: ESECUZIONE OTTIMIZZAZIONE E RISULTATI
# ==============================================================================
st.divider()
if st.button("Calcola Profilo Posizionale e Predici TAG", type="primary"):
    if len(active_fas) < 2:
        st.error("Servono almeno 2 acidi grassi diversi nei TAG noti per poter ottimizzare.")
        st.stop()

    p2_opt, p13_opt, res, conv = solve_positional_model(
        T, known_tags, active_fas, coupled_map, frozen_fas,
        loss_type=loss_type, n_starts=n_starts
    )

    if res is None:
        st.error("L'ottimizzatore non è riuscito a convergere. Controlla la coerenza dei dati inseriti.")
        st.stop()

    # Controllo Blend Detector (se POP, SOS, POS sono presenti)
    p_pop = known_tags.get(('P', 'O', 'P'))
    p_sos = known_tags.get(('S', 'O', 'S'))
    p_pos = known_tags.get(('P', 'O', 'S'))
    if p_pop and p_sos and p_pos and (p_pop * p_sos > 0):
        R_index = p_pos / (2.0 * np.sqrt(p_pop * p_sos))
        if R_index < 0.65:
            st.warning(
                f"**Attenzione (Possibile Blend Fisico):** l'indice di equilibrio "
                f"$R = \\text{{POS}} / (2\\sqrt{{\\text{{POP}} \\cdot \\text{{SOS}}}}) = {R_index:.2f}$ è molto basso. "
                f"Il campione potrebbe essere una miscela fisica non interesterificata; il modello a 2 magazzini potrebbe avere scarti elevati."
            )

    # Metriche rapide
    m1, m2, m3 = st.columns(3)
    m1.metric(f"Loss finale ({loss_type})", f"{res.fun:.4f}")
    m2.metric("Convergenze Multi-start", f"{conv}/{n_starts}")
    m3.metric("Iterazioni miglior run", f"{res.nit}")

    # Tabella 1: Profilo sn-2 vs sn-1,3
    st.subheader("Profilo Posizionale Ricostruito")
    prof_rows = []
    for fa in fa_list:
        alpha = (p2_opt[fa] / (3.0 * T[fa])) * 100.0
        if fa in active_fas:
            stato = "Ottimizzato"
        elif fa in coupled_map:
            stato = f"Accoppiato a {coupled_map[fa]}"
        else:
            stato = "Fisso (Casuale)"
        prof_rows.append({
            "FA": fa,
            "Totale T (%)": round(T[fa] * 100, 2),
            "Magazzino sn-2 (p2 %)": round(p2_opt[fa] * 100, 2),
            "Magazzino sn-1,3 (p13 %)": round(p13_opt[fa] * 100, 2),
            "% di FA in sn-2 (α)": round(alpha, 1),
            "% di FA in sn-1,3": round(100.0 - alpha, 1),
            "Stato": stato
        })
    st.dataframe(pd.DataFrame(prof_rows), use_container_width=True, hide_index=True)

    # Tabella 2 & 3 affiancate: Fit sui noti + Predizione completa
    c_fit, c_pred = st.columns([1, 1.3])

    with c_fit:
        st.subheader("Fit sui TAG Noti")
        fit_rows = []
        for tag, exp in known_tags.items():
            pred = predict_tag(tag, p2_opt, p13_opt)
            fit_rows.append({
                "TAG": "-".join(tag),
                "Reale (%)": round(exp, 2),
                "Predetto (%)": round(pred, 2),
                "Delta (%)": round(pred - exp, 2)
            })
        st.dataframe(pd.DataFrame(fit_rows), use_container_width=True, hide_index=True)

    with c_pred:
        st.subheader(f"Tutti i TAG Predetti (≥ {min_display}%)")
        df_all = generate_all_tags(T, p2_opt, p13_opt)
        df_show = df_all[df_all["Predetto (%)"] >= min_display].copy()
        df_show["Predetto (%)"] = df_show["Predetto (%)"].round(2)
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        csv_data = df_all.to_csv(index=False).encode("utf-8")
        st.download_button("Scarica tabella completa CSV", csv_data, "tag_predetti.csv", "text/csv")
