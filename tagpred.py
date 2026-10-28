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
            
        st.subheader("Risultati Probabilistici")
        
        somma_verifica = 0.0
        
        # 3. GESTIONE PERMUTAZIONI E STAMPA A SCHERMO
        for key in percentualitag:
            ordinate = list(set(itertools.permutations(list(key), 3)))
            centriordinate = [el1[1] for el1 in ordinate]
            
            # Creiamo una stringa vuota per simulare il comportamento del tuo "print(..., end='  ')"
            riga_output = f"**Famiglia {'-'.join(key)}:** &nbsp;&nbsp;&nbsp; "
            
            for el in ordinate:
                if el[0] <= el[2]:
                    # Calcolo finale
                    prob_finale = percentualitag[key] * centriordinate.count(el[1])
                    somma_verifica += prob_finale
                    
                    # Aggiungiamo i dati alla stringa, convertiti in % con 2 decimali
                    molecola = "".join(el)
                    riga_output += f"`{molecola}: {prob_finale * 100:.2f}%` &nbsp;&nbsp;&nbsp; "
            
            # Stampiamo l'intera riga della famiglia su Streamlit
            st.markdown(riga_output)
            st.divider() # Riga orizzontale per separare visivamente le famiglie
            
        # Un check finale per confermare che la somma faccia effettivamente 100%
        st.info(f"Verifica algebrica totale: **{somma_verifica * 100:.0f}%**")
