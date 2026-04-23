import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Simulador HT - Estratégico", layout="wide")

st.title("📊 Simulador HT: Planejamento Detalhado")

# --- SIDEBAR: CONFIGURAÇÕES REAIS (CENÁRIO A) ---
st.sidebar.header("⚙️ Cenário Atual (Referência)")
v_aquecimento = st.sidebar.number_input("Aquecimento (min)", 10, 300, 54)
v_carga = st.sidebar.number_input("Carga (min)", 1, 120, 10)
v_descarga = st.sidebar.number_input("Descarga (min)", 1, 120, 10)
v_prep = st.sidebar.number_input("Preparação (min)", 1, 60, 5)

st.sidebar.header("📦 Produtividade")
v_plts_por_carga = st.sidebar.number_input("Paletes por Carga", 1, 100, 30)

st.sidebar.header("📅 Calendário")
v_sem_parada = st.sidebar.toggle("Operação 24/7 (Sem Paradas)", value=False)
h_inicio_dom = st.sidebar.time_input("Início Domingo", time(22, 0))
h_fim_sab = st.sidebar.time_input("Fim Sábado", time(13, 30))

# --- MOTOR DE CÁLCULO ---
def simular(aquec, carga, descarga, prep, plts, sem_parada):
    data_inicio = datetime(2026, 4, 19, h_inicio_dom.hour, h_inicio_dom.minute)
    data_limite = data_inicio + timedelta(days=7)
    ciclos = []
    tempo_atual = data_inicio
    
    while tempo_atual < data_limite:
        if not sem_parada:
            if tempo_atual.weekday() == 5 and tempo_atual.time() >= h_fim_sab:
                tempo_atual = tempo_atual.replace(hour=h_inicio_dom.hour, minute=h_inicio_dom.minute) + timedelta(days=1)
                continue
            if tempo_atual.weekday() == 6 and tempo_atual.time() < h_inicio_dom:
                tempo_atual = tempo_atual.replace(hour=h_inicio_dom.hour, minute=h_inicio_dom.minute)
                continue

        inicio_ciclo = tempo_atual
        # Fluxo: Carga + Prep + Aquec + 32m Tratamento + 20m Resfriamento + Descarga
        fim_ciclo = inicio_ciclo + timedelta(minutes=carga + prep + aquec + 32 + 20 + descarga)

        if not sem_parada and fim_ciclo.weekday() == 5 and fim_ciclo.time() > h_fim_sab:
            tempo_atual = fim_ciclo.replace(hour=h_inicio_dom.hour, minute=h_inicio_dom.minute) + timedelta(days=1)
            continue

        if fim_ciclo > data_limite: break
        
        ciclos.append({
            "Tarefa": f"Carga {len(ciclos)+1}",
            "Início": inicio_ciclo,
            "Fim": fim_ciclo,
            "Paletes": plts,
            "Dia": inicio_ciclo.strftime("%A")
        })
        tempo_atual = fim_ciclo
    return pd.DataFrame(ciclos)

# Gerar dados do Cenário A
df_atual = simular(v_aquecimento, v_carga, v_descarga, v_prep, v_plts_por_carga, v_sem_parada)

# --- UI: DASHBOARD ---
st.subheader("🚀 Performance: Cenário Atual")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de Cargas", len(df_atual))
c2.metric("Total de Paletes", f"{len(df_atual) * v_plts_por_carga} PLTs")
tempo_ciclo_a = v_aquecimento + v_carga + v_descarga + v_prep + 52
c3.metric("Tempo Ciclo", f"{tempo_ciclo_a} min")
c4.metric("Ocupação Semanal", f"{round((len(df_atual) * tempo_ciclo_a) / 100.8, 1)}%")

# --- GRÁFICO DE GANTT ---
st.divider()
st.subheader("📅 Linha do Tempo (Ocupação da Estufa)")
if not df_atual.empty:
    fig = px.timeline(df_atual, x_start="Início", x_end="Fim", y="Tarefa", color="Dia",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_yaxes(autorange="reversed") 
    st.plotly_chart(fig, use_container_width=True)

# --- COMPARAÇÃO DE CENÁRIOS ---
st.divider()
st.subheader("⚖️ Simulação de Melhoria (Cenário B)")
expander = st.expander("Clique para ajustar as variáveis do Cenário B e comparar resultados", expanded=True)

with expander:
    col_v1, col_v2, col_v3, col_v4 = st.columns(4)
    s_aq = col_v1.number_input("Simular Aquecimento", 10, 300, v_aquecimento)
    s_ca = col_v2.number_input("Simular Carga", 1, 120, v_carga)
    s_de = col_v3.number_input("Simular Descarga", 1, 120, v_descarga)
    s_pr = col_v4.number_input("Simular Preparação", 1, 60, v_prep)

    df_sim = simular(s_aq, s_ca, s_de, s_pr, v_plts_por_carga, v_sem_parada)

    # Comparação visual
    diff_cargas = len(df_sim) - len(df_atual)
    diff_plts = (len(df_sim) * v_plts_por_carga) - (len(df_atual) * v_plts_por_carga)
    
    res1, res2 = st.columns(2)
    res1.metric("Cargas no Cenário B", len(df_sim), delta=diff_cargas)
    res2.metric("Paletes no Cenário B", f"{len(df_sim) * v_plts_por_carga} PLTs", delta=diff_plts)

if diff_plts > 0:
    st.success(f"📈 O Cenário B entrega {diff_plts} paletes a mais por semana!")
elif diff_plts < 0:
    st.error(f"📉 O Cenário B reduz a produção em {abs(diff_plts)} paletes.")