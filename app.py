import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Gestão HT - Multiestufas", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSNNztHYDN-1icWKcCdUZKovBSFspptohMMW-4BnYIANz75MX3ahlQGbUfoFMIsyQ/pub?gid=602841256&single=true&output=csv"

# --- SIDEBAR: FILTROS ---
st.sidebar.header("📅 Período de Análise")
col_d1, col_d2 = st.sidebar.columns(2)
d_inicio = col_d1.date_input("Data Início", datetime(2026, 4, 19))
d_fim = col_d2.date_input("Data Fim", datetime(2026, 4, 26))

col_h1, col_h2 = st.sidebar.columns(2)
h_inicio = col_h1.time_input("Hora Início", time(22, 0))
h_fim = col_h2.time_input("Hora Fim", time(13, 30))

dt_inicio_full = datetime.combine(d_inicio, h_inicio)
dt_fim_full = datetime.combine(d_fim, h_fim)

st.sidebar.divider()
st.sidebar.header("⚙️ Ajustes Desejáveis (Simulador)")
v_aq = st.sidebar.number_input("Aquecimento (min)", 10, 300, 54)
v_ca = st.sidebar.number_input("Carga (min)", 1, 120, 10)
v_de = st.sidebar.number_input("Descarga (min)", 1, 120, 10)
v_pr = st.sidebar.number_input("Preparação (min)", 1, 60, 5)
v_plts = st.sidebar.number_input("Paletes por Carga", 1, 100, 30)

# --- CARREGAMENTO DE DADOS (ESTUFA 1 E 2) ---
@st.cache_data(ttl=60)
def carregar_dados_reais(inicio, fim):
    try:
        df_raw = pd.read_csv(SHEET_URL)
        df_2026 = df_raw.iloc[15523:].copy()
        df_2026['Lote'] = df_2026['Lote'].astype(str).str.strip()
        
        # Criar Data/Hora
        df_2026['Inicio_DT'] = pd.to_datetime(df_2026['Data Inicial Trat.'] + ' ' + df_2026['Hora Inicio Trat.'], dayfirst=True)
        df_2026['Nº Paletes'] = pd.to_numeric(df_2026['Nº Paletes'], errors='coerce').fillna(0)
        df_2026['Data_Dia'] = df_2026['Inicio_DT'].dt.date
        
        # Filtro de Período
        mask = (df_2026['Inicio_DT'] >= inicio) & (df_2026['Inicio_DT'] <= fim)
        df_f = df_2026.loc[mask].copy()
        
        # Separar Estufas
        df_e1 = df_f[df_f['Lote'].str.startswith('1')].copy()
        df_e2 = df_f[df_f['Lote'].str.startswith('2')].copy()
        
        return df_e1, df_e2
    except: return pd.DataFrame(), pd.DataFrame()

df_real_e1, df_real_e2 = carregar_dados_reais(dt_inicio_full, dt_fim_full)

# --- MOTOR DO SIMULADOR ---
def simular(inicio, fim, aq, ca, de, pr, plts):
    ciclos = []
    tempo_atual = inicio
    t_ciclo = aq + ca + de + pr + 52
    while tempo_atual + timedelta(minutes=t_ciclo) <= fim:
        ini = tempo_atual
        f = ini + timedelta(minutes=t_ciclo)
        ciclos.append({"Lote": f"Sim {len(ciclos)+1}", "Início": ini, "Fim": f, "Paletes": plts, "Dia": ini.strftime("%A"), "Data_Dia": ini.date()})
        tempo_atual = f
    return pd.DataFrame(ciclos)

df_sim = simular(dt_inicio_full, dt_fim_full, v_aq, v_ca, v_de, v_pr, v_plts)

# --- INTERFACE ---
st.title("📊 Gestão HT Performance: Estufas 01 & 02")
tab1, tab2, tab3 = st.tabs(["🎯 Simulador (Desejável)", "🏭 Executável (Real)", "⚖️ Comparativo Geral"])

with tab1:
    st.subheader("Planejamento Teórico")
    s1, s2, s3 = st.columns(3)
    s1.metric("Ciclos Totais", len(df_sim))
    s2.metric("Paletes Totais", len(df_sim) * v_plts)
    s3.metric("Tempo Ciclo", f"{v_aq + v_ca + v_de + v_pr + 52} min")
    
    fig_sim = px.timeline(df_sim, x_start="Início", x_end="Fim", y="Lote", color="Dia", 
                         color_discrete_sequence=px.colors.qualitative.Pastel, title="Escalonamento Ideal por Dia")
    fig_sim.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_sim, use_container_width=True)

with tab2:
    st.subheader("Dados Reais da Planilha")
    e1, e2 = st.columns(2)
    with e1:
        st.write("### Estufa 01")
        st.metric("Ciclos E1", len(df_real_e1))
        st.dataframe(df_real_e1[['Lote', 'Data Inicial Trat.', 'Nº Paletes']], use_container_width=True, hide_index=True)
    with e2:
        st.write("### Estufa 02")
        st.metric("Ciclos E2", len(df_real_e2))
        st.dataframe(df_real_e2[['Lote', 'Data Inicial Trat.', 'Nº Paletes']], use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Análise de Tendência e GAP (Estufa 01 vs Desejável)")
    
    # 1. Gráfico de Linhas: Evolução Diária de Ciclos
    st.write("#### Ciclos Realizados Dia a Dia")
    
    # Agrupar ciclos por dia
    resumo_sim = df_sim.groupby('Data_Dia').size().reset_index(name='Desejável')
    resumo_real = df_real_e1.groupby('Data_Dia').size().reset_index(name='Realizado')
    
    # Unir dados para o gráfico de linha
    df_linha = pd.merge(resumo_sim, resumo_real, on='Data_Dia', how='outer').fillna(0)
    df_linha = df_linha.sort_values('Data_Dia')
    
    fig_linha = go.Figure()
    fig_linha.add_trace(go.Scatter(x=df_linha['Data_Dia'], y=df_linha['Desejável'], name='Desejável', line=dict(color='green', width=3, dash='dot')))
    fig_linha.add_trace(go.Scatter(x=df_linha['Data_Dia'], y=df_linha['Realizado'], name='Realizado (E1)', line=dict(color='blue', width=3)))
    
    fig_linha.update_layout(xaxis_title="Data", yaxis_title="Quantidade de Ciclos", hovermode="x unified")
    st.plotly_chart(fig_linha, use_container_width=True)
    
    # 2. Cards de Resumo
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    r_c = len(df_real_e1)
    s_c = len(df_sim)
    r_p = int(df_real_e1['Nº Paletes'].sum())
    s_p = s_c * v_plts
    
    c1.metric("Ciclos (Real E1)", r_c)
    c2.metric("Ciclos (Desejável)", s_c, delta=r_c - s_c)
    c3.metric("Paletes (Real E1)", r_p)
    c4.metric("Paletes (Desejável)", s_p, delta=r_p - s_p)

    # 3. Comparativo Global de Barras
    df_bar = pd.DataFrame({
        "Categoria": ["Real E1", "Real E2", "Desejável"],
        "Paletes": [r_p, int(df_real_e2['Nº Paletes'].sum()), s_p]
    })
    st.plotly_chart(px.bar(df_bar, x="Categoria", y="Paletes", color="Categoria", text_auto=True, title="Volume Total por Categoria"), use_container_width=True)