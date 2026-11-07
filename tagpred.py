import streamlit as st
import itertools
import pandas as pd

st.title("Predittore trigliceridi")

# SEZIONE 1: ACIDI GRASSI
st.subheader("Imposta gli acidi grassi di partenza")
n_tags = st.number_input("Quanti acidi grassi diversi vuoi inserire?", min_value=1, max_value=10, value=3)

input_data = []
somma_perc = 0.0

for i in range(n_tags):
    col1, col2 = st.columns(2)
    with col1:
        default_tag = ["A", "B", "C"][i] if i < 3 else f"L{i}"
        tag = st.text_input(f"Acido grasso {i+1} ", value=default_tag, key=f"tag_{i}").upper()
    with col2:
        default_q = [17, 43, 40][i] if i < 3 else 0
        quantita = st.number_input(f"Percentuale {tag} (%)", min_value=0.0, max_value=100.0, value=float(default_q), step=1.0, key=f"q_{i}")
        somma_perc += quantita
    
    if len(tag) >= 1 and quantita > 0:
        input_data.append((tag, quantita))

st.divider()

# SEZIONE 2: TAG NOTI (DA FORZARE)
st.subheader("Imposta i Trigliceridi (TAG) noti (Opzionale)")
n_known = st.number_input("Quanti TAG noti vuoi forzare?", min_value=0, max_value=10, value=1)

known_tags_data = []
somma_known = 0.0

