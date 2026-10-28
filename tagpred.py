import streamlit as st
import collections
import itertools

st.title("Predittore trigliceridi")

st.subheader("Imposta gli acidi grassi di partenza (Totale: 100%)")
n_tags = st.number_input("Quanti acidi grassi diversi vuoi inserire?", min_value=1, max_value=10, value=3)

input_data = []
somma_perc = 0.0

for i in range(n_tags):
    col1, col2 = st.columns(2)
    with col1:
        default_tag = ["A", "B", "C"][i] if i < 3 else "A"
        tag = st.text_input(f"Molecola {i+1} (1 lettera)", value=default_tag, key=f"tag_{i}").upper()
    with col2:
        default_q = [20, 40, 40][i] if i < 3 else 0
        # Permettiamo anche i decimali
        quantita = st.number_input(f"Percentuale {tag} (%)", min_value=0.0, max_value=100.0, value=float(default_q), step=1.0, key=f"q_{i}")
        somma_perc += quantita
    
    if len(tag) == 1 and quantita > 0:
        input_data.append((tag, quantita))

if round(somma_perc, 2) != 100.00:
    st.error(f"La somma attuale è {somma_perc}%. Aggiusta i valori per arrivare esattamente a 100%.")
else:
    st.success("Composizione iniziale valida (100%).")
    
    if st.button("Calcola Trigliceridi"):
        pass


'''a="A"
b="B"
c="C"
elementi=["A","B","C"]
aperc=17
bperc=43
cperc=40
composizione={a:aperc/100, b:bperc/100, c:cperc/100}
comb=(list(itertools.combinations_with_replacement(elementi, 3)))
percentualitag={}
for elem in comb:
    percentualitag[elem]=round((composizione[elem[0]])*(composizione[elem[1]])*(composizione[elem[2]]),6)


for key in percentualitag:
    ordinate=(list(set(itertools.permutations(list(key), 3))))
    centriordinate=[]
    for el1 in ordinate:
        centriordinate.append(el1[1])
    for el in ordinate:
        if el[0]<=el[2]:
            print(f"{el}: {percentualitag[key]*centriordinate.count(el[1])}", end="  " )
    print()'''
