import pandas as pd
import plotly.express as px
import streamlit as st

# -----------------------------------------------------------------------------
# 1. TRATAMENTO E PREPARAÇÃO DOS DADOS
# -----------------------------------------------------------------------------


def preparar_dados(df):
    # Garante que a coluna de data está no formato datetime
    df['Data'] = pd.to_datetime(df['Data'])

    # Cria coluna para ordenação cronológica real (ex: 2024-09)
    df['AnoMes_Sort'] = df['Data'].dt.strftime('%Y-%m')

    # Cria rótulo visual formatado para exibição (ex: 09/2024)
    df['Mes_Ano'] = df['Data'].dt.strftime('%m/%Y')

    return df


# -----------------------------------------------------------------------------
# 2. GERAÇÃO DA MATRIZ MATRIZ DE DADOS MÊS A MÊS (ORDENAÇÃO CORRETA)
# -----------------------------------------------------------------------------


def gerar_matriz_contratos(df, valor_ou_qtd='qtd'):
    # Ordena primeiro a base de dados pela chave cronológica
    df_ordenado = df.sort_values('AnoMes_Sort')

    campo_valor = 'Qtd_Contratos' if valor_ou_qtd == 'qtd' else 'Valor_Total'
    funcao_agg = 'count' if valor_ou_qtd == 'qtd' else 'sum'

    # Cria a matriz mantendo a ordem das colunas (sort=False)
    matriz = df_ordenado.pivot_table(
        index='Secretaria',
        columns='Mes_Ano',
        values=campo_valor,
        aggfunc=funcao_agg,
        fill_value=0,
        sort=False,  # Preserva a ordem cronológica vinda de 'df_ordenado'
    )

    return matriz


# -----------------------------------------------------------------------------
# 3. GERAÇÃO DO GRÁFICO DE ROSCA (SEM LINHAS CORTADAS)
# -----------------------------------------------------------------------------


def gerar_grafico_locadoras(df, threshold_percent=2.0):
    # Agrupa valores por Locadora
    df_locadoras = (
        df.groupby('Locadora', as_index=False)['Valor_Total']
        .sum()
        .sort_values('Valor_Total', ascending=False)
    )

    # Calcula percentual de cada locadora
    total_custo = df_locadoras['Valor_Total'].sum()
    df_locadoras['Percentual'] = (
        df_locadoras['Valor_Total'] / total_custo
    ) * 100

    # Agrupa locadoras com participação menor que o limite (ex: 2%) em 'Outros'
    locadoras_principais = df_locadoras[
        df_locadoras['Percentual'] >= threshold_percent
    ].copy()
    outros_valor = df_locadoras[
        df_locadoras['Percentual'] < threshold_percent
    ]['Valor_Total'].sum()

    if outros_valor > 0:
        df_outros = pd.DataFrame(
            [{'Locadora': 'Outros', 'Valor_Total': outros_valor}]
        )
        df_final = pd.concat(
            [locadoras_principais[['Locadora', 'Valor_Total']], df_outros],
            ignore_index=True,
        )
    else:
        df_final = locadoras_principais[['Locadora', 'Valor_Total']]

    # Criação do Gráfico no Plotly
    fig = px.pie(
        df_final,
        values='Valor_Total',
        names='Locadora',
        hole=0.4,
        title='Distribuição de Custos por Locadora',
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )

    # Oculta linhas de chamada externas e coloca os rótulos no interior das fatias
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        insidetextorientation='radial',
    )

    fig.update_layout(
        template='plotly_dark',
        margin=dict(t=50, b=20, l=20, r=20),
        legend=dict(orientation='v', yanchor='middle', y=0.5, xanchor='left', x=1.05),
    )

    return fig


# -----------------------------------------------------------------------------
# 4. EXECUÇÃO NO STREAMLIT (EXEMPLO DE INTERFACE)
# -----------------------------------------------------------------------------

# Exemplo de carregamento de dados (substitua pelo seu dataframe real)
# df = pd.read_csv("seus_dados.csv")

st.set_page_config(layout='wide', page_title='Dashboard de Contratos')

# Supondo que 'df' é o seu DataFrame carregado:
if 'df' in locals():
    df = preparar_dados(df)

    st.subheader(' Matrizes de Dados Mês a Mês')
    matriz_qtd = gerar_matriz_contratos(df, valor_ou_qtd='qtd')
    st.dataframe(matriz_qtd, use_container_width=True)

    st.subheader(' Distribuição de Custos')
    fig_rosca = gerar_grafico_locadoras(df, threshold_percent=2.0)
    st.plotly_chart(fig_rosca, use_container_width=True)
