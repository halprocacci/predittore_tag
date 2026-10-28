import streamlit as st
import collections
import itertools

a="A"
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
    print()