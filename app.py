import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="Simulador HT - 24/7", layout="wide")

st.title("🔥 Simulador de Capacidade de Tratamento Térmico (HT)")
st.markdown("Ajuste as variáveis para ver o impacto na produtividade semanal (Segunda a Segunda).")

# --- SIDEBAR: VARIÁVEIS DE SIMULAÇÃO ---
st.sidebar.header("Configuração das Variáveis (Minutos)")

v_aquecimento = st.sidebar.slider("Tempo de Aquecimento (min)", 10, 150, 54)
v_carga = st.sidebar.slider("Tempo de Carga (min)", 5, 60, 10)
v_descarga = st.sidebar.slider("Tempo de Descarga (min)", 5, 60, 10)
v_preparacao = st.sidebar.slider("Preparação da Estufa (min)", 2, 30, 5)

# Constantes do processo
TEMPO_TRATAMENTO_FIXO = 32
TEMPO_CARIMBAR_FIXO = 20  # Resfriamento/Selo

# --- MOTOR DE CÁLCULO ---
def simular_semana(h_inicio, min_aquec, min_carga, min_descarga, min_prep):
    data_atual = h_inicio
    data_limite = h_inicio + timedelta(days=7)
    
    cargas = []
    ciclo = 1
    
    while data_atual + timedelta(minutes=min_carga + min_prep + min_aquec + TEMPO_TRATAMENTO_FIXO) <= data_limite:
        # 1. Início da preparação/carga
        inicio_processo = data_atual
        
        # 2. Início do Tratamento (após carga e prep)
        inicio_tratamento = inicio_processo + timedelta(minutes=min_carga + min_prep)
        
        # 3. Final do Tratamento (Aquecimento + Tratamento + Carimbar)
        final_tratamento = inicio_tratamento + timedelta(minutes=min_aquec + TEMPO_TRATAMENTO_FIXO + TEMPO_CARIMBAR_FIXO)
        
        # 4. Final da Descarga (Liberação da estufa)
        fim_ciclo_total = final_tratamento + timedelta(minutes=min_descarga)
        
        cargas.append({
            "Ciclo": ciclo,
            "Dia": inicio_processo.strftime("%d/%m (%a)"),
            "Início Carga": inicio_processo.strftime("%H:%M"),
            "Início HT": inicio_tratamento.strftime("%H:%M"),
            "Fim HT": final_tratamento.strftime("%H:%M"),
            "Fim Descarga": fim_ciclo_total.strftime("%H:%M"),
            "Tempo Total (min)": (fim_ciclo_total - inicio_processo).total_seconds() / 60
        })
        
        # O próximo ciclo começa imediatamente após a descarga do anterior
        data_atual = fim_ciclo_total
        ciclo += 1
        
    return pd.DataFrame(cargas)

# --- EXECUÇÃO ---
# Início na Segunda-feira às 05:00
data_segunda = datetime(2026, 4, 20, 5, 0) # Data fictícia para uma segunda-feira

df_resultado = simular_semana(data_segunda, v_aquecimento, v_carga, v_descarga, v_preparacao)

# --- DASHBOARD ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total de Lotes/Semana", len(df_resultado))
with col2:
    tempo_ciclo = v_aquecimento + v_carga + v_descarga + v_preparacao + TEMPO_TRATAMENTO_FIXO + TEMPO_CARIMBAR_FIXO
    st.metric("Tempo de Ciclo Total", f"{tempo_ciclo} min")
with col3:
    st.metric("Eficiência da Máquina", f"{round((len(df_resultado)*tempo_ciclo)/100.8, 1)}%") # 100.8 é 168h em % simplificada

st.subheader("📋 Cronograma Detalhado da Operação")
st.dataframe(df_resultado, use_container_width=True)

# Opção para baixar o resultado
csv = df_resultado.to_csv(index=False).encode('utf-8')
st.download_button("Baixar Simulação (CSV)", csv, "simulacao_ht.csv", "text/csv")