for i in range(n_known):
    col1, col2 = st.columns(2)
    with col1:
        default_known_tag = ["POP", "POS", "SOS"][i] if i < 3 else f"TAG{i}"
        known_tag = st.text_input(f"Nome TAG noto {i+1}", value=default_known_tag, key=f"known_name_{i}").upper()
    with col2:
        quantita_known = st.number_input(f"Percentuale {known_tag} (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key=f"known_q_{i}")
        somma_known += quantita_known
        
    if len(known_tag) >= 1 and quantita_known > 0:
        known_tags_data.append((known_tag, quantita_known))

st.divider()

# VALIDAZIONE E CALCOLO
if round(somma_perc, 2) <= 0.0:
    st.error("Inserisci delle quantità per gli acidi grassi.")
elif somma_known >= 100.0:
    st.error("I TAG forzati non possono superare o eguagliare il 100%.")
else:
    if st.button("Calcola Trigliceridi"):
        
        # 1. NORMALIZZAZIONE A 100 DEGLI ACIDI GRASSI INIZIALI
        fa_norm = {item[0]: (item[1] / somma_perc) * 100.0 for item in input_data}
        
        # 2. SOTTRAZIONE DEI MATTONI DEI TAG FORZATI
        fa_rimasti = fa_norm.copy()
        famiglie_forzate = []
        
        for k_tag, k_q in known_tags_data:
            lettere = list(k_tag)
            famiglia = tuple(sorted(lettere))
            famiglie_forzate.append(famiglia)
            
            # Un TAG consuma un terzo del suo peso in % per ogni posizione
            consumo_per_lettera = k_q / 3.0
            for char in lettere:
                if char in fa_rimasti:
                    fa_rimasti[char] -= consumo_per_lettera
                else:
                    st.error(f"Errore: Il TAG forzato {k_tag} contiene l'acido '{char}' che non è presente negli acidi grassi inziali.")
                    st.stop()
                    
        # Controllo che le forzature non mandino in negativo gli acidi grassi
        for k, v in fa_rimasti.items():
            if v < -0.01:
                st.error(f"Impossibile: forzare i TAG inseriti consuma più '{k}' di quanto ce ne sia a disposizione.")
                st.stop()
            fa_rimasti[k] = max(0.0, v) # Pulisce eventuali errori di virgola mobile tipo -0.00001
            
        # 3. RICALCOLO DELLE FRAZIONI SUL RESTO
        somma_fa_rimasti = sum(fa_rimasti.values())
        if somma_fa_rimasti > 0:
            composizione_motore = {k: v / somma_fa_rimasti for k, v in fa_rimasti.items()}
        else:
            composizione_motore = {k: 0.0 for k in fa_rimasti.keys()}
            
        # 4. IL TUO MOTORE COMBINATORIO
        elementi = list(fa_rimasti.keys())
        comb = list(itertools.combinations_with_replacement(elementi, 3))
        
        prob_grezze_restanti = {}
        somma_prob_rimaste = 0.0
        
        for elem in comb:
            famiglia_chiave = tuple(sorted(elem))
            
            # FILTRO: Rimuove completamente le combinazioni già forzate
            if famiglia_chiave in famiglie_forzate:
                continue
                
            prob = composizione_motore[elem[0]] * composizione_motore[elem[1]] * composizione_motore[elem[2]]
            prob_grezze_restanti[famiglia_chiave] = prob
            
            # Calcoliamo la somma delle probabilità delle famiglie sopravvissute per poterle rimettere in scala
            ordinate = list(set(itertools.permutations(list(famiglia_chiave), 3)))
            centriordinate = [el1[1] for el1 in ordinate]
            for el in ordinate:
                if el[0] <= el[2]:
                    somma_prob_rimaste += prob * centriordinate.count(el[1])

        # 5. OUTPUT: TABELLA FORZATI
        st.subheader("Trigliceridi Forzati (Dati Noti)")
        dati_forzati = []
        for k_tag, k_q in known_tags_data:
            dati_forzati.append({"Molecola Forzata": k_tag, "Quantità Imposta (%)": f"{k_q:.2f}%"})
        if dati_forzati:
            st.dataframe(pd.DataFrame(dati_forzati), use_container_width=True, hide_index=True)
        else:
            st.info("Nessun TAG forzato inserito.")
            
        # 6. OUTPUT: TABELLA PROBABILISTICI (Su quello che resta)
        st.subheader(f"Trigliceridi Probabilistici (Calcolati sul restante {100.0 - somma_known:.2f}%)")
        dati_tabella = []
        somma_verifica = somma_known # Partiamo già col totale di quelli imposti
        spazio_rimanente = 100.0 - somma_known
        
        for key, prob_motore in prob_grezze_restanti.items():
            ordinate = list(set(itertools.permutations(list(key), 3)))
            centriordinate = [el1[1] for el1 in ordinate]
            
            Gruppo = "-".join(key)
            riga = {}
            somma_famiglia = 0.0
            
            indice_colonna = 1
            for el in ordinate:
                if el[0] <= el[2]:
                    # Riproposizioniamo la probabilità per farla stare nello spazio rimanente
                    prob_base_isomero = prob_motore * centriordinate.count(el[1])
                    if somma_prob_rimaste > 0:
                        prob_aggiustata = prob_base_isomero / somma_prob_rimaste
                    else:
                        prob_aggiustata = 0
                        
                    prob_finale_percentuale = prob_aggiustata * spazio_rimanente
                    
                    somma_verifica += prob_finale_percentuale
                    somma_famiglia += prob_finale_percentuale
                    molecola = "".join(el)
                    
                    riga[f"Isomero {indice_colonna}"] = f"{molecola}: {prob_finale_percentuale:.2f}%"
                    indice_colonna += 1
                    
            if indice_colonna > 1:
                # Creiamo la riga finale con il totale nel nome e una chiave temporanea per l'ordinamento
                riga_completa = {"Famiglia": f"{Gruppo} ({somma_famiglia:.2f}%)", "_SortKey": somma_famiglia}
                riga_completa.update(riga)
                dati_tabella.append(riga_completa)
        
        # Ordina la lista in modo decrescente e rimuove la chiave temporanea
        dati_tabella = sorted(dati_tabella, key=lambda x: x["_SortKey"], reverse=True)
        for riga in dati_tabella:
            del riga["_SortKey"]
            
        df_prob = pd.DataFrame(dati_tabella)
        df_prob = df_prob.fillna("")
        st.dataframe(df_prob, use_container_width=True, hide_index=True)
            
        # Check finale
        st.info(f"Verifica algebrica totale: **{somma_verifica:.0f}%**")
