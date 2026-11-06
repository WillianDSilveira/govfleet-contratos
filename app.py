import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="GovFleet - Gestão de Contratos e Frota",
    page_icon="🚘",
    layout="wide"
)

# Estilização CSS customizada
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# Função para carregar e tratar os dados da planilha
@st.cache_data
def carregar_dados(caminho_arquivo):
    df = pd.read_excel(caminho_arquivo)
    
    # Tratamento dos nomes das Secretarias (Remove pontos e sub-órgãos)
    df['Secretaria_Limpa'] = df['Secretaria/Órgão'].apply(
        lambda x: str(x).strip().lstrip('.').split('/')[0].strip()
    )
    
    # Garantir formato de data e moeda
    df['Início Contrato'] = pd.to_datetime(df['Início Contrato'])
    df['Fim Contrato'] = pd.to_datetime(df['Fim Contrato'])
    df['Valor Mensal'] = pd.to_numeric(df['Valor Mensal'], errors='coerce')
    
    return df

# Função para calcular histórico mês a mês por Secretaria
def calcular_historico_mensal(df):
    inicio_min = df['Início Contrato'].min()
    fim_max = df['Fim Contrato'].max()
    
    # Gerar intervalo mensal
    intervalo_meses = pd.date_range(
        start=inicio_min.replace(day=1),
        end=min(fim_max, pd.to_datetime('2026-10-31')).replace(day=1),
        freq='MS'
    )
    
    registros = []
    for dt in intervalo_meses:
        fim_do_mes = dt + pd.offsets.MonthEnd(1)
        
        # Filtrar contratos vigentes no mês de referência
        df_mes = df[(df['Início Contrato'] <= fim_do_mes) & (df['Fim Contrato'] >= dt)]
        
        grp = df_mes.groupby('Secretaria_Limpa').agg(
            qtd_contratos=('Contrato', 'count'),
            valor_total=('Valor Mensal', 'sum')
        ).reset_index()
        
        grp['Data_Ref'] = dt
        grp['Mes_Ano'] = dt.strftime('%Y-%m')
        grp['Mes_Formatado'] = dt.strftime('%m/%Y')
        registros.append(grp)
        
    if registros:
        return pd.concat(registros, ignore_index=True)
    return pd.DataFrame()

# Título Principal
st.title("🚘 GovFleet — Sistema de Controle de Contratos e Frota")
st.caption("Painel Executivo e Histórico Evolutivo Mês a Mês das Secretarias.")

# Carregamento do arquivo
caminho_excel = 'Contratos vigentes em 31-10-2026.xlsx'

try:
    df = carregar_dados(caminho_excel)
    df_historico = calcular_historico_mensal(df)
except Exception as e:
    st.error(f"Erro ao carregar o arquivo {caminho_excel}: {e}")
    st.stop()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("🔍 Filtros Globais")

secretarias = ["Todas"] + sorted(list(df['Secretaria_Limpa'].unique()))
sec_selecionada = st.sidebar.selectbox("Filtrar por Secretaria", secretarias)

locadoras = ["Todas"] + sorted(list(df['Locadora'].unique()))
loc_selecionada = st.sidebar.selectbox("Filtrar por Locadora", locadoras)

tipos_veiculo = ["Todos"] + sorted(list(df['Tipo Veículo'].unique()))
tipo_selecionado = st.sidebar.selectbox("Filtrar por Tipo de Veículo", tipos_veiculo)

# Aplicando os Filtros aos Dados Atuais
df_filtrado = df.copy()
df_hist_filtrado = df_historico.copy()

if sec_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['Secretaria_Limpa'] == sec_selecionada]
    if not df_hist_filtrado.empty:
        df_hist_filtrado = df_hist_filtrado[df_hist_filtrado['Secretaria_Limpa'] == sec_selecionada]

if loc_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['Locadora'] == loc_selecionada]
if tipo_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Tipo Veículo'] == tipo_selecionado]

# --- PAINEL DE KPIS ---
col1, col2, col3, col4 = st.columns(4)

total_valor = df_filtrado['Valor Mensal'].sum()
total_contratos = len(df_filtrado)
ticket_medio = df_filtrado['Valor Mensal'].mean() if total_contratos > 0 else 0
total_secretarias = df_filtrado['Secretaria_Limpa'].nunique()

