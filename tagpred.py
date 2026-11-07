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
if round(somma_perc, 2) < 70.00:
    st.error(f"La somma attuale degli acidi grassi è {somma_perc}%. Troppo bassa.")
else:
    st.success(f"Acidi grassi: {somma_perc}%. TAG noti da forzare: {somma_known}%.")
    
    if st.button("Calcola Trigliceridi"):
        
        # 1. TRADUZIONE DEGLI INPUT NEL TUO FORMATO
        elementi = [item[0] for item in input_data]
        composizione = {item[0]: item[1] / 100.0 for item in input_data}
        
        # NOTA: known_tags_data contiene ora una lista di tuple es. [("POP", 30.0)]
        # Pronta per essere usata nei calcoli futuri.

        # 2. IL TUO MOTORE COMBINATORIO
        comb = list(itertools.combinations_with_replacement(elementi, 3))
        percentualitag = {}
        for elem in comb:
            # Calcolo esatto senza arrotondamenti preventivi per non perdere decimali
            percentualitag[elem] = (composizione[elem[0]]) * (composizione[elem[1]]) * (composizione[elem[2]])
            
        somma_verifica = 0.0
        
        # 3. GESTIONE PERMUTAZIONI E TABELLA ORIZZONTALE
        dati_tabella = []
        somma_verifica = 0.0
        
        for key in percentualitag:
            ordinate = list(set(itertools.permutations(list(key), 3)))
            centriordinate = [el1[1] for el1 in ordinate]
            
            Gruppo = "-".join(key)
            # Inizializziamo la riga per questo gruppo
            riga = {"Gruppo": Gruppo}
            
            indice_colonna = 1
            for el in ordinate:
                if el[0] <= el[2]:
                    # Calcolo finale
                    prob_finale = percentualitag[key] * centriordinate.count(el[1])
                    somma_verifica += prob_finale
                    molecola = "".join(el)
                    
                    # Salviamo la stringa completa nella colonna dinamica corrispondente
                    riga[f"Isomero {indice_colonna}"] = f"{molecola}: {prob_finale * 100:.2f}%"
                    indice_colonna += 1
                    
            # Aggiungiamo la riga completata alla lista
            dati_tabella.append(riga)
            
        # Creiamo il DataFrame
        df = pd.DataFrame(dati_tabella)
        
        # Sostituiamo i famosi "punti vuoti" (che Pandas chiamerebbe NaN) con celle vuote pulite
        df = df.fillna("")
        
        # Mostriamo la tabella
        st.subheader("Tabella delle Probabilità")
        st.dataframe(df, use_container_width=True, hide_index=True)
            
        # Check finale
        st.info(f"Verifica algebrica totale: **{somma_verifica * 100:.0f}%**")
