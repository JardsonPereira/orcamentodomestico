import streamlit as st
import pandas as pd

# 1. Configuração da Página
st.set_page_config(page_title="Orçamento Doméstico", layout="wide")

# 2. Função para carregar dados (Substitua pelo seu caminho de arquivo real)
def carregar_dados():
    # Simulando a criação de um DataFrame para o exemplo
    # No seu caso, seria: df = pd.read_csv("seuarquivo.csv") ou pd.read_excel(...)
    data = {
        'Data': ['2023-10-01', '2023-10-02'],
        'Tipo': ['Despesa', 'Receita'],
        'Categoria': ['Alimentação', 'Salário'],
        'Descrição': ['Mercado', 'Pagamento'],
        'Valor': [150.00, 5000.00]
    }
    df = pd.DataFrame(data)
    
    # --- ATUALIZAÇÃO CRUCIAL PARA CORRIGIR O KEYERROR ---
    # Removemos acentos, espaços extras e deixamos tudo em minúsculo
    # para que o código não quebre por diferenças de digitação no cabeçalho
    df.columns = [
        col.strip().lower()
           .replace('á', 'a').replace('é', 'e').replace('í', 'i')
           .replace('ó', 'o').replace('ú', 'u')
           .replace('ç', 'c').replace('ã', 'a').replace('õ', 'o')
        for col in df.columns
    ]
    return df

# 3. Lógica do App
st.header("📝 Extrato")

df_view = carregar_dados()

# 4. Exibição do Extrato (Linha 139 corrigida)
# Agora usamos os nomes em minúsculo e sem acento, conforme normalizado acima
try:
    # Definimos as colunas que queremos mostrar (ajustadas para a normalização)
    colunas_para_exibir = ['data', 'tipo', 'categoria', 'descricao', 'valor']
    
    # Verificamos se todas existem para evitar erro visual
    colunas_reais = [c for c in colunas_para_exibir if c in df_view.columns]
    
    st.dataframe(
        df_view[colunas_reais], 
        use_container_width=True, 
        hide_index=True
    )

except KeyError as e:
    st.error(f"Erro: A coluna {e} não foi encontrada no banco de dados.")
    st.info("Verifique se o nome das colunas no seu arquivo CSV/Excel está correto.")

# --- Mantenha suas outras atualizações abaixo ---
# (Código de gráficos, filtros ou cadastros que você já tenha feito)
