# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import BytesIO
import chardet
import os

# --- KONFIGURACJA ---
st.set_page_config(page_title="KAM Rocket Tracker", layout="wide", page_icon="🚀")

ODDZIALY = ["Konin", "Gdańsk", "Olsztyn", "Białystok", "Warszawa", "Rzeszów",
            "Wrocław", "Opole", "Katowice", "Dąbrowa G."]

def get_encoding(file_path):
    if not os.path.exists(file_path): return 'utf-8-sig'
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
        return result['encoding'] if result['encoding'] else 'utf-8-sig'

def load_data():
    file_path = 'kam_data.csv'
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=['Data', 'Oddzial', 'Klient', 'Sprzedaz_LY', 'Sprzedaz_Current', 'Notatki'])
    try:
        enc = get_encoding(file_path)
        return pd.read_csv(file_path, encoding=enc)
    except:
        return pd.read_csv(file_path, encoding='utf-8-sig', errors='ignore')

def save_data(df):
    df.to_csv('kam_data.csv', index=False, encoding='utf-8-sig')

# --- INTERFEJS ---
st.title("🚀 KAM Sales Tracker: Aktywacja")

df = load_data()

# --- PANEL BOCZNY ---
st.sidebar.header("📝 Raportowanie")
mode = st.sidebar.radio("Wybierz tryb:", ["Nowy Klient", "Aktualizacja (Edycja)"])

if mode == "Nowy Klient":
    with st.sidebar.form("new_entry_form"):
        o = st.selectbox("Oddział", ODDZIALY)
        k = st.text_input("Nazwa Nowego Klienta")
        s_ly = st.number_input("Sprzedaż Rok Poprzedni", min_value=0.0)
        s_curr = st.number_input("Sprzedaż Bieżąca", min_value=0.0)
        n = st.text_area("Notatki")
        submit = st.form_submit_button("Dodaj do bazy")
        if submit and k:
            new_row = pd.DataFrame([{'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Oddzial': o,
                                     'Klient': k, 'Sprzedaz_LY': s_ly, 'Sprzedaz_Current': s_curr, 'Notatki': n}])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.sidebar.success(f"Dodano klienta {k}")
            st.rerun()

else: # TRYB EDYCJI
    if not df.empty:
        o_edit = st.sidebar.selectbox("Wybierz Oddział", ODDZIALY)
        klient_list = df[df['Oddzial'] == o_edit]['Klient'].unique()
        if len(klient_list) > 0:
            k_edit = st.sidebar.selectbox("Wybierz Klienta", klient_list)
            target_row = df[(df['Oddzial'] == o_edit) & (df['Klient'] == k_edit)]
            current_val = float(target_row['Sprzedaz_Current'].values[0])
            new_val = st.sidebar.number_input(f"Nowa wartość dla {k_edit}", value=current_val, min_value=0.0)
            new_note = st.sidebar.text_area("Nowa notatka")
            if st.sidebar.button("Zaktualizuj"):
                idx = df[(df['Oddzial'] == o_edit) & (df['Klient'] == k_edit)].index[0]
                df.at[idx, 'Sprzedaz_Current'] = new_val
                df.at[idx, 'Data'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                if new_note:
                    old_note = str(df.at[idx, 'Notatki']) if pd.notna(df.at[idx, 'Notatki']) else ""
                    df.at[idx, 'Notatki'] = f"{old_note} | {new_note}".strip(" | ")
                save_data(df)
                st.sidebar.success("Zaktualizowano!")
                st.rerun()
        else:
            st.sidebar.warning("Brak klientów w tym oddziale.")

# --- WIDOK GŁÓWNY ---
if not df.empty:
    # Metryki
    total_ly = df['Sprzedaz_LY'].sum()
    total_curr = df['Sprzedaz_Current'].sum()
    growth = ((total_curr / total_ly) - 1) * 100 if total_ly > 0 else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Baza (Rok Poprzedni)", f"{total_ly:,.2f} T")
    c2.metric("Sprzedaż Bieżąca", f"{total_curr:,.2f} T", delta=f"{total_curr - total_ly:,.2f} T")
    c3.metric("Wydajność KAM (YoY)", f"{growth:.1f}%")

    # 1. WYKRES GŁÓWNY (Oddziały)
    st.write("### 📊 Wyniki per Oddział (Zagregowane)")
    chart_df = df.groupby('Oddzial')[['Sprzedaz_LY', 'Sprzedaz_Current']].sum().reset_index()
    fig_main = px.bar(chart_df, x='Oddzial', y=['Sprzedaz_LY', 'Sprzedaz_Current'], barmode='group',
                      color_discrete_sequence=['#949fb1', '#2ecc71'], height=400)
    st.plotly_chart(fig_main, use_container_width=True)

    # 2. WYKRESY SZCZEGÓŁOWE (Klienci)
    st.divider()
    st.write("### 🔍 Szczegółowa wydajność klientów w oddziałach")

    # Tworzymy siatkę wykresów (2 kolumny)
    oddzialy_z_danymi = df['Oddzial'].unique()
    cols = st.columns(2)

    for i, oddzial_name in enumerate(sorted(oddzialy_z_danymi)):
        with cols[i % 2]: # Rozdzielamy wykresy naprzemiennie do lewej i prawej kolumny
            st.write(f"**Oddział: {oddzial_name}**")
            sub_df = df[df['Oddzial'] == oddzial_name]
            # Wykres dla konkretnego oddziału z podziałem na klientów
            fig_sub = px.bar(sub_df, x='Klient', y=['Sprzedaz_LY', 'Sprzedaz_Current'], barmode='group',
                             color_discrete_sequence=['#ABB2B9', '#27AE60'], height=300)
            fig_sub.update_layout(margin=dict(l=20, r=20, t=30, b=20), showlegend=False)
            st.plotly_chart(fig_sub, use_container_width=True)

    # Tabela i Eksport
    st.divider()
    st.write("### 📋 Tabela zbiorcza")
    st.dataframe(df.sort_values(by='Data', ascending=False), use_container_width=True)

    excel_file = BytesIO()
    with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button(label="📥 Pobierz Raport Excel", data=excel_file.getvalue(),
                       file_name=f"Raport_KAM_{datetime.now().strftime('%d_%m')}.xlsx")
else:

    st.info("💡 Brak danych. Dodaj klienta w panelu bocznym.")
