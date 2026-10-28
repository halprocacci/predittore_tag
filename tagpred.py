import streamlit as st
import itertools

st.title("Predittore trigliceridi")

st.subheader("Imposta gli acidi grassi di partenza (Totale: 100%)")
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
        # Permettiamo anche i decimali
        quantita = st.number_input(f"Percentuale {tag} (%)", min_value=0.0, max_value=100.0, value=float(default_q), step=1.0, key=f"q_{i}")
        somma_perc += quantita
    
    if len(tag) >= 1 and quantita > 0:
        input_data.append((tag, quantita))

if round(somma_perc, 2) != 100.00:
    st.error(f"La somma attuale è {somma_perc}%. Aggiusta i valori per arrivare esattamente a 100%.")
else:
    st.success("Composizione iniziale valida (100%).")
    
    if st.button("Calcola Trigliceridi"):
        
        # 1. TRADUZIONE DEGLI INPUT NEL TUO FORMATO
        # Estrae i nomi e calcola le frazioni (es. 17 -> 0.17) direttamente dai dati inseriti dall'utente
        elementi = [item[0] for item in input_data]
        composizione = {item[0]: item[1] / 100.0 for item in input_data}
        
        # 2. IL TUO MOTORE COMBINATORIO
        comb = list(itertools.combinations_with_replacement(elementi, 3))
        percentualitag = {}
        for elem in comb:
            # Calcolo esatto senza arrotondamenti preventivi per non perdere decimali
            percentualitag[elem] = (composizione[elem[0]]) * (composizione[elem[1]]) * (composizione[elem[2]])
            
        
        somma_verifica = 0.0
        
       # 3. GESTIONE PERMUTAZIONI E STAMPA A SCHERMO
        for key in percentualitag:
            ordinate = list(set(itertools.permutations(list(key), 3)))
            centriordinate = [el1[1] for el1 in ordinate]
            
            # Intestazione della famiglia
            st.markdown(f"**Famiglia {'-'.join(key)}**")
            
            # Prepariamo una lista temporanea per salvare le molecole di questa famiglia
            dati_molecole = []
            
            for el in ordinate:
                if el[0] <= el[2]:
                    # Calcolo finale
                    prob_finale = percentualitag[key] * centriordinate.count(el[1])
                    somma_verifica += prob_finale
                    molecola = "".join(el)
                    dati_molecole.append((molecola, prob_finale * 100))
            
            # Creiamo un numero di colonne pari a quanti isomeri abbiamo trovato (1, 2 o 3)
            cols = st.columns(len(dati_molecole))
            
            # Inseriamo i dati graficamente come "metriche" dentro le colonne
            for i, (mol, prob) in enumerate(dati_molecole):
                cols[i].metric(label=mol, value=f"{prob:.2f}%")
            
            st.divider() # Riga orizzontale per separare visivamente le famiglie