col1.metric("Valor Mensal Atual", f"R$ {total_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
col2.metric("Contratos Vigentes", f"{total_contratos}")
col3.metric("Valor Médio / Veículo", f"R$ {ticket_medio:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
col4.metric("Secretarias Ativas", f"{total_secretarias}")

st.markdown("---")

# --- NAVEGAÇÃO POR ABAS ---
tab1, tab2, tab3 = st.tabs(["📊 Visão Geral (Out/2026)", "📈 Evolução Mês a Mês", "📄 Tabela Detalhada de Contratos"])

# === ABA 1: VISÃO GERAL ===
with tab1:
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        resumo_sec = df_filtrado.groupby('Secretaria_Limpa')['Valor Mensal'].sum().reset_index()
        resumo_sec = resumo_sec.sort_values(by='Valor Mensal', ascending=False)
        
        fig_sec = px.bar(
            resumo_sec,
            x='Secretaria_Limpa',
            y='Valor Mensal',
            title="Valor Mensal Total por Secretaria",
            labels={'Secretaria_Limpa': 'Secretaria', 'Valor Mensal': 'Valor (R$)'},
            text_auto='.2s',
            color='Valor Mensal',
            color_continuous_scale='Blues'
        )
        fig_sec.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_sec, use_container_width=True)

    with col_g2:
        resumo_loc = df_filtrado.groupby('Locadora')['Valor Mensal'].agg(['sum', 'count']).reset_index()
        resumo_loc.columns = ['Locadora', 'Valor_Total', 'Quantidade']
        
        fig_loc = px.pie(
            resumo_loc,
            names='Locadora',
            values='Valor_Total',
            title="Distribuição de Custos por Locadora",
            hole=0.4
        )
        st.plotly_chart(fig_loc, use_container_width=True)

# === ABA 2: EVOLUÇÃO MÊS A MÊS ===
with tab2:
    st.subheader("📈 Acompanhamento Histórico Mensal por Secretaria")
    
    if not df_hist_filtrado.empty:
        # Gráfico de Linha do Valor Total ao longo do tempo
        hist_agrupado = df_hist_filtrado.groupby(['Mes_Ano', 'Mes_Formatado', 'Data_Ref'])['valor_total'].sum().reset_index()
        hist_agrupado = hist_agrupado.sort_values(by='Data_Ref')
        
        fig_linha = px.line(
            hist_agrupado,
            x='Mes_Formatado',
            y='valor_total',
            title="Evolução Total do Gasto Mensal com Contratos (R$)",
            markers=True,
            labels={'Mes_Formatado': 'Mês/Ano', 'valor_total': 'Valor Total (R$)'}
        )
        st.plotly_chart(fig_linha, use_container_width=True)
        
        # Tabelas Dinâmicas Mês a Mês
        st.markdown("### 📊 Matrizes de Dados Mês a Mês")
        
        tab_matriz1, tab_matriz2 = st.tabs(["Matriz de Valores (R$)", "Matriz de Quantidade de Contratos"])
        
        with tab_matriz1:
            pivot_valor = df_hist_filtrado.pivot_table(
                index='Secretaria_Limpa',
                columns='Mes_Formatado',
                values='valor_total',
                aggfunc='sum',
                fill_value=0
            )
            st.dataframe(pivot_valor.style.format("R$ {:,.2f}"), use_container_width=True)
            
        with tab_matriz2:
            pivot_qtd = df_hist_filtrado.pivot_table(
                index='Secretaria_Limpa',
                columns='Mes_Formatado',
                values='qtd_contratos',
                aggfunc='sum',
                fill_value=0
            )
            st.dataframe(pivot_qtd.style.format("{:.0f}"), use_container_width=True)
    else:
        st.info("Nenhum dado histórico encontrado para os filtros selecionados.")

# === ABA 3: TABELA GERAL ===
with tab3:
    st.subheader("📄 Cadastro de Contratos Vigentes")
    
    busca = st.text_input("🔎 Pesquisar por Placa, Número de Contrato, Licitação ou Órgão:")
    
    if busca:
        df_filtrado = df_filtrado[
            df_filtrado['Contrato'].astype(str).str.contains(busca, case=False, na=False) |
            df_filtrado['Véiculo Placas'].astype(str).str.contains(busca, case=False, na=False) |
            df_filtrado['Licitação'].astype(str).str.contains(busca, case=False, na=False) |
            df_filtrado['Secretaria/Órgão'].astype(str).str.contains(busca, case=False, na=False)
        ]
        
    df_exibicao = df_filtrado[[
        'Contrato', 'Licitação', 'Secretaria_Limpa', 'Secretaria/Órgão', 
        'Véiculo Placas', 'Tipo Veículo', 'Valor Mensal', 'Início Contrato', 'Fim Contrato', 'Locadora'
    ]].copy()

    df_exibicao['Início Contrato'] = df_exibicao['Início Contrato'].dt.strftime('%d/%m/%Y')
    df_exibicao['Fim Contrato'] = df_exibicao['Fim Contrato'].dt.strftime('%d/%m/%Y')
    df_exibicao['Valor Mensal'] = df_exibicao['Valor Mensal'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

    st.dataframe(df_exibicao, use_container_width=True, height=400)

    st.download_button(
        label="📥 Exportar Dados Filtrados (CSV)",
        data=df_filtrado.to_csv(index=False).encode('utf-8-sig'),
        file_name="contratos_filtrados.csv",
        mime="text/csv"
    )
