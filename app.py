import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÃO SUPABASE ---
# No Streamlit Cloud, configure estes valores em Settings > Secrets
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Erro: Configurações do Supabase não encontradas. Verifique os Secrets.")
    st.stop()

st.set_page_config(page_title="Orçamento Doméstico", layout="wide", page_icon="💰")

# --- ESTADO DA SESSÃO ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- FUNÇÕES AUXILIARES ---
def format_moeda(valor):
    """Formata valor numérico para String em Real R$"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- SISTEMA DE AUTENTICAÇÃO ---
def login_form():
    st.title("💰 Meu Orçamento Doméstico")
    col_login, col_vazia = st.columns([1, 1])
    
    with col_login:
        aba1, aba2 = st.tabs(["Entrar", "Criar Conta"])
        
        with aba1:
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password", key="login_pass")
            if st.button("Acessar Sistema"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                    st.session_state.user = res.user
                    st.rerun()
                except Exception:
                    st.error("E-mail ou senha inválidos.")

        with aba2:
            novo_email = st.text_input("Novo E-mail")
            nova_senha = st.text_input("Nova Senha", type="password", key="reg_pass")
            st.info("O cadastro não exige confirmação de e-mail (se configurado no Supabase).")
            if st.button("Cadastrar"):
                try:
                    res = supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                    if res.user:
                        st.success("Conta criada! Você já pode fazer login.")
                except Exception as e:
                    st.error(f"Erro ao cadastrar: {e}")

# --- APLICAÇÃO LOGADA ---
if st.session_state.user is None:
    login_form()
else:
    u_id = st.session_state.user.id
    
    # Barra Lateral
    st.sidebar.title("Menu")
    st.sidebar.write(f"👤 {st.session_state.user.email}")
    menu = st.sidebar.radio("Ir para:", ["Dashboard Mensal", "Lançar Valores", "Cartões de Crédito"])
    
    if st.sidebar.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    # --- ABA: LANÇAMENTOS ---
    if menu == "Lançar Valores":
        st.header("📝 Novo Lançamento")
        
        with st.form("form_lancamento", clear_on_submit=True):
            tipo = st.selectbox("Tipo de Lançamento", ["Receita", "Despesa"])
            desc = st.text_input("Descrição (Ex: Aluguel, Supermercado)")
            valor_total = st.number_input("Valor Total (R$)", min_value=0.0, format="%.2f", step=0.01)
            data_base = st.date_input("Data do Lançamento", date.today())
            
            # Busca cartões do usuário
            res_c = supabase.table("cartoes").select("nome_cartao").eq("user_id", u_id).execute()
            lista_cartoes = [c['nome_cartao'] for c in res_c.data]
            
            cartao_sel = st.selectbox("Forma de Pagamento (Cartão)", ["Dinheiro / Pix"] + lista_cartoes)
            parcelas = st.number_input("Quantidade de Parcelas", min_value=1, value=1)
            
            enviar = st.form_submit_button("Salvar Lançamento")
            
            if enviar:
                if not desc or valor_total <= 0:
                    st.warning("Preencha a descrição e o valor.")
                else:
                    dados_para_inserir = []
                    valor_parcela = valor_total / parcelas
                    
                    for i in range(parcelas):
                        nova_data = data_base + relativedelta(months=i)
                        dados_para_inserir.append({
                            "user_id": u_id,
                            "tipo": tipo,
                            "descricao": desc,
                            "valor": round(float(valor_parcela), 2),
                            "data": str(nova_data),
                            "parcela_atual": i + 1,
                            "total_parcelas": parcelas,
                            "cartao_nome": cartao_sel if cartao_sel != "Dinheiro / Pix" else None
                        })
                    
                    try:
                        supabase.table("lancamentos").insert(dados_para_inserir).execute()
                        st.success(f"Sucesso! {parcelas} parcela(s) lançada(s).")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

    # --- ABA: DASHBOARD ---
    elif menu == "Dashboard Mensal":
        st.header("📊 Resumo de Contas")
        
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            df['data'] = pd.to_datetime(df['data'])
            df['MesAno'] = df['data'].dt.strftime('%m/%Y')
            
            mes_escolhido = st.selectbox("Selecione o Mês para Visualizar", sorted(df['MesAno'].unique(), reverse=True))
            
            df_mes = df[df['MesAno'] == mes_escolhido].copy()
            
            # Métricas
            rec = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
            des = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
            saldo = rec - des
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Receitas", format_moeda(rec))
            c2.metric("Despesas", format_moeda(des))
            c3.metric("Saldo Mensal", format_moeda(saldo))
            
            st.divider()
            st.subheader(f"Detalhes de {mes_escolhido}")
            
            # Preparar tabela para exibição
            df_exibir = df_mes.copy()
            df_exibir['Valor'] = df_exibir['valor'].apply(format_moeda)
            df_exibir = df_exibir.rename(columns={'data': 'Data', 'descricao': 'Descrição', 'tipo': 'Tipo'})
            
            st.dataframe(df_exibir[['Data', 'Descrição', 'Tipo', 'Valor']], use_container_width=True)
            
            # Opção de Edição Simples
            with st.expander("📝 Editar/Excluir Lançamentos"):
                st.write("Para editar, altere diretamente na tabela abaixo (Funcionalidade de visualização)")
                st.info("Dica: Você pode gerenciar os dados diretamente no painel do Supabase ou via código adicional.")
        else:
            st.info("Nenhum lançamento encontrado. Vá em 'Lançar Valores'.")

    # --- ABA: CARTÕES ---
    elif menu == "Cartões de Crédito":
        st.header("💳 Gestão de Cartões")
        
        aba_lista, aba_cad = st.tabs(["Meus Cartões e Parcelas", "Cadastrar Novo Cartão"])
        
        with aba_cad:
            nome_novo_c = st.text_input("Nome do Cartão (Ex: Nubank, Inter)")
            if st.button("Salvar Cartão"):
                if nome_novo_c:
                    supabase.table("cartoes").insert({"user_id": u_id, "nome_cartao": nome_novo_c}).execute()
                    st.success("Cartão cadastrado!")
                    st.rerun()

        with aba_lista:
            st.subheader("Lançamentos por Cartão")
            res_l = supabase.table("lancamentos").select("*").eq("user_id", u_id).neq("cartao_nome", None).execute()
            
            if res_l.data:
                df_c = pd.DataFrame(res_l.data)
                # Formatação solicitada: 1/10
                df_c['Parcela'] = df_c['parcela_atual'].astype(str) + "/" + df_c['total_parcelas'].astype(str)
                df_c['Valor'] = df_c['valor'].apply(format_moeda)
                
                # Filtro por nome do cartão
                lista_nomes = df_c['cartao_nome'].unique()
                cartao_filtro = st.selectbox("Filtrar por Cartão", ["Todos"] + list(lista_nomes))
                
                if cartao_filtro != "Todos":
                    df_c = df_c[df_c['cartao_nome'] == cartao_filtro]
                
                st.table(df_c[['data', 'cartao_nome', 'descricao', 'Parcela', 'Valor']])
            else:
                st.write("Nenhuma despesa parcelada em cartão encontrada.")
