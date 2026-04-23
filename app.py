import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time

# Configuração da página
st.set_page_config(page_title="Simulador HT Profissional", layout="wide")

st.title("🚀 Planejador de Produção HT - V2.1")
st.markdown("Simulação de capacidade com regras de fluxo contínuo e paradas de final de semana.")

# --- SIDEBAR: CONFIGURAÇÕES ---
st.sidebar.header("⚙️ Variáveis do Processo")
v_aquecimento = st.sidebar.number_input("Tempo de Aquecimento (min)", 10, 300, 54)
v_carga = st.sidebar.number_input("Tempo de Carga (min)", 1, 120, 10)
v_descarga = st.sidebar.number_input("Tempo de Descarga (min)", 1, 120, 10)
v_prep = st.sidebar.number_input("Preparação Estufa (min)", 1, 60, 5)

st.sidebar.header("📦 Produtividade")
v_plts_por_carga = st.sidebar.number_input("Paletes por Carga", 1, 100, 30)

st.sidebar.header("📅 Calendário Operacional")
# Novo: Opção para rodar sem paradas
v_sem_parada = st.sidebar.toggle("Operação 24/7 (Sem Paradas)", value=False)

h_inicio_domingo = st.sidebar.time_input("Início no Domingo", time(22, 0))
h_fim_sabado = st.sidebar.time_input("Encerramento Sábado", time(13, 30))

# --- MOTOR DE CÁLCULO ---
def simular_producao():
    # Fixamos uma data de início (Domingo 19/04/2026 como referência)
    data_inicio_simulacao = datetime(2026, 4, 19, h_inicio_domingo.hour, h_inicio_domingo.minute)
    data_limite = data_inicio_simulacao + timedelta(days=7)
    
    ciclos = []
    tempo_atual = data_inicio_simulacao
    
    TEMPO_TRATAMENTO = 32
    TEMPO_CARIMBAR = 20 
    
    while tempo_atual < data_limite:
        # Lógica de Parada de Final de Semana (Só processa se o Toggle estiver desligado)
        if not v_sem_parada:
            dia_semana = tempo_atual.weekday() # 5 = Sábado, 6 = Domingo
            hora_atual = tempo_atual.time()
            
            # Se for sábado após o horário de corte, pula para o domingo às 22h
            if dia_semana == 5 and hora_atual >= h_fim_sabado:
                tempo_atual = tempo_atual.replace(hour=h_inicio_domingo.hour, minute=h_inicio_domingo.minute) + timedelta(days=1)
                continue
            
            # Se for domingo antes do horário de início, ajusta para as 22h
            if dia_semana == 6 and hora_atual < h_inicio_domingo:
                tempo_atual = tempo_atual.replace(hour=h_inicio_domingo.hour, minute=h_inicio_domingo.minute)
                continue

        # Cálculo dos tempos do ciclo
        inicio_carga = tempo_atual
        inicio_ht = inicio_carga + timedelta(minutes=v_carga + v_prep)
        fim_ht = inicio_ht + timedelta(minutes=v_aquecimento + TEMPO_TRATAMENTO + TEMPO_CARIMBAR)
        fim_descarga = fim_ht + timedelta(minutes=v_descarga)

        # Se não for 24/7, verifica se o ciclo invade a parada do sábado
        if not v_sem_parada:
            if fim_descarga.weekday() == 5 and fim_descarga.time() > h_fim_sabado:
                # Empurra o início para o próximo ciclo de domingo
                tempo_atual = fim_descarga.replace(hour=h_inicio_domingo.hour, minute=h_inicio_domingo.minute) + timedelta(days=1)
                if tempo_atual >= data_limite: break
                continue

        # Se passou pelas validações, registra a carga
        ciclos.append({
            "Carga": len(ciclos) + 1,
            "Dia da Semana": inicio_carga.strftime("%A"),
            "Data/Hora Início": inicio_carga.strftime("%d/%m %H:%M"),
            "Fim HT": fim_ht.strftime("%H:%M"),
            "Fim Descarga": fim_descarga.strftime("%H:%M"),
            "Paletes": v_plts_por_carga
        })
        
        # Próxima carga começa onde a anterior terminou
        tempo_atual = fim_descarga
        
    return pd.DataFrame(ciclos)

df_res = simular_producao()

# --- INTERFACE DASHBOARD ---
st.divider()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total de Cargas", len(df_res))
with col2:
    st.metric("Total de Paletes", f"{len(df_res) * v_plts_por_carga} PLTs")
with col3:
    tempo_ciclo = v_aquecimento + v_carga + v_descarga + v_prep + 52
    st.metric("Tempo Ciclo", f"{tempo_ciclo} min")
with col4:
    total_horas = (tempo_ciclo * len(df_res)) / 60
    st.metric("Horas em Operação", f"{round(total_horas, 1)}h")

st.subheader("📅 Cronograma de Produção HT")
if not df_res.empty:
    # Tradução simples dos dias para ficar mais visual
    dias_pt = {
        'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira', 'Wednesday': 'Quarta-feira',
        'Thursday': 'Quinta-feira', 'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }
    df_res['Dia da Semana'] = df_res['Dia da Semana'].map(dias_pt)
    st.dataframe(df_res, use_container_width=True)
else:
    st.error("Ajuste os horários: a carga é maior que a janela disponível.")

st.divider()
st.caption("Dica: Use o botão 'Operação 24/7' na lateral para ignorar a parada de sábado e domingo.")